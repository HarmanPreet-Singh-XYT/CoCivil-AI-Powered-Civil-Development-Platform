"""Pydantic schemas for infrastructure endpoints."""

from typing import Literal

from pydantic import BaseModel, Field


class PipelineComplianceRequest(BaseModel):
    pipe_type: Literal["water_main", "sanitary_sewer", "storm_sewer", "gas_line"]
    diameter_mm: float | None = None
    cover_m: float | None = None
    slope_pct: float | None = None
    velocity_m_s: float | None = None
    manhole_spacing_m: float | None = None
    material: str | None = None
    separation_from_water_m: float | None = None


class BridgeComplianceRequest(BaseModel):
    bridge_type: Literal["road_bridge", "pedestrian_bridge", "culvert"]
    deck_width_m: float | None = None
    clearance_m: float | None = None
    barrier_height_m: float | None = None
    structure_type: str | None = None
    span_m: float | None = None
    structural_depth_m: float | None = None
    cover_m: float | None = None


class NearbyPipelineRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    radius_m: float = Field(default=500, ge=1, le=10000)


class NearbyBridgeRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    radius_m: float = Field(default=2000, ge=1, le=50000)


class PipelineAssetResponse(BaseModel):
    id: str
    asset_id: str
    pipe_type: str
    material: str | None = None
    diameter_mm: float | None = None
    install_year: int | None = None
    depth_m: float | None = None
    slope_pct: float | None = None
    distance_m: float | None = None

    class Config:
        from_attributes = True


class BridgeAssetResponse(BaseModel):
    id: str
    asset_id: str
    bridge_type: str
    structure_type: str | None = None
    span_m: float | None = None
    deck_width_m: float | None = None
    clearance_m: float | None = None
    year_built: int | None = None
    condition_rating: str | None = None
    road_name: str | None = None
    crossing_name: str | None = None
    distance_m: float | None = None

    class Config:
        from_attributes = True


class InfraModelUpdate(BaseModel):
    pipe_type: str | None = None
    material: str | None = None
    diameter_mm: float | None = None
    depth_m: float | None = None
    slope_pct: float | None = None
    bridge_type: str | None = None
    structure_type: str | None = None
    span_m: float | None = None
    deck_width_m: float | None = None
    clearance_m: float | None = None
    warnings: list[str] | None = None


class InfraModelParseRequest(BaseModel):
    text: str
    asset_type: Literal["pipeline", "bridge"]
    current_params: dict | None = None


class InfraModelParseResponse(BaseModel):
    asset_type: str
    params: dict
    warnings: list[str] | None = None
