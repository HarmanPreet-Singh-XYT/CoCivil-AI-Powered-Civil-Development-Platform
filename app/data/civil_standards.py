"""Hardcoded civil engineering standards for infrastructure compliance.

All data is deterministic reference data — no AI involved.
Sources: OPSD, OPSS, MTO Drainage Manual, AWWA, CSA S6:19, Manning's equation.
"""

# ---------------------------------------------------------------------------
# Pipe material properties
# ---------------------------------------------------------------------------

PIPE_MATERIALS: dict[str, dict] = {
    "PVC": {
        "label": "Polyvinyl Chloride",
        "standards_ref": "OPSS 410, AWWA C900/C905",
        "c_value": 150,
        "design_life_years": 75,
        "valid_uses": ["water_main", "sanitary_sewer", "storm_sewer"],
    },
    "HDPE": {
        "label": "High-Density Polyethylene",
        "standards_ref": "OPSS 410, AWWA C906",
        "c_value": 150,
        "design_life_years": 100,
        "valid_uses": ["water_main", "sanitary_sewer", "storm_sewer"],
    },
    "DI": {
        "label": "Ductile Iron",
        "standards_ref": "OPSS 410, AWWA C151/C150",
        "c_value": 130,
        "design_life_years": 100,
        "valid_uses": ["water_main"],
    },
    "CSP": {
        "label": "Corrugated Steel Pipe",
        "standards_ref": "OPSS 410, ASTM A760",
        "c_value": 60,
        "design_life_years": 50,
        "valid_uses": ["storm_sewer"],
    },
    "RCP": {
        "label": "Reinforced Concrete Pipe",
        "standards_ref": "OPSS 410, ASTM C76",
        "c_value": 120,
        "design_life_years": 75,
        "valid_uses": ["sanitary_sewer", "storm_sewer"],
    },
}

# ---------------------------------------------------------------------------
# Pipe type standards — minimum/maximum values per pipe use
# ---------------------------------------------------------------------------

PIPE_TYPE_STANDARDS: dict[str, dict] = {
    "water_main": {
        "label": "Water Main",
        "min_cover_m": 1.5,
        "max_cover_m": 3.0,
        "min_diameter_mm": 150,
        "max_diameter_mm": 1200,
        "min_velocity_m_s": 0.3,
        "max_velocity_m_s": 3.0,
        "min_slope_pct": 0.1,
        "separation_from_sanitary_m": 3.0,
        "separation_from_storm_m": 1.5,
        "standards_ref": "OPSD 806.010, AWWA M11, OPSS 441",
    },
    "sanitary_sewer": {
        "label": "Sanitary Sewer",
        "min_cover_m": 2.4,
        "max_cover_m": 6.0,
        "min_diameter_mm": 200,
        "max_diameter_mm": 1500,
        "min_velocity_m_s": 0.6,
        "max_velocity_m_s": 3.0,
        "min_slope_pct": 0.22,
        "separation_from_water_m": 3.0,
        "separation_from_storm_m": 0.9,
        "standards_ref": "OPSD 802.010, OPSS 410, MOE Design Guidelines",
    },
    "storm_sewer": {
        "label": "Storm Sewer",
        "min_cover_m": 1.2,
        "max_cover_m": 6.0,
        "min_diameter_mm": 250,
        "max_diameter_mm": 3000,
        "min_velocity_m_s": 0.6,
        "max_velocity_m_s": 4.5,
        "min_slope_pct": 0.10,
        "separation_from_water_m": 1.5,
        "separation_from_sanitary_m": 0.9,
        "standards_ref": "OPSD 804.010, OPSS 410, MTO Drainage Manual Ch.8",
    },
    "gas_line": {
        "label": "Gas Line",
        "min_cover_m": 0.6,
        "max_cover_m": 1.5,
        "min_diameter_mm": 25,
        "max_diameter_mm": 600,
        "min_velocity_m_s": None,
        "max_velocity_m_s": None,
        "min_slope_pct": None,
        "separation_from_water_m": 0.6,
        "separation_from_sanitary_m": 0.6,
        "standards_ref": "TSSA O.Reg 210/01, CSA Z662",
    },
}

# ---------------------------------------------------------------------------
# Sanitary sewer minimum slope by diameter (from Manning's equation)
# ---------------------------------------------------------------------------

