"""CKAN Open Data ingestion for Toronto infrastructure assets (water, sewer, bridges)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog
from geoalchemy2 import WKTElement
from pyproj import Transformer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.infrastructure import BridgeAsset, PipelineAsset
from app.services.geospatial_ingestion import (
    IngestionSummary,
    _coerce_float,
    _now,
    create_ingestion_job,
    create_snapshot,
    get_or_create_jurisdiction,
    publish_snapshot,
    _finalize_job,
)

logger = structlog.get_logger()

CKAN_BASE = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action"
CKAN_PAGE_SIZE = 100

# UTM Zone 17N -> WGS84
_utm_transformer = Transformer.from_crs("EPSG:26917", "EPSG:4326", always_xy=True)


def _discover_resource_id(package_name: str) -> str:
    """Discover the datastore resource_id for a CKAN package (sync HTTP)."""
    url = f"{CKAN_BASE}/package_show"
    resp = httpx.get(url, params={"id": package_name}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    resources = data.get("result", {}).get("resources", [])
    for r in resources:
        if r.get("datastore_active"):
            return r["id"]
    if resources:
        return resources[0]["id"]
    raise ValueError(f"No resources found for CKAN package: {package_name}")


def _fetch_ckan_records(resource_id: str, bbox: dict | None = None) -> list[dict[str, Any]]:
    """Fetch all records from a CKAN datastore resource, handling pagination."""
    all_records: list[dict[str, Any]] = []
    offset = 0
    while True:
        params: dict[str, Any] = {
            "resource_id": resource_id,
            "limit": CKAN_PAGE_SIZE,
            "offset": offset,
        }
        resp = httpx.get(
            f"{CKAN_BASE}/datastore_search",
            params=params,
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json().get("result", {})
        records = result.get("records", [])
        if not records:
            break
        all_records.extend(records)
        offset += len(records)
        if len(records) < CKAN_PAGE_SIZE:
            break
    return all_records


def _content_hash(records: list[dict]) -> str:
    """Compute a hash of the fetched records for snapshot tracking."""
    raw = str(sorted(str(r) for r in records[:100]))
    return hashlib.sha256(raw.encode()).hexdigest()


def _parse_geometry_linestring(rec: dict) -> WKTElement | None:
    """Parse geometry from CKAN record as LineString."""
    geom = rec.get("geometry") or rec.get("GEOMETRY")
    if geom and isinstance(geom, dict):
        coords = geom.get("coordinates", [])
        if coords and geom.get("type") == "LineString":
            coord_str = ", ".join(f"{c[0]} {c[1]}" for c in coords)
            return WKTElement(f"LINESTRING ({coord_str})", srid=4326)

    # Fallback: try X/Y fields as UTM for start/end point as line
    x1 = _coerce_float(rec.get("X") or rec.get("X_START"))
    y1 = _coerce_float(rec.get("Y") or rec.get("Y_START"))
    x2 = _coerce_float(rec.get("X_END"))
    y2 = _coerce_float(rec.get("Y_END"))
    if x1 is not None and y1 is not None:
        if x1 > 1000:
            lon1, lat1 = _utm_transformer.transform(x1, y1)
        else:
            lon1, lat1 = x1, y1
        if x2 is not None and y2 is not None:
            if x2 > 1000:
                lon2, lat2 = _utm_transformer.transform(x2, y2)
            else:
                lon2, lat2 = x2, y2
            return WKTElement(f"LINESTRING ({lon1} {lat1}, {lon2} {lat2})", srid=4326)
        return WKTElement(f"LINESTRING ({lon1} {lat1}, {lon1} {lat1})", srid=4326)
    return None


def _parse_geometry_point(rec: dict) -> WKTElement | None:
    """Parse geometry from CKAN record as Point."""
    lat = _coerce_float(rec.get("LATITUDE") or rec.get("Y"))
    lon = _coerce_float(rec.get("LONGITUDE") or rec.get("X"))
    if lat is not None and lon is not None:
        if lon > 1000:
            lon, lat = _utm_transformer.transform(lon, lat)
        return WKTElement(f"POINT ({lon} {lat})", srid=4326)
    return None


def ingest_water_mains(
    db: Session,
    jurisdiction_id: uuid.UUID,
    bbox: dict | None = None,
) -> IngestionSummary:
    """Fetch water mains from Toronto CKAN and upsert into pipeline_assets."""
    logger.info("ckan.water_mains.starting")
    resource_id = _discover_resource_id("watermains")
    records = _fetch_ckan_records(resource_id, bbox)
    logger.info("ckan.water_mains.fetched", count=len(records))

    snapshot = create_snapshot(
        db,
        jurisdiction_id=jurisdiction_id,
        snapshot_type="water_mains_ckan",
        version_label=f"ckan-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        source_url=f"{CKAN_BASE}/datastore_search?resource_id={resource_id}",
        publisher="City of Toronto Open Data",
        file_hash=_content_hash(records),
        schema_version="ckan-datastore",
    )
    job = create_ingestion_job(
        db,
        jurisdiction_id=jurisdiction_id,
        source_url=f"{CKAN_BASE}/datastore_search?resource_id={resource_id}",
        source_snapshot_id=snapshot.id,
        job_type="water_mains_ckan",
    )

    summary = IngestionSummary(issues=[])
    seen: set[str] = set()

    for idx, rec in enumerate(records):
        asset_id = str(rec.get("_id") or rec.get("OBJECTID") or idx)
        if asset_id in seen:
            continue
        seen.add(asset_id)

        existing = db.execute(
            select(PipelineAsset).where(
                PipelineAsset.jurisdiction_id == jurisdiction_id,
                PipelineAsset.asset_id == asset_id,
                PipelineAsset.pipe_type == "water_main",
            )
        ).scalar_one_or_none()
        if existing:
            summary.processed += 1
            continue

        asset = PipelineAsset(
            jurisdiction_id=jurisdiction_id,
            source_snapshot_id=snapshot.id,
            asset_id=asset_id,
            pipe_type="water_main",
            material=rec.get("MATERIAL") or rec.get("PIPE_MATERIAL"),
            diameter_mm=_coerce_float(rec.get("DIAMETER") or rec.get("DIAMETER_MM")),
            install_year=int(rec["INSTALL_YEAR"]) if rec.get("INSTALL_YEAR") else None,
            depth_m=_coerce_float(rec.get("DEPTH") or rec.get("DEPTH_M")),
            slope_pct=_coerce_float(rec.get("SLOPE") or rec.get("SLOPE_PCT")),
            geom=_parse_geometry_linestring(rec),
            attributes_json={
                k: v for k, v in rec.items()
                if k not in {"_id", "OBJECTID", "MATERIAL", "PIPE_MATERIAL",
                             "DIAMETER", "DIAMETER_MM", "INSTALL_YEAR",
                             "DEPTH", "DEPTH_M", "SLOPE", "SLOPE_PCT",
                             "geometry", "GEOMETRY", "X", "Y",
                             "X_START", "Y_START", "X_END", "Y_END"}
            },
        )
        db.add(asset)
        summary.processed += 1

    publish_snapshot(db, snapshot, validation_summary=summary.as_json())
    _finalize_job(job, summary)
    db.commit()

    logger.info("ckan.water_mains.completed", processed=summary.processed, failed=summary.failed)
    return summary


def ingest_sanitary_sewers(
    db: Session,
    jurisdiction_id: uuid.UUID,
    bbox: dict | None = None,
) -> IngestionSummary:
    """Fetch sanitary sewers from Toronto CKAN and upsert into pipeline_assets."""
    logger.info("ckan.sanitary_sewers.starting")
    resource_id = _discover_resource_id("sewer-gravity-mains")
    records = _fetch_ckan_records(resource_id, bbox)
    logger.info("ckan.sanitary_sewers.fetched", count=len(records))

    snapshot = create_snapshot(
        db,
        jurisdiction_id=jurisdiction_id,
        snapshot_type="sanitary_sewers_ckan",
        version_label=f"ckan-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        source_url=f"{CKAN_BASE}/datastore_search?resource_id={resource_id}",
        publisher="City of Toronto Open Data",
        file_hash=_content_hash(records),
        schema_version="ckan-datastore",
    )
    job = create_ingestion_job(
        db,
        jurisdiction_id=jurisdiction_id,
        source_url=f"{CKAN_BASE}/datastore_search?resource_id={resource_id}",
        source_snapshot_id=snapshot.id,
        job_type="sanitary_sewers_ckan",
    )

    summary = IngestionSummary(issues=[])
    seen: set[str] = set()

    for idx, rec in enumerate(records):
        asset_id = str(rec.get("_id") or rec.get("OBJECTID") or idx)
        if asset_id in seen:
            continue
        seen.add(asset_id)

        existing = db.execute(
            select(PipelineAsset).where(
                PipelineAsset.jurisdiction_id == jurisdiction_id,
                PipelineAsset.asset_id == asset_id,
                PipelineAsset.pipe_type == "sanitary_sewer",
            )
        ).scalar_one_or_none()
        if existing:
            summary.processed += 1
            continue

        asset = PipelineAsset(
            jurisdiction_id=jurisdiction_id,
            source_snapshot_id=snapshot.id,
            asset_id=asset_id,
            pipe_type="sanitary_sewer",
            material=rec.get("MATERIAL") or rec.get("PIPE_MATERIAL"),
            diameter_mm=_coerce_float(rec.get("DIAMETER") or rec.get("DIAMETER_MM")),
            install_year=int(rec["INSTALL_YEAR"]) if rec.get("INSTALL_YEAR") else None,
            depth_m=_coerce_float(rec.get("DEPTH") or rec.get("DEPTH_M")),
            slope_pct=_coerce_float(rec.get("SLOPE") or rec.get("SLOPE_PCT")),
            geom=_parse_geometry_linestring(rec),
            attributes_json={
                k: v for k, v in rec.items()
                if k not in {"_id", "OBJECTID", "MATERIAL", "PIPE_MATERIAL",
                             "DIAMETER", "DIAMETER_MM", "INSTALL_YEAR",
                             "DEPTH", "DEPTH_M", "SLOPE", "SLOPE_PCT",
                             "geometry", "GEOMETRY", "X", "Y",
                             "X_START", "Y_START", "X_END", "Y_END"}
            },
        )
        db.add(asset)
        summary.processed += 1

    publish_snapshot(db, snapshot, validation_summary=summary.as_json())
    _finalize_job(job, summary)
    db.commit()

    logger.info("ckan.sanitary_sewers.completed", processed=summary.processed, failed=summary.failed)
    return summary


def ingest_storm_sewers(
    db: Session,
    jurisdiction_id: uuid.UUID,
    bbox: dict | None = None,
) -> IngestionSummary:
    """Fetch storm sewers from Toronto CKAN and upsert into pipeline_assets."""
    logger.info("ckan.storm_sewers.starting")
    resource_id = _discover_resource_id("sewer-pressurized-mains")
    records = _fetch_ckan_records(resource_id, bbox)
    logger.info("ckan.storm_sewers.fetched", count=len(records))

    snapshot = create_snapshot(
        db,
        jurisdiction_id=jurisdiction_id,
        snapshot_type="storm_sewers_ckan",
        version_label=f"ckan-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        source_url=f"{CKAN_BASE}/datastore_search?resource_id={resource_id}",
        publisher="City of Toronto Open Data",
        file_hash=_content_hash(records),
        schema_version="ckan-datastore",
    )
    job = create_ingestion_job(
        db,
        jurisdiction_id=jurisdiction_id,
        source_url=f"{CKAN_BASE}/datastore_search?resource_id={resource_id}",
        source_snapshot_id=snapshot.id,
        job_type="storm_sewers_ckan",
    )

    summary = IngestionSummary(issues=[])
    seen: set[str] = set()

    for idx, rec in enumerate(records):
        asset_id = str(rec.get("_id") or rec.get("OBJECTID") or idx)
        if asset_id in seen:
            continue
        seen.add(asset_id)

        existing = db.execute(
            select(PipelineAsset).where(
                PipelineAsset.jurisdiction_id == jurisdiction_id,
                PipelineAsset.asset_id == asset_id,
                PipelineAsset.pipe_type == "storm_sewer",
            )
        ).scalar_one_or_none()
        if existing:
            summary.processed += 1
            continue

        asset = PipelineAsset(
            jurisdiction_id=jurisdiction_id,
            source_snapshot_id=snapshot.id,
            asset_id=asset_id,
            pipe_type="storm_sewer",
            material=rec.get("MATERIAL") or rec.get("PIPE_MATERIAL"),
            diameter_mm=_coerce_float(rec.get("DIAMETER") or rec.get("DIAMETER_MM")),
            install_year=int(rec["INSTALL_YEAR"]) if rec.get("INSTALL_YEAR") else None,
            depth_m=_coerce_float(rec.get("DEPTH") or rec.get("DEPTH_M")),
            slope_pct=_coerce_float(rec.get("SLOPE") or rec.get("SLOPE_PCT")),
            geom=_parse_geometry_linestring(rec),
            attributes_json={
                k: v for k, v in rec.items()
                if k not in {"_id", "OBJECTID", "MATERIAL", "PIPE_MATERIAL",
                             "DIAMETER", "DIAMETER_MM", "INSTALL_YEAR",
                             "DEPTH", "DEPTH_M", "SLOPE", "SLOPE_PCT",
                             "geometry", "GEOMETRY", "X", "Y",
                             "X_START", "Y_START", "X_END", "Y_END"}
            },
        )
        db.add(asset)
        summary.processed += 1

    publish_snapshot(db, snapshot, validation_summary=summary.as_json())
    _finalize_job(job, summary)
    db.commit()

    logger.info("ckan.storm_sewers.completed", processed=summary.processed, failed=summary.failed)
    return summary


def ingest_bridge_inventory(
    db: Session,
    jurisdiction_id: uuid.UUID,
) -> IngestionSummary:
    """Fetch bridge inventory from Ontario/MTO data and upsert into bridge_assets.

    Note: Bridge data may come from MTO or municipal datasets.
    This function attempts to discover a CKAN package first, then falls back.
    """
    logger.info("ckan.bridges.starting")
    try:
        resource_id = _discover_resource_id("bridge-structure")
    except (ValueError, httpx.HTTPError):
        logger.warning("ckan.bridges.no_ckan_package", msg="Bridge CKAN package not found, skipping")
        return IngestionSummary(issues=[{"reason": "no_ckan_package_found"}])

    records = _fetch_ckan_records(resource_id)
    logger.info("ckan.bridges.fetched", count=len(records))

    snapshot = create_snapshot(
        db,
        jurisdiction_id=jurisdiction_id,
        snapshot_type="bridges_ckan",
        version_label=f"ckan-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        source_url=f"{CKAN_BASE}/datastore_search?resource_id={resource_id}",
        publisher="City of Toronto / MTO",
        file_hash=_content_hash(records),
        schema_version="ckan-datastore",
    )
    job = create_ingestion_job(
        db,
        jurisdiction_id=jurisdiction_id,
        source_url=f"{CKAN_BASE}/datastore_search?resource_id={resource_id}",
        source_snapshot_id=snapshot.id,
        job_type="bridges_ckan",
    )

    summary = IngestionSummary(issues=[])
    seen: set[str] = set()

    for idx, rec in enumerate(records):
        asset_id = str(rec.get("_id") or rec.get("OBJECTID") or rec.get("STRUCTURE_ID") or idx)
        if asset_id in seen:
            continue
        seen.add(asset_id)

        existing = db.execute(
            select(BridgeAsset).where(
                BridgeAsset.jurisdiction_id == jurisdiction_id,
                BridgeAsset.asset_id == asset_id,
            )
        ).scalar_one_or_none()
        if existing:
            summary.processed += 1
            continue

        # Determine bridge type
        type_raw = (rec.get("STRUCTURE_TYPE") or rec.get("TYPE") or "road_bridge").lower()
        if "culvert" in type_raw:
            bridge_type = "culvert"
        elif "pedestrian" in type_raw or "foot" in type_raw:
            bridge_type = "pedestrian_bridge"
        else:
            bridge_type = "road_bridge"

        # Determine structure type
        struct_raw = (rec.get("SUPERSTRUCTURE_TYPE") or rec.get("STRUCTURE_MATERIAL") or "").lower()
        structure_type = None
        if "steel" in struct_raw and "truss" in struct_raw:
            structure_type = "steel_truss"
        elif "steel" in struct_raw:
            structure_type = "steel_beam"
        elif "concrete" in struct_raw and "slab" in struct_raw:
            structure_type = "concrete_slab"
        elif "concrete" in struct_raw and "girder" in struct_raw:
            structure_type = "concrete_girder"
        elif "arch" in struct_raw:
            structure_type = "arch"
        elif "box" in struct_raw or "culvert" in struct_raw:
            structure_type = "box_culvert"

        asset = BridgeAsset(
            jurisdiction_id=jurisdiction_id,
            source_snapshot_id=snapshot.id,
            asset_id=asset_id,
            bridge_type=bridge_type,
            structure_type=structure_type,
            span_m=_coerce_float(rec.get("SPAN_M") or rec.get("SPAN_LENGTH")),
            deck_width_m=_coerce_float(rec.get("DECK_WIDTH") or rec.get("DECK_WIDTH_M")),
            clearance_m=_coerce_float(rec.get("CLEARANCE") or rec.get("VERTICAL_CLEARANCE")),
            year_built=int(float(rec["YEAR_BUILT"])) if rec.get("YEAR_BUILT") and str(rec["YEAR_BUILT"]).strip() not in ("", "None", "null") else None,
            condition_rating=rec.get("BCI") or rec.get("CONDITION_RATING"),
            road_name=rec.get("ROAD_NAME") or rec.get("FEATURE_CARRIED"),
            crossing_name=rec.get("CROSSING_NAME") or rec.get("FEATURE_CROSSED"),
            geom=_parse_geometry_point(rec),
            geom_line=_parse_geometry_linestring(rec),
            attributes_json={
                k: v for k, v in rec.items()
                if k not in {"_id", "OBJECTID", "STRUCTURE_ID", "STRUCTURE_TYPE",
                             "TYPE", "SUPERSTRUCTURE_TYPE", "STRUCTURE_MATERIAL",
                             "SPAN_M", "SPAN_LENGTH", "DECK_WIDTH", "DECK_WIDTH_M",
                             "CLEARANCE", "VERTICAL_CLEARANCE", "YEAR_BUILT",
                             "BCI", "CONDITION_RATING", "ROAD_NAME",
                             "FEATURE_CARRIED", "CROSSING_NAME", "FEATURE_CROSSED",
                             "geometry", "GEOMETRY", "X", "Y",
                             "LATITUDE", "LONGITUDE"}
            },
        )
        db.add(asset)
        summary.processed += 1

    publish_snapshot(db, snapshot, validation_summary=summary.as_json())
    _finalize_job(job, summary)
    db.commit()

    logger.info("ckan.bridges.completed", processed=summary.processed, failed=summary.failed)
    return summary
