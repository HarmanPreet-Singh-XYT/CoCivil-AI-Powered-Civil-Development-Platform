import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDPrimaryKey


class SourceSnapshot(Base, UUIDPrimaryKey):
    __tablename__ = "source_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "jurisdiction_id", "snapshot_type", "version_label",
            name="uq_source_snapshots_jurisdiction_type_label"
        ),
    )

    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=False
    )
    snapshot_type: Mapped[str] = mapped_column(String, nullable=False)
    version_label: Mapped[str] = mapped_column(String, nullable=False)
    extractor_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    extraction_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    validation_summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")


class IngestionJob(Base, UUIDPrimaryKey):
    __tablename__ = "ingestion_jobs"

    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=False, index=True
    )
    source_url: Mapped[str] = mapped_column(String, nullable=False)
    source_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshots.id"), nullable=True, index=True
    )
    source_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    job_type: Mapped[str] = mapped_column(String, nullable=False)
    parser_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending", server_default="pending")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    records_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    records_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    validation_summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SnapshotManifest(Base, UUIDPrimaryKey):
    __tablename__ = "snapshot_manifests"
    __table_args__ = (
        UniqueConstraint("manifest_hash", name="uq_snapshot_manifests_manifest_hash"),
    )

    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=False, index=True
    )
    manifest_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    parser_versions_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    model_versions_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    notes_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list["SnapshotManifestItem"]] = relationship(
        back_populates="manifest", cascade="all, delete-orphan"
    )


class SnapshotManifestItem(Base, UUIDPrimaryKey):
    __tablename__ = "snapshot_manifest_items"
    __table_args__ = (
        UniqueConstraint("manifest_id", "source_snapshot_id", "snapshot_role", name="uq_manifest_snapshot_role"),
    )

    manifest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("snapshot_manifests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_role: Mapped[str] = mapped_column(String, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    manifest: Mapped["SnapshotManifest"] = relationship(back_populates="items")


class ParseArtifact(Base, UUIDPrimaryKey):
    __tablename__ = "parse_artifacts"

    source_family: Mapped[str] = mapped_column(String, nullable=False)
    source_entity_type: Mapped[str] = mapped_column(String, nullable=False)
    source_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    artifact_type: Mapped[str] = mapped_column(String, nullable=False)
    object_key: Mapped[str] = mapped_column(String, nullable=False)
    file_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    content_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    producer_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    validation_summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    parent_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parse_artifacts.id"), nullable=True
    )
    ingestion_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_jobs.id"), nullable=True
    )
    source_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshots.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReviewQueueItem(Base, UUIDPrimaryKey):
    __tablename__ = "review_queue_items"

    queue_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    reason_code: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parse_artifacts.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending", server_default="pending")
    priority: Mapped[str] = mapped_column(String, nullable=False, default="normal", server_default="normal")
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_code: Mapped[str | None] = mapped_column(String, nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")


class RefreshSchedule(Base, UUIDPrimaryKey):
    __tablename__ = "refresh_schedules"

    source_family: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(String, nullable=False)
    cadence: Mapped[str] = mapped_column(String, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner: Mapped[str | None] = mapped_column(String, nullable=True)
    failure_policy: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
