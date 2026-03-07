import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UUIDPrimaryKey:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.uuid_generate_v4()
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class GovernanceMixin:
    publisher: Mapped[str | None] = mapped_column(String, nullable=True)
    acquired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_schema_version: Mapped[str | None] = mapped_column(String, nullable=True)
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
    retention_policy: Mapped[str | None] = mapped_column(String, nullable=True)
    license_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    lineage_chain_json: Mapped[list] = mapped_column(JSON, nullable=False, server_default="[]")
