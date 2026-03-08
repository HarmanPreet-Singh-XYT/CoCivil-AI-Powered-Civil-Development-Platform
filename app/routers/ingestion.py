"""Admin endpoints for triggering data ingestion from Toronto Open Data."""

from __future__ import annotations

import threading
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db_session
from app.models.entitlement import BuildingPermit, DevelopmentApplication
from app.models.geospatial import Jurisdiction
from app.models.ingestion import IngestionJob

router = APIRouter()
logger = structlog.get_logger()

TORONTO_JURISDICTION = {"name": "Toronto", "province": "Ontario", "country": "CA"}


@router.post("/admin/ingest/building-permits")
async def ingest_building_permits(
    user: dict = Depends(get_current_user),
):
    """Trigger building permit ingestion from Toronto CKAN Open Data."""
    from app.tasks.ingestion import ingest_building_permits_task

    threading.Thread(target=ingest_building_permits_task, daemon=True).start()
    return {
        "status": "accepted",
        "message": "Building permit ingestion started",
    }


@router.post("/admin/ingest/coa-applications")
async def ingest_coa_applications(
    user: dict = Depends(get_current_user),
):
    """Trigger Committee of Adjustment application ingestion from Toronto CKAN."""
    from app.tasks.ingestion import ingest_coa_applications_task

    threading.Thread(target=ingest_coa_applications_task, daemon=True).start()
    return {
        "status": "accepted",
        "message": "COA application ingestion started",
    }


@router.post("/admin/ingest/water-mains")
async def ingest_water_mains(
    user: dict = Depends(get_current_user),
):
    """Trigger water main ingestion from Toronto CKAN Open Data."""
    from app.tasks.infrastructure_ingestion import ingest_water_mains_task

    threading.Thread(target=ingest_water_mains_task, daemon=True).start()
    return {
        "status": "accepted",
        "message": "Water main ingestion started",
    }


@router.post("/admin/ingest/sanitary-sewers")
async def ingest_sanitary_sewers(
    user: dict = Depends(get_current_user),
):
    """Trigger sanitary sewer ingestion from Toronto CKAN Open Data."""
    from app.tasks.infrastructure_ingestion import ingest_sanitary_sewers_task

    threading.Thread(target=ingest_sanitary_sewers_task, daemon=True).start()
    return {
        "status": "accepted",
        "message": "Sanitary sewer ingestion started",
    }


@router.post("/admin/ingest/storm-sewers")
async def ingest_storm_sewers(
    user: dict = Depends(get_current_user),
):
    """Trigger storm sewer ingestion from Toronto CKAN Open Data."""
    from app.tasks.infrastructure_ingestion import ingest_storm_sewers_task

    threading.Thread(target=ingest_storm_sewers_task, daemon=True).start()
    return {
        "status": "accepted",
        "message": "Storm sewer ingestion started",
    }


@router.post("/admin/ingest/bridges")
async def ingest_bridges(
    user: dict = Depends(get_current_user),
):
    """Trigger bridge inventory ingestion."""
    from app.tasks.infrastructure_ingestion import ingest_bridges_task

    threading.Thread(target=ingest_bridges_task, daemon=True).start()
    return {
        "status": "accepted",
        "message": "Bridge inventory ingestion started",
    }


@router.get("/admin/ingest/status")
async def get_ingestion_status(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Return counts and last ingestion job info for Toronto data."""
    permit_count = await db.scalar(select(func.count()).select_from(BuildingPermit))
    app_count = await db.scalar(select(func.count()).select_from(DevelopmentApplication))
    apps_with_decision = await db.scalar(
        select(func.count()).select_from(DevelopmentApplication).where(
            DevelopmentApplication.decision.isnot(None)
        )
    )

    # Last ingestion jobs
    last_permit_job = (
        await db.execute(
            select(IngestionJob)
            .where(IngestionJob.job_type.in_(["building_permits_ckan"]))
            .order_by(IngestionJob.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    last_coa_job = (
        await db.execute(
            select(IngestionJob)
            .where(IngestionJob.job_type.in_(["coa_applications_ckan"]))
            .order_by(IngestionJob.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    return {
        "building_permits": {
            "total_count": permit_count or 0,
            "last_job": {
                "status": last_permit_job.status,
                "records_processed": last_permit_job.records_processed,
                "records_failed": last_permit_job.records_failed,
                "completed_at": str(last_permit_job.completed_at) if last_permit_job.completed_at else None,
            } if last_permit_job else None,
        },
        "development_applications": {
            "total_count": app_count or 0,
            "with_decision": apps_with_decision or 0,
            "last_job": {
                "status": last_coa_job.status,
                "records_processed": last_coa_job.records_processed,
                "records_failed": last_coa_job.records_failed,
                "completed_at": str(last_coa_job.completed_at) if last_coa_job.completed_at else None,
            } if last_coa_job else None,
        },
    }
