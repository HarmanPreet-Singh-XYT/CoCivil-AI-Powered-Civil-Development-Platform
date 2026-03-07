from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.dataset import DatasetFeature
    from app.models.ingestion import SourceSnapshot


class Jurisdiction(Base, UUIDPrimaryKey):
    __tablename__ = "jurisdictions"

    name: Mapped[str] = mapped_column(String, nullable=False)
    province: Mapped[str] = mapped_column(String, nullable=False)
    country: Mapped[str] = mapped_column(String, nullable=False, default="CA", server_default="CA")
    bbox_geom = mapped_column(Geometry("Polygon", srid=4326), nullable=True)
    timezone: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="America/Toronto",
        server_default="America/Toronto",
    )
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parcels: Mapped[list["Parcel"]] = relationship(back_populates="jurisdiction")


class Parcel(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "parcels"
    __table_args__ = (
        UniqueConstraint("jurisdiction_id", "pin", "source_snapshot_id", name="uq_parcels_jurisdiction_pin_snapshot"),
    )

    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=False, index=True
    )
    source_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshots.id"), nullable=True, index=True
    )
    pin: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    address: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    geom = mapped_column(Geometry("MultiPolygon", srid=4326), nullable=False)
    geom_area_m2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lot_area_m2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lot_frontage_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lot_depth_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    current_use: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    assessed_value: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    zone_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    jurisdiction: Mapped["Jurisdiction"] = relationship(back_populates="parcels")
    source_snapshot: Mapped[Optional[SourceSnapshot]] = relationship(foreign_keys=[source_snapshot_id])
    metrics: Mapped[list["ParcelMetric"]] = relationship(back_populates="parcel")
    addresses: Mapped[list["ParcelAddress"]] = relationship(back_populates="parcel", cascade="all, delete-orphan")
    zoning_assignments: Mapped[list["ParcelZoningAssignment"]] = relationship(
        back_populates="parcel", cascade="all, delete-orphan"
    )


class ParcelMetric(Base, UUIDPrimaryKey):
    __tablename__ = "parcel_metrics"
    __table_args__ = (
        UniqueConstraint("parcel_id", "metric_type", name="uq_parcel_metrics_parcel_type"),
    )

    parcel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parcels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    metric_type: Mapped[str] = mapped_column(String, nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parcel: Mapped["Parcel"] = relationship(back_populates="metrics")


class ParcelAddress(Base, UUIDPrimaryKey):
    __tablename__ = "parcel_addresses"
    __table_args__ = (
        UniqueConstraint(
            "source_snapshot_id",
            "source_record_id",
            name="uq_parcel_addresses_snapshot_source_record",
        ),
        UniqueConstraint(
            "parcel_id",
            "source_snapshot_id",
            "address_text",
            name="uq_parcel_addresses_parcel_snapshot_address",
        ),
    )

    parcel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parcels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshots.id"), nullable=False, index=True
    )
    source_record_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    address_text: Mapped[str] = mapped_column(String, nullable=False)
    address_point_geom = mapped_column(Geometry("Point", srid=4326), nullable=True)
    match_method: Mapped[str] = mapped_column(String, nullable=False)
    match_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_canonical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parcel: Mapped["Parcel"] = relationship(back_populates="addresses")
    source_snapshot: Mapped[SourceSnapshot] = relationship(foreign_keys=[source_snapshot_id])


class ParcelZoningAssignment(Base, UUIDPrimaryKey):
    __tablename__ = "parcel_zoning_assignments"
    __table_args__ = (
        UniqueConstraint(
            "parcel_id",
            "dataset_feature_id",
            "source_snapshot_id",
            name="uq_parcel_zoning_assignments_parcel_feature_snapshot",
        ),
    )

    parcel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parcels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dataset_feature_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_features.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshots.id"), nullable=False, index=True
    )
    zone_code: Mapped[str] = mapped_column(String, nullable=False)
    overlap_area_m2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    assignment_method: Mapped[str] = mapped_column(String, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parcel: Mapped["Parcel"] = relationship(back_populates="zoning_assignments")
    dataset_feature: Mapped[DatasetFeature] = relationship(back_populates="zoning_assignments")
    source_snapshot: Mapped[SourceSnapshot] = relationship(foreign_keys=[source_snapshot_id])


class ProjectParcel(Base, UUIDPrimaryKey):
    __tablename__ = "project_parcels"
    __table_args__ = (
        UniqueConstraint("project_id", "parcel_id", name="uq_project_parcels_project_parcel"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    parcel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String, nullable=False, default="primary", server_default="primary")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
