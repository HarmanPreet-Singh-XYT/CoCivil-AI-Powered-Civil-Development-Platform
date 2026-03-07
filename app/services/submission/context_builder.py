"""Assembles template context from pipeline data.

Bridges pipeline results to template placeholders. Every placeholder gets
a real value or explicit "[NOT AVAILABLE — requires manual input]".
"""

from __future__ import annotations

from typing import Any

from app.services.compliance_engine import ComplianceResult, render_compliance_matrix_markdown
from app.services.zoning_service import ZoningAnalysis


_NOT_AVAILABLE = "[NOT AVAILABLE — requires manual input]"


def _fmt_number(value: float | int | None, decimals: int = 0, prefix: str = "", suffix: str = "") -> str:
    if value is None:
        return _NOT_AVAILABLE
    if decimals == 0:
        return f"{prefix}{int(value):,}{suffix}"
    return f"{prefix}{value:,.{decimals}f}{suffix}"


def _fmt_area(value: float | None) -> str:
    return _fmt_number(value, decimals=1, suffix=" m²")


def _fmt_money(value: float | None) -> str:
    return _fmt_number(value, decimals=2, prefix="$")


def _or(value: Any, default: str = _NOT_AVAILABLE) -> str:
    if value is None or value == "":
        return default
    return str(value)


def _build_policy_stack_summary(policy_stack: dict | None) -> str:
    """Format policy stack into readable summary for template."""
    if not policy_stack:
        return _NOT_AVAILABLE

    policies = policy_stack.get("applicable_policies", [])
    if not policies:
        return "No applicable policies found in database."

    lines = []
    for entry in policies:
        title = entry.get("document_title", "Unknown")
        section = entry.get("section_ref", "")
        raw_text = entry.get("raw_text", "")
        citation = f"§{section}" if section else ""
        lines.append(f"- **{title}** {citation}: {raw_text[:200]}")

    return "\n".join(lines)


def _build_variance_summary(compliance: ComplianceResult | None) -> str:
    """Build variance summary from compliance result."""
    if compliance is None:
        return _NOT_AVAILABLE

    if not compliance.variances_needed:
        return "No variances required — proposal is as-of-right."

    lines = []
    for v in compliance.variances_needed:
        pct = f" ({v.variance_pct:+.1f}%)" if v.variance_pct is not None else ""
        lines.append(
            f"- **{v.parameter}** ({v.bylaw_section}): "
            f"Required {_format_rule_value(v.permitted_value, v.unit)}, "
            f"Proposed {_format_rule_value(v.proposed_value, v.unit)}{pct}"
        )

    if compliance.minor_variance_applicable:
        lines.append(
            "\n*All variances may qualify as minor variances under "
            "Section 45(1) of the Planning Act.*"
        )
    else:
        lines.append(
            "\n*Zoning By-law Amendment may be required for one or more variances.*"
        )

    return "\n".join(lines)


def _format_rule_value(value: float | None, unit: str) -> str:
    if value is None:
        return "[TBD]"
    if unit == "%":
        return f"{value:.1f}%"
    if unit in ("m", "m²"):
        return f"{value:.1f} {unit}"
    return f"{value}"


def _build_massing_parameters(massing: dict | None) -> str:
    if not massing:
        return _NOT_AVAILABLE

    lines = [
        f"- Typology: {massing.get('typology', _NOT_AVAILABLE)}",
        f"- Lot Area: {_fmt_area(massing.get('lot_area_m2'))}",
        f"- Buildable Floorplate: {_fmt_area(massing.get('buildable_floorplate_m2'))}",
        f"- Storeys: {massing.get('storeys', _NOT_AVAILABLE)}",
        f"- Height: {_fmt_number(massing.get('height_m'), 1, suffix=' m')}",
        f"- Estimated GFA: {_fmt_area(massing.get('estimated_gfa_m2'))}",
        f"- Estimated GLA: {_fmt_area(massing.get('estimated_gla_m2'))}",
        f"- FSI: {_fmt_number(massing.get('estimated_fsi'), 3)}",
        f"- Lot Coverage: {_fmt_number(massing.get('lot_coverage_pct', 0) * 100 if massing.get('lot_coverage_pct') is not None else None, 1, suffix='%')}",
    ]
    return "\n".join(lines)


