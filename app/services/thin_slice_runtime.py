from __future__ import annotations

import math
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.finance import FinancialAssumptionSet
from app.models.geospatial import Jurisdiction, Parcel, ProjectParcel
from app.models.simulation import MassingTemplate, UnitType
from app.models.tenant import ScenarioRun


class GeometryDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    residential_floor_to_floor_m: float = Field(gt=0)
    retail_floor_to_floor_m: float = Field(gt=0)
    efficiency_pct: float = Field(gt=0, le=1)
    max_lot_coverage_pct: float = Field(gt=0, le=1)
    parking_spaces_per_unit: float = Field(ge=0)
    amenity_area_per_unit_m2: float = Field(ge=0)
    accessible_unit_pct: float = Field(ge=0, le=1)


class LayoutDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_mix_targets: dict[str, float]
    objective: str = "max_revenue"


class PolicyGeometryDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_fsi: float = Field(gt=0)
    angular_plane_ratio: float = Field(gt=0)
    stepback_m: float = Field(ge=0)


class MassingTemplateParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    typology: str
    target_height_m: float = Field(gt=0)
    target_storeys: int = Field(gt=0)
    geometry_defaults: GeometryDefaults
    layout_defaults: LayoutDefaults
    policy_geometry_defaults: PolicyGeometryDefaults


class RevenueAssumptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rate_per_m2_by_unit_type: dict[str, float]
    annualization_factor: float = Field(gt=0, default=1.0)


class CostAssumptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hard_cost_per_m2: float = Field(gt=0)
    soft_cost_pct: float = Field(ge=0, le=1)
    opex_pct_of_revenue: float = Field(ge=0, le=1)
    contingency_pct: float = Field(ge=0, le=1)


class ValuationAssumptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cap_rate: float | None = Field(default=None, gt=0, lt=1)


class FinancingAssumptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loan_to_cost_pct: float = Field(ge=0, le=1)
    interest_rate: float = Field(ge=0, lt=1)


class FinancialAssumptionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenure: str
    revenue_assumptions: RevenueAssumptions
    cost_assumptions: CostAssumptions
    vacancy_rate: float = Field(ge=0, le=1)
    absorption_months: int = Field(ge=0)
    valuation: ValuationAssumptions
    financing: FinancingAssumptions


@dataclass(slots=True)
class ResolvedProjectContext:
    scenario: ScenarioRun
    parcel: Parcel


