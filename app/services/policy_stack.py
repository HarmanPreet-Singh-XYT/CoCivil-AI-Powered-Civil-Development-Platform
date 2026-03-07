import uuid
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geospatial import Parcel
from app.models.ingestion import SourceSnapshot
from app.models.policy import PolicyApplicabilityRule, PolicyClause, PolicyDocument, PolicyVersion
from app.schemas.geospatial import (
    PolicyCitationResponse,
    PolicyEntryResponse,
    PolicyStackResponse,
    SnapshotReferenceResponse,
)


@dataclass(frozen=True)
class PolicyStackRecord:
    clause_id: uuid.UUID
    policy_version_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    doc_type: str
    override_level: int
    section_ref: str
    page_ref: str | None
    raw_text: str
    normalized_type: str
    normalized_json: dict
    applicability_json: dict
    confidence: float
    effective_date: date | None
    source_url: str | None
    snapshot_id: uuid.UUID | None
    snapshot_type: str | None
    snapshot_label: str | None
    snapshot_published_at: datetime | None


def build_policy_stack_response(parcel_id: uuid.UUID, records: list[PolicyStackRecord]) -> PolicyStackResponse:
    ordered = sorted(
        records,
        key=lambda record: (record.override_level, record.document_title.lower(), record.section_ref),
    )

    snapshots: dict[uuid.UUID, SnapshotReferenceResponse] = {}
    citations: dict[uuid.UUID, PolicyCitationResponse] = {}
    entries: list[PolicyEntryResponse] = []

    for record in ordered:
        snapshot = None
        if record.snapshot_id:
            snapshot = snapshots.setdefault(
                record.snapshot_id,
                SnapshotReferenceResponse(
                    id=record.snapshot_id,
                    snapshot_type=record.snapshot_type,
                    version_label=record.snapshot_label,
                    published_at=record.snapshot_published_at,
                ),
            )

        citations.setdefault(
            record.clause_id,
            PolicyCitationResponse(
                clause_id=record.clause_id,
                document_title=record.document_title,
                doc_type=record.doc_type,
                section_ref=record.section_ref,
                page_ref=record.page_ref,
                source_url=record.source_url,
                effective_date=record.effective_date,
            ),
        )
        entries.append(
            PolicyEntryResponse(
                clause_id=record.clause_id,
                policy_version_id=record.policy_version_id,
                document_id=record.document_id,
                document_title=record.document_title,
                doc_type=record.doc_type,
                override_level=record.override_level,
                section_ref=record.section_ref,
                page_ref=record.page_ref,
                raw_text=record.raw_text,
                normalized_type=record.normalized_type,
                normalized_json=record.normalized_json,
                applicability_json=record.applicability_json,
                confidence=record.confidence,
                effective_date=record.effective_date,
                source_url=record.source_url,
                snapshot=snapshot,
            )
        )

    return PolicyStackResponse(
        parcel_id=parcel_id,
        applicable_policies=entries,
        citations=list(citations.values()),
        snapshots=list(snapshots.values()),
    )


async def get_policy_stack_response(db: AsyncSession, parcel: Parcel) -> PolicyStackResponse:
    parcel_geom = select(Parcel.geom).where(Parcel.id == parcel.id).scalar_subquery()

    zone_match = func.coalesce(func.cardinality(PolicyApplicabilityRule.zone_filter), 0) == 0
    if parcel.zone_code:
        zone_match = or_(zone_match, PolicyApplicabilityRule.zone_filter.any(parcel.zone_code))

    use_match = func.coalesce(func.cardinality(PolicyApplicabilityRule.use_filter), 0) == 0
    if parcel.current_use:
        use_match = or_(use_match, PolicyApplicabilityRule.use_filter.any(parcel.current_use))

    query = (
        select(
            PolicyApplicabilityRule,
            PolicyClause,
            PolicyVersion,
            PolicyDocument,
            SourceSnapshot,
        )
        .join(PolicyClause, PolicyApplicabilityRule.policy_clause_id == PolicyClause.id)
        .join(PolicyVersion, PolicyClause.policy_version_id == PolicyVersion.id)
        .join(PolicyDocument, PolicyVersion.document_id == PolicyDocument.id)
        .outerjoin(SourceSnapshot, PolicyVersion.source_snapshot_id == SourceSnapshot.id)
        .where(PolicyApplicabilityRule.jurisdiction_id == parcel.jurisdiction_id)
        .where(PolicyVersion.is_active.is_(True))
        .where(or_(PolicyDocument.effective_date.is_(None), PolicyDocument.effective_date <= func.current_date()))
        .where(or_(PolicyDocument.expiry_date.is_(None), PolicyDocument.expiry_date >= func.current_date()))
        .where(zone_match)
        .where(use_match)
        .where(
            or_(
                PolicyApplicabilityRule.geometry_filter.is_(None),
                func.ST_Intersects(PolicyApplicabilityRule.geometry_filter, parcel_geom),
            )
        )
    )

    rows = (await db.execute(query)).all()
    records = [
        PolicyStackRecord(
            clause_id=clause.id,
            policy_version_id=version.id,
            document_id=document.id,
            document_title=document.title,
            doc_type=document.doc_type,
            override_level=applicability.override_level,
            section_ref=clause.section_ref,
            page_ref=clause.page_ref,
            raw_text=clause.raw_text,
            normalized_type=clause.normalized_type,
            normalized_json=clause.normalized_json,
            applicability_json=applicability.applicability_json,
            confidence=clause.confidence,
            effective_date=document.effective_date,
            source_url=document.source_url,
            snapshot_id=snapshot.id if snapshot else None,
            snapshot_type=snapshot.snapshot_type if snapshot else None,
            snapshot_label=snapshot.version_label if snapshot else None,
            snapshot_published_at=snapshot.published_at if snapshot else None,
        )
        for applicability, clause, version, document, snapshot in rows
    ]
    return build_policy_stack_response(parcel.id, records)