def _build_unit_mix_data(layout: dict | None) -> str:
    if not layout:
        return _NOT_AVAILABLE

    allocations = layout.get("allocations", [])
    if not allocations:
        return "No unit allocations available."

    lines = [
        "| Unit Type | Count | Typical Area | Allocated Area | Accessible |",
        "|-----------|-------|-------------|----------------|------------|",
    ]
    for alloc in allocations:
        name = alloc.get("name", "unknown")
        count = alloc.get("count", 0)
        typical = alloc.get("typical_area_m2", 0)
        allocated = alloc.get("allocated_area_m2", 0)
        accessible = "Yes" if alloc.get("is_accessible") else "No"
        lines.append(f"| {name} | {count} | {typical:.1f} m² | {allocated:,.1f} m² | {accessible} |")

    lines.append(f"\n**Total Units**: {layout.get('total_units', 0)}")
    lines.append(f"**Available Area**: {_fmt_area(layout.get('available_area_m2'))}")
    lines.append(f"**Allocated Area**: {_fmt_area(layout.get('allocated_area_m2'))}")

    return "\n".join(lines)


def _build_financial_results(finance: dict | None) -> str:
    if not finance:
        return _NOT_AVAILABLE

    lines = [
        f"- Tenure: {finance.get('tenure', _NOT_AVAILABLE)}",
        f"- Total Revenue: {_fmt_money(finance.get('total_revenue'))}",
        f"- Hard Cost: {_fmt_money(finance.get('hard_cost'))}",
        f"- Soft Cost: {_fmt_money(finance.get('soft_cost'))}",
        f"- Contingency: {_fmt_money(finance.get('contingency_cost'))}",
        f"- Total Development Cost: {_fmt_money(finance.get('total_cost'))}",
        f"- Operating Expenses: {_fmt_money(finance.get('opex'))}",
        f"- Net Operating Income: {_fmt_money(finance.get('noi'))}",
        f"- Valuation: {_fmt_money(finance.get('valuation'))}",
        f"- Residual Land Value: {_fmt_money(finance.get('residual_land_value'))}",
    ]
    return "\n".join(lines)


def _build_precedent_results(precedents: list[dict] | None) -> str:
    if not precedents:
        return "No precedent applications found in database."

    lines = []
    for p in precedents:
        addr = p.get("address", "Unknown")
        app_num = p.get("app_number", "N/A")
        decision = p.get("decision", "Unknown")
        height = p.get("proposed_height_m")
        units = p.get("proposed_units")
        distance = p.get("distance_m")
        score = p.get("score", 0)

        lines.append(
            f"- **{addr}** (App #{app_num}) — {decision}\n"
            f"  Height: {height or 'N/A'}m, Units: {units or 'N/A'}, "
            f"Distance: {distance or 'N/A'}m, Match Score: {score:.2f}"
        )

    return "\n".join(lines)