TORONTO_MASSING_TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "name": "Toronto Tower on Podium",
        "typology": "tower_on_podium",
        "parameters_json": {
            "typology": "tower_on_podium",
            "target_height_m": 84.0,
            "target_storeys": 28,
            "geometry_defaults": {
                "residential_floor_to_floor_m": 3.0,
                "retail_floor_to_floor_m": 4.5,
                "efficiency_pct": 0.82,
                "max_lot_coverage_pct": 0.45,
                "parking_spaces_per_unit": 0.35,
                "amenity_area_per_unit_m2": 2.0,
                "accessible_unit_pct": 0.15,
            },
            "layout_defaults": {
                "unit_mix_targets": {
                    "studio": 0.15,
                    "one_bed": 0.4,
                    "two_bed": 0.35,
                    "three_bed": 0.1,
                },
                "objective": "max_revenue",
            },
            "policy_geometry_defaults": {
                "max_fsi": 10.0,
                "angular_plane_ratio": 1.5,
                "stepback_m": 3.0,
            },
        },
    },
    {
        "name": "Toronto Mid-Rise",
        "typology": "midrise",
        "parameters_json": {
            "typology": "midrise",
            "target_height_m": 30.0,
            "target_storeys": 10,
            "geometry_defaults": {
                "residential_floor_to_floor_m": 3.0,
                "retail_floor_to_floor_m": 4.2,
                "efficiency_pct": 0.85,
                "max_lot_coverage_pct": 0.6,
                "parking_spaces_per_unit": 0.45,
                "amenity_area_per_unit_m2": 1.8,
                "accessible_unit_pct": 0.15,
            },
            "layout_defaults": {
                "unit_mix_targets": {
                    "studio": 0.1,
                    "one_bed": 0.35,
                    "two_bed": 0.4,
                    "three_bed": 0.15,
                },
                "objective": "max_revenue",
            },
            "policy_geometry_defaults": {
                "max_fsi": 4.5,
                "angular_plane_ratio": 1.0,
                "stepback_m": 2.0,
            },
        },
    },
    {
        "name": "Toronto Townhouse",
        "typology": "townhouse",
        "parameters_json": {
            "typology": "townhouse",
            "target_height_m": 12.0,
            "target_storeys": 4,
            "geometry_defaults": {
                "residential_floor_to_floor_m": 3.0,
                "retail_floor_to_floor_m": 4.0,
                "efficiency_pct": 0.9,
                "max_lot_coverage_pct": 0.55,
                "parking_spaces_per_unit": 1.0,
                "amenity_area_per_unit_m2": 1.0,
                "accessible_unit_pct": 0.1,
            },
            "layout_defaults": {
                "unit_mix_targets": {
                    "two_bed": 0.5,
                    "three_bed": 0.5,
                },
                "objective": "max_revenue",
            },
            "policy_geometry_defaults": {
                "max_fsi": 1.5,
                "angular_plane_ratio": 0.8,
                "stepback_m": 1.5,
            },
        },
    },
    {
        "name": "Toronto Mixed-Use Mid-Rise",
        "typology": "mixed_use_midrise",
        "parameters_json": {
            "typology": "mixed_use_midrise",
            "target_height_m": 36.0,
            "target_storeys": 12,
            "geometry_defaults": {
                "residential_floor_to_floor_m": 3.0,
                "retail_floor_to_floor_m": 4.5,
                "efficiency_pct": 0.83,
                "max_lot_coverage_pct": 0.58,
                "parking_spaces_per_unit": 0.4,
                "amenity_area_per_unit_m2": 2.0,
                "accessible_unit_pct": 0.15,
            },
            "layout_defaults": {
                "unit_mix_targets": {
                    "studio": 0.1,
                    "one_bed": 0.35,
                    "two_bed": 0.4,
                    "three_bed": 0.15,
                },
                "objective": "max_revenue",
            },
            "policy_geometry_defaults": {
                "max_fsi": 6.0,
                "angular_plane_ratio": 1.0,
                "stepback_m": 2.5,
            },
        },
    },
)

TORONTO_UNIT_TYPES: tuple[dict[str, Any], ...] = (
    {"name": "studio", "bedroom_count": 0, "min_area_m2": 35.0, "max_area_m2": 45.0, "typical_area_m2": 40.0, "min_width_m": 4.5, "is_accessible": False},
    {"name": "one_bed", "bedroom_count": 1, "min_area_m2": 45.0, "max_area_m2": 60.0, "typical_area_m2": 52.0, "min_width_m": 5.5, "is_accessible": False},
    {"name": "two_bed", "bedroom_count": 2, "min_area_m2": 65.0, "max_area_m2": 85.0, "typical_area_m2": 74.0, "min_width_m": 7.0, "is_accessible": False},
    {"name": "three_bed", "bedroom_count": 3, "min_area_m2": 85.0, "max_area_m2": 110.0, "typical_area_m2": 96.0, "min_width_m": 8.0, "is_accessible": False},
    {"name": "one_bed_accessible", "bedroom_count": 1, "min_area_m2": 50.0, "max_area_m2": 65.0, "typical_area_m2": 58.0, "min_width_m": 6.0, "is_accessible": True},
    {"name": "two_bed_accessible", "bedroom_count": 2, "min_area_m2": 72.0, "max_area_m2": 92.0, "typical_area_m2": 82.0, "min_width_m": 7.5, "is_accessible": True},
)

