import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKey


class Organization(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    settings_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")

    users: Mapped[list["User"]] = relationship(back_populates="organization", secondary="workspace_members")
    workspace_members: Mapped[list["WorkspaceMember"]] = relationship(back_populates="organization")
    projects: Mapped[list["Project"]] = relationship(back_populates="organization")


class User(Base, UUIDPrimaryKey):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization: Mapped[Optional["Organization"]] = relationship(
        back_populates="users", secondary="workspace_members", viewonly=True
    )
    workspace_memberships: Mapped[list["WorkspaceMember"]] = relationship(back_populates="user")


class WorkspaceMember(Base, UUIDPrimaryKey):
    __tablename__ = "workspace_members"
    __table_args__ = (
        {"comment": "Links users to organizations with a role"},
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="workspace_members")
    user: Mapped["User"] = relationship(back_populates="workspace_memberships")


class Project(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "projects"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active", server_default="active")

    organization: Mapped["Organization"] = relationship(back_populates="projects")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
    shares: Mapped[list["ProjectShare"]] = relationship(back_populates="project")
    scenario_runs: Mapped[list["ScenarioRun"]] = relationship(back_populates="project")


class ProjectShare(Base, UUIDPrimaryKey):
    __tablename__ = "project_shares"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    shared_with: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    permission: Mapped[str] = mapped_column(String, nullable=False, default="view")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="shares")
    shared_user: Mapped["User"] = relationship(foreign_keys=[shared_with])


class ScenarioRun(Base, UUIDPrimaryKey):
    __tablename__ = "scenario_runs"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_scenario_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenario_runs.id"), nullable=True, index=True
    )
    scenario_type: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    input_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    snapshot_manifest_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("snapshot_manifests.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending", server_default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="scenario_runs")
    parent_scenario: Mapped[Optional["ScenarioRun"]] = relationship(
        remote_side="ScenarioRun.id", foreign_keys=[parent_scenario_id]
    )
    snapshot_manifest: Mapped[Optional["AnalysisSnapshotManifest"]] = relationship(
        back_populates="scenario_run", uselist=False
    )
    governance_manifest: Mapped[Optional["SnapshotManifest"]] = relationship(foreign_keys=[snapshot_manifest_id])


class AnalysisSnapshotManifest(Base, UUIDPrimaryKey):
    __tablename__ = "analysis_snapshot_manifests"

    scenario_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenario_runs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    parcel_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshots.id"), nullable=True
    )
    policy_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshots.id"), nullable=True
    )
    overlay_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshots.id"), nullable=True
    )
    precedent_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshots.id"), nullable=True
    )
    market_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshots.id"), nullable=True
    )
    model_versions_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scenario_run: Mapped["ScenarioRun"] = relationship(back_populates="snapshot_manifest")
