import uuid
from datetime import datetime

from pydantic import BaseModel


class JobStatusResponse(BaseModel):
    job_id: uuid.UUID
    job_type: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict | list | None = None
    error_message: str | None = None
