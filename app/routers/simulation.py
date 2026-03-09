import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_user, get_db_session, get_optional_idempotency_key
from app.models.simulation import LayoutRun, Massing, MassingTemplate, UnitType
from app.schemas.common import JobAccepted
from app.schemas.simulation import (
    LayoutRunRequest,
    LayoutRunResponse,
    MassingRequest,
    MassingResponse,
    MassingTemplateReferenceResponse,
    UnitTypeReferenceResponse,
)
from app.services.access_control import get_layout_run_for_org, get_massing_for_org, get_scenario_for_org
from app.services.idempotency import cache_response, get_cached_response
from app.services.thin_slice_runtime import ensure_reference_data, validate_massing_template
from app.tasks.layout import run_layout
from app.tasks.massing import run_massing

router = APIRouter()


def _serialize_template(template: MassingTemplate | None) -> MassingTemplateReferenceResponse | None:
    if template is None:
        return None
    return MassingTemplateReferenceResponse.model_validate(
        {
            "id": template.id,
            "name": template.name,
            "typology": template.typology,
            "parameters_json": validate_massing_template(template),
            "created_at": template.created_at,
        }
    )


def _serialize_massing(massing: Massing) -> dict[str, Any]:
    return {
        "id": massing.id,
        "scenario_run_id": massing.scenario_run_id,
        "template_id": massing.template_id,
        "template_name": massing.template_name,
        "geometry_3d_key": massing.geometry_3d_key,
        "total_gfa_m2": massing.total_gfa_m2,
        "total_gla_m2": massing.total_gla_m2,
        "storeys": massing.storeys,
        "height_m": massing.height_m,
        "lot_coverage_pct": massing.lot_coverage_pct,
        "fsi": massing.fsi,
        "summary_json": massing.summary_json or None,
        "compliance_json": massing.compliance_json or None,
        "template": _serialize_template(massing.template),
        "created_at": massing.created_at,
    }


def _serialize_unit_type(unit_type: UnitType) -> UnitTypeReferenceResponse:
    return UnitTypeReferenceResponse.model_validate(unit_type)


@router.post("/scenarios/{scenario_id}/massings", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_massing(
    scenario_id: uuid.UUID,
    body: MassingRequest,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_optional_idempotency_key),
):
    cached_response = await get_cached_response(idempotency_key, JobAccepted)
    if cached_response is not None:
        return cached_response

    await get_scenario_for_org(db, scenario_id, user["organization_id"])
    if body.template_id is not None:
        template_result = await db.execute(select(MassingTemplate).where(MassingTemplate.id == body.template_id))
        template = template_result.scalar_one_or_none()
        if template is None:
            raise HTTPException(status_code=404, detail="Massing template not found")
        try:
            validate_massing_template(template)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    massing = Massing(scenario_run_id=scenario_id, template_id=body.template_id)
    db.add(massing)
    await db.flush()
    await db.refresh(massing)
    await db.commit()

    run_massing.delay(str(massing.id), str(scenario_id), body.parameters)

    response = JobAccepted(
        job_id=massing.id,
        status="accepted",
        location=f"{settings.API_V1_PREFIX}/massings/{massing.id}",
    )
    await cache_response(idempotency_key, response)
    return response


@router.get("/massings/{massing_id}", response_model=MassingResponse)
async def get_massing(
    massing_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
):
    massing = await get_massing_for_org(db, massing_id, user["organization_id"], load_template=True)
    return _serialize_massing(massing)


@router.get("/reference/massing-templates", response_model=list[MassingTemplateReferenceResponse])
async def list_massing_templates(
    db: AsyncSession = Depends(get_db_session),
):
    await db.run_sync(ensure_reference_data)
    result = await db.execute(select(MassingTemplate).order_by(MassingTemplate.name.asc()))
    templates = result.scalars().all()
    return [_serialize_template(template) for template in templates]


@router.get("/reference/unit-types", response_model=list[UnitTypeReferenceResponse])
async def list_unit_types(
    jurisdiction_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
):
    default_jurisdiction = await db.run_sync(ensure_reference_data)
    target_jurisdiction_id = jurisdiction_id or default_jurisdiction.id
    query = (
        select(UnitType)
        .where(UnitType.jurisdiction_id == target_jurisdiction_id)
        .order_by(UnitType.bedroom_count.asc(), UnitType.name.asc())
    )
    result = await db.execute(query)
    unit_types = result.scalars().all()
    if not unit_types:
        fallback = await db.execute(
            select(UnitType)
            .where(UnitType.jurisdiction_id.is_(None))
            .order_by(UnitType.bedroom_count.asc(), UnitType.name.asc())
        )
        unit_types = fallback.scalars().all()
    return [_serialize_unit_type(unit_type) for unit_type in unit_types]


@router.post("/massings/{massing_id}/layout-runs", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_layout_run(
    massing_id: uuid.UUID,
    body: LayoutRunRequest,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_optional_idempotency_key),
):
    cached_response = await get_cached_response(idempotency_key, JobAccepted)
    if cached_response is not None:
        return cached_response

    await get_massing_for_org(db, massing_id, user["organization_id"])
    normalized_objective = (
        "max_revenue"
        if body.optimization_objective == "maximize_revenue"
        else body.optimization_objective
    )
    if body.unit_types:
        requested_ids = list(dict.fromkeys(body.unit_types))
        result = await db.execute(select(UnitType.id).where(UnitType.id.in_(requested_ids)))
        found_ids = set(result.scalars().all())
        missing_ids = [unit_type_id for unit_type_id in requested_ids if unit_type_id not in found_ids]
        if missing_ids:
            raise HTTPException(
                status_code=404,
                detail={"message": "One or more unit types were not found", "unit_type_ids": missing_ids},
            )

    task_params = dict(body.parameters or {})
    task_params["objective"] = normalized_objective
    if body.unit_types is not None:
        task_params["unit_type_ids"] = [str(unit_type_id) for unit_type_id in body.unit_types]

    layout = LayoutRun(
        massing_id=massing_id,
        objective=normalized_objective,
        status="pending",
    )
    db.add(layout)
    await db.flush()
    await db.refresh(layout)
    await db.commit()

    run_layout.delay(str(layout.id), str(massing_id), task_params)

    response = JobAccepted(
        job_id=layout.id,
        status="accepted",
        location=f"{settings.API_V1_PREFIX}/layout-runs/{layout.id}",
    )
    await cache_response(idempotency_key, response)
    return response


@router.get("/layout-runs/{layout_run_id}", response_model=LayoutRunResponse)
async def get_layout_run(
    layout_run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
):
    return await get_layout_run_for_org(db, layout_run_id, user["organization_id"])
