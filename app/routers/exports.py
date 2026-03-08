import threading
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_user, get_db_session, get_optional_idempotency_key
from app.models.export import ExportJob
from app.schemas.common import JobAccepted
from app.schemas.export import ExportRequest, ExportResponse
from app.services.access_control import get_export_job_for_org, get_project_for_org, get_scenario_for_org
from app.services.idempotency import cache_response, get_cached_response
from app.tasks.export import run_export

router = APIRouter()


@router.post("/exports", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_export(
    body: ExportRequest,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_optional_idempotency_key),
):
    cached_response = await get_cached_response(idempotency_key, JobAccepted)
    if cached_response is not None:
        return cached_response

    await get_project_for_org(db, body.project_id, user["organization_id"])
    if body.scenario_run_id is not None:
        scenario = await get_scenario_for_org(db, body.scenario_run_id, user["organization_id"])
        if scenario.project_id != body.project_id:
            raise HTTPException(status_code=400, detail="Scenario does not belong to project")
    export = ExportJob(
        project_id=body.project_id,
        scenario_run_id=body.scenario_run_id,
        export_type=body.export_type,
        status="pending",
    )
    db.add(export)
    await db.flush()
    await db.refresh(export)
    await db.commit()

    threading.Thread(
        target=run_export,
        args=(
            str(export.id),
            str(body.project_id),
            {"export_type": body.export_type, "source_controls": body.source_controls or []},
        ),
        daemon=True,
    ).start()

    response = JobAccepted(
        job_id=export.id,
        status="accepted",
        location=f"{settings.API_V1_PREFIX}/exports/{export.id}",
    )
    await cache_response(idempotency_key, response)
    return response


@router.get("/exports/{export_id}", response_model=ExportResponse)
async def get_export(
    export_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
):
    return await get_export_job_for_org(db, export_id, user["organization_id"])