TORONTO_FINANCIAL_ASSUMPTIONS: tuple[dict[str, Any], ...] = (
    {
        "name": "toronto_rental_base",
        "is_default": True,
        "assumptions_json": {
            "tenure": "rental",
            "revenue_assumptions": {
                "rate_per_m2_by_unit_type": {
                    "studio": 420.0,
                    "one_bed": 400.0,
                    "two_bed": 385.0,
                    "three_bed": 365.0,
                    "one_bed_accessible": 390.0,
                    "two_bed_accessible": 375.0,
                },
                "annualization_factor": 12.0,
            },
            "cost_assumptions": {
                "hard_cost_per_m2": 4800.0,
                "soft_cost_pct": 0.22,
                "opex_pct_of_revenue": 0.28,
                "contingency_pct": 0.06,
            },
            "vacancy_rate": 0.03,
            "absorption_months": 12,
            "valuation": {
                "cap_rate": 0.045,
            },
            "financing": {
                "loan_to_cost_pct": 0.65,
                "interest_rate": 0.055,
            },
        },
    },
    {
        "name": "toronto_condo_base",
        "is_default": False,
        "assumptions_json": {
            "tenure": "condo",
            "revenue_assumptions": {
                "rate_per_m2_by_unit_type": {
                    "studio": 13250.0,
                    "one_bed": 12750.0,
                    "two_bed": 12100.0,
                    "three_bed": 11500.0,
                    "one_bed_accessible": 12400.0,
                    "two_bed_accessible": 11850.0,
                },
                "annualization_factor": 1.0,
            },
            "cost_assumptions": {
                "hard_cost_per_m2": 5050.0,
                "soft_cost_pct": 0.24,
                "opex_pct_of_revenue": 0.02,
                "contingency_pct": 0.06,
            },
            "vacancy_rate": 0.0,
            "absorption_months": 18,
            "valuation": {
                "cap_rate": None,
            },
            "financing": {
                "loan_to_cost_pct": 0.65,
                "interest_rate": 0.058,
            },
        },
    },
)


def _get_or_create_toronto_jurisdiction(db: Session) -> Jurisdiction:
    jurisdiction = db.execute(
        select(Jurisdiction).where(
            Jurisdiction.name == "Toronto",
            Jurisdiction.province == "ON",
            Jurisdiction.country == "CA",
        )
    ).scalar_one_or_none()
    if jurisdiction is not None:
        return jurisdiction

    jurisdiction = Jurisdiction(name="Toronto", province="ON", country="CA", timezone="America/Toronto")
    db.add(jurisdiction)
    db.flush()
    return jurisdiction


def ensure_reference_data(db: Session) -> Jurisdiction:
    jurisdiction = _get_or_create_toronto_jurisdiction(db)

    existing_templates = {
        template.name: template for template in db.execute(select(MassingTemplate)).scalars().all()
    }
    for payload in TORONTO_MASSING_TEMPLATES:
        template = existing_templates.get(payload["name"])
        if template is None:
            db.add(MassingTemplate(**payload))
            continue
        template.typology = payload["typology"]
        template.parameters_json = payload["parameters_json"]

    existing_unit_types = {
        unit_type.name: unit_type
        for unit_type in db.execute(
            select(UnitType).where(UnitType.jurisdiction_id == jurisdiction.id)
        ).scalars().all()
    }
    for payload in TORONTO_UNIT_TYPES:
        unit_type = existing_unit_types.get(payload["name"])
        if unit_type is None:
            db.add(UnitType(jurisdiction_id=jurisdiction.id, **payload))
            continue
        unit_type.bedroom_count = payload["bedroom_count"]
        unit_type.min_area_m2 = payload["min_area_m2"]
        unit_type.max_area_m2 = payload["max_area_m2"]
        unit_type.typical_area_m2 = payload["typical_area_m2"]
        unit_type.min_width_m = payload["min_width_m"]
        unit_type.is_accessible = payload["is_accessible"]

    existing_assumptions = {
        assumption.name: assumption
        for assumption in db.execute(
            select(FinancialAssumptionSet).where(FinancialAssumptionSet.organization_id.is_(None))
        ).scalars().all()
    }
    for payload in TORONTO_FINANCIAL_ASSUMPTIONS:
        assumption = existing_assumptions.get(payload["name"])
        if assumption is None:
            db.add(FinancialAssumptionSet(organization_id=None, **payload))
            continue
        assumption.is_default = payload["is_default"]
        assumption.assumptions_json = payload["assumptions_json"]

    db.flush()
    return jurisdiction


