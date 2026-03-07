import uuid
from datetime import datetime

from pydantic import BaseModel


class ExportRequest(BaseModel):
    project_id: uuid.UUID
    scenario_run_id: uuid.UUID | None = None
    export_type: str = "pdf"
    source_controls: list[dict] | None = None


class ExportResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    scenario_run_id: uuid.UUID | None = None
    export_type: str
    status: str
    governance_status: str
    blocked_reason: str | None = None
    object_key: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
