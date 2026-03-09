import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select

from app.celery_app import celery
from app.database import get_sync_db
from app.models.dataset import DatasetLayer
from app.models.ingestion import SourceSnapshot
from app.models.policy import PolicyClause, PolicyReviewItem, PolicyVersion
from app.services.geospatial_ingestion import get_or_create_jurisdiction
logger = structlog.get_logger()


@celery.task(bind=True, max_retries=2)
def activate_source_snapshot(self, snapshot_id: str):
    db = get_sync_db()
    try:
        snapshot = db.query(SourceSnapshot).filter(SourceSnapshot.id == uuid.UUID(snapshot_id)).one_or_none()
        if not snapshot:
            raise ValueError("Source snapshot not found")

        db.query(SourceSnapshot).filter(
            SourceSnapshot.jurisdiction_id == snapshot.jurisdiction_id,
            SourceSnapshot.snapshot_type == snapshot.snapshot_type,
            SourceSnapshot.id != snapshot.id,
        ).update({"is_active": False, "published_at": snapshot.published_at}, synchronize_session=False)

        snapshot.is_active = True
        snapshot.published_at = snapshot.published_at or datetime.now(timezone.utc)
        db.commit()
        return {"snapshot_id": snapshot_id, "status": "activated"}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@celery.task(bind=True, max_retries=2)
def publish_policy_version(self, policy_version_id: str, source_snapshot_id: str | None = None):
    db = get_sync_db()
    try:
        version = db.query(PolicyVersion).filter(PolicyVersion.id == uuid.UUID(policy_version_id)).one_or_none()
        if not version:
            raise ValueError("Policy version not found")

        db.query(PolicyVersion).filter(
            PolicyVersion.document_id == version.document_id,
            PolicyVersion.id != version.id,
        ).update({"is_active": False}, synchronize_session=False)

        if source_snapshot_id:
            version.source_snapshot_id = uuid.UUID(source_snapshot_id)
        version.is_active = True
        version.published_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "policy_version_id": policy_version_id,
            "status": "published",
            "source_snapshot_id": source_snapshot_id,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@celery.task(bind=True, max_retries=2)
def sync_policy_review_items(self, policy_version_id: str, review_reason: str = "needs_review_flag"):
    db = get_sync_db()
    try:
        version_uuid = uuid.UUID(policy_version_id)
        clauses = db.execute(
            select(PolicyClause).where(
                PolicyClause.policy_version_id == version_uuid,
                PolicyClause.needs_review.is_(True),
            )
        ).scalars().all()

        created = 0
        for clause in clauses:
            existing = db.execute(
                select(PolicyReviewItem).where(
                    PolicyReviewItem.policy_clause_id == clause.id,
                    PolicyReviewItem.status.in_(("pending", "in_review")),
                )
            ).scalar_one_or_none()
            if existing:
                continue
            db.add(
                PolicyReviewItem(
                    policy_clause_id=clause.id,
                    status="pending",
                    review_reason=review_reason,
                )
            )
            created += 1

        db.commit()
        return {"policy_version_id": policy_version_id, "created_review_items": created}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@celery.task(bind=True, max_retries=2)
def publish_dataset_layer(self, dataset_layer_id: str, source_snapshot_id: str | None = None):
    db = get_sync_db()
    try:
        layer = db.query(DatasetLayer).filter(DatasetLayer.id == uuid.UUID(dataset_layer_id)).one_or_none()
        if not layer:
            raise ValueError("Dataset layer not found")

        if source_snapshot_id:
            layer.source_snapshot_id = uuid.UUID(source_snapshot_id)
        layer.last_refreshed = layer.last_refreshed or datetime.now(timezone.utc)
        layer.published_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(
            "dataset.layer.published",
            dataset_layer_id=dataset_layer_id,
            source_snapshot_id=source_snapshot_id,
        )
        return {
            "dataset_layer_id": dataset_layer_id,
            "status": "published",
            "source_snapshot_id": source_snapshot_id,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@celery.task(bind=True, max_retries=2)
def ingest_building_permits_task(self):
    """Ingest building permits from Toronto CKAN Open Data."""
    from app.services.ckan_ingestion import ingest_building_permits

    db = get_sync_db()
    try:
        jurisdiction = get_or_create_jurisdiction(db, name="Toronto")
        db.commit()
        summary = ingest_building_permits(db, jurisdiction.id)
        return {
            "status": "completed",
            "processed": summary.processed,
            "failed": summary.failed,
        }
    except Exception as e:
        logger.error("ingestion.building_permits.failed", error=str(e))
        raise
    finally:
        db.close()


@celery.task(bind=True, max_retries=2)
def ingest_coa_applications_task(self):
    """Ingest COA applications from Toronto CKAN Open Data."""
    from app.services.ckan_ingestion import ingest_coa_applications

    db = get_sync_db()
    try:
        jurisdiction = get_or_create_jurisdiction(db, name="Toronto")
        db.commit()
        summary = ingest_coa_applications(db, jurisdiction.id)
        return {
            "status": "completed",
            "processed": summary.processed,
            "failed": summary.failed,
        }
    except Exception as e:
        logger.error("ingestion.coa_applications.failed", error=str(e))
        raise
    finally:
        db.close()


@celery.task(bind=True, max_retries=2)
def ingest_toronto_open_data(self):
    """Run both building permit and COA ingestion sequentially."""
    from app.services.ckan_ingestion import ingest_building_permits, ingest_coa_applications

    db = get_sync_db()
    try:
        jurisdiction = get_or_create_jurisdiction(db, name="Toronto")
        db.commit()

        permit_summary = ingest_building_permits(db, jurisdiction.id)
        coa_summary = ingest_coa_applications(db, jurisdiction.id)

        return {
            "status": "completed",
            "building_permits": {
                "processed": permit_summary.processed,
                "failed": permit_summary.failed,
            },
            "coa_applications": {
                "processed": coa_summary.processed,
                "failed": coa_summary.failed,
            },
        }
    except Exception as e:
        logger.error("ingestion.toronto_open_data.failed", error=str(e))
        raise
    finally:
        db.close()
