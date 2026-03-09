"""Upload REST endpoints for document upload + AI analysis pipeline."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db_session, get_optional_user
from app.models.upload import DocumentPage, UploadedDocument
from app.schemas.upload import (
    GeneratePlanFromUploadRequest,
    GenerateResponseRequest,
    PageDetail,
    UploadDetail,
    UploadListItem,
    UploadResponse,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/uploads", tags=["uploads"])

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# Dev fallback org/user when no auth token is present
_DEV_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _resolve_user(user: dict | None) -> dict:
    """Return authenticated user or dev fallback."""
    if user:
        return user
    return {"id": _DEV_USER_ID, "organization_id": _DEV_ORG_ID, "role": "admin"}


@router.post("", response_model=UploadResponse, status_code=202)
async def upload_document(
    file: UploadFile,
    db: AsyncSession = Depends(get_db_session),
    user: dict | None = Depends(get_optional_user),
):
    """Upload a file for AI analysis. Returns a job reference to poll for results."""
    user = _resolve_user(user)
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit")
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    from app.services.document_processor import compute_file_hash, get_file_category

    file_hash = compute_file_hash(file_bytes)
    filename = file.filename or "unknown"
    content_type = file.content_type or "application/octet-stream"
    doc_category = get_file_category(filename, content_type)
    doc_id = uuid.uuid4()
    is_dxf = filename.lower().endswith(".dxf")

    # DXF files: parse inline — no S3, no DB needed
    if is_dxf:
        from app.services.dxf_parser import detect_dxf_type, parse_dxf

        try:
            dxf_type = detect_dxf_type(file_bytes)
            if dxf_type == "pipeline":
                from app.services.pipeline_dxf_parser import parse_pipeline_dxf
                data = parse_pipeline_dxf(file_bytes)
                extracted_data = {"pipeline_network": data}
            else:
                data = parse_dxf(file_bytes)
                extracted_data = {"floor_plans": data}
        except Exception as e:
            logger.warning("upload.dxf_parse_failed", error=str(e))
            raise HTTPException(status_code=422, detail=f"DXF parsing failed: {e}")

        return UploadResponse(
            id=doc_id,
            job_id=doc_id,
            status="analyzed",
            original_filename=filename,
            content_type=content_type,
            file_size_bytes=len(file_bytes),
            location=f"{settings.API_V1_PREFIX}/uploads/{doc_id}",
            extracted_data=extracted_data,
        )

    # All other files: upload to S3 and kick off background analysis
    from app.services.storage import ensure_bucket_exists, upload_file

    object_key = f"uploads/{user['organization_id']}/{doc_id}/{filename}"
    ensure_bucket_exists()
    upload_file(file_bytes, object_key, content_type)

    doc = UploadedDocument(
        id=doc_id,
        organization_id=user["organization_id"],
        uploaded_by=user["id"],
        original_filename=filename,
        content_type=content_type,
        file_size_bytes=len(file_bytes),
        object_key=object_key,
        file_hash=file_hash,
        status="uploaded",
        doc_category=doc_category,
    )
    db.add(doc)
    await db.flush()

    from app.tasks.document_analysis import analyze_document

    analyze_document.delay(str(doc_id))

    return UploadResponse(
        id=doc_id,
        job_id=doc_id,
        status="uploaded",
        original_filename=filename,
        content_type=content_type,
        file_size_bytes=len(file_bytes),
        location=f"{settings.API_V1_PREFIX}/uploads/{doc_id}",
    )


@router.get("", response_model=list[UploadListItem])
async def list_uploads(
    db: AsyncSession = Depends(get_db_session),
    user: dict | None = Depends(get_optional_user),
):
    """List all uploads for the current user's organization."""
    user = _resolve_user(user)
    result = await db.execute(
        select(UploadedDocument)
        .where(UploadedDocument.organization_id == user["organization_id"])
        .order_by(UploadedDocument.created_at.desc())
    )
    docs = result.scalars().all()
    return [
        UploadListItem(
            id=d.id,
            original_filename=d.original_filename,
            content_type=d.content_type,
            file_size_bytes=d.file_size_bytes,
            status=d.status,
            doc_category=d.doc_category,
            page_count=d.page_count,
            created_at=d.created_at,
        )
        for d in docs
    ]


