"""Ontario infrastructure policy knowledge base.

Structured constants for AI grounding context — same pattern as ontario_policy.py.
These constants are embedded in AI document generation prompts so the model
cites real law rather than relying on training data.
"""

# ---------------------------------------------------------------------------
# Infrastructure Regulatory Hierarchy
# ---------------------------------------------------------------------------

ONTARIO_INFRASTRUCTURE_HIERARCHY = """
## Ontario Infrastructure Regulatory Hierarchy (Descending Precedence)

Every municipal infrastructure decision must conform to this ladder.

1. Ontario Water Resources Act (R.S.O. 1990, c. O.40)
   — Governs water supply, sewage disposal, and storm water management.
   — Prohibits discharge of pollutants into water bodies.
   — Environmental Compliance Approval (ECA) required for new municipal sewers and water mains.

2. Environmental Protection Act (R.S.O. 1990, c. E.19)
   — Regulates waste management, air quality, and contaminated sites.
   — MECP approval required for sewage works, stormwater management facilities.

3. Safe Drinking Water Act, 2002 (S.O. 2002, c. 32)
   — Drinking water quality standards (O.Reg 169/03).
   — Municipal drinking water system licensing and operator certification.
   — Requires source water protection plans.

4. Municipal Act, 2001 (S.O. 2001, c. 25)
   — Grants municipalities authority over roads, bridges, water, sewer, and drainage.
   — Development charges (DCA) fund growth-related infrastructure.
   — Asset management plans required (O.Reg 588/17).

5. Technical Standards and Safety Act (TSSA), 2000
   — Regulates gas pipelines, fuel storage, pressure vessels.
   — O.Reg 210/01: gas pipeline safety and integrity management.
   — TSSA authorization required before gas line construction or alteration.

6. Canadian Highway Bridge Design Code — CSA S6:19 (CAN/CSA-S6)
   — Governs design, evaluation, and rehabilitation of all highway bridges.
   — CL-625 design truck loading (§3.8.3).
   — Seismic design provisions (§4).
   — Fatigue and fracture requirements for steel (§10).

7. Ontario Provincial Standards (OPSS / OPSD)
   — OPSS: construction specifications (materials, installation, testing).
   — OPSD: design drawings (manholes, pipe bedding, catch basins).
   — OPSS 410: pipe installation; OPSD 701/801/802/804: sewer/manhole design.
   — Adopted by reference in most municipal specifications.

8. MTO Drainage Management Manual
   — Hydrologic and hydraulic design for storm sewers, culverts, and ditches.
   — Chapter 8: storm sewer design; Chapter 9: culvert design.
   — IDF curves and rational method for flow calculations.

9. Municipal Design Criteria / Standards
   — City of Toronto: Toronto Municipal Code Chapter 681 (Sewers).
   — Toronto Water Design Criteria for watermain and sewer construction.
   — Municipality-specific standards for road geometry, pipe depth, utility clearances.
"""

# ---------------------------------------------------------------------------
# Infrastructure Approval Process
# ---------------------------------------------------------------------------

INFRASTRUCTURE_APPROVAL_PROCESS = """
## Infrastructure Approval Process

### Environmental Compliance Approval (ECA) — Sewers & Water
Required for: new sanitary sewers, storm sewers, water mains, and pumping stations.
Authority: Ministry of the Environment, Conservation and Parks (MECP).
Process:
1. Submit design report and drawings to MECP.
2. Public notification may be required for large works.
3. MECP review (typical timeline: 3-6 months for routine, 12+ months for complex).
4. ECA issued with conditions (monitoring, reporting, commissioning).
Exemption: Municipal Class EA may be self-filing for routine replacements.

### Municipal Class Environmental Assessment (Class EA) — Bridges & Major Infrastructure
Required for: new bridges, bridge replacements, major road improvements, large storm facilities.
Authority: Environmental Assessment Act (R.S.O. 1990, c. E.18).
Schedules:
- Schedule A: pre-approved (routine maintenance, minor repairs).
- Schedule A+: pre-approved with public notification.
- Schedule B: screening process (bridge rehabilitation, minor widening).
- Schedule C: full Class EA (new bridges, major realignment, capacity expansion).
Timeline: Schedule B = 6-12 months; Schedule C = 12-24 months.

### TSSA Authorization — Gas Pipelines
Required for: new gas line construction, alteration, or abandonment.
Authority: Technical Standards and Safety Authority (O.Reg 210/01).
Process:
1. Design by licensed Professional Engineer.
2. TSSA permit application with drawings, stress analysis, and material specs.
3. TSSA inspection during and after construction.
4. Pressure testing and commissioning before service.

### TRCA / Conservation Authority Permits
Required for: any work within a regulated area (floodplain, erosion hazard, wetland buffer).
Authority: Conservation Authorities Act (R.S.O. 1990, c. C.27), O.Reg 166/06.
Process:
1. Pre-consultation with Conservation Authority.
2. Submit permit application with environmental impact study.
3. Review timeline: 30-90 days (routine), 6+ months (complex with EIS).
"""


def get_infrastructure_policy_grounding(doc_type: str) -> str:
    """Return appropriate infrastructure policy grounding for a document type."""

    if doc_type == "infrastructure_assessment":
        return "\n".join([
            "## INFRASTRUCTURE POLICY GROUNDING CONTEXT — USE ONLY THESE REFERENCES",
            ONTARIO_INFRASTRUCTURE_HIERARCHY,
            INFRASTRUCTURE_APPROVAL_PROCESS,
        ])

    elif doc_type == "infrastructure_compliance":
        return "\n".join([
            "## INFRASTRUCTURE POLICY GROUNDING CONTEXT — USE ONLY THESE REFERENCES",
            ONTARIO_INFRASTRUCTURE_HIERARCHY,
        ])

    else:
        return "\n".join([
            "## INFRASTRUCTURE POLICY GROUNDING CONTEXT",
            ONTARIO_INFRASTRUCTURE_HIERARCHY,
        ])
