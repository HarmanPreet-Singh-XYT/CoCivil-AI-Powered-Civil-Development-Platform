"""Background tasks for infrastructure data ingestion."""

import structlog

from app.celery_app import celery
from app.database import get_sync_db
from app.services.geospatial_ingestion import get_or_create_jurisdiction

logger = structlog.get_logger()


@celery.task(bind=True, max_retries=2)
def ingest_water_mains_task(self):
    """Ingest water mains from Toronto CKAN Open Data."""
    from app.services.infrastructure_ingestion import ingest_water_mains

    db = get_sync_db()
    try:
        jurisdiction = get_or_create_jurisdiction(db, name="Toronto")
        db.commit()
        summary = ingest_water_mains(db, jurisdiction.id)
        return {
            "status": "completed",
            "processed": summary.processed,
            "failed": summary.failed,
        }
    except Exception as e:
        logger.error("ingestion.water_mains.failed", error=str(e))
        raise
    finally:
        db.close()


@celery.task(bind=True, max_retries=2)
def ingest_sanitary_sewers_task(self):
    """Ingest sanitary sewers from Toronto CKAN Open Data."""
    from app.services.infrastructure_ingestion import ingest_sanitary_sewers

    db = get_sync_db()
    try:
        jurisdiction = get_or_create_jurisdiction(db, name="Toronto")
        db.commit()
        summary = ingest_sanitary_sewers(db, jurisdiction.id)
        return {
            "status": "completed",
            "processed": summary.processed,
            "failed": summary.failed,
        }
    except Exception as e:
        logger.error("ingestion.sanitary_sewers.failed", error=str(e))
        raise
    finally:
        db.close()


@celery.task(bind=True, max_retries=2)
def ingest_storm_sewers_task(self):
    """Ingest storm sewers from Toronto CKAN Open Data."""
    from app.services.infrastructure_ingestion import ingest_storm_sewers

    db = get_sync_db()
    try:
        jurisdiction = get_or_create_jurisdiction(db, name="Toronto")
        db.commit()
        summary = ingest_storm_sewers(db, jurisdiction.id)
        return {
            "status": "completed",
            "processed": summary.processed,
            "failed": summary.failed,
        }
    except Exception as e:
        logger.error("ingestion.storm_sewers.failed", error=str(e))
        raise
    finally:
        db.close()


@celery.task(bind=True, max_retries=2)
def ingest_bridges_task(self):
    """Ingest bridge inventory data."""
    from app.services.infrastructure_ingestion import ingest_bridge_inventory

    db = get_sync_db()
    try:
        jurisdiction = get_or_create_jurisdiction(db, name="Toronto")
        db.commit()
        summary = ingest_bridge_inventory(db, jurisdiction.id)
        return {
            "status": "completed",
            "processed": summary.processed,
            "failed": summary.failed,
        }
    except Exception as e:
        logger.error("ingestion.bridges.failed", error=str(e))
        raise
    finally:
        db.close()
