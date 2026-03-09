"""Task for document upload analysis pipeline."""

import asyncio
import uuid

import structlog

from app.celery_app import celery
from app.database import get_sync_db
from app.models.upload import DocumentPage, UploadedDocument

logger = structlog.get_logger()


def _update_status(db, doc, status, error=None):
    doc.status = status
    if error:
        doc.error_message = error
    db.commit()
    db.refresh(doc)


@celery.task(bind=True, max_retries=2)
def analyze_document(self, document_id: str):
    """Process an uploaded document: convert PDF pages, run AI extraction and compliance review.

    Pipeline:
    1. Download file from S3
    2. If PDF: convert to page PNGs, upload each page to S3
    3. Send pages to Claude vision for data extraction
    4. Send pages to Claude vision for compliance review
    5. Store results in uploaded_documents record
    """
    logger.info("document_analysis.started", document_id=document_id)

    db = get_sync_db()
    try:
        doc = db.query(UploadedDocument).filter(UploadedDocument.id == uuid.UUID(document_id)).one()
        _update_status(db, doc, "processing")

        # Step 1: Download file from S3
        from app.services.storage import download_file

        file_bytes = download_file(doc.object_key)
        logger.info("document_analysis.downloaded", document_id=document_id, size=len(file_bytes))

        # Step 2: Check file type and process accordingly
        page_images: list[bytes] = []
        is_pdf = doc.content_type == "application/pdf" or doc.original_filename.lower().endswith(".pdf")
        is_dxf = doc.original_filename.lower().endswith(".dxf")

        if is_dxf:
            from app.services.dxf_parser import parse_dxf

            try:
                floor_plan_data = parse_dxf(file_bytes)
                doc.floor_plan_data = floor_plan_data
                doc.extracted_data = {"floor_plans": floor_plan_data}
                doc.page_count = len(floor_plan_data.get("floor_plans", []))
                _update_status(db, doc, "analyzed")
                logger.info("document_analysis.dxf_parsed", document_id=document_id,
                           floors=len(floor_plan_data.get("floor_plans", [])))
                return {"document_id": document_id, "status": "analyzed", "type": "dxf"}
            except Exception as e:
                logger.warning("document_analysis.dxf_failed", document_id=document_id, error=str(e))
                doc.extracted_data = {"error": f"DXF parsing failed: {e}"}
                _update_status(db, doc, "failed", error=str(e))
                return {"document_id": document_id, "status": "failed"}

        elif is_pdf:
            from app.services.document_processor import process_pdf
            from app.services.storage import upload_file

            pages = process_pdf(file_bytes)
            doc.page_count = len(pages)

            for page_result in pages:
                page_key = f"uploads/{doc.organization_id}/{doc.id}/pages/page_{page_result.page_number}.png"
                upload_file(page_result.png_bytes, page_key, "image/png")

                db_page = DocumentPage(
                    document_id=doc.id,
                    page_number=page_result.page_number,
                    object_key=page_key,
                    width_px=page_result.width,
                    height_px=page_result.height,
                )
                db.add(db_page)
                page_images.append(page_result.png_bytes)

            db.commit()
            logger.info("document_analysis.pages_converted", document_id=document_id, page_count=len(pages))

            # Try vector extraction for floor plan geometry
            from app.services.document_processor import extract_pdf_vectors
            vectors = extract_pdf_vectors(file_bytes)
            if vectors:
                doc.floor_plan_data = {"pages": vectors, "source": "pdf_vectors"}

        elif doc.content_type.startswith("image/"):
            # Single image — use directly
            page_images = [file_bytes]
            doc.page_count = 1
            db.commit()

        else:
            # Non-PDF, non-image — mark as analyzed with no AI extraction
            doc.page_count = 0
            _update_status(db, doc, "analyzed")
            logger.info("document_analysis.skipped_non_visual", document_id=document_id)
            return {"document_id": document_id, "status": "analyzed", "note": "Non-visual file, no AI extraction"}

        if not page_images:
            _update_status(db, doc, "analyzed")
            return {"document_id": document_id, "status": "analyzed", "note": "No pages to analyze"}

        # Limit to first 20 pages to avoid excessive API costs
        analysis_pages = page_images[:20]

        # Step 3: AI data extraction
        from app.config import settings as app_settings

        if app_settings.AI_API_KEY:
            from app.services.document_analyzer import extract_plan_data, review_compliance

            try:
                extracted = asyncio.run(extract_plan_data(analysis_pages, doc.doc_category or "architectural_plan"))
                doc.extracted_data = extracted
                doc.ai_provider = app_settings.AI_PROVIDER
                doc.ai_model = app_settings.AI_MODEL or "claude-sonnet-4-5-20250514"
                db.commit()
                logger.info("document_analysis.extraction_complete", document_id=document_id)
            except Exception as e:
                logger.warning("document_analysis.extraction_failed", document_id=document_id, error=str(e))
                doc.extracted_data = {"error": str(e)}
                db.commit()

            # Step 4: AI compliance review
            try:
                findings = asyncio.run(review_compliance(analysis_pages, doc.extracted_data or {}))
                doc.compliance_findings = findings
                db.commit()
                logger.info("document_analysis.compliance_complete", document_id=document_id)
            except Exception as e:
                logger.warning("document_analysis.compliance_failed", document_id=document_id, error=str(e))
                doc.compliance_findings = {"error": str(e)}
                db.commit()
        else:
            logger.warning("document_analysis.no_api_key", document_id=document_id)
            doc.extracted_data = {"note": "AI_API_KEY not configured — skipped AI analysis"}
            db.commit()

        _update_status(db, doc, "analyzed")
        logger.info("document_analysis.completed", document_id=document_id)
        return {"document_id": document_id, "status": "analyzed"}

    except Exception as e:
        logger.error("document_analysis.failed", document_id=document_id, error=str(e))
        try:
            doc = db.query(UploadedDocument).filter(UploadedDocument.id == uuid.UUID(document_id)).one()
            _update_status(db, doc, "failed", error=str(e))
        except Exception:
            pass
        raise
    finally:
        db.close()
