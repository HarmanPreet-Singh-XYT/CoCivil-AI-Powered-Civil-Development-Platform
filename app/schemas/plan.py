import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PlanGenerateRequest(BaseModel):
    """Natural language development query."""
    query: str = Field(min_length=10, description="Describe what you want to build and where")
    auto_run: bool = Field(default=True, description="Automatically run the full pipeline after parsing")


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


class PlanListResponse(BaseModel):
    id: uuid.UUID
    original_query: str
    status: str
    current_step: str | None = None
    parse_confidence: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
