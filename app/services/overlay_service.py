import uuid
from dataclasses import dataclass
from datetime import date, datetime

from geoalchemy2 import functions as geo_func
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.dataset import DatasetFeature, DatasetLayer, FeatureToParcelLink
from app.models.geospatial import Parcel, ParcelMetric
from app.models.ingestion import SourceSnapshot
from app.schemas.geospatial import (
    OverlayFeatureResponse,
    ParcelMetricResponse,
    ParcelOverlaysResponse,
    SnapshotReferenceResponse,
)

HARD_CONSTRAINT_LAYER_TYPES = {"heritage", "floodplain", "environmental", "zoning", "height_overlay", "setback_overlay"}
HARD_CONSTRAINT_METRIC_TYPES = {
    "heritage_flag",
    "floodplain_flag",
    "ravine_flag",
    "floodplain_coverage_pct",
    "overlay_feature_count",
}


@dataclass(frozen=True)
class OverlayRecord:
    feature_id: uuid.UUID
    layer_id: uuid.UUID
    layer_name: str
    layer_type: str
    relationship_type: str
    source_record_id: str | None
    source_url: str | None
    effective_date: date | None
    attributes_json: dict
    snapshot_id: uuid.UUID | None
    snapshot_type: str | None
    snapshot_label: str | None
    snapshot_published_at: datetime | None


@dataclass(frozen=True)
class ParcelMetricRecord:
    metric_type: str
    metric_value: float
    unit: str


def build_overlay_response(
    parcel_id: uuid.UUID,
    overlays: list[OverlayRecord],
    metrics: list[ParcelMetricRecord],
) -> ParcelOverlaysResponse:
    ordered_overlays = sorted(
        overlays,
        key=lambda record: (record.layer_type, record.layer_name.lower(), record.relationship_type),
    )
    ordered_metrics = sorted(metrics, key=lambda metric: metric.metric_type)

    snapshots: dict[uuid.UUID, SnapshotReferenceResponse] = {}
    overlay_entries: list[OverlayFeatureResponse] = []

    for overlay in ordered_overlays:
        snapshot = None
        if overlay.snapshot_id:
            snapshot = snapshots.setdefault(
                overlay.snapshot_id,
                SnapshotReferenceResponse(
                    id=overlay.snapshot_id,
                    snapshot_type=overlay.snapshot_type,
                    version_label=overlay.snapshot_label,
                    published_at=overlay.snapshot_published_at,
                ),
            )
        overlay_entries.append(
            OverlayFeatureResponse(
                feature_id=overlay.feature_id,
                layer_id=overlay.layer_id,
                layer_name=overlay.layer_name,
                layer_type=overlay.layer_type,
                relationship_type=overlay.relationship_type,
                source_record_id=overlay.source_record_id,
                source_url=overlay.source_url,
                effective_date=overlay.effective_date,
                attributes_json=overlay.attributes_json,
                snapshot=snapshot,
            )
        )

    metric_entries = [
        ParcelMetricResponse(
            metric_type=metric.metric_type,
            metric_value=metric.metric_value,
            unit=metric.unit,
        )
        for metric in ordered_metrics
    ]

    return ParcelOverlaysResponse(
        parcel_id=parcel_id,
        overlays=overlay_entries,
        parcel_metrics=metric_entries,
        snapshots=list(snapshots.values()),
    )


