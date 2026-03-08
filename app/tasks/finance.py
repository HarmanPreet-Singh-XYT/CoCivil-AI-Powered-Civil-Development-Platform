import structlog
import uuid

from app.database import get_sync_db
from app.models.finance import FinancialRun
from app.models.simulation import LayoutRun, Massing
from app.services.thin_slice_runtime import (
    compute_financial_output,
    resolve_project_context,
    resolve_assumption_set,
    resolve_unit_types,
)
logger = structlog.get_logger()


def run_financial_analysis(job_id: str, scenario_id: str, params: dict | None = None):
    """Run financial pro forma analysis for a scenario.

    TODO: Implement pro forma engine:
    1. Load massing/layout results and assumption set
    2. Calculate revenue projections
    3. Calculate development costs
    4. Compute NOI, cap rate valuation, IRR
    5. Store results and update job status
    """
    logger.info("finance.started", job_id=job_id, scenario_id=scenario_id)
    db = get_sync_db()
    try:
        run = db.query(FinancialRun).filter(FinancialRun.id == job_id).one()
        run.status = "running"
        db.flush()

        assumption_id = uuid.UUID(str(params["assumption_set_id"])) if params and params.get("assumption_set_id") else None
        assumption_set, assumptions = resolve_assumption_set(db, assumption_id or run.assumption_set_id)
        run.assumption_set_id = assumption_set.id

        layout = (
            db.query(LayoutRun)
            .join(Massing, Massing.id == LayoutRun.massing_id)
            .filter(Massing.scenario_run_id == scenario_id, LayoutRun.status == "completed")
            .order_by(LayoutRun.created_at.desc())
            .first()
        )
        if layout is None or not layout.result_json:
            raise ValueError("No completed layout output found for financial analysis")

        massing = db.query(Massing).filter(Massing.id == layout.massing_id).one()
        scenario_context = resolve_project_context(db, scenario_id)
        unit_types = resolve_unit_types(db, jurisdiction_id=scenario_context.parcel.jurisdiction_id)
        output = compute_financial_output(
            layout.result_json,
            massing.summary_json,
            unit_types,
            assumptions,
        )

        run.layout_run_id = layout.id
        run.output_json = output
        run.total_revenue = output["total_revenue"]
        run.total_cost = output["total_cost"]
        run.noi = output["noi"]
        run.valuation = output["valuation"]
        run.residual_land_value = output["residual_land_value"]
        run.status = "completed"

        db.commit()
        logger.info("finance.completed", job_id=job_id, scenario_id=scenario_id, tenure=output["tenure"])
        return {"job_id": job_id, "status": "completed", "output": output}
    except Exception as exc:
        db.rollback()
        try:
            run = db.query(FinancialRun).filter(FinancialRun.id == job_id).one()
            run.status = "failed"
            db.commit()
        except Exception:
            db.rollback()
        logger.error("finance.failed", job_id=job_id, scenario_id=scenario_id, error=str(exc))
        raise
    finally:
        db.close()
