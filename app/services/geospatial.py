from __future__ import annotations

import inspect
import uuid
from dataclasses import dataclass
from typing import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geospatial import Parcel
from app.models.ingestion import SourceSnapshot
from app.schemas.geospatial import ParcelSearchParams

ADDRESS_MATCH_PRIORITY = {
    "source_key": 3,
    "spatial_contains": 2,
    "manual_review": 1,
}

ZONING_ASSIGNMENT_PRIORITY = {
    "max_overlap": 2,
    "centroid_fallback": 1,
    "manual_review": 0,
}


@dataclass(frozen=True)
class AddressCandidate:
    address_text: str
    match_method: str
    match_confidence: float | None = None
    source_record_id: str | None = None


@dataclass(frozen=True)
class ZoningAssignmentCandidate:
    dataset_feature_id: uuid.UUID | None
    zone_code: str
    assignment_method: str
    overlap_area_m2: float | None = None


def normalize_address_text(value: str) -> str:
    return " ".join(value.split()).strip()


def choose_canonical_address(candidates: Sequence[AddressCandidate]) -> AddressCandidate | None:
    if not candidates:
        return None

    normalized = [
        AddressCandidate(
            address_text=normalize_address_text(candidate.address_text),
            match_method=candidate.match_method,
            match_confidence=candidate.match_confidence,
            source_record_id=candidate.source_record_id,
        )
        for candidate in candidates
        if normalize_address_text(candidate.address_text)
    ]
    if not normalized:
        return None

    return sorted(
        normalized,
        key=lambda candidate: (
            -(candidate.match_confidence if candidate.match_confidence is not None else 0.0),
            -ADDRESS_MATCH_PRIORITY.get(candidate.match_method, 0),
            len(candidate.address_text),
            candidate.address_text,
        ),
    )[0]


def choose_primary_zoning_assignment(
    candidates: Sequence[ZoningAssignmentCandidate],
    tie_tolerance_m2: float = 0.01,
) -> ZoningAssignmentCandidate | None:
    if not candidates:
        return None

    overlap_candidates = [candidate for candidate in candidates if candidate.overlap_area_m2 is not None]
    if overlap_candidates:
        ranked = sorted(
            overlap_candidates,
            key=lambda candidate: (
                -(candidate.overlap_area_m2 or 0.0),
                -ZONING_ASSIGNMENT_PRIORITY.get(candidate.assignment_method, 0),
                candidate.zone_code,
                str(candidate.dataset_feature_id or ""),
            ),
        )
        best = ranked[0]
        if (
            len(ranked) > 1
            and abs((ranked[1].overlap_area_m2 or 0.0) - (best.overlap_area_m2 or 0.0)) <= tie_tolerance_m2
        ):
            return None
        return best

    fallback_candidates = sorted(
        candidates,
        key=lambda candidate: (
            -ZONING_ASSIGNMENT_PRIORITY.get(candidate.assignment_method, 0),
            candidate.zone_code,
            str(candidate.dataset_feature_id or ""),
        ),
    )
    best = fallback_candidates[0]
    peer_count = sum(
        1
        for candidate in fallback_candidates
        if ZONING_ASSIGNMENT_PRIORITY.get(candidate.assignment_method, 0)
        == ZONING_ASSIGNMENT_PRIORITY.get(best.assignment_method, 0)
    )
    return best if peer_count == 1 else None


def build_parcel_search_statement(
    params: ParcelSearchParams,
    active_snapshot_ids: Sequence[uuid.UUID] | None = None,
) -> Select:
    query = select(Parcel)

    if active_snapshot_ids:
        query = query.where(Parcel.source_snapshot_id.in_(list(active_snapshot_ids)))
    if params.address:
        query = query.where(Parcel.address.ilike(f"%{params.address}%"))
    if params.pin:
        query = query.where(Parcel.pin == params.pin)
    if params.zoning_code:
        query = query.where(Parcel.zone_code == params.zoning_code)
    if params.min_lot_area is not None:
        query = query.where(Parcel.lot_area_m2 >= params.min_lot_area)
    if params.max_lot_area is not None:
        query = query.where(Parcel.lot_area_m2 <= params.max_lot_area)
    if params.min_frontage is not None:
        query = query.where(Parcel.lot_frontage_m >= params.min_frontage)
    if params.bbox_bounds is not None:
        minx, miny, maxx, maxy = params.bbox_bounds
        envelope = func.ST_MakeEnvelope(minx, miny, maxx, maxy, 4326)
        query = query.where(func.ST_Intersects(Parcel.geom, envelope))

    return query.offset((params.page - 1) * params.page_size).limit(params.page_size)


async def list_active_snapshot_ids(
    db: AsyncSession,
    snapshot_type: str,
    jurisdiction_id: uuid.UUID | None = None,
) -> list[uuid.UUID]:
    if not hasattr(db, "execute"):
        return []

    query = select(SourceSnapshot.id).where(
        SourceSnapshot.snapshot_type == snapshot_type,
        SourceSnapshot.is_active.is_(True),
    )
    if jurisdiction_id is not None:
        query = query.where(SourceSnapshot.jurisdiction_id == jurisdiction_id)

    result = await db.execute(query.order_by(SourceSnapshot.created_at.desc()))
    return list(result.scalars().all())


async def get_active_parcel_by_id(
    db: AsyncSession,
    parcel_id: uuid.UUID,
    active_snapshot_ids: Sequence[uuid.UUID] | None = None,
) -> Parcel | None:
    if not hasattr(db, "execute") and hasattr(db, "get"):
        result = db.get(Parcel, parcel_id)
        return await result if inspect.isawaitable(result) else result

    query = select(Parcel).where(Parcel.id == parcel_id)
    if active_snapshot_ids:
        query = query.where(Parcel.source_snapshot_id.in_(list(active_snapshot_ids)))

    result = await db.execute(query)
    return result.scalar_one_or_none()