def resolve_project_context(db: Session, scenario_id: str) -> ResolvedProjectContext:
    scenario = db.query(ScenarioRun).filter(ScenarioRun.id == uuid.UUID(scenario_id)).one()
    parcel = (
        db.query(Parcel)
        .join(ProjectParcel, ProjectParcel.parcel_id == Parcel.id)
        .filter(ProjectParcel.project_id == scenario.project_id)
        .order_by(ProjectParcel.role.desc(), ProjectParcel.created_at.asc())
        .first()
    )
    if parcel is None:
        raise ValueError("Scenario project has no linked parcel")
    return ResolvedProjectContext(scenario=scenario, parcel=parcel)


def validate_massing_template(template: MassingTemplate) -> MassingTemplateParameters:
    try:
        return MassingTemplateParameters.model_validate(template.parameters_json)
    except ValidationError as exc:
        raise ValueError(f"Invalid massing template payload for '{template.name}': {exc}") from exc


def validate_financial_assumptions(assumption_set: FinancialAssumptionSet) -> FinancialAssumptionPayload:
    try:
        return FinancialAssumptionPayload.model_validate(assumption_set.assumptions_json)
    except ValidationError as exc:
        raise ValueError(f"Invalid financial assumption payload for '{assumption_set.name}': {exc}") from exc


def resolve_template(db: Session, template_id: uuid.UUID | None = None) -> tuple[MassingTemplate, MassingTemplateParameters]:
    ensure_reference_data(db)
    if template_id:
        template = db.query(MassingTemplate).filter(MassingTemplate.id == template_id).one()
    else:
        template = (
            db.query(MassingTemplate)
            .order_by((MassingTemplate.typology == "tower_on_podium").desc(), MassingTemplate.name.asc())
            .first()
        )
    if template is None:
        raise ValueError("No massing template available")
    return template, validate_massing_template(template)


def resolve_unit_types(
    db: Session,
    unit_type_ids: Iterable[uuid.UUID] | None = None,
    jurisdiction_id: uuid.UUID | None = None,
) -> list[UnitType]:
    default_jurisdiction = ensure_reference_data(db)
    if unit_type_ids:
        normalized_ids = [item if isinstance(item, uuid.UUID) else uuid.UUID(str(item)) for item in unit_type_ids]
        unit_types = list(
            db.query(UnitType)
            .filter(UnitType.id.in_(normalized_ids))
            .order_by(UnitType.bedroom_count.asc(), UnitType.name.asc())
        )
        if len(unit_types) != len(normalized_ids):
            raise ValueError("One or more unit types were not found")
        return unit_types

    target_jurisdiction_id = jurisdiction_id or default_jurisdiction.id
    unit_types = list(
        db.query(UnitType)
        .filter(UnitType.jurisdiction_id == target_jurisdiction_id)
        .order_by(UnitType.bedroom_count.asc(), UnitType.name.asc())
    )
    if not unit_types:
        unit_types = list(
            db.query(UnitType)
            .filter(UnitType.jurisdiction_id.is_(None))
            .order_by(UnitType.bedroom_count.asc(), UnitType.name.asc())
        )
    if not unit_types:
        raise ValueError("No unit types available")
    return unit_types


def resolve_assumption_set(
    db: Session,
    assumption_set_id: uuid.UUID | None = None,
) -> tuple[FinancialAssumptionSet, FinancialAssumptionPayload]:
    ensure_reference_data(db)
    if assumption_set_id:
        normalized_id = assumption_set_id if isinstance(assumption_set_id, uuid.UUID) else uuid.UUID(str(assumption_set_id))
        assumption_set = db.query(FinancialAssumptionSet).filter(FinancialAssumptionSet.id == normalized_id).one()
    else:
        assumption_set = (
            db.query(FinancialAssumptionSet)
            .filter(FinancialAssumptionSet.organization_id.is_(None))
            .order_by(FinancialAssumptionSet.is_default.desc(), FinancialAssumptionSet.name.asc())
            .first()
        )
    if assumption_set is None:
        raise ValueError("No financial assumption set available")
    return assumption_set, validate_financial_assumptions(assumption_set)


