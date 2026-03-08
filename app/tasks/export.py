import structlog
import uuid

from app.database import get_sync_db
from app.models.export import ExportJob
from app.services.governance import evaluate_export_controls

logger = structlog.get_logger()


def run_export(job_id: str, project_id: str, params: dict | None = None):
    """Generate an export package (PDF, CSV, spreadsheet, 3D).

    TODO: Implement export generation:
    1. Load project and scenario data
    2. Generate report based on export_type
    3. Upload artifact to S3
    4. Update export job with object_key
    """
    logger.info("export.started", job_id=job_id, project_id=project_id)
    db = get_sync_db()

    try:
        export_id = uuid.UUID(job_id)
        job = db.query(ExportJob).filter(ExportJob.id == export_id).one()
        decision = evaluate_export_controls((params or {}).get("source_controls"))
        job.governance_status = decision.governance_status
        job.applied_controls_json = {"sources": decision.applied_controls}

        if decision.decision == "block":
            job.status = "failed"
            job.blocked_reason = decision.blocked_reason
            job.error_message = "Export blocked by governance controls."
            db.commit()
            logger.info("export.blocked", job_id=job_id, project_id=project_id, reason=decision.blocked_reason)
            return {"job_id": job_id, "status": "failed", "reason": decision.blocked_reason}

        if decision.decision == "redact":
            job.status = "completed"
            job.blocked_reason = None
            job.object_key = f"exports/{job_id}/redacted-{(params or {}).get('export_type', 'pdf')}.json"
            db.commit()
            logger.info("export.redacted", job_id=job_id, project_id=project_id)
            return {"job_id": job_id, "status": "completed", "governance_status": "redacted"}

        job.status = "completed"
        job.blocked_reason = None
        job.object_key = f"exports/{job_id}/{(params or {}).get('export_type', 'pdf')}.json"
        db.commit()
        logger.info("export.completed", job_id=job_id, project_id=project_id)
        return {"job_id": job_id, "status": "completed", "governance_status": "approved"}
    except Exception as exc:
        logger.error("export.failed", job_id=job_id, project_id=project_id, error=str(exc))
        try:
            job = db.query(ExportJob).filter(ExportJob.id == export_id).one()
            job.status = "failed"
            job.error_message = str(exc)
            db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()
