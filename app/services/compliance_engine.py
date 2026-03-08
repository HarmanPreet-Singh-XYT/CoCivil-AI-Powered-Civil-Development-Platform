"""Deterministic compliance engine for Toronto By-law 569-2013.

This is the most critical file for legal safety.
The compliance matrix NEVER uses AI — all checks are pure math
against structured zoning standards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.data.toronto_zoning import AMENITY_SPACE, BICYCLE_PARKING
from app.services.zoning_parser import ZoneStandards
from app.services.zoning_service import ZoningAnalysis


@dataclass(frozen=True)
class ComplianceRule:
    """A single row in the compliance matrix."""

    parameter: str
    bylaw_section: str
    permitted_value: float | None
    proposed_value: float | None
    unit: str
    compliant: bool
    variance_required: bool
    variance_pct: float | None = None
    note: str = ""


@dataclass
class ComplianceResult:
    """Full deterministic compliance check result."""

    rules: list[ComplianceRule] = field(default_factory=list)
    overall_compliant: bool = True
    variances_needed: list[ComplianceRule] = field(default_factory=list)
    minor_variance_applicable: bool = True
    warnings: list[str] = field(default_factory=list)


def _check_max(
    parameter: str,
    bylaw_section: str,
    permitted: float | None,
    proposed: float | None,
    unit: str,
    note: str = "",
) -> ComplianceRule:
    """Check that proposed <= permitted (max constraint)."""
    if permitted is None or proposed is None:
        return ComplianceRule(
            parameter=parameter,
            bylaw_section=bylaw_section,
            permitted_value=permitted,
            proposed_value=proposed,
            unit=unit,
            compliant=True,
            variance_required=False,
            note=note or "Value not available — manual verification required",
        )

    compliant = proposed <= permitted
    variance_pct = None
    if not compliant and permitted > 0:
        variance_pct = round(((proposed - permitted) / permitted) * 100, 2)

    return ComplianceRule(
        parameter=parameter,
        bylaw_section=bylaw_section,
        permitted_value=permitted,
        proposed_value=proposed,
        unit=unit,
        compliant=compliant,
        variance_required=not compliant,
        variance_pct=variance_pct,
        note=note,
    )


def _check_min(
    parameter: str,
    bylaw_section: str,
    required: float | None,
    proposed: float | None,
    unit: str,
    note: str = "",
) -> ComplianceRule:
    """Check that proposed >= required (min constraint)."""
    if required is None or proposed is None:
        return ComplianceRule(
            parameter=parameter,
            bylaw_section=bylaw_section,
            permitted_value=required,
            proposed_value=proposed,
            unit=unit,
            compliant=True,
            variance_required=False,
            note=note or "Value not available — manual verification required",
        )

    compliant = proposed >= required
    variance_pct = None
    if not compliant and required > 0:
        variance_pct = round(((required - proposed) / required) * 100, 2)

    return ComplianceRule(
        parameter=parameter,
        bylaw_section=bylaw_section,
        permitted_value=required,
        proposed_value=proposed,
        unit=unit,
        compliant=compliant,
        variance_required=not compliant,
        variance_pct=variance_pct,
        note=note,
    )


def check_compliance(
    zoning: ZoningAnalysis,
    massing: dict[str, Any],
    layout: dict[str, Any],
    overlays: list[dict] | None = None,
) -> ComplianceResult:
    """Run deterministic compliance checks against By-law 569-2013.

    Each check includes a by-law section citation. No AI touches this.

    Args:
        zoning: Parsed zoning analysis for the parcel.
        massing: Output from compute_massing_summary.
        layout: Output from compute_layout_result.
        overlays: Optional overlay constraint data.

    Returns:
        ComplianceResult with every compliance rule, variances needed,
        and whether minor variance (Section 45(1) Planning Act) applies.
    """
    standards = zoning.standards
    if standards is None:
        return ComplianceResult(
            warnings=["No zoning standards available — compliance check skipped"],
        )

    rules: list[ComplianceRule] = []
    section_prefix = f"569-2013 §{standards.bylaw_section}"

    # 1. Max height
    rules.append(_check_max(
        parameter="Maximum Building Height",
        bylaw_section=section_prefix,
        permitted=standards.max_height_m,
        proposed=massing.get("height_m"),
        unit="m",
    ))

    # 2. Max storeys
    if standards.max_storeys is not None:
        rules.append(_check_max(
            parameter="Maximum Storeys",
            bylaw_section=section_prefix,
            permitted=float(standards.max_storeys),
            proposed=float(massing.get("storeys", 0)),
            unit="storeys",
        ))

    # 3. Max density / FSI
    rules.append(_check_max(
        parameter="Maximum Floor Space Index (FSI)",
        bylaw_section=section_prefix,
        permitted=standards.max_fsi,
        proposed=massing.get("estimated_fsi"),
        unit="x lot area",
    ))

    # 4. Min front setback
    proposed_front_setback = (
        massing.get("front_setback_m")
        or massing.get("assumptions_used", {}).get(
            "policy_geometry_defaults", {}
        ).get("front_setback_m")
        or None
    )
    rules.append(_check_min(
        parameter="Minimum Front Setback",
        bylaw_section=section_prefix,
        required=standards.min_front_setback_m,
        proposed=proposed_front_setback,
        unit="m",
        note="Proposed value from massing assumptions — verify with site plan",
    ))

    # 5. Min rear setback
    rules.append(_check_min(
        parameter="Minimum Rear Setback",
        bylaw_section=section_prefix,
        required=standards.min_rear_setback_m,
        proposed=None,  # requires site plan data
        unit="m",
        note="Requires site plan — manual verification needed",
    ))

    # 6. Min interior side setback
    rules.append(_check_min(
        parameter="Minimum Interior Side Setback",
        bylaw_section=section_prefix,
        required=standards.min_interior_side_setback_m,
        proposed=None,
        unit="m",
        note="Requires site plan — manual verification needed",
    ))

    # 7. Min exterior side setback
    rules.append(_check_min(
        parameter="Minimum Exterior Side Setback",
        bylaw_section=section_prefix,
        required=standards.min_exterior_side_setback_m,
        proposed=None,
        unit="m",
        note="Requires site plan — manual verification needed",
    ))

    # 8. Max lot coverage
    # O.Reg 462/24 §4(3) — 45% lot coverage for ≤3 unit multiplex in R zones
    total_units = layout.get("total_units", 0)
    permitted_lot_coverage = standards.max_lot_coverage_pct
    if (zoning.zone_string.upper().startswith("R")
            and total_units <= 3
            and permitted_lot_coverage is not None):
        permitted_lot_coverage = max(permitted_lot_coverage, 45.0)

    lot_coverage_proposed = massing.get("lot_coverage_pct")
    if lot_coverage_proposed is not None and lot_coverage_proposed <= 1.0:
        lot_coverage_proposed = lot_coverage_proposed * 100.0
    lot_coverage_note = ""
    if (zoning.zone_string.upper().startswith("R")
            and total_units <= 3
            and permitted_lot_coverage != standards.max_lot_coverage_pct):
        lot_coverage_note = "O.Reg 462/24 §4(3) — 45% lot coverage for ≤3 unit multiplex"
    rules.append(_check_max(
        parameter="Maximum Lot Coverage",
        bylaw_section=section_prefix,
        permitted=permitted_lot_coverage,
        proposed=lot_coverage_proposed,
        unit="%",
        note=lot_coverage_note,
    ))

    # 9. Min landscaped area
    proposed_landscaping = layout.get("landscaping_pct")
    rules.append(_check_min(
        parameter="Minimum Landscaped Open Space",
        bylaw_section=section_prefix,
        required=standards.min_landscaping_pct,
        proposed=proposed_landscaping,
        unit="%",
        note="" if proposed_landscaping is not None else "Requires site plan — manual verification needed",
    ))

    # 10. Parking minimums (by policy area)
    parking_std = zoning.parking_standards
    # Bill 185 — zero minimum parking for ≤10 unit residential in R zones
    if total_units <= 10 and zoning.zone_string.upper().startswith("R"):
        parking_per_unit = 0.0
    else:
        parking_per_unit = parking_std.get("residential_per_unit", 0.0)
    required_parking = round(total_units * parking_per_unit, 1)
    proposed_parking = layout.get("parking_required")
    rules.append(_check_min(
        parameter="Minimum Residential Parking Spaces",
        bylaw_section=f"569-2013 §{parking_std.get('bylaw_section', '200.5.10')}",
        required=required_parking,
        proposed=proposed_parking,
        unit="spaces",
        note=f"Based on {zoning.parking_policy_area} standards",
    ))

    # 11. Bicycle parking (Chapter 230)
    bike_section = BICYCLE_PARKING["bylaw_section"]
    required_long_term = round(total_units * float(BICYCLE_PARKING["long_term_per_unit"]), 1)
    required_short_term = round(total_units * float(BICYCLE_PARKING["short_term_per_unit"]), 1)
    rules.append(_check_min(
        parameter="Minimum Long-Term Bicycle Parking",
        bylaw_section=f"569-2013 §{bike_section}",
        required=required_long_term,
        proposed=None,  # not in massing output
        unit="spaces",
        note="Requires detailed design — manual verification needed",
    ))
    rules.append(_check_min(
        parameter="Minimum Short-Term Bicycle Parking",
        bylaw_section=f"569-2013 §{bike_section}",
        required=required_short_term,
        proposed=None,
        unit="spaces",
        note="Requires detailed design — manual verification needed",
    ))

    # 12. Amenity space (Chapter 230)
    amenity_section = AMENITY_SPACE["bylaw_section"]
    required_amenity = round(total_units * float(AMENITY_SPACE["total_per_unit_m2"]), 1)
    proposed_amenity = layout.get("amenity_required_m2")
    rules.append(_check_min(
        parameter="Minimum Amenity Space",
        bylaw_section=f"569-2013 §{amenity_section}",
        required=required_amenity,
        proposed=proposed_amenity,
        unit="m²",
    ))

    # 13. Angular plane (Tall Building Guidelines) — check if height > 80m
    proposed_height = massing.get("height_m", 0)
    if proposed_height and proposed_height > 80:
        rules.append(ComplianceRule(
            parameter="Angular Plane Compliance",
            bylaw_section="Tall Building Design Guidelines §3.2.3",
            permitted_value=80.0,
            proposed_value=proposed_height,
            unit="m",
            compliant=False,
            variance_required=True,
            variance_pct=round(((proposed_height - 80.0) / 80.0) * 100, 2),
            note="Buildings over 80m require angular plane analysis per Tall Building Guidelines",
        ))

    # Build result
    variances_needed = [r for r in rules if r.variance_required]
    overall_compliant = len(variances_needed) == 0

    # Determine if minor variance is applicable (Section 45(1) Planning Act)
    # Minor variance is generally applicable if all variances are < 20%
    minor_variance_applicable = all(
        (v.variance_pct is not None and v.variance_pct < 20.0)
        for v in variances_needed
    ) if variances_needed else True

    warnings = list(zoning.warnings)
    if not overall_compliant and not minor_variance_applicable:
        warnings.append(
            "One or more variances exceed minor variance thresholds — "
            "a Zoning By-law Amendment (ZBA) may be required"
        )

    return ComplianceResult(
        rules=rules,
        overall_compliant=overall_compliant,
        variances_needed=variances_needed,
        minor_variance_applicable=minor_variance_applicable,
        warnings=warnings,
    )


def render_compliance_matrix_markdown(result: ComplianceResult) -> str:
    """Render the compliance matrix as a deterministic Markdown table.

    This output goes directly into the submission document — no AI formatting.
    """
    lines = [
        "| Provision | By-law Section | Required | Proposed | Status |",
        "|-----------|---------------|----------|----------|--------|",
    ]

    for rule in result.rules:
        permitted = _format_value(rule.permitted_value, rule.unit)
        proposed = _format_value(rule.proposed_value, rule.unit)
        status = "COMPLIES" if rule.compliant else "VARIANCE REQUIRED"
        if rule.variance_pct is not None and not rule.compliant:
            status += f" ({rule.variance_pct:+.1f}%)"

        lines.append(
            f"| {rule.parameter} | {rule.bylaw_section} | {permitted} | {proposed} | {status} |"
        )

    # Summary row
    total = len(result.rules)
    compliant_count = sum(1 for r in result.rules if r.compliant)
    variance_count = len(result.variances_needed)
    lines.append("")
    lines.append(f"**Summary**: {compliant_count}/{total} provisions comply. "
                 f"{variance_count} variance(s) required.")

    if result.variances_needed:
        if result.minor_variance_applicable:
            lines.append(
                "\n*All requested variances may be eligible for minor variance "
                "under Section 45(1) of the Planning Act.*"
            )
        else:
            lines.append(
                "\n*One or more variances exceed minor variance thresholds. "
                "A Zoning By-law Amendment may be required.*"
            )

    return "\n".join(lines)


def _format_value(value: float | None, unit: str) -> str:
    """Format a numeric value with its unit for display."""
    if value is None:
        return "[TBD]"
    if unit == "%" :
        return f"{value:.1f}%"
    if unit == "m²":
        return f"{value:,.1f} m²"
    if unit == "m":
        return f"{value:.1f} m"
    if unit == "storeys":
        return f"{int(value)}"
    if unit == "spaces":
        return f"{value:.0f}"
    if unit == "x lot area":
        return f"{value:.2f}x"
    return f"{value}"
