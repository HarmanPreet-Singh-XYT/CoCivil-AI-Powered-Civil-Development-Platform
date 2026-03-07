import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_user, get_db_session, get_optional_idempotency_key
from app.models.export import ExportJob
from app.schemas.common import JobAccepted
from app.schemas.export import ExportRequest, ExportResponse
from app.tasks.export import run_export

router = APIRouter()


@router.post("/exports", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_export(
    body: ExportRequest,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_optional_idempotency_key),
):
    export = ExportJob(
        project_id=body.project_id,
        scenario_run_id=body.scenario_run_id,
        export_type=body.export_type,
        status="pending",
    )
    db.add(export)
    await db.flush()
    await db.refresh(export)

    run_export.delay(
        str(export.id),
        str(body.project_id),
        {"export_type": body.export_type, "source_controls": body.source_controls or []},
    )

    return JobAccepted(
        job_id=export.id,
        status="accepted",
        location=f"{settings.API_V1_PREFIX}/exports/{export.id}",
    )


@router.get("/exports/{export_id}", response_model=ExportResponse)
async def get_export(
    export_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(select(ExportJob).where(ExportJob.id == export_id))
    export = result.scalar_one_or_none()
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")
    return export
