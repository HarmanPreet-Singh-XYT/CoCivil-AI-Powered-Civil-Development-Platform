"""Deterministic infrastructure compliance engine.

This is critical for safety — all checks are pure math
against structured civil engineering standards. NO AI.
"""

from __future__ import annotations

from typing import Any

from app.data.civil_standards import (
    BRIDGE_STRUCTURE_TYPES,
    BRIDGE_TYPE_STANDARDS,
    MANHOLE_STANDARDS,
    PIPE_MATERIALS,
    PIPE_TYPE_STANDARDS,
    SANITARY_MIN_SLOPE,
)
from app.services.compliance_engine import ComplianceResult, ComplianceRule


def _check_min(
    parameter: str,
    standard_ref: str,
    required: float | None,
    proposed: float | None,
    unit: str,
    note: str = "",
) -> ComplianceRule:
    """Check that proposed >= required (min constraint)."""
    if required is None or proposed is None:
        return ComplianceRule(
            parameter=parameter,
            bylaw_section=standard_ref,
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
        bylaw_section=standard_ref,
        permitted_value=required,
        proposed_value=proposed,
        unit=unit,
        compliant=compliant,
        variance_required=not compliant,
        variance_pct=variance_pct,
        note=note,
    )


def _check_max(
    parameter: str,
    standard_ref: str,
    permitted: float | None,
    proposed: float | None,
    unit: str,
    note: str = "",
) -> ComplianceRule:
    """Check that proposed <= permitted (max constraint)."""
    if permitted is None or proposed is None:
        return ComplianceRule(
            parameter=parameter,
            bylaw_section=standard_ref,
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
        bylaw_section=standard_ref,
        permitted_value=permitted,
        proposed_value=proposed,
        unit=unit,
        compliant=compliant,
        variance_required=not compliant,
        variance_pct=variance_pct,
        note=note,
    )


def _check_in_set(
    parameter: str,
    standard_ref: str,
    valid_set: list[str],
    proposed: str | None,
    note: str = "",
) -> ComplianceRule:
    """Check that a proposed value is in a valid set."""
    if proposed is None:
        return ComplianceRule(
            parameter=parameter,
            bylaw_section=standard_ref,
            permitted_value=None,
            proposed_value=None,
            unit="",
            compliant=True,
            variance_required=False,
            note=note or "Value not available — manual verification required",
        )

    compliant = proposed in valid_set
    return ComplianceRule(
        parameter=parameter,
        bylaw_section=standard_ref,
        permitted_value=None,
        proposed_value=None,
        unit="",
        compliant=compliant,
        variance_required=not compliant,
        note=f"{'Acceptable' if compliant else 'Not acceptable'}: {proposed}. Valid: {', '.join(valid_set)}",
    )


