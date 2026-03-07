import uuid
from datetime import datetime

from pydantic import BaseModel


class SnapshotManifestItemResponse(BaseModel):
    id: uuid.UUID
    source_snapshot_id: uuid.UUID
    snapshot_role: str
    is_required: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SnapshotManifestResponse(BaseModel):
    id: uuid.UUID
    jurisdiction_id: uuid.UUID
    manifest_hash: str
    parser_versions_json: dict
    model_versions_json: dict
    notes_json: dict
    created_at: datetime
    items: list[SnapshotManifestItemResponse] = []

    model_config = {"from_attributes": True}


class ReviewQueueItemResponse(BaseModel):
    id: uuid.UUID
    queue_type: str
    reason_code: str
    entity_type: str
    entity_id: uuid.UUID | None = None
    status: str
    priority: str
    assigned_to: uuid.UUID | None = None
    opened_at: datetime
    resolved_at: datetime | None = None
    resolution_code: str | None = None
    resolution_notes: str | None = None
    decision_json: dict

    model_config = {"from_attributes": True}
