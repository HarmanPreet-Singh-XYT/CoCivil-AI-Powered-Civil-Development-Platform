import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class EntitlementRunRequest(BaseModel):
    parameters: dict | None = None


class EntitlementRunResponse(BaseModel):
    id: uuid.UUID
    scenario_run_id: uuid.UUID
    snapshot_manifest_id: uuid.UUID | None = None
    overall_compliance: str
    result_json: dict | None = None
    score: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PrecedentSearchRequest(BaseModel):
    search_params: dict | None = None
    radius_m: float | None = 500.0
    max_results: int = 20
    application_types: list[str] | None = None


class DevelopmentApplicationSummaryResponse(BaseModel):
    id: uuid.UUID
    app_number: str
    source_system: str
    source_url: str | None = None
    authority: str | None = None
    address: str | None = None
    app_type: str
    status: str
    stage: str | None = None
    ward: str | None = None
    submitted_at: date | None = None
    decision: str | None = None
    decision_date: date | None = None
    proposed_height_m: float | None = None
    proposed_units: int | None = None
    proposed_fsi: float | None = None
    proposed_use: str | None = None
    document_count: int = 0

    model_config = {"from_attributes": True}


class PrecedentMatchResponse(BaseModel):
    id: uuid.UUID
    development_application_id: uuid.UUID
    rank: int
    score: float
    distance_m: float | None = None
    matched_permit_count: int = 0
    score_breakdown_json: dict | None = None
    summary_json: dict | None = None
    application: DevelopmentApplicationSummaryResponse | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PrecedentSearchResponse(BaseModel):
    id: uuid.UUID
    scenario_run_id: uuid.UUID
    snapshot_manifest_id: uuid.UUID | None = None
    status: str
    search_params_json: dict | None = None
    result_count: int = 0
    results_json: list[dict] | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    matches: list[PrecedentMatchResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}
