import structlog
import uuid

from app.celery_app import celery
from app.database import get_sync_db
from app.models.simulation import LayoutRun, Massing
from app.services.thin_slice_runtime import (
    compute_layout_result,
    resolve_project_context,
    resolve_template,
    resolve_unit_types,
)
logger = structlog.get_logger()


@celery.task(bind=True, max_retries=2)
def run_layout(self, job_id: str, massing_id: str, params: dict | None = None):
    """Run unit mix / layout optimization for a massing.

    TODO: Implement LP-based layout optimization (OR-Tools):
    1. Load massing geometry and floor areas
    2. Load unit type library
    3. Optimize unit allocation per objective
    4. Store results and update job status
    """
    logger.info("layout.started", job_id=job_id, massing_id=massing_id)
    db = get_sync_db()
    try:
        layout = db.query(LayoutRun).filter(LayoutRun.id == job_id).one()
        massing = db.query(Massing).filter(Massing.id == massing_id).one()
        layout.status = "running"
        db.flush()

        context = resolve_project_context(db, str(massing.scenario_run_id))
        template_id = uuid.UUID(str(params["template_id"])) if params and params.get("template_id") else None
        template, template_payload = resolve_template(db, template_id or massing.template_id)
        unit_type_ids = None
        if params and params.get("unit_type_ids"):
            unit_type_ids = [uuid.UUID(str(unit_type_id)) for unit_type_id in params["unit_type_ids"]]
        overrides = dict(params or {})
        overrides.setdefault("objective", layout.objective)
        unit_types = resolve_unit_types(db, unit_type_ids=unit_type_ids, jurisdiction_id=context.parcel.jurisdiction_id)

        result = compute_layout_result(
            massing.summary_json,
            template_payload,
            unit_types,
            overrides=overrides,
        )

        layout.constraints_json = {
            "requested": overrides,
            "template": template.name,
            "unit_type_ids": [str(unit_type.id) for unit_type in unit_types],
        }
        layout.result_json = result
        layout.total_units = result["total_units"]
        layout.total_area_m2 = result["allocated_area_m2"]
        layout.status = "completed"

        db.commit()
        logger.info("layout.completed", job_id=job_id, massing_id=massing_id, total_units=result["total_units"])
        return {"job_id": job_id, "status": "completed", "result": result}
    except Exception as exc:
        db.rollback()
        try:
            layout = db.query(LayoutRun).filter(LayoutRun.id == job_id).one()
            layout.status = "failed"
            db.commit()
        except Exception:
            db.rollback()
        logger.error("layout.failed", job_id=job_id, massing_id=massing_id, error=str(exc))
        raise
    finally:
        db.close()
