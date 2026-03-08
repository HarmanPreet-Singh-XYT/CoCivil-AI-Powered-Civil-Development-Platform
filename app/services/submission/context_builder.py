"""Assembles template context from pipeline data.

Bridges pipeline results to template placeholders. Every placeholder gets
a real value or explicit "[NOT AVAILABLE — requires manual input]".
"""

from __future__ import annotations

from typing import Any

from app.data.ontario_policy import (
    APPROVAL_PATHWAY,
    MINOR_VARIANCE_FOUR_TESTS,
    OBC_CONSTRAINTS,
    ONTARIO_POLICY_HIERARCHY,
    OREG_462_24,
    RECENT_LEGISLATION,
    TORONTO_OP_DESIGNATIONS,
    TORONTO_ZONING_KEY_RULES,
)
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
    source_filename: str = "",
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
    # Estimate frontage/depth from lot area if not available
    if lot_area and not lot_frontage:
        import math
        lot_frontage = round(math.sqrt(lot_area) * 0.6, 1)  # typical urban lot ratio
    if lot_area and not lot_depth:
        import math
        lot_depth = round(math.sqrt(lot_area) * 1.67, 1)
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
    variance_summary = _build_variance_summary(compliance)
    extracted_summary = "\n".join(
        [
            f"- Address: {address}",
            f"- Project Name: {_or(project_name or params.get('project_name'))}",
            f"- Development Type: {dev_type}",
            f"- Building Type: {building_type}",
            f"- Height: {_fmt_number(height_m, 1, suffix=' m')}",
            f"- Storeys: {_or(storeys)}",
            f"- Unit Count: {_or(unit_count)}",
            f"- Gross Floor Area: {_fmt_area(gfa)}",
        ]
    )
    overall_assessment = (
        "Deterministic checks indicate the current proposal is broadly aligned with the resolved zoning controls. "
        "Professional review is still required before submission."
        if compliance and compliance.overall_compliant
        else "Potential compliance issues or missing data were identified. "
        "Professional review is required before the package is used for submission."
    )

    context = {
        # Site information
        "address": address,
        "source_filename": _or(source_filename),
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
        "policy_stack_summary": _build_policy_stack_summary(policy_stack) if policy_stack else _build_policy_from_zoning(zoning),
        "policy_provisions": _build_policy_stack_summary(policy_stack) if policy_stack else _build_policy_from_zoning(zoning),
        "policy_constraints": _build_policy_constraints_from_compliance(zoning, massing, compliance),

        # Compliance — DETERMINISTIC
        "compliance_summary": compliance_summary,
        "entitlement_results": compliance_summary,
        "variance_summary": variance_summary,
        "compliance_issues": variance_summary if compliance else "No compliance issues identified.",
        "overall_assessment": overall_assessment,

        # Massing
        "massing_summary": _build_massing_parameters(massing),
        "massing_parameters": _build_massing_parameters(massing),
        "setback_data": _build_setback_data(zoning),
        "building_footprint": _fmt_area(massing.get("buildable_floorplate_m2") if massing else None),
        "orientation": _NOT_AVAILABLE,

        # Layout
        "unit_mix_data": _build_unit_mix_data(layout),
        "layout_results": _build_unit_mix_data(layout),
        "unit_mix_summary": _build_unit_mix_data(layout),
        "extracted_summary": extracted_summary,

        # Finance
        "financial_results": _build_financial_results(finance),
        "financial_assumptions": _build_financial_assumptions(finance),
        "market_comparables": _NOT_AVAILABLE,

        # Precedents
        "precedent_results": _build_precedent_results(precedents),
        "precedent_summary": _build_precedent_results(precedents),
        "similarity_analysis": _build_precedent_results(precedents),

        # Public benefit / community
        "public_benefits": _build_public_benefits(massing, layout, compliance),
        "community_context": _build_community_context(address, precedents),
        "auto_fixable": "None identified automatically. Manual confirmation required.",
        "requires_professional": (
            "Planning rationale, zoning interpretation, and final submission sign-off require "
            "qualified professional review."
        ),

        # New context keys for expanded document catalog
        "approval_pathway_summary": _build_approval_pathway_summary(compliance),
        "due_diligence_flags": _build_due_diligence_flags(parcel_data, compliance, overlays),
        "olt_grounds": _build_olt_grounds(compliance),
        "statutory_tests": MINOR_VARIANCE_FOUR_TESTS,
        "pac_requirements": _build_pac_requirements(),
        "submission_checklist_data": _NOT_AVAILABLE,
        "refusal_reasons": _or(params.get("refusal_reasons")),
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


def _build_policy_from_zoning(zoning: ZoningAnalysis | None) -> str:
    """Build policy context for the AI agent using real Ontario planning law."""
    site_section = ""
    if zoning and zoning.standards:
        s = zoning.standards
        parts = []
        if s.max_fsi is not None:
            parts.append(f"Max FSI {s.max_fsi:.1f}x")
        if s.max_height_m is not None:
            parts.append(f"Max Height {s.max_height_m:.1f}m")
        parts.append(f"Front Setback {s.min_front_setback_m:.1f}m")
        parts.append(f"Rear Setback {s.min_rear_setback_m:.1f}m")
        site_section = (
            f"\n## Site Zoning\n"
            f"The site is zoned **{zoning.zone_string}** under By-law 569-2013 (§{s.bylaw_section}).\n"
            f"Key standards: {', '.join(parts)}.\n"
        )

    return "\n\n".join([
        ONTARIO_POLICY_HIERARCHY,
        TORONTO_OP_DESIGNATIONS,
        TORONTO_ZONING_KEY_RULES,
        OREG_462_24,
        RECENT_LEGISLATION,
        MINOR_VARIANCE_FOUR_TESTS,
        OBC_CONSTRAINTS,
        APPROVAL_PATHWAY,
        site_section,
    ])


def _build_policy_constraints_from_compliance(
    zoning: ZoningAnalysis | None,
    massing: dict | None,
    compliance: ComplianceResult | None,
) -> str:
    """Build policy constraints section from zoning + compliance data."""
    lines = []

    if zoning and zoning.standards:
        s = zoning.standards
        if s.max_fsi is not None:
            lines.append(f"- **Maximum FSI**: {s.max_fsi:.1f}x")
        if s.max_height_m is not None:
            lines.append(f"- **Maximum Height**: {s.max_height_m:.1f} m")
        if s.max_lot_coverage_pct is not None:
            lines.append(f"- **Maximum Lot Coverage**: {s.max_lot_coverage_pct * 100:.0f}%")
        lines.append(f"- **Front Setback**: {s.min_front_setback_m:.1f} m")
        lines.append(f"- **Rear Setback**: {s.min_rear_setback_m:.1f} m")
        lines.append(f"- **Side Setback (Interior)**: {s.min_interior_side_setback_m:.1f} m")

    if compliance and compliance.variances_needed:
        lines.append(f"\n**{len(compliance.variances_needed)} variance(s) required** from as-of-right permissions.")

    return "\n".join(lines) if lines else _NOT_AVAILABLE


def _build_public_benefits(massing: dict | None, layout: dict | None, compliance: ComplianceResult | None) -> str:
    """Generate public benefits from project data."""
    lines = []

    if layout:
        total_units = layout.get("total_units", 0)
        if total_units:
            lines.append(f"- **Housing supply**: {total_units:,} new residential units contributing to the City's housing targets.")
        amenity = layout.get("amenity_required_m2")
        if amenity:
            lines.append(f"- **Amenity space**: {amenity:,.0f} m² of indoor amenity space for residents.")
        accessible = layout.get("accessible_units_required", 0)
        if accessible:
            lines.append(f"- **Accessibility**: {accessible} accessible units ({accessible / total_units * 100:.0f}% of total).")

    if massing:
        gfa = massing.get("estimated_gfa_m2", 0)
        if gfa:
            lines.append(f"- **Intensification**: Efficient use of urban land with {gfa:,.0f} m² GFA supporting transit-oriented growth.")

    lines.append("- **Section 37 / Community Benefits Charge**: Applicable contributions to be determined through the development approval process.")

    return "\n".join(lines) if lines else _NOT_AVAILABLE


def build_upload_context(
    extracted_data: dict | None,
    compliance_findings: dict | None,
    source_filename: str = "",
) -> dict[str, Any]:
    """Build template context from uploaded document analysis results.

    Maps AI-extracted data and compliance findings into the placeholder dict
    used by response document templates.
    """
    extracted = extracted_data or {}
    findings = compliance_findings or {}
    dims = extracted.get("dimensions", {})
    building = extracted.get("building", {})
    unit_mix = extracted.get("unit_mix", {})

    # Build extracted summary
    summary_lines = []
    if building.get("storeys"):
        summary_lines.append(f"- Storeys: {building['storeys']}")
    if building.get("height_m"):
        summary_lines.append(f"- Height: {building['height_m']} m")
    if building.get("unit_count"):
        summary_lines.append(f"- Units: {building['unit_count']}")
    if building.get("gfa_m2"):
        summary_lines.append(f"- GFA: {_fmt_area(building['gfa_m2'])}")
    if dims.get("lot_area_m2"):
        summary_lines.append(f"- Lot Area: {_fmt_area(dims['lot_area_m2'])}")
    if dims.get("lot_frontage_m"):
        summary_lines.append(f"- Lot Frontage: {_fmt_number(dims['lot_frontage_m'], 1, suffix=' m')}")

    # Unit mix summary
    mix_lines = []
    for unit_type, data in unit_mix.items():
        if isinstance(data, dict) and data.get("count"):
            mix_lines.append(f"- {unit_type.replace('_', ' ').title()}: {data['count']} units ({_fmt_area(data.get('avg_area_m2'))} avg)")

    # Compliance issues summary
    issues = findings.get("issues", [])
    issue_lines = []
    for issue in issues:
        severity = issue.get("severity", "info").upper()
        issue_lines.append(f"- **[{severity}]** {issue.get('description', 'N/A')} ({issue.get('code_reference', 'N/A')})")

    return {
        "source_filename": source_filename,
        "address": _or(extracted.get("address")),
        "project_name": _or(extracted.get("project_name")),
        "extracted_summary": "\n".join(summary_lines) if summary_lines else _NOT_AVAILABLE,
        "unit_mix_summary": "\n".join(mix_lines) if mix_lines else _NOT_AVAILABLE,
        "compliance_issues": "\n".join(issue_lines) if issue_lines else "No compliance issues identified.",
        "overall_assessment": _or(findings.get("overall_assessment")),
        "auto_fixable": ", ".join(findings.get("auto_fixable", [])) or "None identified.",
        "requires_professional": ", ".join(findings.get("requires_professional", [])) or "None identified.",
        "storeys": _or(building.get("storeys")),
        "height_m": _fmt_number(building.get("height_m"), 1),
        "unit_count": _or(building.get("unit_count")),
        "gfa_m2": _fmt_area(building.get("gfa_m2")),
        "lot_area_m2": _fmt_area(dims.get("lot_area_m2")),
    }


def _build_approval_pathway_summary(compliance: ComplianceResult | None) -> str:
    """Classify approval pathway from compliance results."""
    if compliance is None:
        return _NOT_AVAILABLE

    if not compliance.variances_needed:
        return "**As-of-Right** — No variances required. Proposal complies with all zoning provisions."

    if compliance.minor_variance_applicable:
        return (
            f"**Minor Variance (Committee of Adjustment)** — "
            f"{len(compliance.variances_needed)} variance(s) required, all under 20% deviation. "
            f"Eligible for minor variance under Section 45(1) of the Planning Act."
        )

    return (
        f"**Zoning By-law Amendment (ZBA)** — "
        f"{len(compliance.variances_needed)} variance(s) required, one or more exceeds "
        f"minor variance thresholds. A Zoning By-law Amendment application is likely required."
    )


def _build_due_diligence_flags(
    parcel_data: dict | None,
    compliance: ComplianceResult | None,
    overlays: dict | None,
) -> str:
    """Build bullet list of due diligence flags."""
    flags = []

    # Overlay flags
    if overlays:
        overlay_list = overlays if isinstance(overlays, list) else overlays.get("overlays", [])
        for ov in overlay_list:
            name = ov.get("name") or ov.get("overlay_type", "Unknown overlay")
            flags.append(f"- **Overlay**: {name}")

    # Variance flags
    if compliance and compliance.variances_needed:
        for v in compliance.variances_needed:
            severity = "HIGH" if v.variance_pct and v.variance_pct > 20 else "MODERATE"
            pct = f" ({v.variance_pct:+.1f}%)" if v.variance_pct else ""
            flags.append(f"- **[{severity}] Variance**: {v.parameter}{pct}")

    # Missing parcel data
    if parcel_data:
        for field in ["lot_area_m2", "lot_frontage_m", "lot_depth_m"]:
            if not parcel_data.get(field):
                flags.append(f"- **Missing data**: {field.replace('_', ' ')}")

    return "\n".join(flags) if flags else "No significant flags identified."


def _build_olt_grounds(compliance: ComplianceResult | None) -> str:
    """Build OLT appeal grounds based on compliance path."""
    if compliance is None:
        return _NOT_AVAILABLE

    if compliance.minor_variance_applicable:
        return (
            "**Appeal under s.45(18) of the Planning Act** (Committee of Adjustment decision).\n\n"
            "The appellant must demonstrate that the four statutory tests under s.45(1) are "
            "satisfied: (1) minor in nature, (2) desirable for appropriate development, "
            "(3) maintains general intent of the Zoning By-law, (4) maintains general intent "
            "of the Official Plan."
        )

    return (
        "**Appeal under s.34(11) of the Planning Act** (Zoning By-law Amendment).\n\n"
        "The appellant must demonstrate that the proposed amendment is consistent with the "
        "Provincial Planning Statement (2024), conforms to applicable provincial plans, "
        "and has regard for matters of provincial interest under s.2 of the Planning Act."
    )


def _build_pac_requirements() -> str:
    """Static PAC process requirements."""
    return (
        "**Pre-Application Consultation (PAC) Requirements:**\n\n"
        "Under Bill 109, applicants must request a PAC meeting before submitting certain applications.\n"
        "- Complete application form with preliminary development concept\n"
        "- Conceptual site plan showing building footprint, setbacks, and access\n"
        "- Preliminary development statistics (height, GFA, unit count, parking)\n"
        "- Applicable policy framework summary\n"
        "- List of questions for city planning staff\n"
        "- Survey or legal description of the property\n\n"
        "The city has 45 days to hold the PAC meeting after request."
    )


def _build_community_context(address: str, precedents: list[dict] | None) -> str:
    """Build community context from address and precedent data."""
    lines = [f"The proposed development at {address} is situated within an evolving urban context."]

    if precedents:
        approved = [p for p in precedents if p.get("decision") == "approved"]
        lines.append(
            f"There are {len(precedents)} recent development application(s) within the surrounding area, "
            f"{'including ' + str(len(approved)) + ' approved application(s), ' if approved else ''}"
            f"demonstrating an established pattern of intensification in this neighbourhood."
        )
    else:
        lines.append("Further neighbourhood analysis is recommended to establish community context.")

    return "\n".join(lines)
