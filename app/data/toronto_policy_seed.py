"""Curated Toronto MVP policy corpus for seed-managed policy documents."""

from __future__ import annotations

from datetime import date

CITY_OF_TORONTO = "City of Toronto"
CURATED_POLICY_SCHEMA_VERSION = "toronto-curated-policy-seed-v1"
CURATED_POLICY_OBJECT_KEY_PREFIX = "repo://app/data/toronto_policy_seed.py#"

# Previous synthetic docs created by scripts/seed_policies.py. These can be
# safely replaced when they still use the legacy seed object_key pattern.
LEGACY_SYNTHETIC_SEED_TITLES = (
    "City of Toronto Zoning By-law 569-2013",
    "City of Toronto Official Plan (2023 Office Consolidation)",
    "Toronto Mid-Rise Building Performance Standards",
    "Toronto Tall Building Design Guidelines",
    "Growing Up — Planning for Children in New Vertical Communities",
    "Toronto Inclusionary Zoning Policy",
)


CURATED_TORONTO_POLICY_DOCUMENTS = (
    {
        "slug": "toronto-zoning-bylaw-569-2013-core-zones",
        "doc_type": "zoning_bylaw",
        "title": "City of Toronto Zoning By-law 569-2013",
        "source_url": "https://www.toronto.ca/city-government/planning-development/zoning-by-law-preliminary-zoning-reviews/zoning-by-law-569-2013-2/",
        "publisher": CITY_OF_TORONTO,
        "effective_date": date(2013, 5, 9),
        "source_metadata": {
            "source_kind": "official_city_webpage",
            "document_scope": "core zone permissions and exception review triggers",
            "curation_method": "manual_mvp_clause_selection",
        },
        "clauses": (
            {
                "slug": "r-zone-low-rise-permitted-uses",
                "section_ref": "Chapter 150.5 Residential Zone Uses",
                "raw_text": (
                    "Residential zone parcels are intended for low-rise housing forms such as detached, "
                    "semi-detached, duplex, triplex, and fourplex dwellings, subject to the lot-based "
                    "standards carried by the zone label and Chapter 10."
                ),
                "normalized_type": "permitted_use",
                "normalized_json": {
                    "type": "permitted_use",
                    "zone": "R",
                    "uses": [
                        "detached house",
                        "semi-detached house",
                        "duplex",
                        "triplex",
                        "fourplex",
                    ],
                },
                "confidence": 0.97,
                "needs_review": False,
                "applicability": (
                    {
                        "override_level": 1,
                        "zone_filter": ["R"],
                        "applicability_json": {
                            "scope": "base_zoning",
                            "policy_family": "permitted_use",
                            "source_kind": "curated_excerpt",
                        },
                    },
                ),
            },
            {
                "slug": "rm-zone-multiple-residential-standards",
                "section_ref": "Chapter 15.20 Residential Multiple Zone Standards",
                "raw_text": (
                    "Residential Multiple zones support a broader range of low- and medium-density forms, "
                    "including townhouse and apartment building permissions where the zone label and mapped "
                    "standards permit that intensity."
                ),
                "normalized_type": "zone_provision",
                "normalized_json": {
                    "type": "zone_provision",
                    "zone": "RM",
                    "uses": [
                        "townhouse",
                        "apartment building",
                    ],
                    "max_height_reference": "zone_label_or_chapter_standard",
                },
                "confidence": 0.95,
                "needs_review": False,
                "applicability": (
                    {
                        "override_level": 1,
                        "zone_filter": ["RM"],
                        "applicability_json": {
                            "scope": "base_zoning",
                            "policy_family": "zone_standards",
                        },
                    },
                ),
            },
            {
                "slug": "ra-zone-apartment-intensity",
                "section_ref": "Chapter 20.20 Residential Apartment Zone Standards",
                "raw_text": (
                    "Residential Apartment zones are intended for apartment-form housing, with the allowable "
                    "height and floor space index carried by the zone symbol, mapped density, and any applicable "
                    "schedule suffixes or exception references."
                ),
                "normalized_type": "zone_provision",
                "normalized_json": {
                    "type": "zone_provision",
                    "zone": "RA",
                    "use": "apartment building",
                    "height_control": "zone_label_or_height_schedule",
                    "density_control": "zone_label",
                },
                "confidence": 0.96,
                "needs_review": False,
                "applicability": (
                    {
                        "override_level": 1,
                        "zone_filter": ["RA"],
                        "applicability_json": {
                            "scope": "base_zoning",
                            "policy_family": "density_and_height",
                        },
                    },
                ),
            },
            {
                "slug": "cr-zone-mixed-use-density-split",
                "section_ref": "Chapter 40.10 Commercial Residential Zone General Provisions",
                "raw_text": (
                    "Commercial Residential zones encode total density and, where bracketed values are shown, "
                    "separate commercial and residential floor space index limits. The map label controls the "
                    "allowed mix and intensity."
                ),
                "normalized_type": "zone_provision",
                "normalized_json": {
                    "type": "zone_provision",
                    "zone": "CR",
                    "controls": [
                        "total_fsi",
                        "commercial_fsi",
                        "residential_fsi",
                    ],
                },
                "confidence": 0.96,
                "needs_review": False,
                "applicability": (
                    {
                        "override_level": 1,
                        "zone_filter": ["CR"],
                        "applicability_json": {
                            "scope": "base_zoning",
                            "policy_family": "mixed_use_density",
                        },
                    },
                ),
            },
            {
                "slug": "chapter-900-site-specific-exceptions",
                "section_ref": "Chapter 900 Site Specific Exceptions",
                "raw_text": (
                    "Numbered exceptions and site-specific schedule references can override the base zone rules "
                    "for a parcel. When an exception number or site-specific height suffix is present, the parcel "
                    "requires a manual Chapter 900 review before the zoning conclusion is treated as final."
                ),
                "normalized_type": "review_trigger",
                "normalized_json": {
                    "type": "manual_review",
                    "trigger": "site_specific_exception_or_schedule_suffix",
                    "source": "chapter_900",
                },
                "confidence": 0.91,
                "needs_review": True,
                "applicability": (
                    {
                        "override_level": 2,
                        "zone_filter": ["R", "RM", "RA", "CR", "CL", "CG", "E", "EL", "I"],
                        "applicability_json": {
                            "scope": "exception_review",
                            "manual_review_required": True,
                            "reason": "site_specific_exception_lookup",
                        },
                    },
                ),
            },
        ),
    },
    {
        "slug": "toronto-official-plan-built-form-and-land-use",
        "doc_type": "official_plan",
        "title": "City of Toronto Official Plan",
        "source_url": "https://www.toronto.ca/city-government/planning-development/official-plan-guidelines/official-plan/",
        "publisher": CITY_OF_TORONTO,
        "effective_date": date(2023, 7, 1),
        "source_metadata": {
            "source_kind": "official_city_webpage",
            "document_scope": "built form and core land use designation policies",
            "curation_method": "manual_mvp_clause_selection",
        },
        "clauses": (
            {
                "slug": "built-form-context-and-transition",
                "section_ref": "Section 3.1.2 Built Form",
                "raw_text": (
                    "New development should fit within its existing and planned context, organize massing, "
                    "height, scale, and setbacks to frame streets well, and provide transition toward lower-scale "
                    "areas where intensities change."
                ),
                "normalized_type": "built_form",
                "normalized_json": {
                    "type": "built_form",
                    "checks": ["context_fit", "street_relationship", "transition"],
                },
                "confidence": 0.88,
                "needs_review": True,
                "applicability": (
                    {
                        "override_level": 3,
                        "zone_filter": ["R", "RM", "RA", "CR", "CL", "CG"],
                        "applicability_json": {
                            "scope": "citywide_built_form",
                            "manual_review_required": True,
                        },
                    },
                ),
            },
            {
                "slug": "neighbourhoods-prevailing-character",
                "section_ref": "Section 4.1 Neighbourhoods",
                "raw_text": (
                    "Development in Neighbourhoods should respect and reinforce the existing physical character "
                    "of the area, including prevailing patterns of building type, lot size, setbacks, scale, and "
                    "landscape openness."
                ),
                "normalized_type": "land_use_designation",
                "normalized_json": {
                    "type": "land_use_designation",
                    "designation": "Neighbourhoods",
                    "checks": ["prevailing_building_type", "setbacks", "lot_pattern"],
                },
                "confidence": 0.93,
                "needs_review": True,
                "applicability": (
                    {
                        "override_level": 3,
                        "zone_filter": ["R", "RM"],
                        "applicability_json": {
                            "scope": "designation_policy",
                            "designation": "Neighbourhoods",
                            "manual_review_required": True,
                        },
                    },
                ),
            },
            {
                "slug": "apartment-neighbourhoods-compatible-infill",
                "section_ref": "Section 4.2 Apartment Neighbourhoods",
                "raw_text": (
                    "Apartment Neighbourhoods are stable apartment areas where compatible infill, replacement, "
                    "or redevelopment can proceed when it maintains livability, access, open space, and a fit "
                    "with the planned apartment context."
                ),
                "normalized_type": "land_use_designation",
                "normalized_json": {
                    "type": "land_use_designation",
                    "designation": "Apartment Neighbourhoods",
                    "checks": ["compatibility", "livability", "open_space"],
                },
                "confidence": 0.91,
                "needs_review": True,
                "applicability": (
                    {
                        "override_level": 3,
                        "zone_filter": ["RA"],
                        "applicability_json": {
                            "scope": "designation_policy",
                            "designation": "Apartment Neighbourhoods",
                            "manual_review_required": True,
                        },
                    },
                ),
            },
            {
                "slug": "mixed-use-areas-broad-range-of-uses",
                "section_ref": "Section 4.5 Mixed Use Areas",
                "raw_text": (
                    "Mixed Use Areas are intended to absorb a broad range of residential, commercial, "
                    "institutional, and service uses, usually in mixed-use or single-use buildings that also "
                    "support animation, access, and compatibility with the surrounding area."
                ),
                "normalized_type": "land_use_designation",
                "normalized_json": {
                    "type": "land_use_designation",
                    "designation": "Mixed Use Areas",
                    "uses": ["residential", "commercial", "institutional", "service"],
                },
                "confidence": 0.9,
                "needs_review": True,
                "applicability": (
                    {
                        "override_level": 3,
                        "zone_filter": ["CR", "CL", "CG"],
                        "applicability_json": {
                            "scope": "designation_policy",
                            "designation": "Mixed Use Areas",
                            "manual_review_required": True,
                        },
                    },
                ),
            },
        ),
    },
    {
        "slug": "toronto-mid-rise-building-performance-standards",
        "doc_type": "design_guideline",
        "title": "Toronto Mid-Rise Building Performance Standards",
        "source_url": "https://www.toronto.ca/city-government/planning-development/official-plan-guidelines/design-guidelines/mid-rise-buildings/",
        "publisher": CITY_OF_TORONTO,
        "effective_date": date(2010, 7, 8),
        "source_metadata": {
            "source_kind": "official_city_webpage",
            "document_scope": "avenue and main-street mid-rise performance guidance",
            "curation_method": "manual_mvp_clause_selection",
        },
        "clauses": (
            {
                "slug": "mid-rise-height-to-right-of-way",
                "section_ref": "Performance Standard 1 Height and Street Proportion",
                "raw_text": (
                    "On a typical mid-rise corridor, the building height should generally fit within a 1-to-1 "
                    "relationship to the adjacent public right-of-way width, with upper-level stepbacks where "
                    "needed to maintain an appropriate street wall."
                ),
                "normalized_type": "design_guideline",
                "normalized_json": {
                    "type": "mid_rise_height",
                    "max_height_ratio_to_row": 1.0,
                    "stepback_consideration": True,
                },
                "confidence": 0.85,
                "needs_review": True,
                "applicability": (
                    {
                        "override_level": 5,
                        "zone_filter": ["CR", "CL", "CG", "RM", "RA"],
                        "use_filter": ["apartment building", "dwelling units above the first storey"],
                        "applicability_json": {
                            "scope": "mid_rise_corridor_guideline",
                            "context_required": "avenue_or_main_street",
                            "manual_review_required": True,
                        },
                    },
                ),
            },
            {
                "slug": "mid-rise-rear-transition-angular-plane",
                "section_ref": "Performance Standard 6 Rear Transition",
                "raw_text": (
                    "Where a mid-rise site abuts lower-scale residential fabric, rear massing should provide a "
                    "45-degree transition plane and protect privacy, sky view, and sunlight for the adjacent "
                    "neighbourhood condition."
                ),
                "normalized_type": "design_guideline",
                "normalized_json": {
                    "type": "rear_transition",
                    "angular_plane_degrees": 45,
                    "sensitive_edge": "rear_lot_line",
                },
                "confidence": 0.84,
                "needs_review": True,
                "applicability": (
                    {
                        "override_level": 5,
                        "zone_filter": ["CR", "CL", "CG", "RM", "RA"],
                        "use_filter": ["apartment building", "dwelling units above the first storey"],
                        "applicability_json": {
                            "scope": "mid_rise_corridor_guideline",
                            "context_required": "abuts_lower_scale_area",
                            "manual_review_required": True,
                        },
                    },
                ),
            },
        ),
    },
    {
        "slug": "growing-up-planning-for-children",
        "doc_type": "design_guideline",
        "title": "Growing Up: Planning for Children in New Vertical Communities",
        "source_url": "https://www.toronto.ca/city-government/planning-development/planning-studies-initiatives/growing-up-planning-for-children-in-new-vertical-communities/",
        "publisher": CITY_OF_TORONTO,
        "effective_date": date(2020, 7, 28),
        "source_metadata": {
            "source_kind": "official_city_webpage",
            "document_scope": "family-sized unit guidance for multi-unit housing",
            "curation_method": "manual_mvp_clause_selection",
        },
        "clauses": (
            {
                "slug": "growing-up-family-sized-unit-mix",
                "section_ref": "Guideline 1 Family-Sized Unit Mix",
                "raw_text": (
                    "New multi-unit housing should provide a meaningful share of larger family-oriented units, "
                    "including a minimum target for two-bedroom and three-bedroom apartments in vertical communities."
                ),
                "normalized_type": "housing",
                "normalized_json": {
                    "type": "unit_mix",
                    "min_two_bedroom_pct": 25,
                    "min_three_bedroom_pct": 10,
                },
                "confidence": 0.87,
                "needs_review": True,
                "applicability": (
                    {
                        "override_level": 5,
                        "zone_filter": ["RA", "CR", "CL", "CG"],
                        "use_filter": ["apartment building", "dwelling units above the first storey"],
                        "applicability_json": {
                            "scope": "family_housing_guideline",
                            "manual_review_required": True,
                        },
                    },
                ),
            },
            {
                "slug": "growing-up-minimum-larger-unit-size",
                "section_ref": "Guideline 2 Larger Unit Sizes",
                "raw_text": (
                    "Larger family-oriented apartments should be sized to remain functional for long-term living, "
                    "with minimum size benchmarks for typical two-bedroom and three-bedroom layouts."
                ),
                "normalized_type": "design_guideline",
                "normalized_json": {
                    "type": "unit_size",
                    "min_two_bedroom_m2": 87,
                    "min_three_bedroom_m2": 100,
                },
                "confidence": 0.83,
                "needs_review": True,
                "applicability": (
                    {
                        "override_level": 5,
                        "zone_filter": ["RA", "CR", "CL", "CG"],
                        "use_filter": ["apartment building", "dwelling units above the first storey"],
                        "applicability_json": {
                            "scope": "family_housing_guideline",
                            "manual_review_required": True,
                        },
                    },
                ),
            },
        ),
    },
    {
        "slug": "toronto-inclusionary-zoning-policy",
        "doc_type": "amendment",
        "title": "Toronto Inclusionary Zoning Policy",
        "source_url": "https://www.toronto.ca/city-government/planning-development/planning-studies-initiatives/inclusionary-zoning-policy/",
        "publisher": CITY_OF_TORONTO,
        "effective_date": date(2022, 9, 18),
        "source_metadata": {
            "source_kind": "official_city_webpage",
            "document_scope": "protected major transit station area affordable housing requirements",
            "curation_method": "manual_mvp_clause_selection",
        },
        "clauses": (
            {
                "slug": "iz-pmtsa-affordable-set-aside-trigger",
                "section_ref": "IZ Requirement Set-Aside Trigger",
                "raw_text": (
                    "Within the city’s protected major transit station areas, larger residential projects are "
                    "expected to dedicate a regulated share of residential gross floor area as affordable housing, "
                    "with the exact rate depending on location and implementation timing."
                ),
                "normalized_type": "inclusionary_zoning",
                "normalized_json": {
                    "type": "affordable_set_aside",
                    "applies_in": "PMTSA",
                    "min_units_trigger": 100,
                },
                "confidence": 0.89,
                "needs_review": True,
                "applicability": (
                    {
                        "override_level": 4,
                        "zone_filter": ["RA", "CR", "CL", "CG"],
                        "use_filter": ["apartment building", "dwelling units above the first storey"],
                        "applicability_json": {
                            "scope": "inclusionary_zoning",
                            "context_required": "pmtsa_check",
                            "manual_review_required": True,
                        },
                    },
                ),
            },
            {
                "slug": "iz-affordability-term",
                "section_ref": "IZ Affordability Term",
                "raw_text": (
                    "Affordable units secured through Toronto’s inclusionary zoning framework must remain "
                    "affordable for a long duration after first occupancy, reflecting the city’s long-term "
                    "housing retention objective."
                ),
                "normalized_type": "inclusionary_zoning",
                "normalized_json": {
                    "type": "affordability_period",
                    "min_years": 99,
                },
                "confidence": 0.9,
                "needs_review": True,
                "applicability": (
                    {
                        "override_level": 4,
                        "zone_filter": ["RA", "CR", "CL", "CG"],
                        "use_filter": ["apartment building", "dwelling units above the first storey"],
                        "applicability_json": {
                            "scope": "inclusionary_zoning",
                            "context_required": "pmtsa_check",
                            "manual_review_required": True,
                        },
                    },
                ),
            },
        ),
    },
)
