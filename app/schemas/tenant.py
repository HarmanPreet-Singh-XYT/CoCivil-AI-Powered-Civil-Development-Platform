import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AddParcelRequest(BaseModel):
    parcel_id: uuid.UUID
    role: str = "primary"


class ScenarioCreate(BaseModel):
    scenario_type: str = Field(default="base", pattern="^(base|variance|what_if)$")
    parent_scenario_id: uuid.UUID | None = None
    snapshot_manifest_id: uuid.UUID | None = None
    parameters: dict | None = None


class ScenarioResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    parent_scenario_id: uuid.UUID | None = None
    scenario_type: str
    status: str
    input_hash: str
    label: str | None = None
    snapshot_manifest_id: uuid.UUID | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}
