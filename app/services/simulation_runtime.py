from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from math import floor
from typing import Any

from app.services.reference_data import money


def deep_merge(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    result = deepcopy(base)
    if not override:
        return result
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def compute_massing_summary(parcel: Any, template_defaults: dict[str, Any], params: dict[str, Any] | None = None) -> dict[str, Any]:
    merged = deep_merge(template_defaults, params or {})
    geometry_defaults = merged.get("geometry_defaults", {})
    policy_defaults = merged.get("policy_geometry_defaults", {})
    site_area_m2 = float(parcel.lot_area_m2 or parcel.geom_area_m2 or 0.0)
    if site_area_m2 <= 0:
        raise ValueError("Parcel site area is required for massing generation")

    requested_storeys = int(merged.get("storeys") or geometry_defaults.get("default_storeys") or 1)
    floor_to_floor_m = float(geometry_defaults.get("default_floor_to_floor_m") or 3.0)
    ground_floor_m = float(geometry_defaults.get("ground_floor_height_m") or floor_to_floor_m)
    height_m = float(
        merged.get("height_m")
        or ground_floor_m + max(requested_storeys - 1, 0) * floor_to_floor_m
    )

    max_lot_coverage_pct = float(geometry_defaults.get("max_lot_coverage_pct") or 60.0)
    lot_coverage_pct = float(merged.get("lot_coverage_pct") or max_lot_coverage_pct)
    buildable_floorplate_m2 = site_area_m2 * (lot_coverage_pct / 100.0)
    total_gfa_m2 = buildable_floorplate_m2 * requested_storeys
    efficiency = float(geometry_defaults.get("core_efficiency") or 0.82)
    total_gla_m2 = total_gfa_m2 * efficiency
    fsi = total_gfa_m2 / site_area_m2

    warnings: list[str] = []
    if policy_defaults.get("tower_floorplate_max_m2") and buildable_floorplate_m2 > float(
        policy_defaults["tower_floorplate_max_m2"]
    ):
        warnings.append("Estimated floorplate exceeds template tower floorplate guidance")
    if policy_defaults.get("max_height_m") and height_m > float(policy_defaults["max_height_m"]):
        warnings.append("Estimated height exceeds template max height guidance")

    return {
        "storeys": requested_storeys,
        "height_m": round(height_m, 2),
        "lot_coverage_pct": round(lot_coverage_pct, 2),
        "site_area_m2": round(site_area_m2, 2),
        "buildable_floorplate_m2": round(buildable_floorplate_m2, 2),
        "total_gfa_m2": round(total_gfa_m2, 2),
        "total_gla_m2": round(total_gla_m2, 2),
        "fsi": round(fsi, 3),
        "assumptions_used": {
            "floor_to_floor_m": floor_to_floor_m,
            "ground_floor_m": ground_floor_m,
            "core_efficiency": efficiency,
            "geometry_defaults": geometry_defaults,
            "policy_geometry_defaults": policy_defaults,
        },
        "warnings": warnings,
    }


def compute_layout_result(
    massing_summary: dict[str, Any],
    unit_types: list[Any],
    template_defaults: dict[str, Any],
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged = deep_merge(template_defaults, params or {})
    layout_defaults = merged.get("layout_defaults", {})
    target_mix = params.get("unit_mix") if params else None
    mix = target_mix or layout_defaults.get("target_unit_mix") or {}
    if not mix:
        raise ValueError("Layout defaults must define a target unit mix")

    gla_m2 = float(massing_summary["total_gla_m2"])
    amenity_ratio = float(layout_defaults.get("amenity_ratio") or 0.05)
    usable_residential_area_m2 = gla_m2 * (1.0 - amenity_ratio)
    parking_ratio = float(layout_defaults.get("parking_ratio_per_unit") or 0.0)
    accessible_share = float(layout_defaults.get("accessible_share") or 0.0)

    unit_rows = []
    total_units = 0
    accessible_units = 0
    for unit_type in unit_types:
        base_name = unit_type.name.replace("_accessible", "")
        share = float(mix.get(base_name, 0.0))
        if share <= 0:
            continue
        allocated_area = usable_residential_area_m2 * share
        count = floor(allocated_area / float(unit_type.typical_area_m2))
        if count <= 0:
            continue
        total_units += count
        if getattr(unit_type, "is_accessible", False):
            accessible_units += count
        unit_rows.append(
            {
                "unit_type_id": str(unit_type.id),
                "name": unit_type.name,
                "bedroom_count": unit_type.bedroom_count,
                "count": count,
                "typical_area_m2": float(unit_type.typical_area_m2),
                "allocated_area_m2": round(count * float(unit_type.typical_area_m2), 2),
                "is_accessible": bool(getattr(unit_type, "is_accessible", False)),
            }
        )

    minimum_accessible = floor(total_units * accessible_share)
    parking_spaces = round(total_units * parking_ratio, 1)
    return {
        "total_units": total_units,
        "total_area_m2": round(usable_residential_area_m2, 2),
        "amenity_area_m2": round(gla_m2 * amenity_ratio, 2),
        "estimated_parking_spaces": parking_spaces,
        "accessible_units": accessible_units,
        "minimum_accessible_units": minimum_accessible,
        "unit_mix": unit_rows,
        "constraints_used": {
            "amenity_ratio": amenity_ratio,
            "parking_ratio_per_unit": parking_ratio,
            "accessible_share": accessible_share,
            "target_unit_mix": mix,
        },
    }


def compute_financial_output(
    layout_result: dict[str, Any],
    assumption_set: dict[str, Any],
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged = deep_merge(assumption_set, params or {})
    tenure = merged.get("tenure", "rental")
    revenue_assumptions = merged.get("revenue_assumptions", {})
    cost_assumptions = merged.get("cost_assumptions", {})
    vacancy_assumptions = merged.get("vacancy_and_absorption", {})
    valuation_assumptions = merged.get("valuation", {})
    contingency_assumptions = merged.get("contingency", {})

    total_revenue = Decimal("0")
    for unit in layout_result.get("unit_mix", []):
        bedroom_key = str(unit["bedroom_count"])
        area = Decimal(str(unit["allocated_area_m2"]))
        if tenure == "condo":
            rate = Decimal(str(revenue_assumptions.get("sale_per_m2_by_bedroom", {}).get(bedroom_key, 0)))
            total_revenue += area * rate
        else:
            rate = Decimal(str(revenue_assumptions.get("rent_per_m2_monthly_by_bedroom", {}).get(bedroom_key, 0)))
            total_revenue += area * rate * Decimal("12")

    vacancy_rate = Decimal(str(vacancy_assumptions.get("vacancy_rate", 0)))
    gross_revenue_after_vacancy = total_revenue * (Decimal("1") - vacancy_rate)
    hard_cost_per_m2 = Decimal(str(cost_assumptions.get("hard_cost_per_m2", 0)))
    gross_area = Decimal(str(layout_result.get("total_area_m2", 0) + layout_result.get("amenity_area_m2", 0)))
    hard_cost = gross_area * hard_cost_per_m2
    soft_cost = hard_cost * Decimal(str(cost_assumptions.get("soft_cost_pct", 0)))
    contingency = (hard_cost + soft_cost) * Decimal(str(contingency_assumptions.get("contingency_pct", 0)))
    total_cost = hard_cost + soft_cost + contingency

    if tenure == "condo":
        sales_commission_pct = Decimal(str(valuation_assumptions.get("sales_commission_pct", 0)))
        net_sales = gross_revenue_after_vacancy * (Decimal("1") - sales_commission_pct)
        noi = net_sales - total_cost
        valuation = net_sales
    else:
        opex_ratio = Decimal(str(valuation_assumptions.get("opex_ratio", 0.28)))
        noi = gross_revenue_after_vacancy * (Decimal("1") - opex_ratio)
        cap_rate = Decimal(str(valuation_assumptions.get("cap_rate", 0.05)))
        valuation = noi / cap_rate if cap_rate > 0 else Decimal("0")

    residual_land_value = valuation - total_cost
    irr_pct = ((valuation - total_cost) / total_cost * Decimal("100")) if total_cost > 0 else Decimal("0")
    return {
        "tenure": tenure,
        "total_revenue": money(gross_revenue_after_vacancy),
        "total_cost": money(total_cost),
        "noi": money(noi),
        "valuation": money(valuation),
        "residual_land_value": money(residual_land_value),
        "irr_pct": round(float(irr_pct), 2),
        "assumptions_used": merged,
    }
