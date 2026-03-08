import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PlanGenerateRequest(BaseModel):
    """Natural language development query."""
    query: str = Field(min_length=10, description="Describe what you want to build and where")
    auto_run: bool = Field(default=True, description="Automatically run the full pipeline after parsing")
    generate_subset: list[str] | None = Field(default=None, description="Generate only these doc types (None = all)")


class PlanGenerateDocumentRequest(BaseModel):
    """Request to generate/regenerate a single document from an existing plan."""
    extra_context: dict | None = None


class PlanClarifyResponse(BaseModel):
    """Respond to clarification questions."""
    plan_id: uuid.UUID
    answers: dict = Field(description="Map of question → answer")


class ParsedParametersResponse(BaseModel):
    address: str | None = None
    project_name: str | None = None
    development_type: str | None = None
    building_type: str | None = None
    storeys: int | None = None
    height_m: float | None = None
    unit_count: int | None = None
    ground_floor_use: str | None = None
    unit_mix: dict | None = None
    confidence: float | None = None
    clarification_needed: list[str] = []


class SubmissionDocumentResponse(BaseModel):
    id: uuid.UUID
    doc_type: str
    title: str
    description: str | None = None
    format: str
    status: str
    sort_order: int
    content_text: str | None = None
    review_status: str = "draft"
    reviewed_by: uuid.UUID | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None
    disclaimer_accepted: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewSubmitRequest(BaseModel):
    """Request to submit a document for review."""
    pass


class ReviewActionRequest(BaseModel):
    """Request to approve or reject a document."""
    notes: str | None = None


class PlanReadinessIssueResponse(BaseModel):
    code: str
    severity: Literal["blocking", "review", "warning"]
    message: str
    action: str


class PlanReadinessDocumentResponse(BaseModel):
    doc_type: str
    title: str
    status: str
    review_status: str
    ready: bool
    has_placeholders: bool


class PlanSubmissionReadinessResponse(BaseModel):
    ready_for_submission: bool
    blocking_issues: list[PlanReadinessIssueResponse] = Field(default_factory=list)
    review_issues: list[PlanReadinessIssueResponse] = Field(default_factory=list)
    warnings: list[PlanReadinessIssueResponse] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    documents: list[PlanReadinessDocumentResponse] = Field(default_factory=list)


class PlanResponse(BaseModel):
    id: uuid.UUID
    original_query: str
    parsed_parameters: dict | None = None
    status: str
    current_step: str | None = None
    pipeline_progress: dict | None = None
    parse_confidence: float | None = None
    clarifications_needed: dict | None = None
    summary: dict | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    documents: list[SubmissionDocumentResponse] = []

    model_config = {"from_attributes": True}


class ContractorResult(BaseModel):
    name: str
    rating: float | None = None
    review_count: int | None = None
    phone: str | None = None
    website: str | None = None
    address: str | None = None
    trade: str | None = None


class ContractorRecommendationsResponse(BaseModel):
    contractors: list[ContractorResult] = []


class PlanListResponse(BaseModel):
    id: uuid.UUID
    original_query: str
    status: str
    current_step: str | None = None
    parse_confidence: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
