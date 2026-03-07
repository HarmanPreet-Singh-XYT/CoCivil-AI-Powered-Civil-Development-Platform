import uuid
from datetime import datetime
from typing import Optional

from geoalchemy2 import Geometry
from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Date, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDPrimaryKey


class PolicyDocument(Base, UUIDPrimaryKey):
    __tablename__ = "policy_documents"

    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=False, index=True
    )
    doc_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    publisher: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    acquired_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    object_key: Mapped[str] = mapped_column(String, nullable=False)
    file_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    lineage_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    redistribution_policy: Mapped[Optional[str]] = mapped_column(String, nullable=True)
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
    parse_status: Mapped[str] = mapped_column(String, nullable=False, default="pending", server_default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    versions: Mapped[list["PolicyVersion"]] = relationship(back_populates="document")


class PolicyVersion(Base, UUIDPrimaryKey):
    __tablename__ = "policy_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_policy_versions_doc_version"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_documents.id", ondelete="CASCADE"), nullable=False
    )
    source_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshots.id"), nullable=True, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parser_version: Mapped[str] = mapped_column(String, nullable=False)
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confidence_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    clause_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped["PolicyDocument"] = relationship(back_populates="versions")
    clauses: Mapped[list["PolicyClause"]] = relationship(back_populates="policy_version")


class PolicyClause(Base, UUIDPrimaryKey):
    __tablename__ = "policy_clauses"

    policy_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_ref: Mapped[str] = mapped_column(String, nullable=False)
    page_ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    normalized_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    embedding = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    policy_version: Mapped["PolicyVersion"] = relationship(back_populates="clauses")
    outgoing_references: Mapped[list["PolicyReference"]] = relationship(
        back_populates="from_clause", foreign_keys="PolicyReference.from_clause_id"
    )
    incoming_references: Mapped[list["PolicyReference"]] = relationship(
        back_populates="to_clause", foreign_keys="PolicyReference.to_clause_id"
    )
    applicability_rules: Mapped[list["PolicyApplicabilityRule"]] = relationship(back_populates="policy_clause")
    review_items: Mapped[list["PolicyReviewItem"]] = relationship(back_populates="policy_clause")


class PolicyReference(Base, UUIDPrimaryKey):
    __tablename__ = "policy_references"
    __table_args__ = (
        UniqueConstraint("from_clause_id", "to_clause_id", "relation_type", name="uq_policy_refs_from_to_type"),
    )

    from_clause_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_clauses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    to_clause_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_clauses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_type: Mapped[str] = mapped_column(String, nullable=False)

    from_clause: Mapped["PolicyClause"] = relationship(
        back_populates="outgoing_references", foreign_keys=[from_clause_id]
    )
    to_clause: Mapped["PolicyClause"] = relationship(
        back_populates="incoming_references", foreign_keys=[to_clause_id]
    )


class PolicyApplicabilityRule(Base, UUIDPrimaryKey):
    __tablename__ = "policy_applicability_rules"

    policy_clause_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_clauses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=False
    )
    geometry_filter = mapped_column(Geometry("MultiPolygon", srid=4326), nullable=True)
    zone_filter = mapped_column(ARRAY(String), nullable=True)
    use_filter = mapped_column(ARRAY(String), nullable=True)
    override_level: Mapped[int] = mapped_column(Integer, nullable=False)
    applicability_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")

    policy_clause: Mapped["PolicyClause"] = relationship(back_populates="applicability_rules")


class PolicyReviewItem(Base, UUIDPrimaryKey):
    __tablename__ = "policy_review_items"

    policy_clause_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_clauses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending", server_default="pending")
    review_reason: Mapped[str] = mapped_column(String, nullable=False)
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    resolution_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    policy_clause: Mapped["PolicyClause"] = relationship(back_populates="review_items")
