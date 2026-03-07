import uuid
from collections.abc import Sequence
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.finance import FinancialAssumptionSet
from app.models.geospatial import Jurisdiction, Parcel, ProjectParcel
from app.models.simulation import MassingTemplate, UnitType
from app.models.tenant import ScenarioRun


TORONTO_JURISDICTION = {
    "name": "Toronto",
    "province": "ON",
    "country": "CA",
    "timezone": "America/Toronto",
}

TORONTO_MASSING_TEMPLATES = [
    {
        "name": "Toronto Tower-on-Podium",
        "typology": "tower_on_podium",
        "parameters_json": {
            "typology": "tower_on_podium",
            "geometry_defaults": {
                "storeys": 28,
                "height_m": 92.0,
                "lot_coverage_pct": 62.0,
                "fsi_target": 8.0,
                "efficiency_factor": 0.82,
                "floor_to_floor_heights_m": {
                    "residential": 3.1,
                    "retail": 4.8,
                },
            },
            "layout_defaults": {
                "unit_mix_targets": {
                    "studio": 0.10,
                    "one_bed": 0.44,
                    "two_bed": 0.34,
                    "three_bed": 0.12,
                },
                "amenity_m2_per_unit": 2.0,
                "parking_ratio": 0.45,
                "accessible_unit_ratio": 0.15,
            },
            "policy_geometry_defaults": {
                "front_setback_m": 3.0,
                "side_setback_m": 7.5,
                "rear_setback_m": 7.5,
                "stepback_m": 1.5,
                "angular_plane_ratio": 1.0,
            },
            "validation_rules": {
                "min_frontage_m": 30.0,
                "min_lot_area_m2": 1500.0,
            },
        },
    },
    {
        "name": "Toronto Midrise",
        "typology": "midrise",
        "parameters_json": {
            "typology": "midrise",
            "geometry_defaults": {
                "storeys": 10,
                "height_m": 32.0,
                "lot_coverage_pct": 72.0,
                "fsi_target": 4.5,
                "efficiency_factor": 0.84,
                "floor_to_floor_heights_m": {
                    "residential": 3.05,
                    "retail": 4.5,
                },
            },
            "layout_defaults": {
                "unit_mix_targets": {
                    "studio": 0.08,
                    "one_bed": 0.36,
                    "two_bed": 0.40,
                    "three_bed": 0.16,
                },
                "amenity_m2_per_unit": 2.2,
                "parking_ratio": 0.35,
                "accessible_unit_ratio": 0.15,
            },
            "policy_geometry_defaults": {
                "front_setback_m": 0.0,
                "side_setback_m": 5.5,
                "rear_setback_m": 7.5,
                "stepback_m": 1.5,
                "angular_plane_ratio": 1.0,
            },
            "validation_rules": {
                "min_frontage_m": 20.0,
                "min_lot_area_m2": 800.0,
            },
        },
    },
    {
        "name": "Toronto Townhouse",
        "typology": "townhouse",
        "parameters_json": {
            "typology": "townhouse",
            "geometry_defaults": {
                "storeys": 3,
                "height_m": 11.0,
                "lot_coverage_pct": 58.0,
                "fsi_target": 1.2,
                "efficiency_factor": 0.88,
                "floor_to_floor_heights_m": {
                    "residential": 3.0,
                },
            },
            "layout_defaults": {
                "unit_mix_targets": {
                    "two_bed": 0.55,
                    "three_bed": 0.45,
                },
                "amenity_m2_per_unit": 1.2,
                "parking_ratio": 1.0,
                "accessible_unit_ratio": 0.05,
            },
            "policy_geometry_defaults": {
                "front_setback_m": 3.0,
                "side_setback_m": 1.2,
                "rear_setback_m": 7.5,
                "stepback_m": 0.0,
                "angular_plane_ratio": 0.0,
            },
            "validation_rules": {
                "min_frontage_m": 6.0,
                "min_lot_area_m2": 120.0,
            },
        },
    },
    {
        "name": "Toronto Mixed-Use Midrise",
        "typology": "mixed_use_midrise",
        "parameters_json": {
            "typology": "mixed_use_midrise",
            "geometry_defaults": {
                "storeys": 12,
                "height_m": 38.0,
                "lot_coverage_pct": 70.0,
                "fsi_target": 5.2,
                "efficiency_factor": 0.83,
                "floor_to_floor_heights_m": {
                    "residential": 3.05,
                    "retail": 5.0,
                },
            },
            "layout_defaults": {
                "unit_mix_targets": {
                    "studio": 0.08,
                    "one_bed": 0.42,
                    "two_bed": 0.34,
                    "three_bed": 0.16,
                },
                "amenity_m2_per_unit": 2.0,
                "parking_ratio": 0.40,
                "accessible_unit_ratio": 0.15,
            },
            "policy_geometry_defaults": {
                "front_setback_m": 0.0,
                "side_setback_m": 5.5,
                "rear_setback_m": 7.5,
                "stepback_m": 1.5,
                "angular_plane_ratio": 1.0,
            },
            "validation_rules": {
                "min_frontage_m": 22.0,
                "min_lot_area_m2": 900.0,
            },
        },
    },
]

