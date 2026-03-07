"""Ontario and Toronto planning policy knowledge base.

Structured constants derived from:
- Planning Act (R.S.O. 1990, c. P.13)
- Provincial Planning Statement, 2024 (PPS 2024)
- Toronto Official Plan (consolidated 2022)
- Toronto Zoning By-law 569-2013
- Ontario Building Code (O.Reg 332/12)
- O.Reg 462/24 (Additional Residential Units)
- Bills 23, 97, 109, 185, 60

These constants are embedded in AI document generation prompts as grounding
context, so the model cites real law rather than relying on training data.
"""

# ---------------------------------------------------------------------------
# Policy Hierarchy
# ---------------------------------------------------------------------------

ONTARIO_POLICY_HIERARCHY = """
## Ontario Planning Policy Hierarchy (Descending Precedence)

Every municipal planning decision must conform to this ladder.
Lower documents must be consistent with higher documents.

1. Planning Act (R.S.O. 1990, c. P.13)
   — Establishes zoning, appeals, and planning approval rules.
   — Key sections: s.34 (Zoning By-laws), s.45 (Minor Variances), s.41 (Site Plan Control).
   — Ontario Land Tribunal (OLT) hears appeals.

2. Provincial Planning Statement, 2024 (PPS 2024) — effective October 20, 2024
   — Replaced PPS 2020 and the Growth Plan for the Greater Golden Horseshoe.
   — Every municipal decision "shall be consistent with" the PPS.
   — Key directions: strong direction to permit housing; intensification around transit;
     development prohibited in significant natural features and flood-prone areas;
     employment land conversion requires a Municipal Comprehensive Review (MCR).

3. Greenbelt Plan (geographic-specific; prevails over PPS in conflict areas)
   — Applies to portions of Scarborough, Etobicoke, Rouge Park.
   — Development severely restricted within the Natural Heritage System.

4. Toronto Official Plan (consolidated 2022)
   — Assigns land use designations to every parcel.
   — Overrides the Zoning By-law where they conflict.
   — SASPs (Site and Area Specific Policies, Chapter 7) legally override base OP
     designations if there is a conflict.
   — Secondary Plans overlay the base OP with more detailed policies (King-Spadina,
     Yonge-Eglinton, Waterfront, etc.). Secondary Plan provisions override base OP.

5. Toronto Zoning By-law 569-2013 (as amended)
   — Day-to-day numeric rules: height, FSI, lot coverage, setbacks, parking, uses.
   — Chapter 900 contains site-specific exceptions that override base zone standards
     for specific properties — always check Chapter 900 for the subject parcel.
   — Hatched areas on the zoning map are governed by legacy by-laws (pre-amalgamation),
     not By-law 569-2013.

6. Site Plan Control (technical layer: landscaping, drainage, building-street interface)
   — Post-Bill 185 (2024): residential buildings of 10 units or fewer are EXEMPT
     unless within 300m of a railway corridor or 120m of a wetland.
"""

# ---------------------------------------------------------------------------
# Toronto Official Plan — Land Use Designations
# ---------------------------------------------------------------------------

TORONTO_OP_DESIGNATIONS = """
## Toronto Official Plan — Key Land Use Designations

| Designation | Development Intent | Typical Zone |
|-------------|-------------------|-------------|
| Neighbourhoods | "Physically stable" low-rise residential. New development must respect existing physical character (building types, lot sizes, setbacks). 1–4 storeys. | RD, RS, RT |
| Apartment Neighbourhoods | Physically stable areas with taller buildings. Significant growth not anticipated, but compatible infill (e.g., townhouses on surface parking) permitted. | RA |
| Mixed Use Areas | Absorbs majority of anticipated retail, office, service, and housing growth. Ground-floor commercial preferred on main streets. Low to mid-rise range. | CR |
| Employment Areas (Core/General) | Exclusively preserved for business and economic activities. Conversion to non-employment requires MCR. Very limited residential permitted. | E, EL, EH, EO |
| Regeneration Areas | Largely vacant or underused areas. Permits broad mix: commercial, residential, institutional, light industrial. | Varies |
| Natural Areas / Parks | Environmentally sensitive or public open space. Very limited development. | G, GA, O, OR |

**Important**: OP designation boundary ≠ zoning boundary. OP boundaries exclude
right-of-ways (ROW); zoning boundaries extend to the street centreline. For parcels
near designation boundaries, flag for professional confirmation.
"""