def check_pipeline_compliance(
    pipe_type: str,
    params: dict[str, Any],
) -> ComplianceResult:
    """Run deterministic compliance checks for a pipeline asset.

    Args:
        pipe_type: One of water_main, sanitary_sewer, storm_sewer, gas_line.
        params: Dict with keys: diameter_mm, cover_m, slope_pct, velocity_m_s,
                manhole_spacing_m, material, separation_from_water_m.

    Returns:
        ComplianceResult with every compliance rule and variances needed.
    """
    standards = PIPE_TYPE_STANDARDS.get(pipe_type)
    if not standards:
        return ComplianceResult(
            warnings=[f"Unknown pipe type: {pipe_type}"],
        )

    rules: list[ComplianceRule] = []
    std_ref = standards["standards_ref"]

    # 1. Minimum diameter
    rules.append(_check_min(
        parameter="Minimum Pipe Diameter",
        standard_ref=std_ref,
        required=standards.get("min_diameter_mm"),
        proposed=params.get("diameter_mm"),
        unit="mm",
    ))

    # 2. Minimum cover depth
    rules.append(_check_min(
        parameter="Minimum Cover Depth",
        standard_ref=std_ref,
        required=standards.get("min_cover_m"),
        proposed=params.get("cover_m"),
        unit="m",
    ))

    # 3. Maximum cover depth
    rules.append(_check_max(
        parameter="Maximum Cover Depth",
        standard_ref=std_ref,
        permitted=standards.get("max_cover_m"),
        proposed=params.get("cover_m"),
        unit="m",
    ))

    # 4. Minimum slope — use diameter-specific for sanitary
    min_slope = standards.get("min_slope_pct")
    slope_note = ""
    if pipe_type == "sanitary_sewer" and params.get("diameter_mm"):
        diameter = int(params["diameter_mm"])
        # Find closest diameter in SANITARY_MIN_SLOPE
        closest_d = min(SANITARY_MIN_SLOPE.keys(), key=lambda d: abs(d - diameter))
        min_slope = SANITARY_MIN_SLOPE[closest_d]
        slope_note = f"Manning's equation for {closest_d}mm diameter"

    rules.append(_check_min(
        parameter="Minimum Slope",
        standard_ref=std_ref,
        required=min_slope,
        proposed=params.get("slope_pct"),
        unit="%",
        note=slope_note,
    ))

    # 5. Minimum velocity
    if standards.get("min_velocity_m_s") is not None:
        rules.append(_check_min(
            parameter="Minimum Flow Velocity",
            standard_ref=std_ref,
            required=standards.get("min_velocity_m_s"),
            proposed=params.get("velocity_m_s"),
            unit="m/s",
        ))

    # 6. Maximum velocity
    if standards.get("max_velocity_m_s") is not None:
        rules.append(_check_max(
            parameter="Maximum Flow Velocity",
            standard_ref=std_ref,
            permitted=standards.get("max_velocity_m_s"),
            proposed=params.get("velocity_m_s"),
            unit="m/s",
        ))

    # 7. Manhole spacing
    if pipe_type in ("sanitary_sewer", "storm_sewer"):
        rules.append(_check_max(
            parameter="Maximum Manhole Spacing",
            standard_ref=MANHOLE_STANDARDS["standards_ref"],
            permitted=MANHOLE_STANDARDS["max_spacing_m"],
            proposed=params.get("manhole_spacing_m"),
            unit="m",
        ))

    # 8. Material suitability
    material = params.get("material")
    if material:
        mat_info = PIPE_MATERIALS.get(material)
        if mat_info:
            valid_uses = mat_info["valid_uses"]
            rules.append(_check_in_set(
                parameter="Material Suitability",
                standard_ref=mat_info["standards_ref"],
                valid_set=valid_uses,
                proposed=pipe_type,
                note=f"{material} ({mat_info['label']})",
            ))
        else:
            rules.append(ComplianceRule(
                parameter="Material Suitability",
                bylaw_section=std_ref,
                permitted_value=None,
                proposed_value=None,
                unit="",
                compliant=False,
                variance_required=True,
                note=f"Unknown material: {material}",
            ))

    # 9. Separation from water main (for non-water pipes)
    if pipe_type != "water_main":
        sep_key = "separation_from_water_m"
        rules.append(_check_min(
            parameter="Separation from Water Main",
            standard_ref=std_ref,
            required=standards.get(sep_key),
            proposed=params.get("separation_from_water_m"),
            unit="m",
        ))

    # Build result
    variances_needed = [r for r in rules if r.variance_required]
    overall_compliant = len(variances_needed) == 0
    warnings: list[str] = []
    if not overall_compliant:
        warnings.append("Infrastructure does not meet minimum standards — redesign or variance required")

    return ComplianceResult(
        rules=rules,
        overall_compliant=overall_compliant,
        variances_needed=variances_needed,
        minor_variance_applicable=False,
        warnings=warnings,
    )


