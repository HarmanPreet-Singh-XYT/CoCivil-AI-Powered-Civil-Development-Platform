"""Submission document templates with system prompts and user prompt templates.

Each template defines how to generate a specific government submission document.
The AI provider uses these to produce professional, citation-rich content.

IMPORTANT: All references use Provincial Planning Statement, 2024 (PPS 2024),
which replaced PPS 2020 and the Growth Plan effective October 20, 2024.
"""

SAFETY_PREAMBLE = (
    "DRAFT — FOR PROFESSIONAL REVIEW ONLY. This document was generated with "
    "computational assistance and must be reviewed by a qualified Ontario Land "
    "Use Planner (RPP) before submission to any municipal authority. Do not "
    "rely on this document as legal or planning advice without independent "
    "professional verification."
)

_GROUNDING_INSTRUCTION = (
    "IMPORTANT: Only reference by-law sections and policy numbers provided in "
    "the context below. Do not invent or assume any legal references. If specific "
    "data is not provided, state that it requires manual verification rather than "
    "fabricating values."
)

DOCUMENT_TEMPLATES = {
    "cover_letter": {
        "system_prompt": (
            f"{SAFETY_PREAMBLE}\n\n"
            "You are a professional urban planning consultant in Toronto, Ontario. "
            "Write a formal cover letter to the City of Toronto Planning Department "
            "introducing a development application. Be concise, professional, and reference "
            "the specific municipal address, application type, and key proposal metrics. "
            "Use standard Canadian business letter format.\n\n"
            f"{_GROUNDING_INSTRUCTION}"
        ),
        "user_prompt_template": (
            "Write a cover letter for a development application with these details:\n\n"
            "Address: {address}\n"
            "Project Name: {project_name}\n"
            "Development Type: {development_type}\n"
            "Building Type: {building_type}\n"
            "Proposed Height: {height_m}m ({storeys} storeys)\n"
            "Total Units: {unit_count}\n"
            "GFA: {gross_floor_area_sqm}\n"
            "Applicant Organization: {organization_name}\n\n"
            "Key points to cover:\n"
            "- Introduction of the applicant and property\n"
            "- Brief description of the proposed development\n"
            "- Statement that the proposal conforms to applicable policies\n"
            "- List of enclosed submission documents\n"
            "- Contact information for follow-up"
        ),
        "max_tokens": 2048,
    },

    "planning_rationale": {
        "system_prompt": (
            f"{SAFETY_PREAMBLE}\n\n"
            "You are a senior planning consultant writing a Planning Rationale for submission "
            "to the City of Toronto. This document must analyze conformity with the applicable "
            "policy framework in the following hierarchy:\n\n"
            "1. Provincial Planning Statement, 2024 (PPS 2024) — replaced PPS 2020 and the "
            "Growth Plan for the Greater Golden Horseshoe, effective October 20, 2024\n"
            "2. City of Toronto Official Plan (consolidated 2022)\n"
            "3. Secondary Plans / Site and Area Specific Policies\n"
            "4. Zoning By-law 569-2013 (as amended)\n"
            "5. Design Guidelines (Tall Building, Mid-Rise, Growing Up, Pet-Friendly)\n\n"
            "For each policy layer:\n"
            "- Describe the site and surrounding context\n"
            "- Analyze conformity with specific policies, citing section numbers\n"
            "- Justify any requested variances with precedent\n"
            "- Conclude with a recommendation for approval\n\n"
            "Use professional planning language. Cite specific by-law sections. "
            "This is a legal document that will be reviewed by city planners.\n\n"
            f"{_GROUNDING_INSTRUCTION}"
        ),
        "user_prompt_template": (
            "Write a Planning Rationale for this development proposal:\n\n"
            "## Site Information\n"
            "Address: {address}\n"
            "Current Zoning: {zoning_code}\n"
            "Lot Area: {lot_area_sqm}\n"
            "Lot Frontage: {lot_frontage_m}\n"
            "Current Use: {current_use}\n\n"
            "## Proposed Development\n"
            "Project: {project_name}\n"
            "Type: {development_type} — {building_type}\n"
            "Height: {height_m}m ({storeys} storeys)\n"
            "GFA: {gross_floor_area_sqm}\n"
            "Units: {unit_count}\n"
            "Ground Floor: {ground_floor_use}\n"
            "Parking: {parking_type}\n\n"
            "## Policy Context\n"
            "{policy_stack_summary}\n\n"
            "## Compliance Results\n"
            "{compliance_summary}\n\n"
            "## Precedent Applications\n"
            "{precedent_summary}\n\n"
            "## Variances Requested\n"
            "{variance_summary}"
        ),
        "max_tokens": 8192,
    },

    "compliance_matrix": {
        "system_prompt": (
            f"{SAFETY_PREAMBLE}\n\n"
            "You are writing a brief introductory narrative for a Policy Compliance Matrix. "
            "The actual compliance matrix table is provided below and was generated "
            "deterministically from by-law standards — do NOT modify, re-generate, or "
            "reformat the table. Write only a 2-3 paragraph introduction summarizing "
            "the compliance status and any key variances.\n\n"
            f"{_GROUNDING_INSTRUCTION}"
        ),
        "user_prompt_template": (
            "Write an introductory narrative for this compliance matrix:\n\n"
            "Address: {address}\n"
            "Zoning: {zoning_code}\n\n"
            "## Proposed Metrics\n"
            "Height: {height_m}m ({storeys} storeys)\n"
            "GFA: {gross_floor_area_sqm}\n"
            "Lot Coverage: {lot_coverage_pct}\n"
            "FSI/FAR: {fsi}\n"
            "Units: {unit_count}\n\n"
            "## Deterministic Compliance Matrix\n"
            "The following table was computed from By-law 569-2013 standards and must "
            "not be modified:\n\n"
            "{compliance_summary}\n\n"
            "## Variances Required\n"
            "{variance_summary}\n\n"
            "Write a brief professional narrative introducing this compliance matrix. "
            "Do NOT reproduce or alter the table above."
        ),
        "max_tokens": 2048,
    },

    "site_plan_data": {
        "system_prompt": (
            f"{SAFETY_PREAMBLE}\n\n"
            "You are generating a Site Plan Data Summary for a development application. "
            "Present the parcel geometry, setback dimensions, building footprint, "
            "access points, servicing, and key site dimensions in a clear, structured format. "
            "Use metric units (metres, square metres). Include a data table and narrative description.\n\n"
            f"{_GROUNDING_INSTRUCTION}"
        ),
        "user_prompt_template": (
            "Generate a site plan data summary:\n\n"
            "Address: {address}\n"
            "Lot Area: {lot_area_sqm}\n"
            "Lot Frontage: {lot_frontage_m}\n"
            "Lot Depth: {lot_depth_m}\n"
            "Current Use: {current_use}\n\n"
            "## Setbacks & Building Envelope\n"
            "{setback_data}\n\n"
            "## Massing Summary\n"
            "{massing_summary}\n\n"
            "Present as structured data tables with metric measurements."
        ),
        "max_tokens": 3072,
    },

    "massing_summary": {
        "system_prompt": (
            f"{SAFETY_PREAMBLE}\n\n"
            "You are generating a Built Form / Massing Summary for a development application. "
            "Describe the building envelope, height strategy, stepback regime, podium/tower "
            "relationship (if applicable), and key volumetric metrics. "
            "Reference Toronto's Tall Building Design Guidelines where relevant.\n\n"
            f"{_GROUNDING_INSTRUCTION}"
        ),
        "user_prompt_template": (
            "Generate a massing summary:\n\n"
            "Project: {project_name}\n"
            "Building Type: {building_type}\n"
            "Height: {height_m}m ({storeys} storeys)\n"
            "GFA: {gross_floor_area_sqm}\n\n"
            "## Massing Parameters\n"
            "{massing_parameters}\n\n"
            "## Policy Constraints Applied\n"
            "{policy_constraints}\n\n"
            "Describe the built form strategy, floor plate sizes, "
            "podium height, tower separation (if applicable), and angular plane compliance."
        ),
        "max_tokens": 3072,
    },

    "unit_mix_summary": {
        "system_prompt": (
            f"{SAFETY_PREAMBLE}\n\n"
            "You are generating a Unit Mix Summary for a Toronto development application. "
            "Present the unit breakdown by type (studio, 1-bed, 2-bed, 3-bed), count, "
            "area ranges, and percentage. Include accessible unit counts. "
            "Reference Toronto's Growing Up Guidelines for family-sized unit requirements.\n\n"
            f"{_GROUNDING_INSTRUCTION}"
        ),
        "user_prompt_template": (
            "Generate a unit mix summary:\n\n"
            "Total Units: {unit_count}\n"
            "Building Type: {building_type}\n"
            "GFA: {gross_floor_area_sqm}\n\n"
            "## Unit Mix\n"
            "{unit_mix_data}\n\n"
            "## Layout Optimization Results\n"
            "{layout_results}\n\n"
            "Present as a Markdown table and include family-sized unit compliance analysis."
        ),
        "max_tokens": 3072,
        "structured_output": {
            "type": "object",
            "properties": {
                "units": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "count": {"type": "integer"},
                            "percentage": {"type": "number"},
                            "avg_area_sqm": {"type": "number"},
                            "accessible_count": {"type": "integer"},
                        },
                    },
                },
                "total_units": {"type": "integer"},
                "family_sized_pct": {"type": "number"},
            },
        },
    },

    "financial_feasibility": {
        "system_prompt": (
            f"{SAFETY_PREAMBLE}\n\n"
            "You are generating a Financial Feasibility Summary for a development application. "
            "Present high-level pro forma metrics: revenue projections, construction costs, "
            "land value assumptions, NOI, cap rate, and return estimates. "
            "This is a summary — not a full pro forma — intended to demonstrate project viability. "
            "Use Toronto market assumptions. Present in a professional format suitable for "
            "a planning submission or investor review.\n\n"
            f"{_GROUNDING_INSTRUCTION}"
        ),
        "user_prompt_template": (
            "Generate a financial feasibility summary:\n\n"
            "Project: {project_name}\n"
            "Units: {unit_count}\n"
            "GFA: {gross_floor_area_sqm}\n"
            "Building Type: {building_type}\n\n"
            "## Financial Analysis Results\n"
            "{financial_results}\n\n"
            "## Assumptions Used\n"
            "{financial_assumptions}\n\n"
            "## Market Comparables\n"
            "{market_comparables}\n\n"
            "Present key metrics: total development cost, projected revenue, NOI, "
            "cap rate valuation, and estimated return on cost."
        ),
        "max_tokens": 4096,
    },

    "precedent_report": {
        "system_prompt": (
            f"{SAFETY_PREAMBLE}\n\n"
            "You are generating a Precedent Analysis Report for a development application. "
            "Present comparable approved developments nearby, including their address, "
            "application number, approval date, key metrics (height, units, FSI), "
            "and relevant excerpts from planning rationales or staff reports. "
            "This strengthens the application by showing that similar proposals have been approved.\n\n"
            f"{_GROUNDING_INSTRUCTION}"
        ),
        "user_prompt_template": (
            "Generate a precedent analysis report:\n\n"
            "Subject Site: {address}\n"
            "Proposed: {building_type}, {height_m}m, {unit_count} units\n"
            "Zoning: {zoning_code}\n\n"
            "## Precedent Search Results\n"
            "{precedent_results}\n\n"
            "## Similarity Analysis\n"
            "{similarity_analysis}\n\n"
            "For each precedent, present: address, app number, decision, key metrics, "
            "and why it supports this proposal."
        ),
        "max_tokens": 4096,
    },

    "public_benefit_statement": {
        "system_prompt": (
            f"{SAFETY_PREAMBLE}\n\n"
            "You are generating a Public Benefit Statement (Community Benefits) "
            "for a Toronto development application. Describe how the proposed development "
            "contributes to the community: affordable housing commitments, public realm "
            "improvements, community facilities, parkland contributions, public art, "
            "sustainability features, and transit infrastructure support. "
            "Reference Toronto's Official Plan policies on community benefits.\n\n"
            "Note: Section 37 of the Planning Act was replaced by the Community Benefits "
            "Charge framework under Bill 108/197. Reference the current CBC framework.\n\n"
            f"{_GROUNDING_INSTRUCTION}"
        ),
        "user_prompt_template": (
            "Generate a public benefit statement:\n\n"
            "Project: {project_name}\n"
            "Address: {address}\n"
            "Units: {unit_count}\n"
            "Type: {development_type}\n\n"
            "## Proposed Public Benefits\n"
            "{public_benefits}\n\n"
            "## Community Context\n"
            "{community_context}\n\n"
            "Describe community contributions and Community Benefits Charge considerations."
        ),
        "max_tokens": 3072,
    },

    "shadow_study": {
        "system_prompt": (
            f"{SAFETY_PREAMBLE}\n\n"
            "You are generating Shadow Study Data for a development application. "
            "Present the shadow impact analysis: which neighboring properties are affected, "
            "duration of shadow at key times (March 21, June 21, September 21), "
            "and comparison to the as-of-right shadow. Reference Toronto's shadow study "
            "requirements and Official Plan policies on sunlight access.\n\n"
            f"{_GROUNDING_INSTRUCTION}"
        ),
        "user_prompt_template": (
            "Generate shadow study data:\n\n"
            "Address: {address}\n"
            "Building Height: {height_m}m ({storeys} storeys)\n"
            "Building Footprint: {building_footprint}\n"
            "Orientation: {orientation}\n\n"
            "## Massing Geometry\n"
            "{massing_parameters}\n\n"
            "Present shadow analysis for March 21, June 21, September 21 "
            "at 9:18am, 12:18pm, 3:18pm, and 6:18pm (Toronto standard times). "
            "Note: actual shadow geometry requires 3D modeling — present methodology "
            "and estimated impact based on building dimensions."
        ),
        "max_tokens": 3072,
    },
}