TORONTO_UNIT_TYPES = [
    {"name": "studio", "bedroom_count": 0, "min_area_m2": 32.0, "max_area_m2": 45.0, "typical_area_m2": 38.0, "min_width_m": 4.8, "is_accessible": False},
    {"name": "one_bed", "bedroom_count": 1, "min_area_m2": 45.0, "max_area_m2": 62.0, "typical_area_m2": 53.0, "min_width_m": 5.4, "is_accessible": False},
    {"name": "two_bed", "bedroom_count": 2, "min_area_m2": 65.0, "max_area_m2": 88.0, "typical_area_m2": 76.0, "min_width_m": 7.2, "is_accessible": False},
    {"name": "three_bed", "bedroom_count": 3, "min_area_m2": 90.0, "max_area_m2": 120.0, "typical_area_m2": 102.0, "min_width_m": 8.4, "is_accessible": False},
    {"name": "one_bed_accessible", "bedroom_count": 1, "min_area_m2": 55.0, "max_area_m2": 70.0, "typical_area_m2": 62.0, "min_width_m": 6.0, "is_accessible": True},
    {"name": "two_bed_accessible", "bedroom_count": 2, "min_area_m2": 75.0, "max_area_m2": 98.0, "typical_area_m2": 86.0, "min_width_m": 7.8, "is_accessible": True},
]

TORONTO_FINANCIAL_ASSUMPTION_SETS = [
    {
        "name": "toronto_rental_base",
        "assumptions_json": {
            "tenure": "rental",
            "revenue_assumptions": {
                "rent_psf_monthly_by_unit_type": {
                    "studio": 4.45,
                    "one_bed": 4.25,
                    "two_bed": 3.95,
                    "three_bed": 3.70,
                    "one_bed_accessible": 4.10,
                    "two_bed_accessible": 3.85,
                },
                "other_income_pct": 0.03,
            },
            "cost_assumptions": {
                "hard_cost_per_m2": 4300.0,
                "soft_cost_pct": 0.22,
                "parking_cost_per_space": 55000.0,
            },
            "vacancy_and_absorption": {
                "vacancy_rate": 0.035,
                "absorption_months": 14,
                "opex_ratio": 0.28,
            },
            "valuation": {
                "cap_rate": 0.0475,
            },
            "financing": {
                "loan_to_cost_pct": 0.65,
                "interest_rate": 0.060,
            },
            "contingency": {
                "construction_contingency_pct": 0.05,
            },
        },
    },
    {
        "name": "toronto_condo_base",
        "assumptions_json": {
            "tenure": "condo",
            "revenue_assumptions": {
                "sale_psf_by_unit_type": {
                    "studio": 1385.0,
                    "one_bed": 1360.0,
                    "two_bed": 1315.0,
                    "three_bed": 1260.0,
                    "one_bed_accessible": 1335.0,
                    "two_bed_accessible": 1290.0,
                },
                "sales_cost_pct": 0.04,
            },
            "cost_assumptions": {
                "hard_cost_per_m2": 4450.0,
                "soft_cost_pct": 0.24,
                "parking_cost_per_space": 60000.0,
            },
            "vacancy_and_absorption": {
                "absorption_months": 18,
            },
            "valuation": {},
            "financing": {
                "loan_to_cost_pct": 0.65,
                "interest_rate": 0.0625,
            },
            "contingency": {
                "construction_contingency_pct": 0.05,
            },
        },
    },
]


def _clone(data: dict) -> dict:
    return deepcopy(data)


def _get_or_create_jurisdiction_sync(db: Session) -> Jurisdiction:
    jurisdiction = db.execute(
        select(Jurisdiction).where(
            Jurisdiction.name == TORONTO_JURISDICTION["name"],
            Jurisdiction.province == TORONTO_JURISDICTION["province"],
            Jurisdiction.country == TORONTO_JURISDICTION["country"],
        )
    ).scalar_one_or_none()
    if jurisdiction:
        return jurisdiction

    jurisdiction = Jurisdiction(**TORONTO_JURISDICTION)
    db.add(jurisdiction)
    db.flush()
    return jurisdiction


