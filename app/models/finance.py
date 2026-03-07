import uuid
from datetime import datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDPrimaryKey


class MarketComparable(Base, UUIDPrimaryKey):
    __tablename__ = "market_comparables"

    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=False, index=True
    )
    comp_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    geom = mapped_column(Geometry("Point", srid=4326), nullable=True)
    effective_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    publisher: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    acquired_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    source_schema_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    license_status: Mapped[str] = mapped_column(String, nullable=False, default="unknown", server_default="unknown")
    internal_storage_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    redistribution_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    export_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    derived_export_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    aggregation_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    retention_policy: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    license_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    source_metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    lineage_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    attributes_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FinancialAssumptionSet(Base, UUIDPrimaryKey):
    __tablename__ = "financial_assumption_sets"

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    assumptions_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    financial_runs: Mapped[list["FinancialRun"]] = relationship(back_populates="assumption_set")


class FinancialRun(Base, UUIDPrimaryKey):
    __tablename__ = "financial_runs"

    scenario_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenario_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assumption_set_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financial_assumption_sets.id"), nullable=True
    )
    layout_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("layout_runs.id"), nullable=True
    )
    output_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    total_revenue: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    total_cost: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    noi: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    valuation: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    residual_land_value: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    irr_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="completed", server_default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assumption_set: Mapped[Optional["FinancialAssumptionSet"]] = relationship(back_populates="financial_runs")
    layout_run: Mapped[Optional["LayoutRun"]] = relationship()
