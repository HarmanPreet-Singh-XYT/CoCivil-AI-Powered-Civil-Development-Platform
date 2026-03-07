import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_user, get_db_session
from app.models.ingestion import ReviewQueueItem, SnapshotManifest
from app.schemas.governance import ReviewQueueItemResponse, SnapshotManifestResponse

router = APIRouter()


@router.get("/snapshot-manifests/{manifest_id}", response_model=SnapshotManifestResponse)
async def get_snapshot_manifest(
    manifest_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(SnapshotManifest)
        .options(selectinload(SnapshotManifest.items))
        .where(SnapshotManifest.id == manifest_id)
    )
    manifest = result.scalar_one_or_none()
    if not manifest:
        raise HTTPException(status_code=404, detail="Snapshot manifest not found")
    return manifest


@router.get("/review-queue", response_model=list[ReviewQueueItemResponse])
async def list_review_queue_items(
    status: str | None = Query(default=None),
    queue_type: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
):
    query = select(ReviewQueueItem).order_by(ReviewQueueItem.opened_at.desc())
    if status:
        query = query.where(ReviewQueueItem.status == status)
    if queue_type:
        query = query.where(ReviewQueueItem.queue_type == queue_type)
    result = await db.execute(query)
    return result.scalars().all()
