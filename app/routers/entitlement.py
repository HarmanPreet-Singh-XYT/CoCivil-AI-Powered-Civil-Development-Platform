import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_user, get_db_session, get_optional_idempotency_key
from app.models.entitlement import EntitlementResult, PrecedentSearch
from app.schemas.common import JobAccepted
from app.schemas.entitlement import (
    EntitlementRunRequest,
    EntitlementRunResponse,
    PrecedentSearchRequest,
    PrecedentSearchResponse,
)
from app.services.access_control import (
    get_entitlement_result_for_org,
    get_precedent_search_for_org,
    get_scenario_for_org,
)
from app.services.idempotency import cache_response, get_cached_response
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
    cached_response = await get_cached_response(idempotency_key, JobAccepted)
    if cached_response is not None:
        return cached_response

    scenario = await get_scenario_for_org(db, scenario_id, user["organization_id"])
    result = EntitlementResult(
        scenario_run_id=scenario_id,
        snapshot_manifest_id=scenario.snapshot_manifest_id if scenario else None,
        overall_compliance="pending",
        result_json={},
    )
    db.add(result)
    await db.flush()
    await db.refresh(result)
    await db.commit()

    run_entitlement_check.delay(str(result.id), str(scenario_id), body.parameters)

    response = JobAccepted(
        job_id=result.id,
        status="accepted",
        location=f"{settings.API_V1_PREFIX}/entitlement-runs/{result.id}",
    )
    await cache_response(idempotency_key, response)
    return response


@router.get("/entitlement-runs/{run_id}", response_model=EntitlementRunResponse)
async def get_entitlement_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
):
    return await get_entitlement_result_for_org(db, run_id, user["organization_id"])


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
    cached_response = await get_cached_response(idempotency_key, JobAccepted)
    if cached_response is not None:
        return cached_response

    scenario = await get_scenario_for_org(db, scenario_id, user["organization_id"])
    search = PrecedentSearch(
        scenario_run_id=scenario_id,
        snapshot_manifest_id=scenario.snapshot_manifest_id if scenario else None,
        search_params_json=body.model_dump(),
        status="pending",
    )
    db.add(search)
    await db.flush()
    await db.refresh(search)
    await db.commit()

    run_precedent_search.delay(str(search.id), str(scenario_id), body.model_dump())

    response = JobAccepted(
        job_id=search.id,
        status="accepted",
        location=f"{settings.API_V1_PREFIX}/precedent-searches/{search.id}",
    )
    await cache_response(idempotency_key, response)
    return response


@router.get("/precedent-searches/{search_id}", response_model=PrecedentSearchResponse)
async def get_precedent_search(
    search_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
):
    return await get_precedent_search_for_org(db, search_id, user["organization_id"], load_matches=True)
