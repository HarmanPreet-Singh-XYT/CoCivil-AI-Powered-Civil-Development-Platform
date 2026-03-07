"""Structured By-law 569-2013 zoning standards for Toronto.

All data is deterministic reference data — no AI involved.
Sources: City of Toronto By-law 569-2013 (as amended).
"""

# Zone category standards from By-law 569-2013
ZONE_STANDARDS: dict[str, dict] = {
    "R": {
        "label": "Residential",
        "permitted_uses": [
            "detached house", "semi-detached house", "duplex",
            "triplex", "fourplex", "home occupation",
        ],
        "max_height_m": 10.0,
        "max_storeys": 3,
        "min_front_setback_m": 6.0,
        "min_rear_setback_m": 7.5,
        "min_side_setback_m": {"interior": 0.9, "exterior": 3.0},
        "max_lot_coverage_pct": 35.0,
        "min_landscaping_pct": 30.0,
        "max_fsi": 0.6,
        "bylaw_section": "10.20",
    },
    "RM": {
        "label": "Residential Multiple",
        "permitted_uses": [
            "detached house", "semi-detached house", "duplex",
            "triplex", "fourplex", "townhouse", "apartment building",
        ],
        "max_height_m": 12.0,
        "max_storeys": 4,
        "min_front_setback_m": 4.5,
        "min_rear_setback_m": 7.5,
        "min_side_setback_m": {"interior": 1.2, "exterior": 3.0},
        "max_lot_coverage_pct": 40.0,
        "min_landscaping_pct": 25.0,
        "max_fsi": 1.0,
        "bylaw_section": "15.20",
    },
    "RA": {
        "label": "Residential Apartment",
        "permitted_uses": [
            "apartment building", "retirement home",
            "dwelling units above the first storey",
        ],
        "max_height_m": 36.0,
        "max_storeys": 12,
        "min_front_setback_m": 6.0,
        "min_rear_setback_m": 7.5,
        "min_side_setback_m": {"interior": 3.0, "exterior": 6.0},
        "max_lot_coverage_pct": 45.0,
        "min_landscaping_pct": 20.0,
        "max_fsi": 2.5,
        "bylaw_section": "20.20",
    },
    "CR": {
        "label": "Commercial Residential",
        "permitted_uses": [
            "retail store", "office", "service shop",
            "restaurant", "apartment building", "dwelling units above the first storey",
        ],
        "max_height_m": None,  # set by zone suffix
        "max_storeys": None,
        "min_front_setback_m": 0.0,
        "min_rear_setback_m": 7.5,
        "min_side_setback_m": {"interior": 0.0, "exterior": 0.0},
        "max_lot_coverage_pct": 100.0,
        "min_landscaping_pct": 0.0,
        "max_fsi": None,  # set by zone suffix
        "bylaw_section": "40.10",
    },
    "CL": {
        "label": "Commercial Local",
        "permitted_uses": [
            "retail store", "service shop", "office",
            "restaurant", "medical office",
        ],
        "max_height_m": 12.0,
        "max_storeys": 3,
        "min_front_setback_m": 0.0,
        "min_rear_setback_m": 7.5,
        "min_side_setback_m": {"interior": 0.0, "exterior": 0.0},
        "max_lot_coverage_pct": 100.0,
        "min_landscaping_pct": 0.0,
        "max_fsi": 1.0,
        "bylaw_section": "30.20",
    },
    "CG": {
        "label": "Commercial General",
        "permitted_uses": [
            "retail store", "service shop", "office",
            "restaurant", "entertainment place of assembly",
            "hotel", "medical office",
        ],
        "max_height_m": 14.0,
        "max_storeys": 4,
        "min_front_setback_m": 0.0,
        "min_rear_setback_m": 7.5,
        "min_side_setback_m": {"interior": 0.0, "exterior": 0.0},
        "max_lot_coverage_pct": 100.0,
        "min_landscaping_pct": 0.0,
        "max_fsi": 2.0,
        "bylaw_section": "35.20",
    },
    "E": {
        "label": "Employment",
        "permitted_uses": [
            "manufacturing", "warehouse", "wholesaling",
            "office", "research and development",
        ],
        "max_height_m": 15.0,
        "max_storeys": 4,
        "min_front_setback_m": 10.0,
        "min_rear_setback_m": 7.5,
        "min_side_setback_m": {"interior": 3.0, "exterior": 6.0},
        "max_lot_coverage_pct": 45.0,
        "min_landscaping_pct": 15.0,
        "max_fsi": 1.0,
        "bylaw_section": "50.20",
    },
    "EL": {
        "label": "Employment Light",
        "permitted_uses": [
            "office", "light manufacturing",
            "research and development", "retail store",
        ],
        "max_height_m": 12.0,
        "max_storeys": 3,
        "min_front_setback_m": 6.0,
        "min_rear_setback_m": 7.5,
        "min_side_setback_m": {"interior": 3.0, "exterior": 6.0},
        "max_lot_coverage_pct": 40.0,
        "min_landscaping_pct": 20.0,
        "max_fsi": 0.75,
        "bylaw_section": "55.20",
    },
    "I": {
        "label": "Institutional",
        "permitted_uses": [
            "place of worship", "school", "community centre",
            "hospital", "day nursery", "library",
        ],
        "max_height_m": 14.0,
        "max_storeys": 4,
        "min_front_setback_m": 6.0,
        "min_rear_setback_m": 7.5,
        "min_side_setback_m": {"interior": 3.0, "exterior": 6.0},
        "max_lot_coverage_pct": 35.0,
        "min_landscaping_pct": 30.0,
        "max_fsi": 1.0,
        "bylaw_section": "60.20",
    },
    "OS": {
        "label": "Open Space",
        "permitted_uses": [
            "park", "playground", "conservation area",
            "public recreation", "community garden",
        ],
        "max_height_m": 9.0,
        "max_storeys": 2,
        "min_front_setback_m": 3.0,
        "min_rear_setback_m": 3.0,
        "min_side_setback_m": {"interior": 3.0, "exterior": 3.0},
        "max_lot_coverage_pct": 10.0,
        "min_landscaping_pct": 60.0,
        "max_fsi": 0.15,
        "bylaw_section": "70.20",
    },
    "OR": {
        "label": "Open Space Recreation",
        "permitted_uses": [
            "recreation use", "amusement park",
            "golf course", "outdoor sports facility",
        ],
        "max_height_m": 14.0,
        "max_storeys": 3,
        "min_front_setback_m": 6.0,
        "min_rear_setback_m": 7.5,
        "min_side_setback_m": {"interior": 3.0, "exterior": 6.0},
        "max_lot_coverage_pct": 15.0,
        "min_landscaping_pct": 50.0,
        "max_fsi": 0.25,
        "bylaw_section": "75.20",
    },
    "U": {
        "label": "Utility",
        "permitted_uses": [
            "public utility", "transportation use",
            "railway", "transit facility",
        ],
        "max_height_m": 12.0,
        "max_storeys": 3,
        "min_front_setback_m": 6.0,
        "min_rear_setback_m": 7.5,
        "min_side_setback_m": {"interior": 3.0, "exterior": 6.0},
        "max_lot_coverage_pct": 50.0,
        "min_landscaping_pct": 10.0,
        "max_fsi": 0.5,
        "bylaw_section": "80.20",
    },
}

