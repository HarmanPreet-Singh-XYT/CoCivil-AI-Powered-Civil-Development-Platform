"""Zoning lookup orchestrator.

Combines zone string parsing with DB parcel data and overlay constraints.
All values are deterministic — no AI involved.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.data.toronto_zoning import BICYCLE_PARKING, PARKING_STANDARDS, AMENITY_SPACE
from app.models.geospatial import Parcel
from app.services.zoning_parser import ZoneComponents, ZoneStandards, get_zone_standards, parse_zone_string


@dataclass
class ZoningAnalysis:
    """Complete zoning analysis for a parcel — fully deterministic."""

    parcel_id: Any
    address: str | None
    zone_string: str | None
    components: ZoneComponents | None
    standards: ZoneStandards | None
    parking_policy_area: str
    parking_standards: dict = field(default_factory=dict)
    bicycle_parking: dict = field(default_factory=dict)
    amenity_space: dict = field(default_factory=dict)
    overlay_constraints: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def get_zoning_analysis_sync(
    db: Session,
    parcel: Parcel,
    parking_policy_area: str = "PA3",
    overlay_data: list[dict] | None = None,
) -> ZoningAnalysis:
    """Build a complete deterministic zoning analysis for a parcel.

    Combines: zone string parsing + ZONE_STANDARDS lookup + overlay constraints.
    All values are from By-law 569-2013 reference data.
    """
    warnings: list[str] = []
    components = None
    standards = None

    zone_string = parcel.zone_code
    if zone_string:
        try:
            components = parse_zone_string(zone_string)
            standards = get_zone_standards(components)
        except ValueError as e:
            warnings.append(f"Zone parsing failed: {e}")
    else:
        warnings.append("Parcel has no zone_code — zoning standards unavailable")

    if standards and standards.exception_number:
        warnings.append(
            f"Site-specific exception (x{standards.exception_number}) may modify standards — "
            "verify with City of Toronto by-law office"
        )

    if standards and standards.has_site_specific_height:
        warnings.append(
            "Site-specific height provision detected — actual height limit may differ from base zone"
        )

    # Parking standards
    parking = PARKING_STANDARDS.get(parking_policy_area, PARKING_STANDARDS["PA3"])

    # Overlay constraints
    overlay_constraints = []
    if overlay_data:
        for overlay in overlay_data:
            layer_type = overlay.get("layer_type", "")
            attrs = overlay.get("attributes_json", {})
            constraint: dict[str, Any] = {
                "layer_type": layer_type,
                "layer_name": overlay.get("layer_name", ""),
            }
            if layer_type == "heritage":
                constraint["impact"] = "Heritage Conservation District — additional approvals required"
                constraint["affects"] = ["demolition", "exterior_alterations", "height"]
            elif layer_type == "floodplain":
                constraint["impact"] = "Floodplain overlay — TRCA permit required"
                constraint["affects"] = ["building_envelope", "grading", "fill"]
            elif layer_type == "environmental":
                constraint["impact"] = "Environmental constraint — ESA/ANSI review required"
                constraint["affects"] = ["setbacks", "lot_coverage", "grading"]

            overlay_constraints.append(constraint)

    return ZoningAnalysis(
        parcel_id=parcel.id,
        address=parcel.address,
        zone_string=zone_string,
        components=components,
        standards=standards,
        parking_policy_area=parking_policy_area,
        parking_standards=dict(parking),
        bicycle_parking=dict(BICYCLE_PARKING),
        amenity_space=dict(AMENITY_SPACE),
        overlay_constraints=overlay_constraints,
        warnings=warnings,
    )
