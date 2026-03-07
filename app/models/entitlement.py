import uuid
from datetime import datetime
from typing import Optional

from geoalchemy2 import Geometry
from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKey


class EntitlementResult(Base, UUIDPrimaryKey):
    __tablename__ = "entitlement_results"

    scenario_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenario_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    snapshot_manifest_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("snapshot_manifests.id"), nullable=True, index=True
    )
    overall_compliance: Mapped[str] = mapped_column(String, nullable=False)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PrecedentSearch(Base, UUIDPrimaryKey):
    __tablename__ = "precedent_searches"

    scenario_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenario_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_manifest_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("snapshot_manifests.id"), nullable=True, index=True
    )
    search_params_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending", server_default="pending")
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    results_json: Mapped[list[dict]] = mapped_column(JSON, nullable=False, server_default="[]")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    matches: Mapped[list["PrecedentMatch"]] = relationship(
        back_populates="precedent_search",
        cascade="all, delete-orphan",
        order_by=lambda: PrecedentMatch.rank,
    )


class DevelopmentApplication(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "development_applications"
    __table_args__ = (
        UniqueConstraint("jurisdiction_id", "app_number", name="uq_dev_apps_jurisdiction_app"),
    )

    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=False, index=True
    )
    app_number: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_system: Mapped[str] = mapped_column(String, nullable=False, default="unknown", server_default="unknown")
    source_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    authority: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    parcel_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=True, index=True
    )
    geom = mapped_column(Geometry("Point", srid=4326), nullable=True)
    app_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    stage: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ward: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    decision: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    decision_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    proposed_height_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    proposed_units: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    proposed_fsi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    proposed_use: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    document_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    publisher: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    acquired_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    source_schema_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    license_status: Mapped[str] = mapped_column(String, nullable=False, default="unknown", server_default="unknown")
    internal_storage_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    redistribution_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    export_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    derived_export_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    aggregation_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    retention_policy: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    license_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    lineage_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    source_metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")

    documents: Mapped[list["ApplicationDocument"]] = relationship(back_populates="application")
    permits: Mapped[list["BuildingPermit"]] = relationship(back_populates="application")
    precedent_matches: Mapped[list["PrecedentMatch"]] = relationship(back_populates="application")


class ApplicationDocument(Base, UUIDPrimaryKey):
    __tablename__ = "application_documents"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("development_applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    doc_type: Mapped[str] = mapped_column(String, nullable=False)
    document_title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    document_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    object_key: Mapped[str] = mapped_column(String, nullable=False)
    download_status: Mapped[str] = mapped_column(String, nullable=False, default="pending", server_default="pending")
    publisher: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    acquired_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    source_schema_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    license_status: Mapped[str] = mapped_column(String, nullable=False, default="unknown", server_default="unknown")
    internal_storage_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    redistribution_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
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
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    citation_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    embedding = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    application: Mapped["DevelopmentApplication"] = relationship(back_populates="documents")
    rationale_extracts: Mapped[list["RationaleExtract"]] = relationship(back_populates="application_document")


class RationaleExtract(Base, UUIDPrimaryKey):
    __tablename__ = "rationale_extracts"

    application_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("application_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    extract_type: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    embedding = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    application_document: Mapped["ApplicationDocument"] = relationship(back_populates="rationale_extracts")


class BuildingPermit(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "building_permits"
    __table_args__ = (
        UniqueConstraint("jurisdiction_id", "permit_number", name="uq_building_permits_jurisdiction_number"),
    )

    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=False, index=True
    )
    development_application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("development_applications.id"), nullable=True, index=True
    )
    parcel_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=True, index=True
    )
    permit_number: Mapped[str] = mapped_column(String, nullable=False, index=True)
    permit_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_system: Mapped[str] = mapped_column(String, nullable=False, default="unknown", server_default="unknown")
    source_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    application_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    issue_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    closed_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    geom = mapped_column(Geometry("Point", srid=4326), nullable=True)

    application: Mapped[Optional["DevelopmentApplication"]] = relationship(back_populates="permits")


class PrecedentMatch(Base, UUIDPrimaryKey):
    __tablename__ = "precedent_matches"
    __table_args__ = (
        UniqueConstraint("precedent_search_id", "development_application_id", name="uq_precedent_match_search_app"),
    )

    precedent_search_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("precedent_searches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    development_application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("development_applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    distance_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    matched_permit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    score_breakdown_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    precedent_search: Mapped["PrecedentSearch"] = relationship(back_populates="matches")
    application: Mapped["DevelopmentApplication"] = relationship(back_populates="precedent_matches")
