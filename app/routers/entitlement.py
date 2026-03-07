import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.dependencies import get_current_user, get_db_session, get_optional_idempotency_key
from app.models.entitlement import EntitlementResult, PrecedentMatch, PrecedentSearch
from app.models.tenant import ScenarioRun
from app.schemas.common import JobAccepted
from app.schemas.entitlement import (
    EntitlementRunRequest,
    EntitlementRunResponse,
    PrecedentSearchRequest,
    PrecedentSearchResponse,
)
from app.tasks.entitlement import run_entitlement_check, run_precedent_search

router = APIRouter()


@router.post(
    "/scenarios/{scenario_id}/entitlement-runs", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED
)
async def create_entitlement_run(
    scenario_id: uuid.UUID,
    body: EntitlementRunRequest,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_optional_idempotency_key),
):
    scenario = await db.get(ScenarioRun, scenario_id)
    result = EntitlementResult(
        scenario_run_id=scenario_id,
        snapshot_manifest_id=scenario.snapshot_manifest_id if scenario else None,
        overall_compliance="pending",
        result_json={},
    )
    db.add(result)
    await db.flush()
    await db.refresh(result)

    run_entitlement_check.delay(str(result.id), str(scenario_id), body.parameters)

    return JobAccepted(
        job_id=result.id,
        status="accepted",
        location=f"{settings.API_V1_PREFIX}/entitlement-runs/{result.id}",
    )


@router.get("/entitlement-runs/{run_id}", response_model=EntitlementRunResponse)
async def get_entitlement_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(select(EntitlementResult).where(EntitlementResult.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Entitlement run not found")
    return run


@router.post(
    "/scenarios/{scenario_id}/precedent-searches", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED
)
async def create_precedent_search(
    scenario_id: uuid.UUID,
    body: PrecedentSearchRequest,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_optional_idempotency_key),
):
    scenario = await db.get(ScenarioRun, scenario_id)
    search = PrecedentSearch(
        scenario_run_id=scenario_id,
        snapshot_manifest_id=scenario.snapshot_manifest_id if scenario else None,
        search_params_json=body.model_dump(),
        status="pending",
    )
    db.add(search)
    await db.flush()
    await db.refresh(search)

    run_precedent_search.delay(str(search.id), str(scenario_id), body.model_dump())

    return JobAccepted(
        job_id=search.id,
        status="accepted",
        location=f"{settings.API_V1_PREFIX}/precedent-searches/{search.id}",
    )


@router.get("/precedent-searches/{search_id}", response_model=PrecedentSearchResponse)
async def get_precedent_search(
    search_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
        select(PrecedentSearch)
        .options(selectinload(PrecedentSearch.matches).selectinload(PrecedentMatch.application))
        .where(PrecedentSearch.id == search_id)
    )
    search = result.scalar_one_or_none()
    if not search:
        raise HTTPException(status_code=404, detail="Precedent search not found")
    return search