@router.get("/{upload_id}", response_model=UploadDetail)
async def get_upload(
    upload_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: dict | None = Depends(get_optional_user),
):
    """Get upload status and results."""
    user = _resolve_user(user)
    doc = await _get_upload_for_org(db, upload_id, user["organization_id"])
    return UploadDetail(
        id=doc.id,
        original_filename=doc.original_filename,
        content_type=doc.content_type,
        file_size_bytes=doc.file_size_bytes,
        status=doc.status,
        doc_category=doc.doc_category,
        page_count=doc.page_count,
        extracted_data=doc.extracted_data,
        compliance_findings=doc.compliance_findings,
        ai_provider=doc.ai_provider,
        ai_model=doc.ai_model,
        error_message=doc.error_message,
        plan_id=doc.plan_id,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.get("/{upload_id}/pages", response_model=list[PageDetail])
async def get_upload_pages(
    upload_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: dict | None = Depends(get_optional_user),
):
    """Get page images as presigned URLs."""
    user = _resolve_user(user)
    doc = await _get_upload_for_org(db, upload_id, user["organization_id"])

    result = await db.execute(
        select(DocumentPage)
        .where(DocumentPage.document_id == doc.id)
        .order_by(DocumentPage.page_number)
    )
    pages = result.scalars().all()

    from app.services.storage import generate_presigned_url

    return [
        PageDetail(
            page_number=p.page_number,
            url=generate_presigned_url(p.object_key),
            width_px=p.width_px,
            height_px=p.height_px,
            extracted_text=p.extracted_text,
        )
        for p in pages
    ]


@router.get("/{upload_id}/analysis")
async def get_upload_analysis(
    upload_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: dict | None = Depends(get_optional_user),
):
    """Get extracted data and compliance findings."""
    doc = await _get_upload_for_org(db, upload_id, user["organization_id"])
    return {
        "extracted_data": doc.extracted_data,
        "compliance_findings": doc.compliance_findings,
        "status": doc.status,
        "doc_category": doc.doc_category,
    }


@router.post("/{upload_id}/generate-plan", status_code=202)
async def generate_plan_from_upload(
    upload_id: uuid.UUID,
    body: GeneratePlanFromUploadRequest | None = None,
    db: AsyncSession = Depends(get_db_session),
    user: dict | None = Depends(get_optional_user),
):
    """Feed extracted data into the existing plan generation pipeline."""
    user = _resolve_user(user)
    doc = await _get_upload_for_org(db, upload_id, user["organization_id"])

    if doc.status != "analyzed":
        raise HTTPException(status_code=400, detail="Document must be fully analyzed before generating a plan")
    if not doc.extracted_data:
        raise HTTPException(status_code=400, detail="No extracted data available for plan generation")

    from app.models.plan import DevelopmentPlan
    from app.tasks.plan import run_plan_generation

    # Map extracted data to parsed_parameters format
    extracted = doc.extracted_data
    dims = extracted.get("dimensions", {})
    building = extracted.get("building", {})

    parsed_parameters = {
        "status": "extracted_from_upload",
        "address": extracted.get("address"),
        "project_name": (body.project_name if body else None) or extracted.get("project_name"),
        "development_type": building.get("building_type", "mixed_use"),
        "building_type": building.get("building_type"),
        "storeys": building.get("storeys"),
        "height_m": building.get("height_m"),
        "unit_count": building.get("unit_count"),
        "gfa_m2": building.get("gfa_m2"),
        "lot_area_m2": dims.get("lot_area_m2"),
        "lot_frontage_m": dims.get("lot_frontage_m"),
        "lot_depth_m": dims.get("lot_depth_m"),
        "setback_front_m": dims.get("setback_front_m"),
        "setback_rear_m": dims.get("setback_rear_m"),
        "setback_side_m": dims.get("setback_side_m"),
        "confidence": 0.9,
        "source": "document_upload",
        "upload_id": str(upload_id),
    }
    # Remove None values
    parsed_parameters = {k: v for k, v in parsed_parameters.items() if v is not None}

    query = f"Development plan based on uploaded document: {doc.original_filename}"
    plan = DevelopmentPlan(
        organization_id=user["organization_id"],
        created_by=user["id"],
        original_query=query,
        parsed_parameters=parsed_parameters,
        status="draft",
    )
    db.add(plan)
    await db.flush()

    # Link upload to plan
    doc.plan_id = plan.id
    await db.flush()

    run_plan_generation.delay(str(plan.id), query)

    return {
        "plan_id": plan.id,
        "job_id": plan.id,
        "status": "accepted",
        "location": f"{settings.API_V1_PREFIX}/plans/{plan.id}",
    }


@router.post("/{upload_id}/generate-response", status_code=202)
async def generate_response_from_upload(
    upload_id: uuid.UUID,
    body: GenerateResponseRequest | None = None,
    db: AsyncSession = Depends(get_db_session),
    user: dict | None = Depends(get_optional_user),
):
    """Generate a response document from compliance findings."""
    user = _resolve_user(user)
    doc = await _get_upload_for_org(db, upload_id, user["organization_id"])

    if doc.status != "analyzed":
        raise HTTPException(status_code=400, detail="Document must be fully analyzed before generating a response")

    response_type = body.response_type if body else "correction_response"

    from app.services.submission.context_builder import build_upload_context
    from app.services.submission.templates import DOCUMENT_TEMPLATES, SAFETY_PREAMBLE

    template = DOCUMENT_TEMPLATES.get(response_type)
    if not template:
        raise HTTPException(status_code=400, detail=f"Unknown response type: {response_type}")

    context = build_upload_context(doc.extracted_data, doc.compliance_findings, doc.original_filename)

    # Build document content from context
    content_parts = [f"> {SAFETY_PREAMBLE}\n\n---\n\n"]
    content_parts.append(f"# {template.get('title', response_type.replace('_', ' ').title())}\n\n")
    content_parts.append(f"**Source Document**: {doc.original_filename}\n\n")

    if response_type == "correction_response":
        content_parts.append("## Response to Corrections\n\n")
        issues = (doc.compliance_findings or {}).get("issues", [])
        if issues:
            for i, issue in enumerate(issues, 1):
                content_parts.append(f"### Item {i}: {issue.get('category', 'General')}\n\n")
                content_parts.append(f"**Issue**: {issue.get('description', 'N/A')}\n\n")
                content_parts.append(f"**Code Reference**: {issue.get('code_reference', 'N/A')}\n\n")
                content_parts.append(f"**Response**: {issue.get('suggestion', 'To be addressed by design team.')}\n\n")
        else:
            content_parts.append("No specific corrections identified.\n\n")

    elif response_type == "compliance_review_report":
        content_parts.append("## Compliance Review Summary\n\n")
        assessment = (doc.compliance_findings or {}).get("overall_assessment", "No assessment available.")
        content_parts.append(f"{assessment}\n\n")
        content_parts.append("## Detailed Findings\n\n")
        issues = (doc.compliance_findings or {}).get("issues", [])
        for issue in issues:
            severity = issue.get("severity", "info").upper()
            content_parts.append(f"- **[{severity}]** {issue.get('description', 'N/A')} ")
            content_parts.append(f"({issue.get('code_reference', 'N/A')})\n")

    elif response_type == "variance_justification":
        content_parts.append("## Variance Justification\n\n")
        content_parts.append(context.get("extracted_summary", "No extracted data available."))
        content_parts.append("\n\n## Required Variances\n\n")
        issues = (doc.compliance_findings or {}).get("issues", [])
        variance_issues = [i for i in issues if i.get("severity") in ("critical", "major")]
        if variance_issues:
            for issue in variance_issues:
                content_parts.append(f"### {issue.get('category', 'General').title()}\n\n")
                content_parts.append(f"**Provision**: {issue.get('code_reference', 'N/A')}\n\n")
                content_parts.append(f"**Variance Requested**: {issue.get('description', 'N/A')}\n\n")
                content_parts.append(f"**Justification**: {issue.get('suggestion', 'Justification to be provided.')}\n\n")
        else:
            content_parts.append("No major variances identified requiring justification.\n\n")

    content = "".join(content_parts)

    return {
        "response_type": response_type,
        "content": content,
        "source_document": doc.original_filename,
        "upload_id": str(upload_id),
    }


async def _get_upload_for_org(
    db: AsyncSession, upload_id: uuid.UUID, organization_id: uuid.UUID
) -> UploadedDocument:
    result = await db.execute(
        select(UploadedDocument).where(
            UploadedDocument.id == upload_id,
            UploadedDocument.organization_id == organization_id,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Upload not found")
    return doc