# ---------------------------------------------------------------------------
# Zoning — Key Standards and Override Rules
# ---------------------------------------------------------------------------

TORONTO_ZONING_KEY_RULES = """
## Toronto Zoning By-law 569-2013 — Key Rules

### Zone Map Formula
Map labels encode site-specific standards. Example: `RD (f12.0; a370; d0.6)` means:
- f = minimum lot frontage (12.0m)
- a = minimum lot area (370 m²)
- d = maximum FSI (0.6)
Always read the map label — it overrides zone defaults.

### Low-Rise Residential (RD/RS/RT)
- Max height: 10m (~3 storeys); flat roof exception: 7.2m max if slope < 1:4
- Min rear setback: 7.5m or 25% of lot depth (whichever is greater)
- Min side setback: 0.45–1.2m (depends on wall height)
- Max lot coverage: 33–40% (dictated by Lot Coverage Overlay Map)
- FSI: typically 0.6 × lot area; REMOVED for duplexes, triplexes, fourplexes

### Mid-Rise Mixed-Use (CR Zones — Avenues)
Height tied to Right-of-Way (ROW) width per Toronto Mid-Rise Guidelines:
| ROW Width | Max Height | Approx. Storeys |
|-----------|-----------|-----------------|
| 20m | 20m | ~6 storeys |
| 23m | 23m | ~7 storeys |
| 27m | 27m | ~8 storeys |
| 30m | 30m | ~9 storeys |
| 36m | 36m | ~11 storeys |
- Front angular plane: 45-degree plane from opposite side of street at 80% of ROW width
- Rear transition: minimum 10.5m (3-storey) base protecting adjacent Neighbourhoods
- Step-back above streetwall: minimum 1.5m above the 4th–6th storey

### Chapter 900 — Site-Specific Exceptions
CRITICAL: Chapter 900 contains property-specific overrides that can raise or lower
any standard in the base zone. Always check Chapter 900 for the subject parcel.
There is no machine-readable API — requires text search or licensed platform.
Flag all Chapter 900 checks as requiring human confirmation.

### Hatched Areas — Legacy By-laws
If the zoning map shows hatching over a property, By-law 569-2013 does NOT apply.
The governing by-law is a pre-amalgamation (pre-1998) legacy by-law:
- North York: By-law 7625
- Etobicoke: By-law 1994-0225
- Scarborough: By-law 9813
- East York: By-law 6752
- City of York: By-law 1-83
Flag hatched parcels and mark all standards as "inferred — requires confirmation."
"""

# ---------------------------------------------------------------------------
# O.Reg 462/24 — Additional Residential Units (Multiplex Override)
# ---------------------------------------------------------------------------

OREG_462_24 = """
## O.Reg 462/24 — Additional Residential Units (Provincial Override)

Applies to: lots containing a total of 3 units or fewer after the addition.

### What it overrides (more permissive provincial standard prevails):
- FSI restriction: COMPLETELY REMOVED for the lot
- Lot coverage: 45% maximum (local ZBL prevails if it permits more)
- Minimum parking: 0 required (Bill 185 removed minimum vehicle parking for multiplexes)
- Angular plane: EXEMPT — walls can extend straight up to maximum height

### What it does NOT override:
- Minimum setbacks (front, rear, side)
- Minimum lot frontage requirements
- Maximum Gross Floor Area (GFA) limits
- Chapter 900 exceptions that restrict frontage, setbacks, or GFA

### Units permitted as-of-right:
- Up to 4 units on most residential lots citywide
- Up to 6 units in specific wards

### Garden Suites and Laneway Suites:
- Max footprint: garden suite = smaller of 60m² or 40% of rear yard
- Laneway suite: 8m wide × 10m long absolute (80m²)
- Max height: 4.0m default; up to 6.0m if set back ≥7.5m from main house
- Min separation from main building: 4.0m
- Min rear setback: 1.5m from rear lot line or lane
"""