async def _get_or_create_jurisdiction_async(db: AsyncSession) -> Jurisdiction:
    result = await db.execute(
        select(Jurisdiction).where(
            Jurisdiction.name == TORONTO_JURISDICTION["name"],
            Jurisdiction.province == TORONTO_JURISDICTION["province"],
            Jurisdiction.country == TORONTO_JURISDICTION["country"],
        )
    )
    jurisdiction = result.scalar_one_or_none()
    if jurisdiction:
        return jurisdiction

    jurisdiction = Jurisdiction(**TORONTO_JURISDICTION)
    db.add(jurisdiction)
    await db.flush()
    return jurisdiction


def ensure_toronto_reference_data_sync(db: Session) -> Jurisdiction:
    jurisdiction = _get_or_create_jurisdiction_sync(db)

    existing_templates = {
        template.name: template
        for template in db.execute(select(MassingTemplate)).scalars().all()
    }
    for row in TORONTO_MASSING_TEMPLATES:
        template = existing_templates.get(row["name"])
        if template is None:
            db.add(MassingTemplate(**_clone(row)))
            continue
        template.typology = row["typology"]
        template.parameters_json = _clone(row["parameters_json"])

    existing_units = {
        unit.name: unit
        for unit in db.execute(
            select(UnitType).where(UnitType.jurisdiction_id == jurisdiction.id)
        ).scalars().all()
    }
    for row in TORONTO_UNIT_TYPES:
        unit = existing_units.get(row["name"])
        payload = _clone(row)
        payload["jurisdiction_id"] = jurisdiction.id
        if unit is None:
            db.add(UnitType(**payload))
            continue
        unit.bedroom_count = payload["bedroom_count"]
        unit.min_area_m2 = payload["min_area_m2"]
        unit.max_area_m2 = payload["max_area_m2"]
        unit.typical_area_m2 = payload["typical_area_m2"]
        unit.min_width_m = payload["min_width_m"]
        unit.is_accessible = payload["is_accessible"]

    existing_sets = {
        assumption_set.name: assumption_set
        for assumption_set in db.execute(
            select(FinancialAssumptionSet).where(FinancialAssumptionSet.organization_id.is_(None))
        ).scalars().all()
    }
    for row in TORONTO_FINANCIAL_ASSUMPTION_SETS:
        assumption_set = existing_sets.get(row["name"])
        payload = _clone(row)
        payload["organization_id"] = None
        payload["is_default"] = True
        if assumption_set is None:
            db.add(FinancialAssumptionSet(**payload))
            continue
        assumption_set.is_default = True
        assumption_set.assumptions_json = payload["assumptions_json"]

    db.flush()
    return jurisdiction


async def ensure_toronto_reference_data_async(db: AsyncSession) -> Jurisdiction:
    jurisdiction = await _get_or_create_jurisdiction_async(db)

    template_result = await db.execute(select(MassingTemplate))
    existing_templates = {template.name: template for template in template_result.scalars().all()}
    for row in TORONTO_MASSING_TEMPLATES:
        template = existing_templates.get(row["name"])
        if template is None:
            db.add(MassingTemplate(**_clone(row)))
            continue
        template.typology = row["typology"]
        template.parameters_json = _clone(row["parameters_json"])

    unit_result = await db.execute(
        select(UnitType).where(UnitType.jurisdiction_id == jurisdiction.id)
    )
    existing_units = {unit.name: unit for unit in unit_result.scalars().all()}
    for row in TORONTO_UNIT_TYPES:
        unit = existing_units.get(row["name"])
        payload = _clone(row)
        payload["jurisdiction_id"] = jurisdiction.id
        if unit is None:
            db.add(UnitType(**payload))
            continue
        unit.bedroom_count = payload["bedroom_count"]
        unit.min_area_m2 = payload["min_area_m2"]
        unit.max_area_m2 = payload["max_area_m2"]
        unit.typical_area_m2 = payload["typical_area_m2"]
        unit.min_width_m = payload["min_width_m"]
        unit.is_accessible = payload["is_accessible"]

    assumption_result = await db.execute(
        select(FinancialAssumptionSet).where(FinancialAssumptionSet.organization_id.is_(None))
    )
    existing_sets = {assumption_set.name: assumption_set for assumption_set in assumption_result.scalars().all()}
    for row in TORONTO_FINANCIAL_ASSUMPTION_SETS:
        assumption_set = existing_sets.get(row["name"])
        payload = _clone(row)
        payload["organization_id"] = None
        payload["is_default"] = True
        if assumption_set is None:
            db.add(FinancialAssumptionSet(**payload))
            continue
        assumption_set.is_default = True
        assumption_set.assumptions_json = payload["assumptions_json"]

    await db.flush()
    return jurisdiction


