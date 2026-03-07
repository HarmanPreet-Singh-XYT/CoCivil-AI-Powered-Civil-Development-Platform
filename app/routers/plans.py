import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.dependencies import get_current_user, get_db_session
from app.models.plan import DevelopmentPlan, SubmissionDocument
from app.schemas.common import JobAccepted
from app.schemas.plan import (
    PlanClarifyResponse,
    PlanGenerateRequest,
    PlanListResponse,
    PlanResponse,
    ReviewActionRequest,
    ReviewSubmitRequest,
    SubmissionDocumentResponse,
)
from app.services.submission.review import (
    approve_document,
    reject_document,
    submit_for_review,
)
from app.tasks.plan import run_plan_generation

router = APIRouter()


@router.post("/plans/generate", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def generate_plan(
    body: PlanGenerateRequest,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
):
    """Submit a natural language development query to generate a full plan.

    The system will:
    1. Parse your query into structured development parameters
    2. Look up the parcel and applicable zoning
    3. Generate building massing within policy constraints
    4. Optimize the unit mix
    5. Run financial pro forma
    6. Check entitlement compliance
    7. Search for precedent applications
    8. Generate government submission documents
    """
    plan = DevelopmentPlan(
        organization_id=user["organization_id"],
        created_by=user["id"],
        original_query=body.query,
        status="pending",
    )
    db.add(plan)
    await db.flush()
    await db.refresh(plan)

    run_plan_generation.delay(str(plan.id), body.query, body.auto_run)

    return JobAccepted(
        job_id=plan.id,
        status="accepted",
        location=f"{settings.API_V1_PREFIX}/plans/{plan.id}",
    )


@router.get("/plans", response_model=list[PlanListResponse])
async def list_plans(
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(DevelopmentPlan)
        .where(DevelopmentPlan.organization_id == user["organization_id"])
        .order_by(DevelopmentPlan.created_at.desc())
    )
    return result.scalars().all()


@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(DevelopmentPlan)
        .options(selectinload(DevelopmentPlan.documents))
        .where(
            DevelopmentPlan.id == plan_id,
            DevelopmentPlan.organization_id == user["organization_id"],
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.post("/plans/{plan_id}/clarify", response_model=PlanResponse)
async def clarify_plan(
    plan_id: uuid.UUID,
    body: PlanClarifyResponse,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
):
    """Provide answers to clarification questions and resume pipeline."""
    result = await db.execute(
        select(DevelopmentPlan)
        .options(selectinload(DevelopmentPlan.documents))
        .where(
            DevelopmentPlan.id == plan_id,
            DevelopmentPlan.organization_id == user["organization_id"],
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.status != "needs_clarification":
        raise HTTPException(status_code=400, detail=f"Plan is not awaiting clarification (status: {plan.status})")

    # Merge answers into parsed parameters
    params = plan.parsed_parameters or {}
    params["user_clarifications"] = body.answers
    plan.parsed_parameters = params
    plan.status = "parsed"
    await db.flush()
    await db.refresh(plan)

    # Resume pipeline
    run_plan_generation.delay(str(plan.id), plan.original_query, True)

    return plan


@router.get("/plans/{plan_id}/documents", response_model=list[SubmissionDocumentResponse])
async def list_plan_documents(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(SubmissionDocument)
        .join(DevelopmentPlan)
        .where(
            SubmissionDocument.plan_id == plan_id,
            DevelopmentPlan.organization_id == user["organization_id"],
        )
        .order_by(SubmissionDocument.sort_order)
    )
    return result.scalars().all()


@router.get("/plans/{plan_id}/documents/{doc_id}", response_model=SubmissionDocumentResponse)
async def get_plan_document(
    plan_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(SubmissionDocument)
        .join(DevelopmentPlan)
        .where(
            SubmissionDocument.id == doc_id,
            SubmissionDocument.plan_id == plan_id,
            DevelopmentPlan.organization_id == user["organization_id"],
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post(
    "/plans/{plan_id}/documents/{doc_id}/submit-review",
    response_model=SubmissionDocumentResponse,
)
async def submit_document_for_review(
    plan_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
):
    """Submit a generated document for human review."""
    # Verify ownership
    plan_result = await db.execute(
        select(DevelopmentPlan).where(
            DevelopmentPlan.id == plan_id,
            DevelopmentPlan.organization_id == user["organization_id"],
        )
    )
    if not plan_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Plan not found")

    try:
        doc = await submit_for_review(db, doc_id, user["id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return doc


@router.post(
    "/plans/{plan_id}/documents/{doc_id}/approve",
    response_model=SubmissionDocumentResponse,
)
async def approve_plan_document(
    plan_id: uuid.UUID,
    doc_id: uuid.UUID,
    body: ReviewActionRequest,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
):
    """Approve a document after review."""
    plan_result = await db.execute(
        select(DevelopmentPlan).where(
            DevelopmentPlan.id == plan_id,
            DevelopmentPlan.organization_id == user["organization_id"],
        )
    )
    if not plan_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Plan not found")

    try:
        doc = await approve_document(db, doc_id, user["id"], body.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return doc


@router.post(
    "/plans/{plan_id}/documents/{doc_id}/reject",
    response_model=SubmissionDocumentResponse,
)
async def reject_plan_document(
    plan_id: uuid.UUID,
    doc_id: uuid.UUID,
    body: ReviewActionRequest,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
):
    """Reject a document — returns it to draft for revision."""
    plan_result = await db.execute(
        select(DevelopmentPlan).where(
            DevelopmentPlan.id == plan_id,
            DevelopmentPlan.organization_id == user["organization_id"],
        )
    )
    if not plan_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Plan not found")

    try:
        doc = await reject_document(db, doc_id, user["id"], body.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return doc
