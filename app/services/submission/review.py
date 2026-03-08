"""Human review workflow for submission documents.

Every generated document must go through review before submission.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.plan import SubmissionDocument
from app.services.submission.readiness import document_has_unresolved_placeholders


async def submit_for_review(
    db: AsyncSession,
    doc_id: uuid.UUID,
    user_id: uuid.UUID,
) -> SubmissionDocument:
    """Set a document's review_status to 'under_review'."""
    result = await db.execute(
        select(SubmissionDocument).where(SubmissionDocument.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise ValueError(f"Document not found: {doc_id}")
    if doc.review_status not in ("draft", "rejected"):
        raise ValueError(
            f"Document cannot be submitted for review from status '{doc.review_status}'"
        )
    if doc.status != "completed":
        raise ValueError("Document must be fully generated before review")
    if not doc.content_text and not doc.content_json:
        raise ValueError("Document has no generated content to review")

    doc.review_status = "under_review"
    await db.flush()
    await db.refresh(doc)
    return doc


async def approve_document(
    db: AsyncSession,
    doc_id: uuid.UUID,
    user_id: uuid.UUID,
    notes: str | None = None,
) -> SubmissionDocument:
    """Approve a document after review."""
    result = await db.execute(
        select(SubmissionDocument).where(SubmissionDocument.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise ValueError(f"Document not found: {doc_id}")
    if doc.review_status != "under_review":
        raise ValueError(
            f"Document cannot be approved from status '{doc.review_status}'"
        )
    if document_has_unresolved_placeholders(doc.content_text):
        raise ValueError("Document still contains unresolved placeholders and cannot be approved")

    doc.review_status = "approved"
    doc.reviewed_by = user_id
    doc.reviewed_at = datetime.now(timezone.utc)
    doc.review_notes = notes
    doc.disclaimer_accepted = True
    await db.flush()
    await db.refresh(doc)
    return doc


async def reject_document(
    db: AsyncSession,
    doc_id: uuid.UUID,
    user_id: uuid.UUID,
    notes: str | None = None,
) -> SubmissionDocument:
    """Reject a document — sends it back to draft for revision."""
    result = await db.execute(
        select(SubmissionDocument).where(SubmissionDocument.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise ValueError(f"Document not found: {doc_id}")
    if doc.review_status != "under_review":
        raise ValueError(
            f"Document cannot be rejected from status '{doc.review_status}'"
        )

    doc.review_status = "rejected"
    doc.reviewed_by = user_id
    doc.reviewed_at = datetime.now(timezone.utc)
    doc.review_notes = notes
    await db.flush()
    await db.refresh(doc)
    return doc


async def get_review_history(
    db: AsyncSession,
    plan_id: uuid.UUID,
) -> list[SubmissionDocument]:
    """Return all documents for a plan with their review status."""
    result = await db.execute(
        select(SubmissionDocument)
        .where(SubmissionDocument.plan_id == plan_id)
        .order_by(SubmissionDocument.sort_order)
    )
    return list(result.scalars().all())


def submit_for_review_sync(
    db: Session,
    doc_id: uuid.UUID,
    user_id: uuid.UUID,
) -> SubmissionDocument:
    """Sync version for background tasks."""
    doc = db.query(SubmissionDocument).filter(SubmissionDocument.id == doc_id).one_or_none()
    if doc is None:
        raise ValueError(f"Document not found: {doc_id}")
    doc.review_status = "under_review" if doc.review_status in ("draft", "rejected") else doc.review_status
    db.flush()
    db.refresh(doc)
    return doc