def check_bridge_compliance(
    bridge_type: str,
    params: dict[str, Any],
) -> ComplianceResult:
    """Run deterministic compliance checks for a bridge asset.

    Args:
        bridge_type: One of road_bridge, pedestrian_bridge, culvert.
        params: Dict with keys: deck_width_m, clearance_m, barrier_height_m,
                structure_type, span_m, structural_depth_m, cover_m.

    Returns:
        ComplianceResult with every compliance rule and variances needed.
    """
    standards = BRIDGE_TYPE_STANDARDS.get(bridge_type)
    if not standards:
        return ComplianceResult(
            warnings=[f"Unknown bridge type: {bridge_type}"],
        )

    rules: list[ComplianceRule] = []
    std_ref = standards["standards_ref"]

    # 1. Minimum deck width
    if standards.get("min_deck_width_m") is not None:
        rules.append(_check_min(
            parameter="Minimum Deck Width",
            standard_ref=std_ref,
            required=standards["min_deck_width_m"],
            proposed=params.get("deck_width_m"),
            unit="m",
        ))

    # 2. Minimum clearance
    rules.append(_check_min(
        parameter="Minimum Clearance",
        standard_ref=std_ref,
        required=standards.get("min_clearance_m"),
        proposed=params.get("clearance_m"),
        unit="m",
    ))

    # 3. Barrier height
    if standards.get("min_barrier_height_m") is not None:
        rules.append(_check_min(
            parameter="Minimum Barrier Height",
            standard_ref=std_ref,
            required=standards["min_barrier_height_m"],
            proposed=params.get("barrier_height_m"),
            unit="m",
        ))

    # 4. Structure type span range
    structure_type = params.get("structure_type")
    span = params.get("span_m")
    if structure_type and structure_type in BRIDGE_STRUCTURE_TYPES:
        struct_std = BRIDGE_STRUCTURE_TYPES[structure_type]
        struct_ref = struct_std["standards_ref"]

        rules.append(_check_min(
            parameter="Minimum Span for Structure Type",
            standard_ref=struct_ref,
            required=struct_std["min_span_m"],
            proposed=span,
            unit="m",
            note=f"{struct_std['label']}",
        ))

        rules.append(_check_max(
            parameter="Maximum Span for Structure Type",
            standard_ref=struct_ref,
            permitted=struct_std["max_span_m"],
            proposed=span,
            unit="m",
            note=f"{struct_std['label']}",
        ))

        # 5. L/D ratio (structural depth check)
        structural_depth = params.get("structural_depth_m")
        if span and structural_depth and structural_depth > 0:
            ld_ratio = span / structural_depth
            rules.append(_check_min(
                parameter="Minimum L/D Ratio (Structural Slenderness)",
                standard_ref=struct_ref,
                required=float(struct_std["ld_ratio_min"]),
                proposed=round(ld_ratio, 1),
                unit="ratio",
                note=f"L/D = span ({span}m) / depth ({structural_depth}m)",
            ))
            rules.append(_check_max(
                parameter="Maximum L/D Ratio (Structural Slenderness)",
                standard_ref=struct_ref,
                permitted=float(struct_std["ld_ratio_max"]),
                proposed=round(ld_ratio, 1),
                unit="ratio",
                note=f"L/D = span ({span}m) / depth ({structural_depth}m)",
            ))

    # 6. Culvert cover depth
    if bridge_type == "culvert" and standards.get("min_cover_m") is not None:
        rules.append(_check_min(
            parameter="Minimum Culvert Cover Depth",
            standard_ref=std_ref,
            required=standards["min_cover_m"],
            proposed=params.get("cover_m"),
            unit="m",
        ))

    # Build result
    variances_needed = [r for r in rules if r.variance_required]
    overall_compliant = len(variances_needed) == 0
    warnings: list[str] = []
    if not overall_compliant:
        warnings.append("Bridge/culvert does not meet minimum standards — redesign required")

    return ComplianceResult(
        rules=rules,
        overall_compliant=overall_compliant,
        variances_needed=variances_needed,
        minor_variance_applicable=False,
        warnings=warnings,
    )
