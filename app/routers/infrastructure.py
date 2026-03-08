"""Infrastructure endpoints — nearby assets and compliance checks.

Returns GeoJSON FeatureCollections so the map can render infrastructure layers directly.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db_session
from app.models.infrastructure import BridgeAsset, PipelineAsset
from app.schemas.infrastructure import (
    BridgeComplianceRequest,
    PipelineComplianceRequest,
)
from app.services.infrastructure_compliance import (
    check_bridge_compliance,
    check_pipeline_compliance,
)

router = APIRouter()

# Pipe-type → hex color for map rendering
PIPE_COLORS = {
    "water_main": "#2277bb",
    "sanitary_sewer": "#886644",
    "storm_sewer": "#44aa66",
    "gas_line": "#ddaa22",
}


@router.get("/infrastructure/pipelines/nearby")
async def get_nearby_pipelines(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_m: float = Query(default=500, ge=1, le=10000),
    pipe_type: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Return pipeline assets as a GeoJSON FeatureCollection."""
    point_wkt = f"SRID=4326;POINT({lng} {lat})"
    type_filter = "AND pipe_type = :pipe_type" if pipe_type else ""
    result = await db.execute(
        text(f"""
            SELECT id, asset_id, pipe_type, material, diameter_mm,
                   install_year, depth_m, slope_pct, attributes_json,
                   ST_AsGeoJSON(geom)::json AS geometry,
                   ST_Distance(geom::geography, ST_GeomFromEWKT(:point)::geography) AS distance_m
            FROM pipeline_assets
            WHERE ST_DWithin(geom::geography, ST_GeomFromEWKT(:point)::geography, :radius)
              AND geom IS NOT NULL
              {type_filter}
            ORDER BY distance_m
            LIMIT 200
        """),
        {"point": point_wkt, "radius": radius_m, **({"pipe_type": pipe_type} if pipe_type else {})},
    )
    rows = result.mappings().all()
    features = []
    for row in rows:
        features.append({
            "type": "Feature",
            "geometry": row["geometry"],
            "properties": {
                "id": str(row["id"]),
                "asset_id": row["asset_id"],
                "pipe_type": row["pipe_type"],
                "material": row["material"],
                "diameter_mm": row["diameter_mm"],
                "install_year": row["install_year"],
                "depth_m": row["depth_m"],
                "slope_pct": row["slope_pct"],
                "distance_m": round(row["distance_m"], 1) if row["distance_m"] else None,
                "color": PIPE_COLORS.get(row["pipe_type"], "#888888"),
            },
        })
    return {"type": "FeatureCollection", "features": features}


@router.get("/infrastructure/bridges/nearby")
async def get_nearby_bridges(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_m: float = Query(default=2000, ge=1, le=50000),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Return bridge assets as a GeoJSON FeatureCollection."""
    point_wkt = f"SRID=4326;POINT({lng} {lat})"
    result = await db.execute(
        text("""
            SELECT id, asset_id, bridge_type, structure_type, span_m,
                   deck_width_m, clearance_m, year_built, condition_rating,
                   road_name, crossing_name, attributes_json,
                   ST_AsGeoJSON(COALESCE(geom, ST_StartPoint(geom_line)))::json AS geometry,
                   ST_AsGeoJSON(geom_line)::json AS line_geometry,
                   ST_Distance(
                       COALESCE(geom, ST_StartPoint(geom_line))::geography,
                       ST_GeomFromEWKT(:point)::geography
                   ) AS distance_m
            FROM bridge_assets
            WHERE ST_DWithin(
                COALESCE(geom, ST_StartPoint(geom_line))::geography,
                ST_GeomFromEWKT(:point)::geography,
                :radius
            )
              AND (geom IS NOT NULL OR geom_line IS NOT NULL)
            ORDER BY distance_m
            LIMIT 100
        """),
        {"point": point_wkt, "radius": radius_m},
    )
    rows = result.mappings().all()
    features = []
    for row in rows:
        features.append({
            "type": "Feature",
            "geometry": row["geometry"],
            "properties": {
                "id": str(row["id"]),
                "asset_id": row["asset_id"],
                "bridge_type": row["bridge_type"],
                "structure_type": row["structure_type"],
                "span_m": row["span_m"],
                "deck_width_m": row["deck_width_m"],
                "clearance_m": row["clearance_m"],
                "year_built": row["year_built"],
                "condition_rating": row["condition_rating"],
                "road_name": row["road_name"],
                "crossing_name": row["crossing_name"],
                "distance_m": round(row["distance_m"], 1) if row["distance_m"] else None,
                "line_geometry": row["line_geometry"],
            },
        })
    return {"type": "FeatureCollection", "features": features}


@router.post("/infrastructure/compliance/pipeline")
async def check_pipeline(
    body: PipelineComplianceRequest,
    user: dict = Depends(get_current_user),
):
    """Run deterministic compliance check for a pipeline."""
    params = body.model_dump(exclude={"pipe_type"}, exclude_none=True)
    result = check_pipeline_compliance(body.pipe_type, params)
    return {
        "overall_compliant": result.overall_compliant,
        "rules": [asdict(r) for r in result.rules],
        "variances_needed": [asdict(r) for r in result.variances_needed],
        "warnings": result.warnings,
    }


@router.post("/infrastructure/compliance/bridge")
async def check_bridge(
    body: BridgeComplianceRequest,
    user: dict = Depends(get_current_user),
):
    """Run deterministic compliance check for a bridge."""
    params = body.model_dump(exclude={"bridge_type"}, exclude_none=True)
    result = check_bridge_compliance(body.bridge_type, params)
    return {
        "overall_compliant": result.overall_compliant,
        "rules": [asdict(r) for r in result.rules],
        "variances_needed": [asdict(r) for r in result.variances_needed],
        "warnings": result.warnings,
    }
