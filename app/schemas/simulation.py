import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.services.thin_slice_runtime import GeometryDefaults, LayoutDefaults, MassingTemplateParameters


class MassingRequest(BaseModel):
    template_id: uuid.UUID | None = None
    parameters: dict[str, Any] | None = None


class MassingTemplateReferenceResponse(BaseModel):
    id: uuid.UUID
    name: str
    typology: str
    parameters_json: MassingTemplateParameters
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UnitTypeReferenceResponse(BaseModel):
    id: uuid.UUID
    jurisdiction_id: uuid.UUID | None = None
    name: str
    bedroom_count: int
    min_area_m2: float
    max_area_m2: float
    typical_area_m2: float
    min_width_m: float | None = None
    is_accessible: bool

    model_config = ConfigDict(from_attributes=True)


class MassingSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    typology: str | None = None
    lot_area_m2: float | None = None
    buildable_floorplate_m2: float | None = None
    storeys: int | None = None
    height_m: float | None = None
    estimated_gfa_m2: float | None = None
    estimated_gla_m2: float | None = None
    estimated_fsi: float | None = None
    lot_coverage_pct: float | None = None
    assumptions_used: MassingTemplateParameters | dict[str, Any] | None = None


class MassingComplianceResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str | None = None
    warnings: list[str] = Field(default_factory=list)
    max_fsi_applied: float | None = None
    stepback_m: float | None = None
    angular_plane_ratio: float | None = None


class MassingResponse(BaseModel):
    id: uuid.UUID
    scenario_run_id: uuid.UUID
    template_id: uuid.UUID | None = None
    template_name: str | None = None
    geometry_3d_key: str | None = None
    total_gfa_m2: float | None = None
    total_gla_m2: float | None = None
    storeys: int | None = None
    height_m: float | None = None
    lot_coverage_pct: float | None = None
    fsi: float | None = None
    summary_json: MassingSummaryResponse | dict[str, Any] | None = None
    compliance_json: MassingComplianceResponse | dict[str, Any] | None = None
    template: MassingTemplateReferenceResponse | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LayoutRunRequest(BaseModel):
    unit_types: list[uuid.UUID] | None = None
    optimization_objective: str = "max_revenue"
    parameters: dict[str, Any] | None = None


class LayoutAllocationResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    unit_type_id: uuid.UUID | str | None = None
    name: str | None = None
    bedroom_count: int | None = None
    count: int | None = None
    typical_area_m2: float | None = None
    allocated_area_m2: float | None = None
    is_accessible: bool | None = None


class LayoutAssumptionsUsedResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    layout_defaults: LayoutDefaults | dict[str, Any] | None = None
    geometry_defaults: GeometryDefaults | dict[str, Any] | None = None


class LayoutResultResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    objective: str | None = None
    available_area_m2: float | None = None
    allocated_area_m2: float | None = None
    unallocated_area_m2: float | None = None
    total_units: int | None = None
    parking_required: float | None = None
    amenity_required_m2: float | None = None
    accessible_units_required: int | None = None
    accessible_units_supplied: int | None = None
    allocations: list[LayoutAllocationResponse] = Field(default_factory=list)
    assumptions_used: LayoutAssumptionsUsedResponse | dict[str, Any] | None = None


class LayoutRunResponse(BaseModel):
    id: uuid.UUID
    massing_id: uuid.UUID
    status: str
    objective: str | None = None
    constraints_json: dict[str, Any] | None = None
    result_json: LayoutResultResponse | dict[str, Any] | None = None
    total_units: int | None = None
    total_area_m2: float | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
