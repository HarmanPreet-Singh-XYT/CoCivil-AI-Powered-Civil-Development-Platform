import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_user, get_db_session, get_optional_idempotency_key
from app.models.finance import FinancialAssumptionSet, FinancialRun
from app.schemas.common import JobAccepted
from app.schemas.finance import (
    FinancialAssumptionSetReferenceResponse,
    FinancialRunRequest,
    FinancialRunResponse,
)
from app.services.access_control import get_financial_run_for_org, get_scenario_for_org
from app.services.idempotency import cache_response, get_cached_response
from app.services.thin_slice_runtime import ensure_reference_data, validate_financial_assumptions
from app.tasks.finance import run_financial_analysis

router = APIRouter()


def _serialize_assumption_set(
    assumption_set: FinancialAssumptionSet | None,
) -> FinancialAssumptionSetReferenceResponse | None:
    if assumption_set is None:
        return None
    return FinancialAssumptionSetReferenceResponse.model_validate(
        {
            "id": assumption_set.id,
            "organization_id": assumption_set.organization_id,
            "name": assumption_set.name,
            "is_default": assumption_set.is_default,
            "assumptions_json": validate_financial_assumptions(assumption_set),
            "created_at": assumption_set.created_at,
        }
    )


def _serialize_financial_run(run: FinancialRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "scenario_run_id": run.scenario_run_id,
        "assumption_set_id": run.assumption_set_id,
        "layout_run_id": run.layout_run_id,
        "status": run.status,
        "total_revenue": run.total_revenue,
        "total_cost": run.total_cost,
        "noi": run.noi,
        "valuation": run.valuation,
        "residual_land_value": run.residual_land_value,
        "irr_pct": run.irr_pct,
        "output_json": run.output_json or None,
        "assumption_set": _serialize_assumption_set(run.assumption_set),
        "created_at": run.created_at,
    }


@router.post(
    "/scenarios/{scenario_id}/financial-runs", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED
)
async def create_financial_run(
    scenario_id: uuid.UUID,
    body: FinancialRunRequest,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_optional_idempotency_key),
):
    cached_response = await get_cached_response(idempotency_key, JobAccepted)
    if cached_response is not None:
        return cached_response

    await get_scenario_for_org(db, scenario_id, user["organization_id"])
    if body.assumption_set_id is not None:
        result = await db.execute(
            select(FinancialAssumptionSet).where(FinancialAssumptionSet.id == body.assumption_set_id)
        )
        assumption_set = result.scalar_one_or_none()
        if assumption_set is None:
            raise HTTPException(status_code=404, detail="Financial assumption set not found")
        if assumption_set.organization_id not in (None, user["organization_id"]):
            raise HTTPException(status_code=404, detail="Financial assumption set not found")
        try:
            validate_financial_assumptions(assumption_set)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    run = FinancialRun(
        scenario_run_id=scenario_id,
        assumption_set_id=body.assumption_set_id,
        status="pending",
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)
    await db.commit()

    run_financial_analysis.delay(str(run.id), str(scenario_id), body.parameters)

    response = JobAccepted(
        job_id=run.id,
        status="accepted",
        location=f"{settings.API_V1_PREFIX}/financial-runs/{run.id}",
    )
    await cache_response(idempotency_key, response)
    return response


@router.get("/financial-runs/{run_id}", response_model=FinancialRunResponse)
async def get_financial_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
):
    run = await get_financial_run_for_org(db, run_id, user["organization_id"], load_assumption_set=True)
    return _serialize_financial_run(run)


@router.get("/reference/financial-assumption-sets", response_model=list[FinancialAssumptionSetReferenceResponse])
async def list_financial_assumption_sets(
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
):
    await db.run_sync(ensure_reference_data)
    result = await db.execute(
        select(FinancialAssumptionSet)
        .where(
            or_(
                FinancialAssumptionSet.organization_id.is_(None),
                FinancialAssumptionSet.organization_id == user["organization_id"],
            )
        )
        .order_by(FinancialAssumptionSet.is_default.desc(), FinancialAssumptionSet.name.asc())
    )
    assumption_sets = result.scalars().all()
    return [_serialize_assumption_set(assumption_set) for assumption_set in assumption_sets]