def _merge_dict(base: dict[str, Any], overrides: dict[str, Any] | None) -> dict[str, Any]:
    if not overrides:
        return dict(base)
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def compute_massing_summary(
    parcel: Parcel,
    template_payload: MassingTemplateParameters,
    overrides: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = MassingTemplateParameters.model_validate(_merge_dict(template_payload.model_dump(), overrides or {}))
    lot_area = parcel.lot_area_m2 or parcel.geom_area_m2
    if not lot_area or lot_area <= 0:
        raise ValueError("Parcel must have a positive lot area")

    buildable_area = lot_area * payload.geometry_defaults.max_lot_coverage_pct
    floor_height = payload.geometry_defaults.residential_floor_to_floor_m
    height_m = overrides.get("height_m") if overrides else None
    storeys = overrides.get("storeys") if overrides else None
    resolved_storeys = int(storeys or payload.target_storeys)
    resolved_height = float(height_m or resolved_storeys * floor_height)
    raw_gfa = buildable_area * resolved_storeys
    max_policy_gfa = lot_area * payload.policy_geometry_defaults.max_fsi
    total_gfa = min(raw_gfa, max_policy_gfa)
    total_gla = total_gfa * payload.geometry_defaults.efficiency_pct

    summary = {
        "typology": payload.typology,
        "lot_area_m2": round(lot_area, 2),
        "buildable_floorplate_m2": round(buildable_area, 2),
        "storeys": resolved_storeys,
        "height_m": round(resolved_height, 2),
        "estimated_gfa_m2": round(total_gfa, 2),
        "estimated_gla_m2": round(total_gla, 2),
        "estimated_fsi": round(total_gfa / lot_area, 3),
        "lot_coverage_pct": round(payload.geometry_defaults.max_lot_coverage_pct, 3),
        "assumptions_used": payload.model_dump(),
    }
    compliance = {
        "status": "assumption_based",
        "warnings": [
            "Policy resolution is not fully implemented; policy geometry defaults were used for this thin slice."
        ],
        "max_fsi_applied": payload.policy_geometry_defaults.max_fsi,
        "stepback_m": payload.policy_geometry_defaults.stepback_m,
        "angular_plane_ratio": payload.policy_geometry_defaults.angular_plane_ratio,
    }
    return summary, compliance


def _normalized_mix(layout_defaults: LayoutDefaults, unit_types: list[UnitType]) -> dict[str, float]:
    named_defaults = {ut.name: layout_defaults.unit_mix_targets.get(ut.name, 0.0) for ut in unit_types}
    total = sum(named_defaults.values())
    if total <= 0:
        even = 1.0 / len(unit_types)
        return {ut.name: even for ut in unit_types}
    return {name: weight / total for name, weight in named_defaults.items()}


def compute_layout_result(
    massing_summary: dict[str, Any],
    template_payload: MassingTemplateParameters,
    unit_types: list[UnitType],
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    available_area = float(massing_summary.get("estimated_gla_m2") or 0.0)
    if available_area <= 0:
        raise ValueError("Massing summary must include a positive estimated_gla_m2")

    layout_defaults = LayoutDefaults.model_validate(
        _merge_dict(template_payload.layout_defaults.model_dump(), overrides or {})
    )
    mix = _normalized_mix(layout_defaults, unit_types)

    allocations: list[dict[str, Any]] = []
    total_units = 0
    used_area = 0.0
    for unit_type in unit_types:
        target_area = available_area * mix[unit_type.name]
        count = max(0, int(target_area // unit_type.typical_area_m2))
        if count == 0 and mix[unit_type.name] > 0:
            count = 1
        area = count * unit_type.typical_area_m2
        total_units += count
        used_area += area
        allocations.append(
            {
                "unit_type_id": str(unit_type.id),
                "name": unit_type.name,
                "bedroom_count": unit_type.bedroom_count,
                "count": count,
                "typical_area_m2": unit_type.typical_area_m2,
                "allocated_area_m2": round(area, 2),
                "is_accessible": unit_type.is_accessible,
            }
        )

    accessible_required = math.ceil(total_units * template_payload.geometry_defaults.accessible_unit_pct)
    accessible_supplied = sum(a["count"] for a in allocations if a["is_accessible"])
    parking_required = round(total_units * template_payload.geometry_defaults.parking_spaces_per_unit, 2)
    amenity_required = round(total_units * template_payload.geometry_defaults.amenity_area_per_unit_m2, 2)

    return {
        "objective": layout_defaults.objective,
        "available_area_m2": round(available_area, 2),
        "allocated_area_m2": round(used_area, 2),
        "unallocated_area_m2": round(max(available_area - used_area, 0.0), 2),
        "total_units": total_units,
        "parking_required": parking_required,
        "amenity_required_m2": amenity_required,
        "accessible_units_required": accessible_required,
        "accessible_units_supplied": accessible_supplied,
        "allocations": allocations,
        "assumptions_used": {
            "layout_defaults": layout_defaults.model_dump(),
            "geometry_defaults": template_payload.geometry_defaults.model_dump(),
        },
    }


def compute_financial_output(
    layout_result: dict[str, Any],
    massing_summary: dict[str, Any],
    unit_types: list[UnitType],
    assumptions: FinancialAssumptionPayload,
) -> dict[str, Any]:
    unit_types_by_name = {unit_type.name: unit_type for unit_type in unit_types}
    total_revenue = 0.0
    for allocation in layout_result["allocations"]:
        unit_type = unit_types_by_name[allocation["name"]]
        rate = assumptions.revenue_assumptions.rate_per_m2_by_unit_type.get(allocation["name"])
        if rate is None:
            rate = sum(assumptions.revenue_assumptions.rate_per_m2_by_unit_type.values()) / max(
                len(assumptions.revenue_assumptions.rate_per_m2_by_unit_type), 1
            )
        total_revenue += (
            allocation["count"]
            * unit_type.typical_area_m2
            * rate
            * assumptions.revenue_assumptions.annualization_factor
        )

    total_revenue *= (1 - assumptions.vacancy_rate)
    estimated_gfa = float(massing_summary.get("estimated_gfa_m2") or 0.0)
    hard_cost = estimated_gfa * assumptions.cost_assumptions.hard_cost_per_m2
    soft_cost = hard_cost * assumptions.cost_assumptions.soft_cost_pct
    contingency = (hard_cost + soft_cost) * assumptions.cost_assumptions.contingency_pct
    total_cost = hard_cost + soft_cost + contingency
    opex = total_revenue * assumptions.cost_assumptions.opex_pct_of_revenue
    noi = total_revenue - opex
    if assumptions.tenure == "rental" and assumptions.valuation.cap_rate:
        valuation = noi / assumptions.valuation.cap_rate
    else:
        valuation = total_revenue
    residual_land_value = valuation - total_cost

    return {
        "tenure": assumptions.tenure,
        "total_revenue": round(total_revenue, 2),
        "hard_cost": round(hard_cost, 2),
        "soft_cost": round(soft_cost, 2),
        "contingency_cost": round(contingency, 2),
        "total_cost": round(total_cost, 2),
        "opex": round(opex, 2),
        "noi": round(noi, 2),
        "valuation": round(valuation, 2),
        "residual_land_value": round(residual_land_value, 2),
        "assumptions_used": assumptions.model_dump(),
    }


def build_precedent_match_summary(
    *,
    app_id: uuid.UUID,
    app_number: str,
    address: str | None,
    app_type: str,
    decision: str | None,
    proposed_height_m: float | None,
    proposed_units: int | None,
    proposed_fsi: float | None,
    distance_m: float,
    permit_count: int = 0,
) -> dict[str, Any]:
    distance_score = max(0.0, 1 - min(distance_m, 2000.0) / 2000.0)
    height_score = 1.0 if proposed_height_m else 0.5
    unit_score = 1.0 if proposed_units else 0.5
    decision_score = 1.0 if decision == "approved" else 0.7 if decision == "pending" else 0.4
    permit_bonus = min(permit_count * 0.05, 0.2)
    score = round((distance_score * 0.35) + (height_score * 0.2) + (unit_score * 0.15) + (decision_score * 0.2) + permit_bonus, 4)

    return {
        "application_id": str(app_id),
        "app_number": app_number,
        "address": address,
        "app_type": app_type,
        "decision": decision,
        "proposed_height_m": proposed_height_m,
        "proposed_units": proposed_units,
        "proposed_fsi": proposed_fsi,
        "distance_m": round(distance_m, 2),
        "permit_count": permit_count,
        "score": score,
        "score_breakdown": {
            "distance": round(distance_score, 4),
            "height_signal": height_score,
            "unit_signal": unit_score,
            "decision_signal": decision_score,
            "permit_bonus": round(permit_bonus, 4),
        },
    }