def resolve_massing_template_sync(
    db: Session,
    template_id: uuid.UUID | None = None,
) -> MassingTemplate:
    ensure_toronto_reference_data_sync(db)
    if template_id:
        template = db.get(MassingTemplate, template_id)
        if template is None:
            raise ValueError(f"Massing template not found: {template_id}")
        return template

    template = db.execute(
        select(MassingTemplate).where(MassingTemplate.typology == "tower_on_podium")
    ).scalar_one_or_none()
    if template is None:
        raise ValueError("Default Toronto massing template not available")
    return template


async def list_massing_templates_async(db: AsyncSession) -> Sequence[MassingTemplate]:
    await ensure_toronto_reference_data_async(db)
    result = await db.execute(select(MassingTemplate).order_by(MassingTemplate.name.asc()))
    return result.scalars().all()


def resolve_unit_types_sync(
    db: Session,
    jurisdiction_id: uuid.UUID | None,
    unit_type_ids: Sequence[uuid.UUID] | None = None,
) -> list[UnitType]:
    jurisdiction = ensure_toronto_reference_data_sync(db)
    if unit_type_ids:
        rows = db.execute(select(UnitType).where(UnitType.id.in_(list(unit_type_ids)))).scalars().all()
        if len(rows) != len(unit_type_ids):
            raise ValueError("One or more unit types were not found")
        return list(rows)

    target_jurisdiction = jurisdiction_id or jurisdiction.id
    rows = db.execute(
        select(UnitType).where(UnitType.jurisdiction_id == target_jurisdiction).order_by(UnitType.bedroom_count.asc())
    ).scalars().all()
    if rows:
        return list(rows)

    return list(
        db.execute(
            select(UnitType).where(UnitType.jurisdiction_id == jurisdiction.id).order_by(UnitType.bedroom_count.asc())
        ).scalars().all()
    )


async def list_unit_types_async(
    db: AsyncSession,
    jurisdiction_id: uuid.UUID | None = None,
) -> Sequence[UnitType]:
    jurisdiction = await ensure_toronto_reference_data_async(db)
    target_jurisdiction = jurisdiction_id or jurisdiction.id
    result = await db.execute(
        select(UnitType).where(UnitType.jurisdiction_id == target_jurisdiction).order_by(UnitType.bedroom_count.asc())
    )
    rows = result.scalars().all()
    if rows:
        return rows

    fallback = await db.execute(
        select(UnitType).where(UnitType.jurisdiction_id == jurisdiction.id).order_by(UnitType.bedroom_count.asc())
    )
    return fallback.scalars().all()


def resolve_financial_assumption_set_sync(
    db: Session,
    assumption_set_id: uuid.UUID | None = None,
) -> FinancialAssumptionSet:
    ensure_toronto_reference_data_sync(db)
    if assumption_set_id:
        assumption_set = db.get(FinancialAssumptionSet, assumption_set_id)
        if assumption_set is None:
            raise ValueError(f"Financial assumption set not found: {assumption_set_id}")
        return assumption_set

    assumption_set = db.execute(
        select(FinancialAssumptionSet).where(
            FinancialAssumptionSet.organization_id.is_(None),
            FinancialAssumptionSet.name == "toronto_rental_base",
        )
    ).scalar_one_or_none()
    if assumption_set is None:
        raise ValueError("Default Toronto financial assumption set not available")
    return assumption_set


async def list_financial_assumption_sets_async(db: AsyncSession) -> Sequence[FinancialAssumptionSet]:
    await ensure_toronto_reference_data_async(db)
    result = await db.execute(
        select(FinancialAssumptionSet)
        .where(FinancialAssumptionSet.organization_id.is_(None))
        .order_by(FinancialAssumptionSet.name.asc())
    )
    return result.scalars().all()


def normalize_percentage(value: float | int | None, default: float) -> float:
    if value is None:
        return default
    numeric = float(value)
    return numeric if numeric <= 1.0 else numeric / 100.0


def money(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    return float(decimal_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def upsert_reference_data(db: Session) -> Jurisdiction:
    return ensure_toronto_reference_data_sync(db)


def resolve_project_parcel_sync(db: Session, scenario_id: uuid.UUID | str) -> tuple[ScenarioRun, Parcel]:
    scenario_uuid = scenario_id if isinstance(scenario_id, uuid.UUID) else uuid.UUID(str(scenario_id))
    scenario = db.get(ScenarioRun, scenario_uuid)
    if scenario is None:
        raise ValueError(f"Scenario not found: {scenario_uuid}")

    parcel = db.execute(
        select(Parcel)
        .join(ProjectParcel, ProjectParcel.parcel_id == Parcel.id)
        .where(ProjectParcel.project_id == scenario.project_id)
        .order_by(ProjectParcel.role.desc(), ProjectParcel.created_at.asc())
    ).scalars().first()
    if parcel is None:
        raise ValueError("Scenario project has no linked parcel")

    return scenario, parcel
