import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class DevelopmentPlan(Base, UUIDPrimaryKey, TimestampMixin):
    """A full development plan generated from a user query.

    Orchestrates the entire pipeline: query parsing → parcel lookup →
    policy resolution → massing → layout → finance → entitlement →
    submission document generation.
    """
    __tablename__ = "development_plans"

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    scenario_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenario_runs.id"), nullable=True
    )

    # User input
    original_query: Mapped[str] = mapped_column(Text)
    parsed_parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # AI metadata
    ai_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    parse_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    clarifications_needed: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Pipeline state
    status: Mapped[str] = mapped_column(String(50), default="draft")
    # Statuses: draft → parsing → parsed → needs_clarification →
    #           running_pipeline → generating_documents → completed → failed
    current_step: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pipeline_progress: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # e.g. {"parcel_lookup": "completed", "policy_resolution": "running", "massing": "pending", ...}

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Results summary
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Contains high-level results from each pipeline stage

    # Relationships
    documents: Mapped[list["SubmissionDocument"]] = relationship(back_populates="plan", cascade="all, delete-orphan")


class SubmissionDocument(Base, UUIDPrimaryKey, TimestampMixin):
    """A generated document that forms part of the government submission package.

    Each plan can generate multiple documents (planning rationale, compliance matrix,
    shadow study, etc.) that together form the complete submission.
    """
    __tablename__ = "submission_documents"

    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("development_plans.id"))

    doc_type: Mapped[str] = mapped_column(String(100))
    # Types: planning_rationale, compliance_matrix, precedent_report,
    #        site_plan_data, unit_mix_summary, financial_feasibility,
    #        public_benefit_statement, shadow_study, cover_letter, full_package

    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Content
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    object_key: Mapped[str | None] = mapped_column(String(500), nullable=True)  # S3 key for rendered file

    # Generation metadata
    ai_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    generation_prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    format: Mapped[str] = mapped_column(String(20), default="markdown")  # markdown, pdf, json, csv
    status: Mapped[str] = mapped_column(String(50), default="pending")
    # Statuses: pending → generating → completed → failed

    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Review workflow
    review_status: Mapped[str] = mapped_column(String(50), default="draft")
    # Review statuses: draft → under_review → approved / rejected
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    disclaimer_accepted: Mapped[bool] = mapped_column(default=False)

    # Relationship
    plan: Mapped["DevelopmentPlan"] = relationship(back_populates="documents")