# ---------------------------------------------------------------------------
# Recent Provincial Legislation
# ---------------------------------------------------------------------------

RECENT_LEGISLATION = """
## Recent Provincial Legislation (Critical for Pipeline)

### Bill 23 — More Homes Built Faster Act (2022)
- Removed Site Plan Control for most residential ≤10 units.
- Removed the 2-year prohibition on applying for minor variances after a site-specific ZBA.
- RESTRICTED third-party appeals: neighbours can no longer appeal CoA approvals to TLAB as of right.

### Bill 109 — More Homes for Everyone Act (2022)
- Imposed strict mandatory decision timelines on municipalities for ZBA and OPA applications.
- Failure to decide triggers a deemed refusal (applicant can appeal) or deemed approval.

### Bill 185 — Cutting Red Tape to Build More Homes Act (2024)
- Removed minimum vehicle parking requirements for multiplexes citywide.
- Streamlined Committee of Adjustment timelines.
- Site Plan Control: residential ≤10 units exempt unless near railway (300m) or wetland (120m).

### Bill 60 — Fighting Delays, Building Faster Act (2025) — MOST RECENT
- Expanding as-of-right variances: landowners can alter prescribed zoning standards
  (setbacks, etc.) by a "prescribed percentage" WITHOUT a minor variance application.
- Municipalities can now impose lapsing provisions on site plan approvals.
- "Use It or Lose It" servicing capacity: municipalities can reallocate water/wastewater
  capacity from stalled projects to shovel-ready developments.
- Expanded ministerial authority for MZOs.
- PMTSA amendments no longer require ministerial approval — local municipality decides.

### O.Reg 462/24 (Additional Residential Units) — see above
"""

# ---------------------------------------------------------------------------
# Minor Variance — Four Statutory Tests
# ---------------------------------------------------------------------------

MINOR_VARIANCE_FOUR_TESTS = """
## Minor Variance — Four Statutory Tests (Planning Act s.45(1))

The Committee of Adjustment must be satisfied that ALL FOUR tests are met.
A refusal on any single test is sufficient to refuse the entire application.

1. Is the variance MINOR IN NATURE?
   — The deviation from the zoning standard is small in quantity and impact.
   — Consider the magnitude of the requested relief relative to the standard.
   — Consider whether the variance creates undue impact on neighbouring properties.

2. Is it DESIRABLE for the appropriate development or use of the land?
   — The proposed development makes good use of the land.
   — It is consistent with the built character of the surrounding area.
   — It represents a positive contribution to the neighbourhood.

3. Does it maintain the GENERAL INTENT AND PURPOSE OF THE ZONING BY-LAW?
   — The intent of the specific zoning standard is preserved even if the exact number varies.
   — The variance does not undermine the reasons the standard exists.
   — Site-specific conditions justify the different treatment.

4. Does it maintain the GENERAL INTENT AND PURPOSE OF THE OFFICIAL PLAN?
   — The proposed use and built form are consistent with the OP land use designation.
   — The development respects neighbourhood character as described in the OP.
   — Secondary Plan policies (if applicable) are also maintained.

### Appeals
- Minor variance decisions can be appealed to the Toronto Local Appeal Body (TLAB).
- TLAB decisions can be appealed to the Ontario Land Tribunal (OLT) on points of law.
- Post-Bill 23: third-party neighbours can no longer appeal CoA approvals to TLAB as of right.
  Only the applicant and the municipality retain appeal rights.

### Approval Timelines (Toronto)
| Pathway | Optimistic | Likely | Conservative |
|---------|-----------|--------|-------------|
| As-of-right building permit | 2–4 weeks | 4–8 weeks | 8–12 weeks |
| Minor variance (no appeal) | 2–3 months | 3–5 months | 5–7 months |
| Minor variance (appealed to TLAB) | 6–9 months | 9–15 months | 15–24 months |
| Zoning By-law Amendment | 12–18 months | 18–30 months | 30–48 months |
| OPA + ZBA | 18–24 months | 30–48 months | 48+ months |
"""

