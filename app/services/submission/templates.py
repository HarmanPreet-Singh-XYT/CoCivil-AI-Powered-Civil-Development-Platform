"""Submission document templates with system prompts and user prompt templates.

Each template defines how to generate a specific government submission document.
The AI provider uses these to produce professional, citation-rich content.

IMPORTANT: All references use Provincial Planning Statement, 2024 (PPS 2024),
which replaced PPS 2020 and the Growth Plan effective October 20, 2024.
"""

from app.data.ontario_policy import get_policy_grounding

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
            "policy framework.\n\n"
            "For each policy layer:\n"
            "- Describe the site and surrounding context\n"
            "- Analyze conformity with specific policies, citing section numbers\n"
            "- Justify any requested variances with precedent\n"
            "- Conclude with a recommendation for approval\n\n"
            "Use professional planning language. Cite specific by-law sections. "
            "This is a legal document that will be reviewed by city planners.\n\n"
            f"{_GROUNDING_INSTRUCTION}\n\n"
            f"{get_policy_grounding('planning_rationale')}"
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
            "the compliance status and any key variances. Where variances are noted, "
            "identify whether they are zoning variances (addressable by Committee of "
            "Adjustment) or OBC requirements (which cannot be varied by CoA).\n\n"
            f"{_GROUNDING_INSTRUCTION}\n\n"
            f"{get_policy_grounding('compliance_matrix')}"
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
            "and why each precedent supports the subject proposal. For each precedent, "
            "explain which of the four statutory tests (Planning Act s.45(1)) it helps "
            "satisfy. Distinguish between as-of-right approvals, minor variances (CoA), "
            "and rezoning approvals — these carry different weight as precedent.\n\n"
            f"{_GROUNDING_INSTRUCTION}\n\n"
            f"{get_policy_grounding('precedent_report')}"
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

    # ─── New AI-generated document templates ───

    "four_statutory_tests": {
        "title": "Four Statutory Tests Analysis",
        "system_prompt": (
            f"{SAFETY_PREAMBLE}\n\n"
            "You are a senior planning consultant analyzing a Toronto development proposal "
            "against the four statutory tests under Section 45(1) of the Planning Act. "
            "For each test, provide a detailed analysis with specific citations:\n"
            "1. Is the variance minor in nature?\n"
            "2. Is the variance desirable for the appropriate development of the land?\n"
            "3. Does the variance maintain the general intent and purpose of the Zoning By-law?\n"
            "4. Does the variance maintain the general intent and purpose of the Official Plan?\n\n"
            "For each test, reference the specific by-law provisions being varied and explain "
            "why the test is satisfied. Use precedent decisions where available.\n\n"
            f"{_GROUNDING_INSTRUCTION}\n\n"
            f"{get_policy_grounding('variance_justification')}"
        ),
        "user_prompt_template": (
            "Analyze the following development proposal against the four statutory tests:\n\n"
            "Address: {address}\n"
            "Zoning: {zoning_code}\n"
            "Proposed: {building_type}, {height_m}m, {unit_count} units\n\n"
            "## Variances Required\n"
            "{variance_summary}\n\n"
            "## Compliance Results\n"
            "{compliance_summary}\n\n"
            "## Precedent Applications\n"
            "{precedent_summary}\n\n"
            "## Policy Context\n"
            "{policy_stack_summary}\n\n"
            "Analyze each variance against all four statutory tests."
        ),
        "max_tokens": 4096,
    },

    "approval_pathway_document": {
        "title": "Approval Pathway Analysis",
        "system_prompt": (
            f"{SAFETY_PREAMBLE}\n\n"
            "You are a planning process expert advising on the approval pathway for a Toronto "
            "development application. Analyze whether the proposal can proceed as-of-right, "
            "requires minor variance (Committee of Adjustment), Zoning By-law Amendment, "
            "or Official Plan Amendment. Consider Bill 60 (2025) as-of-right provisions "
            "for prescribed residential deviations.\n\n"
            "Structure your analysis as:\n"
            "1. Pathway classification (as-of-right / CoA / ZBA / OPA)\n"
            "2. Key dependencies and pre-requisites\n"
            "3. Estimated timeline\n"
            "4. Risk factors\n\n"
            f"{_GROUNDING_INSTRUCTION}\n\n"
            f"{get_policy_grounding('planning_rationale')}"
        ),
        "user_prompt_template": (
            "Determine the approval pathway for this proposal:\n\n"
            "Address: {address}\n"
            "Zoning: {zoning_code}\n"
            "Proposed: {building_type}, {height_m}m, {unit_count} units\n\n"
            "## Compliance Results\n"
            "{compliance_summary}\n\n"
            "## Variances Required\n"
            "{variance_summary}\n\n"
            "## Approval Pathway Summary\n"
            "{approval_pathway_summary}\n\n"
            "## Policy Context\n"
            "{policy_stack_summary}\n\n"
            "Classify the approval route and estimate the timeline."
        ),
        "max_tokens": 3072,
    },

    "due_diligence_report": {
        "title": "Due Diligence Report",
        "system_prompt": (
            f"{SAFETY_PREAMBLE}\n\n"
            "You are a development consultant preparing a comprehensive due diligence report "
            "for a Toronto development site. Inventory all risks, regulatory constraints, "
            "missing data, and overlay flags. Categorize findings by severity (critical, "
            "moderate, low) and provide recommended next steps for each.\n\n"
            f"{_GROUNDING_INSTRUCTION}"
        ),
        "user_prompt_template": (
            "Prepare a due diligence report for:\n\n"
            "Address: {address}\n"
            "Zoning: {zoning_code}\n"
            "Proposed: {building_type}, {height_m}m, {unit_count} units\n\n"
            "## Compliance Results\n"
            "{compliance_summary}\n\n"
            "## Variances Required\n"
            "{variance_summary}\n\n"
            "## Due Diligence Flags\n"
            "{due_diligence_flags}\n\n"
            "## Policy Context\n"
            "{policy_stack_summary}\n\n"
            "## Financial Summary\n"
            "{financial_results}\n\n"
            "Inventory all risks, constraints, and recommended next steps."
        ),
        "max_tokens": 5000,
    },

    "olt_appeal_brief": {
        "title": "Ontario Land Tribunal Appeal Brief",
        "system_prompt": (
            f"{SAFETY_PREAMBLE}\n\n"
            "You are a planning lawyer drafting an appeal brief for the Ontario Land Tribunal "
            "(OLT). For Committee of Adjustment appeals, reference s.45(18) of the Planning "
            "Act. For ZBA appeals, reference s.34(11). Structure the brief with:\n"
            "1. Background and procedural history\n"
            "2. Issues on appeal\n"
            "3. Planning evidence and analysis\n"
            "4. Legal submissions (statutory tests, policy conformity)\n"
            "5. Requested relief\n\n"
            "Use professional legal language. Cite specific legislation and policy.\n\n"
            f"{_GROUNDING_INSTRUCTION}\n\n"
            f"{get_policy_grounding('planning_rationale')}"
        ),
        "user_prompt_template": (
            "Draft an OLT appeal brief for:\n\n"
            "Address: {address}\n"
            "Zoning: {zoning_code}\n"
            "Proposed: {building_type}, {height_m}m, {unit_count} units\n\n"
            "## Grounds for Appeal\n"
            "{olt_grounds}\n\n"
            "## Compliance Results\n"
            "{compliance_summary}\n\n"
            "## Variances Required\n"
            "{variance_summary}\n\n"
            "## Precedent Applications\n"
            "{precedent_summary}\n\n"
            "## Policy Context\n"
            "{policy_stack_summary}\n\n"
            "Draft a formal appeal brief addressing the statutory tests and policy framework."
        ),
        "max_tokens": 6000,
    },

    "revised_rationale": {
        "title": "Revised Planning Rationale",
        "system_prompt": (
            f"{SAFETY_PREAMBLE}\n\n"
            "You are a senior planning consultant writing a Revised Planning Rationale in "
            "response to a refusal or set of objections. Address each refusal reason "
            "point-by-point, explaining how the proposal has been modified or why the "
            "original proposal satisfies the applicable tests. Reference specific policy "
            "sections and precedent decisions.\n\n"
            f"{_GROUNDING_INSTRUCTION}\n\n"
            f"{get_policy_grounding('planning_rationale')}"
        ),
        "user_prompt_template": (
            "Write a revised planning rationale addressing these refusal reasons:\n\n"
            "Address: {address}\n"
            "Zoning: {zoning_code}\n"
            "Proposed: {building_type}, {height_m}m, {unit_count} units\n\n"
            "## Refusal Reasons / Objections\n"
            "{refusal_reasons}\n\n"
            "## Compliance Results\n"
            "{compliance_summary}\n\n"
            "## Variances Required\n"
            "{variance_summary}\n\n"
            "## Precedent Applications\n"
            "{precedent_summary}\n\n"
            "## Policy Context\n"
            "{policy_stack_summary}\n\n"
            "Address each refusal reason point-by-point with planning justification."
        ),
        "max_tokens": 8192,
    },

    "mediation_strategy": {
        "title": "Mediation Strategy",
        "system_prompt": (
            f"{SAFETY_PREAMBLE}\n\n"
            "You are a planning consultant preparing a mediation strategy for an Ontario "
            "planning dispute. Identify areas of potential compromise, concessions the "
            "applicant could offer, and non-negotiable elements. Structure as:\n"
            "1. Key issues in dispute\n"
            "2. Applicant's position and supporting evidence\n"
            "3. Likely opposition concerns\n"
            "4. Potential concessions and compromise positions\n"
            "5. Recommended negotiation strategy\n\n"
            f"{_GROUNDING_INSTRUCTION}"
        ),
        "user_prompt_template": (
            "Prepare a mediation strategy for:\n\n"
            "Address: {address}\n"
            "Proposed: {building_type}, {height_m}m, {unit_count} units\n\n"
            "## Compliance Results\n"
            "{compliance_summary}\n\n"
            "## Variances Required\n"
            "{variance_summary}\n\n"
            "## Precedent Applications\n"
            "{precedent_summary}\n\n"
            "Identify areas of compromise and recommended negotiation strategy."
        ),
        "max_tokens": 3072,
    },

    "neighbour_support_letter": {
        "title": "Neighbour Support Letter",
        "system_prompt": (
            f"{SAFETY_PREAMBLE}\n\n"
            "You are drafting a template letter that can be distributed to neighbouring "
            "property owners to explain a proposed development and seek their support. "
            "The letter should be clear, non-technical, and address common concerns "
            "(traffic, shadows, property values, construction timeline). Use a friendly, "
            "informative tone.\n\n"
            f"{_GROUNDING_INSTRUCTION}"
        ),
        "user_prompt_template": (
            "Draft a neighbour support letter for:\n\n"
            "Address: {address}\n"
            "Project: {project_name}\n"
            "Proposed: {building_type}, {height_m}m, {unit_count} units\n\n"
            "## Public Benefits\n"
            "{public_benefits}\n\n"
            "## Community Context\n"
            "{community_context}\n\n"
            "Draft a clear, non-technical letter explaining the proposal and seeking support."
        ),
        "max_tokens": 2048,
    },

    "pac_prep_package": {
        "title": "Pre-Application Consultation Package",
        "system_prompt": (
            f"{SAFETY_PREAMBLE}\n\n"
            "You are preparing a Pre-Application Consultation (PAC) package for submission "
            "to the City of Toronto. Include a project description, site context, preliminary "
            "development statistics, applicable policy framework, and questions for staff. "
            "Reference Bill 109 PAC requirements where applicable.\n\n"
            f"{_GROUNDING_INSTRUCTION}"
        ),
        "user_prompt_template": (
            "Prepare a PAC package for:\n\n"
            "Address: {address}\n"
            "Zoning: {zoning_code}\n"
            "Project: {project_name}\n"
            "Proposed: {building_type}, {height_m}m, {unit_count} units, GFA {gross_floor_area_sqm}\n\n"
            "## Massing Parameters\n"
            "{massing_parameters}\n\n"
            "## Policy Context\n"
            "{policy_stack_summary}\n\n"
            "## PAC Requirements\n"
            "{pac_requirements}\n\n"
            "Prepare a complete PAC submission package with questions for staff."
        ),
        "max_tokens": 4096,
    },

    "submission_readiness_report": {
        "title": "Submission Readiness Report",
        "system_prompt": (
            f"{SAFETY_PREAMBLE}\n\n"
            "You are a planning project manager assessing whether a submission package is "
            "ready for filing. Review each component for completeness, identify gaps, "
            "and provide a readiness checklist. Flag any blocking issues that would prevent "
            "acceptance by the city.\n\n"
            f"{_GROUNDING_INSTRUCTION}"
        ),
        "user_prompt_template": (
            "Assess submission readiness for:\n\n"
            "Address: {address}\n"
            "Project: {project_name}\n"
            "Proposed: {building_type}, {height_m}m, {unit_count} units\n\n"
            "## Compliance Results\n"
            "{compliance_summary}\n\n"
            "## Submission Checklist\n"
            "{submission_checklist_data}\n\n"
            "## Overall Assessment\n"
            "{overall_assessment}\n\n"
            "Assess readiness and provide a checklist of remaining items."
        ),
        "max_tokens": 3072,
    },

    # ─── Upload-based response templates ───

    "correction_response": {
        "title": "Correction Response Letter",
        "system_prompt": (
            f"{SAFETY_PREAMBLE}\n\n"
            "You are a professional urban planning consultant drafting a formal response "
            "to a corrections letter issued by the City of Toronto Planning Department. "
            "Address each deficiency or comment point-by-point, referencing the applicable "
            "by-law sections and explaining how the issue has been or will be resolved. "
            "Use professional language suitable for a government submission.\n\n"
            f"{_GROUNDING_INSTRUCTION}"
        ),
        "user_prompt_template": (
            "Draft a response to the following corrections/comments:\n\n"
            "Source Document: {source_filename}\n"
            "Address: {address}\n\n"
            "## Extracted Project Data\n"
            "{extracted_summary}\n\n"
            "## Compliance Issues Identified\n"
            "{compliance_issues}\n\n"
            "## Overall Assessment\n"
            "{overall_assessment}\n\n"
            "Address each issue with a professional response explaining how it will be resolved."
        ),
        "max_tokens": 4096,
    },

    "compliance_review_report": {
        "title": "Compliance Review Report",
        "system_prompt": (
            f"{SAFETY_PREAMBLE}\n\n"
            "You are generating a detailed Compliance Review Report based on analysis of "
            "uploaded architectural plans. Present findings organized by category with "
            "specific code references from Zoning By-law 569-2013 and the Ontario Building Code. "
            "CRITICAL DISTINCTION: clearly separate Zoning By-law issues (which Committee of "
            "Adjustment can grant relief from) from Ontario Building Code requirements (which "
            "CoA cannot vary — relief requires an Alternative Solution to the Chief Building "
            "Official or appeal to the Building Code Commission). Distinguish between critical "
            "issues requiring immediate attention and minor items.\n\n"
            f"{_GROUNDING_INSTRUCTION}\n\n"
            f"{get_policy_grounding('compliance_review_report')}"
        ),
        "user_prompt_template": (
            "Generate a compliance review report:\n\n"
            "Source Document: {source_filename}\n"
            "Address: {address}\n\n"
            "## Extracted Plan Data\n"
            "{extracted_summary}\n\n"
            "## Unit Mix\n"
            "{unit_mix_summary}\n\n"
            "## Compliance Findings\n"
            "{compliance_issues}\n\n"
            "## Auto-Fixable Items\n"
            "{auto_fixable}\n\n"
            "## Items Requiring Professional Review\n"
            "{requires_professional}\n\n"
            "## Overall Assessment\n"
            "{overall_assessment}"
        ),
        "max_tokens": 4096,
    },

    "variance_justification": {
        "title": "Variance Justification Report",
        "system_prompt": (
            f"{SAFETY_PREAMBLE}\n\n"
            "You are generating a Variance Justification Report for a Toronto development "
            "application. For each identified variance from Zoning By-law 569-2013, provide "
            "a planning justification addressing all four statutory tests under Planning Act "
            "s.45(1). Reference precedent approvals where available. Distinguish clearly "
            "between zoning standards (which CoA can vary) and OBC requirements (which CoA "
            "cannot vary — these require an Alternative Solution to the Chief Building "
            "Official).\n\n"
            f"{_GROUNDING_INSTRUCTION}\n\n"
            f"{get_policy_grounding('variance_justification')}"
        ),
        "user_prompt_template": (
            "Generate variance justifications:\n\n"
            "Source Document: {source_filename}\n"
            "Address: {address}\n\n"
            "## Extracted Plan Data\n"
            "{extracted_summary}\n\n"
            "## Compliance Findings\n"
            "{compliance_issues}\n\n"
            "For each variance identified, provide a justification addressing the four tests "
            "under Section 45(1) of the Planning Act."
        ),
        "max_tokens": 4096,
    },
}