# Parking standards by Policy Area (By-law 569-2013 Chapter 200)
PARKING_STANDARDS: dict[str, dict] = {
    "PA1": {
        "label": "Policy Area 1 (Downtown Core)",
        "residential_per_unit": 0.0,
        "visitor_per_unit": 0.0,
        "commercial_per_100m2": 0.0,
        "bylaw_section": "200.5.10",
    },
    "PA2": {
        "label": "Policy Area 2 (Central Waterfront / Centres)",
        "residential_per_unit": 0.3,
        "visitor_per_unit": 0.05,
        "commercial_per_100m2": 0.5,
        "bylaw_section": "200.5.10",
    },
    "PA3": {
        "label": "Policy Area 3 (Rest of former City of Toronto)",
        "residential_per_unit": 0.5,
        "visitor_per_unit": 0.1,
        "commercial_per_100m2": 1.0,
        "bylaw_section": "200.5.10",
    },
    "PA4": {
        "label": "Policy Area 4 (Rest of Toronto)",
        "residential_per_unit": 0.7,
        "visitor_per_unit": 0.1,
        "commercial_per_100m2": 2.0,
        "bylaw_section": "200.5.10",
    },
}

# Bicycle parking (Chapter 230)
BICYCLE_PARKING: dict[str, float | str] = {
    "long_term_per_unit": 0.9,
    "short_term_per_unit": 0.1,
    "commercial_long_term_per_100m2": 0.2,
    "commercial_short_term_per_100m2": 0.3,
    "bylaw_section": "230.5.10",
}

# Amenity space requirements (By-law 569-2013 Chapter 230)
AMENITY_SPACE: dict[str, float | str] = {
    "indoor_per_unit_m2": 2.0,
    "outdoor_per_unit_m2": 2.0,
    "total_per_unit_m2": 4.0,
    "bylaw_section": "230.5.1.10",
}

# Angular plane standards (Tall Building Design Guidelines)
ANGULAR_PLANE: dict[str, float | str] = {
    "ratio": 1.0,  # 1:1 angular plane (45 degrees)
    "base_height_m": 80.0,  # above which angular plane applies
    "reference": "Toronto Tall Building Design Guidelines, Section 3.2.3",
}

# Known valid by-law section references (for citation verification)
VALID_BYLAW_SECTIONS: set[str] = set()
for _zone_data in ZONE_STANDARDS.values():
    VALID_BYLAW_SECTIONS.add(_zone_data["bylaw_section"])
for _parking_data in PARKING_STANDARDS.values():
    VALID_BYLAW_SECTIONS.add(_parking_data["bylaw_section"])
VALID_BYLAW_SECTIONS.add(BICYCLE_PARKING["bylaw_section"])
VALID_BYLAW_SECTIONS.add(AMENITY_SPACE["bylaw_section"])
# Add common section patterns
VALID_BYLAW_SECTIONS.update({
    "10.5", "10.10", "10.20", "10.40",
    "15.5", "15.10", "15.20",
    "20.5", "20.10", "20.20",
    "30.5", "30.10", "30.20",
    "35.5", "35.10", "35.20",
    "40.5", "40.10", "40.10.40.1", "40.10.40.10", "40.10.40.70", "40.10.40.80",
    "50.5", "50.10", "50.20",
    "55.5", "55.10", "55.20",
    "60.5", "60.10", "60.20",
    "70.5", "70.10", "70.20",
    "75.5", "75.10", "75.20",
    "80.5", "80.10", "80.20",
    "200.5", "200.5.1", "200.5.10",
    "220.5", "220.5.10",
    "230.5", "230.5.1", "230.5.1.10", "230.5.10",
})