def build_document_context(
    parcel_data: dict | None,
    zoning: ZoningAnalysis | None,
    massing: dict | None,
    layout: dict | None,
    finance: dict | None,
    compliance: ComplianceResult | None,
    precedents: list[dict] | None,
    policy_stack: dict | None,
    overlays: dict | None,
    project_name: str = "",
    organization_name: str = "",
    parsed_parameters: dict | None = None,
) -> dict[str, Any]:
    """Assemble complete context dict for all 10 document templates.

    Every key maps to a template placeholder.
    Missing data is explicitly marked — never silently omitted.
    All numeric values are pre-formatted where needed.
    All by-law sections are included as citations.
    """
    params = parsed_parameters or {}

    # Basic site info
    address = _or(params.get("address") or (parcel_data or {}).get("address"))
    zoning_code = _or(
        (zoning.zone_string if zoning else None)
        or (parcel_data or {}).get("zone_code")
    )

    lot_area = (parcel_data or {}).get("lot_area_m2")
    lot_frontage = (parcel_data or {}).get("lot_frontage_m")
    lot_depth = (parcel_data or {}).get("lot_depth_m")
    current_use = _or((parcel_data or {}).get("current_use"))

    # Proposed development
    dev_type = _or(params.get("development_type"))
    building_type = _or(params.get("building_type"))
    height_m = massing.get("height_m") if massing else params.get("height_m")
    storeys = massing.get("storeys") if massing else params.get("storeys")
    unit_count = layout.get("total_units") if layout else params.get("unit_count")
    gfa = massing.get("estimated_gfa_m2") if massing else None
    fsi = massing.get("estimated_fsi") if massing else None
    lot_coverage_pct = massing.get("lot_coverage_pct") if massing else None
    if lot_coverage_pct is not None and lot_coverage_pct <= 1.0:
        lot_coverage_pct = lot_coverage_pct * 100.0

    # Compliance matrix — deterministic, never AI-generated
    compliance_summary = (
        render_compliance_matrix_markdown(compliance)
        if compliance
        else _NOT_AVAILABLE
    )

    context = {
        # Site information
        "address": address,
        "zoning_code": zoning_code,
        "lot_area_sqm": _fmt_area(lot_area),
        "lot_frontage_m": _fmt_number(lot_frontage, 1, suffix=" m"),
        "lot_depth_m": _fmt_number(lot_depth, 1, suffix=" m"),
        "current_use": current_use,

        # Proposed development
        "project_name": _or(project_name or params.get("project_name")),
        "organization_name": _or(organization_name),
        "development_type": dev_type,
        "building_type": building_type,
        "height_m": _fmt_number(height_m, 1),
        "storeys": _or(storeys),
        "unit_count": _or(unit_count),
        "gross_floor_area_sqm": _fmt_area(gfa),
        "fsi": _fmt_number(fsi, 3),
        "lot_coverage_pct": _fmt_number(lot_coverage_pct, 1, suffix="%"),
        "ground_floor_use": _or(params.get("ground_floor_use")),
        "parking_type": "Underground" if building_type and "tower" in str(building_type).lower() else "Surface/Underground",

        # Policy context
        "policy_stack_summary": _build_policy_stack_summary(policy_stack),
        "policy_provisions": _build_policy_stack_summary(policy_stack),
        "policy_constraints": _build_policy_stack_summary(policy_stack),

        # Compliance — DETERMINISTIC
        "compliance_summary": compliance_summary,
        "entitlement_results": compliance_summary,
        "variance_summary": _build_variance_summary(compliance),

        # Massing
        "massing_summary": _build_massing_parameters(massing),
        "massing_parameters": _build_massing_parameters(massing),
        "setback_data": _build_setback_data(zoning),
        "building_footprint": _fmt_area(massing.get("buildable_floorplate_m2") if massing else None),
        "orientation": _NOT_AVAILABLE,

        # Layout
        "unit_mix_data": _build_unit_mix_data(layout),
        "layout_results": _build_unit_mix_data(layout),

        # Finance
        "financial_results": _build_financial_results(finance),
        "financial_assumptions": _build_financial_assumptions(finance),
        "market_comparables": _NOT_AVAILABLE,

        # Precedents
        "precedent_results": _build_precedent_results(precedents),
        "precedent_summary": _build_precedent_results(precedents),
        "similarity_analysis": _build_precedent_results(precedents),

        # Public benefit / community
        "public_benefits": _NOT_AVAILABLE,
        "community_context": _NOT_AVAILABLE,
    }

    return context


def _build_setback_data(zoning: ZoningAnalysis | None) -> str:
    if zoning is None or zoning.standards is None:
        return _NOT_AVAILABLE

    s = zoning.standards
    lines = [
        "| Setback | Required | By-law Section |",
        "|---------|----------|---------------|",
        f"| Front | {s.min_front_setback_m:.1f} m | 569-2013 §{s.bylaw_section} |",
        f"| Rear | {s.min_rear_setback_m:.1f} m | 569-2013 §{s.bylaw_section} |",
        f"| Interior Side | {s.min_interior_side_setback_m:.1f} m | 569-2013 §{s.bylaw_section} |",
        f"| Exterior Side | {s.min_exterior_side_setback_m:.1f} m | 569-2013 §{s.bylaw_section} |",
    ]
    return "\n".join(lines)


def _build_financial_assumptions(finance: dict | None) -> str:
    if not finance:
        return _NOT_AVAILABLE

    assumptions = finance.get("assumptions_used", {})
    if not assumptions:
        return "Financial assumptions not available."

    lines = []
    cost = assumptions.get("cost_assumptions", {})
    if cost:
        lines.append(f"- Hard Cost: {_fmt_money(cost.get('hard_cost_per_m2'))}/m²")
        lines.append(f"- Soft Cost: {_fmt_number(cost.get('soft_cost_pct', 0) * 100, 1, suffix='%')} of hard cost")

    valuation = assumptions.get("valuation", {})
    if valuation.get("cap_rate"):
        lines.append(f"- Cap Rate: {valuation['cap_rate'] * 100:.2f}%")

    financing = assumptions.get("financing", {})
    if financing:
        lines.append(f"- LTC: {_fmt_number(financing.get('loan_to_cost_pct', 0) * 100, 1, suffix='%')}")
        lines.append(f"- Interest Rate: {_fmt_number(financing.get('interest_rate', 0) * 100, 2, suffix='%')}")

    return "\n".join(lines) if lines else "Assumptions detail not available."
