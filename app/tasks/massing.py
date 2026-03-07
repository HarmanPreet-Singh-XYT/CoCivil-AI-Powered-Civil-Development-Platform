import structlog

from app.database import get_sync_db
from app.models.simulation import Massing
from app.services.thin_slice_runtime import (
    compute_massing_summary,
    resolve_project_context,
    resolve_template,
)
from app.worker import celery_app

logger = structlog.get_logger()


@celery_app.task(bind=True, name="app.tasks.massing.run_massing")
def run_massing(self, job_id: str, scenario_id: str, params: dict | None = None):
    """Generate building envelope / massing for a scenario.

    TODO: Implement envelope generation algorithm:
    1. Load parcel geometry and policy constraints
    2. Apply setbacks, height limits, FAR/FSI
    3. Generate candidate envelope geometry
    4. Store results and update job status
    """
    logger.info("massing.started", job_id=job_id, scenario_id=scenario_id)
    db = get_sync_db()
    try:
        massing = db.query(Massing).filter(Massing.id == job_id).one()
        context = resolve_project_context(db, scenario_id)
        template, template_payload = resolve_template(db, massing.template_id)
        summary, compliance = compute_massing_summary(
            context.parcel,
            template_payload,
            overrides=params,
        )

        massing.template_id = template.id
        massing.template_name = template.name
        massing.total_gfa_m2 = summary["estimated_gfa_m2"]
        massing.total_gla_m2 = summary["estimated_gla_m2"]
        massing.storeys = summary["storeys"]
        massing.height_m = summary["height_m"]
        massing.lot_coverage_pct = summary["lot_coverage_pct"]
        massing.fsi = summary["estimated_fsi"]
        massing.summary_json = summary
        massing.compliance_json = compliance

        db.commit()
        logger.info("massing.completed", job_id=job_id, scenario_id=scenario_id, template=template.name)
        return {"job_id": job_id, "status": "completed", "summary": summary}
    except Exception as exc:
        db.rollback()
        logger.error("massing.failed", job_id=job_id, scenario_id=scenario_id, error=str(exc))
        raise
    finally:
        db.close()