# ---------------------------------------------------------------------------
# OBC Hard Constraints — What CoA Cannot Vary
# ---------------------------------------------------------------------------

OBC_CONSTRAINTS = """
## Ontario Building Code — Hard Constraints (Cannot Be Varied by Committee of Adjustment)

The Committee of Adjustment operates under the Planning Act and can only grant
relief from Zoning By-law standards. It has NO legal authority to vary OBC requirements.

### What CoA CAN and CANNOT vary:
| Requirement | CoA Can Vary? | Authority |
|-------------|--------------|-----------|
| Building height | YES | Zoning By-law |
| Setbacks | YES | Zoning By-law |
| Lot coverage | YES | Zoning By-law |
| Parking spaces | YES | Zoning By-law |
| Min. fire access path width (0.9m) | NO | OBC |
| Max. fire access travel distance (45m) | NO | OBC |
| Limiting distance / unprotected openings | NO | OBC |
| Fire-resistance ratings between units | NO | OBC |
| Interconnected smoke/CO alarms | NO | OBC |

### Fire Access — Laneway/Garden Suites (BLOCKING if not met)
- Path width: minimum 0.9m unobstructed
- Path height: minimum 2.1m unobstructed
- Maximum travel distance: 45m from street to suite entrance
- Fire hydrant: within 45m of where fire vehicle parks on street
- Extended to 90m ONLY if: sprinkler system + exterior strobe + interconnected
  smoke alarm designed by a Professional Engineer

### Limiting Distances (Building Separation)
- Available limiting distance < 2.4m: no unprotected openings; ¾-hour fire-resistance rating required
- Available limiting distance < 1.2m: exterior face must be non-combustible materials
- "10-minute rule": if fire department cannot guarantee arrival within 10 minutes on 90%
  of calls, limiting distance must be HALVED for calculations (unless building is sprinklered)

### Part 9 vs Part 3
- Part 9: residential ≤3 storeys AND ≤600m² building area — standard residential rules
- Part 3: exceeds Part 9 thresholds — requires rigorous fire protection analysis,
  including confirmation of adequate firefighting water supply

### Relief from OBC (if required)
1. Alternative Solution to the Chief Building Official (CBO) — engineering proof of equivalent performance
2. Appeal to the Building Code Commission (BCC) if CBO refuses
"""

# ---------------------------------------------------------------------------
# Approval Pathway Decision Tree
# ---------------------------------------------------------------------------

APPROVAL_PATHWAY = """
## Approval Pathway Decision Tree

Does the proposal comply with ALL Zoning By-law standards?

├─ YES + no Site Plan required
│   → BUILDING PERMIT (as-of-right). Staff approval only.

├─ YES + Site Plan required (>10 units, or near railway/wetland)
│   → SITE PLAN APPROVAL → Building Permit

└─ NO — what kind of non-compliance?
    ├─ Minor numeric deviation (slightly too tall, small setback reduction, etc.)
    │   → COMMITTEE OF ADJUSTMENT — Minor Variance
    │   → All four statutory tests under Planning Act s.45(1) must be met
    │   → Note: Bill 60 (2025) may allow some deviations as-of-right without CoA
    │
    ├─ Proposed use or density not permitted at all in the zone
    │   → ZONING BY-LAW AMENDMENT (ZBA) — City Council approval required
    │   → If OP designation also conflicts: OFFICIAL PLAN AMENDMENT (OPA) first
    │
    └─ Subdivision/severance of land
        → CONSENT (Committee of Adjustment) or PLAN OF SUBDIVISION (Council)
"""