SANITARY_MIN_SLOPE: dict[int, float] = {
    200: 0.40,
    250: 0.28,
    300: 0.22,
    375: 0.15,
    450: 0.12,
    525: 0.10,
    600: 0.08,
    675: 0.07,
    750: 0.06,
    900: 0.05,
    1050: 0.04,
    1200: 0.03,
    1350: 0.03,
    1500: 0.02,
}

# ---------------------------------------------------------------------------
# Manhole standards (OPSD 701.010)
# ---------------------------------------------------------------------------

MANHOLE_STANDARDS: dict[str, float | str] = {
    "max_spacing_m": 120.0,
    "min_diameter_mm": 1200.0,
    "min_benching_height_mm": 150.0,
    "max_drop_height_m": 3.0,
    "standards_ref": "OPSD 701.010, OPSD 704.010",
}

# ---------------------------------------------------------------------------
# Bridge type standards (CSA S6:19 / CAN/CSA-S6)
# ---------------------------------------------------------------------------

BRIDGE_TYPE_STANDARDS: dict[str, dict] = {
    "road_bridge": {
        "label": "Road Bridge",
        "min_deck_width_m": 8.5,
        "min_clearance_m": 5.0,
        "min_barrier_height_m": 1.07,
        "load_class": "CL-625",
        "standards_ref": "CSA S6:19 §3.8, MTO Structural Manual",
    },
    "pedestrian_bridge": {
        "label": "Pedestrian Bridge",
        "min_deck_width_m": 3.0,
        "min_clearance_m": 2.5,
        "min_barrier_height_m": 1.37,
        "load_class": "CL-625-ONT (pedestrian)",
        "standards_ref": "CSA S6:19 §3.8.9, AODA",
    },
    "culvert": {
        "label": "Culvert",
        "min_deck_width_m": None,
        "min_clearance_m": 0.6,
        "min_barrier_height_m": None,
        "load_class": "CL-625",
        "min_cover_m": 0.6,
        "standards_ref": "CSA S6:19 §7, MTO Drainage Manual Ch.9",
    },
}

# ---------------------------------------------------------------------------
# Bridge structure types — span ranges and L/D ratios
# ---------------------------------------------------------------------------

BRIDGE_STRUCTURE_TYPES: dict[str, dict] = {
    "steel_beam": {
        "label": "Steel Beam",
        "min_span_m": 6.0,
        "max_span_m": 60.0,
        "ld_ratio_min": 15,
        "ld_ratio_max": 25,
        "standards_ref": "CSA S6:19 §10",
    },
    "concrete_slab": {
        "label": "Concrete Slab",
        "min_span_m": 3.0,
        "max_span_m": 15.0,
        "ld_ratio_min": 20,
        "ld_ratio_max": 30,
        "standards_ref": "CSA S6:19 §8",
    },
    "concrete_girder": {
        "label": "Concrete Girder",
        "min_span_m": 10.0,
        "max_span_m": 45.0,
        "ld_ratio_min": 15,
        "ld_ratio_max": 22,
        "standards_ref": "CSA S6:19 §8",
    },
    "steel_truss": {
        "label": "Steel Truss",
        "min_span_m": 30.0,
        "max_span_m": 150.0,
        "ld_ratio_min": 8,
        "ld_ratio_max": 12,
        "standards_ref": "CSA S6:19 §10",
    },
    "arch": {
        "label": "Arch",
        "min_span_m": 10.0,
        "max_span_m": 250.0,
        "ld_ratio_min": 10,
        "ld_ratio_max": 20,
        "standards_ref": "CSA S6:19 §8, §10",
    },
    "box_culvert": {
        "label": "Box Culvert",
        "min_span_m": 1.0,
        "max_span_m": 12.0,
        "ld_ratio_min": 8,
        "ld_ratio_max": 15,
        "standards_ref": "CSA S6:19 §7, OPSD 803.010",
    },
}

# ---------------------------------------------------------------------------
# CL-625 Loading (CSA S6:19 §3.8.3)
# ---------------------------------------------------------------------------

CL_625_LOADING: dict[str, list | float | str] = {
    "axle_loads_kn": [50, 125, 125, 175, 150],
    "axle_spacings_m": [3.6, 1.2, 6.6, 6.6],
    "design_lane_load_kn_per_m": 9.0,
    "dynamic_load_allowance_pct": 25.0,
    "standards_ref": "CSA S6:19 §3.8.3",
}