async def get_parcel_overlays_response(db: AsyncSession, parcel: Parcel) -> ParcelOverlaysResponse:
    # Use pre-computed links if available, otherwise fall back to direct spatial intersection
    parcel_geom = select(Parcel.geom).where(Parcel.id == parcel.id).scalar_subquery()
    overlay_query = (
        select(
            DatasetFeature,
            DatasetLayer,
            SourceSnapshot,
        )
        .join(DatasetLayer, DatasetFeature.dataset_layer_id == DatasetLayer.id)
        .outerjoin(SourceSnapshot, DatasetLayer.source_snapshot_id == SourceSnapshot.id)
        .where(DatasetLayer.layer_type.in_(sorted(HARD_CONSTRAINT_LAYER_TYPES)))
        .where(or_(DatasetLayer.published_at.is_not(None), SourceSnapshot.is_active.is_(True)))
        .where(geo_func.ST_Intersects(DatasetFeature.geom, parcel_geom))
    )
    metric_query = (
        select(ParcelMetric)
        .where(ParcelMetric.parcel_id == parcel.id)
        .where(ParcelMetric.metric_type.in_(sorted(HARD_CONSTRAINT_METRIC_TYPES)))
    )

    overlay_rows = (await db.execute(overlay_query)).all()
    metric_rows = (await db.execute(metric_query)).scalars().all()

    overlays = [
        OverlayRecord(
            feature_id=feature.id,
            layer_id=layer.id,
            layer_name=layer.name,
            layer_type=layer.layer_type,
            relationship_type="intersects",
            source_record_id=feature.source_record_id,
            source_url=layer.source_url,
            effective_date=feature.effective_date,
            attributes_json=feature.attributes_json,
            snapshot_id=snapshot.id if snapshot else None,
            snapshot_type=snapshot.snapshot_type if snapshot else None,
            snapshot_label=snapshot.version_label if snapshot else None,
            snapshot_published_at=snapshot.published_at if snapshot else None,
        )
        for feature, layer, snapshot in overlay_rows
    ]
    metrics = [
        ParcelMetricRecord(metric_type=metric.metric_type, metric_value=metric.metric_value, unit=metric.unit)
        for metric in metric_rows
    ]
    return build_overlay_response(parcel.id, overlays, metrics)


def get_parcel_overlays_response_sync(db: Session, parcel: Parcel) -> ParcelOverlaysResponse:
    """Sync version for use in background tasks."""
    parcel_geom = select(Parcel.geom).where(Parcel.id == parcel.id).scalar_subquery()
    overlay_query = (
        select(DatasetFeature, DatasetLayer, SourceSnapshot)
        .join(DatasetLayer, DatasetFeature.dataset_layer_id == DatasetLayer.id)
        .outerjoin(SourceSnapshot, DatasetLayer.source_snapshot_id == SourceSnapshot.id)
        .where(DatasetLayer.layer_type.in_(sorted(HARD_CONSTRAINT_LAYER_TYPES)))
        .where(or_(DatasetLayer.published_at.is_not(None), SourceSnapshot.is_active.is_(True)))
        .where(geo_func.ST_Intersects(DatasetFeature.geom, parcel_geom))
    )
    metric_query = (
        select(ParcelMetric)
        .where(ParcelMetric.parcel_id == parcel.id)
        .where(ParcelMetric.metric_type.in_(sorted(HARD_CONSTRAINT_METRIC_TYPES)))
    )

    overlay_rows = db.execute(overlay_query).all()
    metric_rows = db.execute(metric_query).scalars().all()

    overlay_list = [
        OverlayRecord(
            feature_id=feature.id,
            layer_id=layer.id,
            layer_name=layer.name,
            layer_type=layer.layer_type,
            relationship_type="intersects",
            source_record_id=feature.source_record_id,
            source_url=layer.source_url,
            effective_date=feature.effective_date,
            attributes_json=feature.attributes_json,
            snapshot_id=snapshot.id if snapshot else None,
            snapshot_type=snapshot.snapshot_type if snapshot else None,
            snapshot_label=snapshot.version_label if snapshot else None,
            snapshot_published_at=snapshot.published_at if snapshot else None,
        )
        for feature, layer, snapshot in overlay_rows
    ]
    metric_list = [
        ParcelMetricRecord(metric_type=m.metric_type, metric_value=m.metric_value, unit=m.unit)
        for m in metric_rows
    ]
    return build_overlay_response(parcel.id, overlay_list, metric_list)
