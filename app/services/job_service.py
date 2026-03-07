import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entitlement import EntitlementResult, PrecedentSearch
from app.models.export import ExportJob
from app.models.finance import FinancialRun
from app.models.ingestion import IngestionJob
from app.models.plan import DevelopmentPlan
from app.models.simulation import LayoutRun
from app.models.tenant import ScenarioRun
from app.schemas.job import JobStatusResponse

JOB_TABLES = [
    ("scenario_run", ScenarioRun),
    ("layout_run", LayoutRun),
    ("financial_run", FinancialRun),
    ("entitlement_result", EntitlementResult),
    ("precedent_search", PrecedentSearch),
    ("export_job", ExportJob),
    ("ingestion_job", IngestionJob),
    ("development_plan", DevelopmentPlan),
]


async def get_job_status(db: AsyncSession, job_id: uuid.UUID) -> JobStatusResponse | None:
    """Query across all job-like tables to find a job by ID."""
    for job_type, model in JOB_TABLES:
        result = await db.execute(select(model).where(model.id == job_id))
        row = result.scalar_one_or_none()
        if row:
            return JobStatusResponse(
                job_id=row.id,
                job_type=job_type,
                status=row.status,
                started_at=getattr(row, "started_at", None),
                completed_at=getattr(row, "completed_at", None),
                result=(
                    getattr(row, "result_json", None)
                    or getattr(row, "output_json", None)
                    or getattr(row, "results_json", None)
                    or getattr(row, "applied_controls_json", None)
                ),
                error_message=getattr(row, "error_message", None),
            )
    return None
