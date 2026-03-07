import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.schemas.geospatial import (
    ParcelDetailResponse,
    ParcelOverlaysResponse,
    ParcelResponse,
    ParcelSearchParams,
    PolicyStackResponse,
)
from app.services.geospatial import build_parcel_search_statement, get_active_parcel_by_id, list_active_snapshot_ids
from app.services.overlay_service import get_parcel_overlays_response
from app.services.policy_stack import get_policy_stack_response

router = APIRouter()


@router.get("/parcels/search", response_model=list[ParcelResponse])
async def search_parcels(
    params: ParcelSearchParams = Depends(),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        _ = params.bbox_bounds
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    active_snapshot_ids = await list_active_snapshot_ids(db, "parcel_base")
    query = build_parcel_search_statement(params, active_snapshot_ids=active_snapshot_ids)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/parcels/{parcel_id}", response_model=ParcelDetailResponse)
async def get_parcel(
    parcel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    active_snapshot_ids = await list_active_snapshot_ids(db, "parcel_base")
    parcel = await get_active_parcel_by_id(db, parcel_id, active_snapshot_ids=active_snapshot_ids)
    if not parcel:
        raise HTTPException(status_code=404, detail="Parcel not found")
    return parcel


@router.get("/parcels/{parcel_id}/policy-stack", response_model=PolicyStackResponse)
async def get_parcel_policy_stack(
    parcel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    active_snapshot_ids = await list_active_snapshot_ids(db, "parcel_base")
    parcel = await get_active_parcel_by_id(db, parcel_id, active_snapshot_ids=active_snapshot_ids)
    if not parcel:
        raise HTTPException(status_code=404, detail="Parcel not found")
    return await get_policy_stack_response(db, parcel)


@router.get("/parcels/{parcel_id}/overlays", response_model=ParcelOverlaysResponse)
async def get_parcel_overlays(
    parcel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    active_snapshot_ids = await list_active_snapshot_ids(db, "parcel_base")
    parcel = await get_active_parcel_by_id(db, parcel_id, active_snapshot_ids=active_snapshot_ids)
    if not parcel:
        raise HTTPException(status_code=404, detail="Parcel not found")
    return await get_parcel_overlays_response(db, parcel)