# ---------------------------------------------------------------------------
# Precedent Research Sources
# ---------------------------------------------------------------------------

PRECEDENT_SOURCES = """
## Precedent Research Sources

### Toronto Application Information Centre (AIC)
URL: https://www.toronto.ca/city-government/planning-development/application-information-centre/
- All active and historical planning applications: ZBAs, OPAs, Site Plans, Subdivisions
- Committee of Adjustment files: Minor Variances (A-files) and Consents (B-files)
- Radius filter: 250m, 500m, or 1000m — use 500m for standard precedent search
- File formats: Minor Variance = A-XXXX/XX, Consent = B-XXXX/XX, ZBA = XX-XXXXXX ZBA

### Ontario Land Tribunal (OLT)
URL: https://olt.gov.on.ca/case-search/
- Appeals of ZBAs, OPAs, CoA decisions (via TLAB), expropriation
- Search by: case number, municipality, address, date range

### CanLII — Historical Tribunal Decisions
- OLT: https://www.canlii.org/en/on/onltb/
- OMB (pre-2021): https://www.canlii.org/en/on/onmb/
- TLAB: https://www.canlii.org/en/on/ontlab/

### Toronto Local Appeal Body (TLAB)
URL: https://www.toronto.ca/tlab/
- Hears Toronto minor variance appeals instead of OLT
- TLAB decisions can be appealed to OLT on points of law only
"""

# ---------------------------------------------------------------------------
# Combined grounding context by document type
# ---------------------------------------------------------------------------

def get_policy_grounding(doc_type: str) -> str:
    """Return the appropriate policy grounding context for a document type."""

    if doc_type == "planning_rationale":
        return "\n".join([
            "## POLICY GROUNDING CONTEXT — USE ONLY THESE REFERENCES",
            ONTARIO_POLICY_HIERARCHY,
            TORONTO_OP_DESIGNATIONS,
            TORONTO_ZONING_KEY_RULES,
            OREG_462_24,
            RECENT_LEGISLATION,
            APPROVAL_PATHWAY,
        ])

    elif doc_type == "variance_justification":
        return "\n".join([
            "## POLICY GROUNDING CONTEXT — USE ONLY THESE REFERENCES",
            MINOR_VARIANCE_FOUR_TESTS,
            OBC_CONSTRAINTS,
            TORONTO_ZONING_KEY_RULES,
            OREG_462_24,
            RECENT_LEGISLATION,
        ])

    elif doc_type in ("compliance_matrix", "compliance_review_report"):
        return "\n".join([
            "## POLICY GROUNDING CONTEXT — USE ONLY THESE REFERENCES",
            TORONTO_ZONING_KEY_RULES,
            OBC_CONSTRAINTS,
            OREG_462_24,
        ])

    elif doc_type == "precedent_report":
        return "\n".join([
            "## POLICY GROUNDING CONTEXT — USE ONLY THESE REFERENCES",
            MINOR_VARIANCE_FOUR_TESTS,
            PRECEDENT_SOURCES,
        ])

    elif doc_type == "public_benefit_statement":
        return "\n".join([
            "## POLICY GROUNDING CONTEXT — USE ONLY THESE REFERENCES",
            TORONTO_OP_DESIGNATIONS,
            RECENT_LEGISLATION,
        ])

    elif doc_type == "approval-pathway":
        return "\n".join([
            "## POLICY GROUNDING CONTEXT — USE ONLY THESE REFERENCES",
            APPROVAL_PATHWAY,
            MINOR_VARIANCE_FOUR_TESTS,
            OBC_CONSTRAINTS,
            RECENT_LEGISLATION,
        ])

    else:
        # Default: just the hierarchy for context
        return "\n".join([
            "## POLICY GROUNDING CONTEXT",
            ONTARIO_POLICY_HIERARCHY,
        ])
