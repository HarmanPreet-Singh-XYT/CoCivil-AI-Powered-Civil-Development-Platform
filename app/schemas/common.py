import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str
    celery: str = "unknown"
    version: str


class JobAccepted(BaseModel):
    job_id: uuid.UUID
    status: str = "accepted"
    location: str = Field(description="URL to poll for job status")


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    items: list = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    pages: int = 0


class Citation(BaseModel):
    source_document: str | None = None
    section_ref: str | None = None
    page_ref: str | None = None
    effective_date: datetime | None = None
    confidence: float | None = None
