# Research: Government Submission Document Generation

> Deep research into Toronto development application requirements, document standards, AI safety, and implementation approach. This informs how we build the document generation system.

---

## CRITICAL FINDING: Policy Framework Changed in 2024

The **Provincial Policy Statement (PPS) 2020** and **A Place to Grow (Growth Plan) 2020** were **replaced** by the **Provincial Planning Statement (PPS) 2024** effective **October 20, 2024**.

This is a major change. Any system generating planning rationales must reference the correct framework:
- Before Oct 20, 2024: PPS 2020 + Growth Plan 2020 (two separate documents)
- After Oct 20, 2024: Provincial Planning Statement 2024 (one merged document)

The legal test also changed:
- Old: "consistent with" the PPS, "conform to" the Growth Plan
- New: "consistent with" the Provincial Planning Statement 2024

**Our system must use the 2024 framework.** All templates referencing PPS 2020 or the Growth Plan need updating.

---

## 1. Toronto Development Application Types

### Major Application Types

| Type | When Required | Key Documents | Typical Timeline |
|------|--------------|---------------|-----------------|
| **Official Plan Amendment (OPA)** | Proposal doesn't conform to Official Plan land use designation | Planning Rationale, Community Services Study, full technical studies | 120 days (Bill 109) |
| **Zoning By-law Amendment (Rezoning)** | Proposal doesn't comply with zoning permissions | Planning Rationale, Urban Design Brief, full technical studies | 90 days (Bill 109) |
| **Site Plan Control** | Most new buildings and major additions in designated areas | Site Plan drawings, Landscape Plan, technical studies | 60 days (Bill 109) |
| **Minor Variance** | Small deviations from zoning (Committee of Adjustment) | Cover Letter, Planning Rationale (shorter), survey | 4-6 weeks to hearing |
| **Consent to Sever** | Splitting a property into two or more parcels | Planning Rationale, survey, reference plan | 4-6 weeks to hearing |
| **Plan of Subdivision** | Dividing land into 3+ lots | Planning Rationale, servicing studies, traffic study | 120 days |
| **Plan of Condominium** | Creating condominium ownership structure | Often combined with site plan | 120 days |

### Bill 109 (More Homes for Everyone Act) Implications

Ontario's Bill 109 imposed strict timelines on municipalities:
- **Zoning By-law Amendment**: 90-day decision deadline, or fees refunded
- **Site Plan Control**: 60-day decision deadline, or fees refunded
- **OPA**: 120-day deadline
- **Combined OPA + Rezoning**: 120-day deadline

If the municipality misses the deadline, application fees are refunded in stages (25%, 50%, 75%, 100%). This creates pressure for **complete applications** — incomplete submissions get sent back, resetting the clock.

### Complete Application Requirements

Toronto requires a **pre-application consultation** before submission. At this meeting, city staff identify exactly which studies and documents are required.

A "complete application" must include ALL required materials. Missing items = application rejected as incomplete.

---

## 2. Required Documents by Application Type

### Rezoning / OPA — Full Submission Package

**Always required:**
1. Application form (city-issued)
2. Filing fee
3. Planning Rationale Report
4. Draft Zoning By-law Amendment
5. Survey Plan (Ontario Land Surveyor)
6. Site Plan (architectural)
7. Building elevations / massing drawings
8. Shadow Study
9. Project Data Sheet (unit count, GFA, parking, etc.)
10. Community Consultation Strategy
11. Public Notice sign on the property

**Commonly required (depends on pre-consultation):**
12. Urban Design Brief / Rationale
13. Traffic Impact Study
14. Pedestrian Level Wind Study
15. Noise and Vibration Feasibility Study
16. Arborist Report / Tree Preservation Plan
17. Phase 1 Environmental Site Assessment
18. Phase 2 ESA (if Phase 1 identifies contamination risk)
19. Stormwater Management Report
20. Servicing and Grading Report
21. Heritage Impact Assessment
22. Archaeological Assessment (Stages 1-4)
23. Housing Issues Report
24. Community Services and Facilities Study
25. Energy Strategy / Sustainability Report
26. Toronto Green Standard Checklist (Tier 1 mandatory)
27. 3D Model / Massing Model (for tall buildings)
28. Functional Servicing Report
29. Geotechnical Study
30. Loading Study
31. Rental Housing Demolition Application (if existing rental units affected)

### Site Plan Control

Similar to above but typically without:
- Draft Zoning By-law Amendment
- Some of the broader policy analysis

Plus additional requirements:
- Detailed landscape plan
- Site servicing plan
- Grading and drainage plan
- Lighting plan
- Signage plan

### Minor Variance (Committee of Adjustment)

Simpler package:
1. Application form
2. Filing fee (~$1,500+)
3. Survey Plan
4. Site Plan / Floor Plans
5. Planning Rationale / Cover Letter (shorter, focused on four tests)
6. Photos of the property and surroundings
7. Written description of the variance(s) requested

The Committee of Adjustment applies the **four tests** from Section 45(1) of the Planning Act:
1. Does the variance maintain the general intent and purpose of the Official Plan?
2. Does the variance maintain the general intent and purpose of the Zoning By-law?
3. Is the variance desirable for the appropriate development of the land?
4. Is the variance minor?

ALL four tests must be satisfied.

---

## 3. Planning Rationale — Document Standard

### What It Is

The Planning Rationale is the most important document in any development application. It is the applicant's argument for why the proposed development should be approved. It must demonstrate that the proposal is consistent with all applicable planning policies.

### Who Writes It

In Ontario, planning rationales are typically prepared by a **Registered Professional Planner (RPP)** who is a member of the **Ontario Professional Planners Institute (OPPI)**. While there is no strict legal requirement that it must be signed by an RPP, city staff and the Ontario Land Tribunal give significantly more weight to opinions from qualified planners.

### Standard Structure (Rezoning / OPA)

A typical Toronto planning rationale for a major application is **30-60 pages** and follows this structure:

```
1. INTRODUCTION
   1.1 Purpose
   1.2 Description of the Proposal
   1.3 Required Approvals

2. SITE AND SURROUNDING AREA
   2.1 Subject Property
       - Municipal address
       - Legal description
       - Lot dimensions (area, frontage, depth)
       - Current use and condition
       - Existing buildings (if any)
   2.2 Surrounding Area Context
       - North, south, east, west land uses
       - Neighborhood character
       - Nearby transit
       - Recent development activity in the area
   2.3 Transportation Context
       - Street classification
       - Transit access (TTC routes, distance to stations)
       - Cycling infrastructure

3. PROPOSED DEVELOPMENT
   3.1 Development Description
       - Building type, height, storeys
       - Total GFA, residential GFA, non-residential GFA
       - Unit count by type
       - Parking and loading
       - Amenity spaces
       - Landscaping
   3.2 Key Statistics Table
   3.3 Design Rationale (or reference to Urban Design Brief)

4. POLICY AND REGULATORY ANALYSIS
   4.1 Provincial Planning Statement 2024
       - Section-by-section analysis
       - How the proposal is "consistent with" each relevant policy
   4.2 City of Toronto Official Plan
       - Chapter 2: Shaping the City
         - Growth management, intensification, reurbanization
       - Chapter 3: Building a Successful City
         - Section 3.1.1: Public Realm
         - Section 3.1.2: Built Form (key section — height, massing, transition)
         - Section 3.1.3: Built Form — Tall Buildings (if applicable)
         - Section 3.2.1: Housing
       - Chapter 4: Land Use Designations
         - Analysis of the site's designation (e.g., Mixed Use Areas, Neighbourhoods)
         - What the designation permits
       - Chapter 5: Implementation
         - Section 5.6: Interpretation
   4.3 Secondary Plan (if applicable)
       - Area-specific policies
   4.4 Urban Design Guidelines
       - City-wide guidelines
       - Tall Building Design Guidelines (if applicable)
       - Avenues and Mid-Rise Guidelines (if applicable)
       - Growing Up Guidelines
       - Area-specific design guidelines
   4.5 Zoning By-law 569-2013
       - Current zoning permissions
       - Proposed zoning changes
       - Compliance table (see Section 5 below)

5. ZONING COMPLIANCE TABLE
   (Detailed provision-by-provision comparison)

6. SUPPORTING STUDIES SUMMARY
   - Reference to traffic study findings
   - Reference to shadow study findings
   - Reference to wind study findings
   - Reference to other technical studies

7. COMMUNITY BENEFITS (if applicable)
   - Section 37 / Community Benefits Charge considerations
   - Proposed contributions

8. PLANNING OPINION AND CONCLUSION
   - Summary of why the proposal represents good planning
   - Request for approval
   - Professional planner's signature and RPP designation
```

### Minor Variance Planning Rationale

Much shorter (5-15 pages). Structured around the four tests:

```
1. Introduction and Proposal Description
2. Site and Surrounding Context
3. Requested Variances (list each one)
4. Analysis of the Four Tests
   4.1 General Intent and Purpose of the Official Plan
   4.2 General Intent and Purpose of the Zoning By-law
   4.3 Desirable for Appropriate Development
   4.4 Minor in Nature
5. Conclusion
```

---

## 4. Policy Framework Reference

### Hierarchy (as of October 2024)

```
Provincial Planning Statement 2024 (PPS)
  ↓ "consistent with"
City of Toronto Official Plan (as amended by OPAs)
  ↓ "conform to"
Secondary Plans (area-specific)
  ↓ "conform to"
Zoning By-law 569-2013 (as amended)
  ↓ "comply with"
Urban Design Guidelines (non-statutory but influential)
```

### Provincial Planning Statement 2024

Replaced PPS 2020 + Growth Plan 2020. Key sections for development applications:

| Section | Topic | Key Policy |
|---------|-------|-----------|
| 2.2 | Housing | Provide range and mix of housing types, densities, and affordability |
| 2.3 | Settlement Areas | Focus growth within settlement areas, support intensification |
| 2.4 | Housing Supply | Maintain 15-year supply of residential land, 5-year supply of serviced land |
| 3.1 | Transportation | Land use patterns that support transit, active transportation |
| 3.4 | Infrastructure | Orderly and efficient use of infrastructure |
| 4.1 | Natural Heritage | Protect natural heritage systems |
| 4.6 | Cultural Heritage | Conserve significant cultural heritage resources |
| 6.1 | Growth Management | Direct growth to settlement areas, strategic growth areas |
| 6.3 | Major Transit Station Areas | Higher density, mixed-use development near transit |

### City of Toronto Official Plan — Key Sections

| Section | Topic | What to cite |
|---------|-------|-------------|
| 2.1 | Downtown | Growth areas, intensification |
| 2.2 | Centres | Mixed-use, higher density |
| 2.2.1 | Downtown: The Heart of Toronto | Growth projections, built form |
| 2.3 | Avenues | Mid-rise intensification along arterials |
| 2.4 | Employment Areas | Protection of employment lands |
| 3.1.1 | Public Realm | Streets, parks, open spaces |
| 3.1.2 | Built Form | Height, massing, setbacks, transition — **most cited section** |
| 3.1.3 | Built Form — Tall Buildings | Tower separation, floor plate, podium, shadow |
| 3.2.1 | Housing | Range of housing, affordability, rental protection |
| 3.4 | Environment | Environmental impact, sustainability |
| 4.5 | Mixed Use Areas | What's permitted in Mixed Use designation |
| 4.1 | Neighbourhoods | Stability, prevailing character, "fit" |
| 5.3.2 | Implementation — Zoning | Interpretation of zoning provisions |
| 5.6 | Interpretation | How to read and apply OP policies |

### Zoning By-law 569-2013 Structure

```
Part 1: Administration
Part 2: Organization of this By-law
Part 3: Zone Categories
  - Residential: R, RD, RS, RT, RM, RA
  - Commercial-Residential: CR
  - Commercial: C, CL, CRE
  - Employment: E, EL, EO
  - Institutional: I
  - Open Space: O, OR, OG
  - Utility: UT
Part 4-14: Zone-Specific Regulations (height, density, setbacks per zone)
Article 200: Parking and Loading
Article 220: Bicycle Parking
Article 230: Loading
Part 15: Site-Specific Exceptions (hundreds of numbered exceptions)
Part 16: Schedules (maps)
```

Reading a zone string: `CR 3.0 (c2.0; r2.5) SS2 (x345)`
- CR = Commercial-Residential zone
- 3.0 = Maximum total FSI
- c2.0 = Maximum commercial FSI
- r2.5 = Maximum residential FSI
- SS2 = Height limit from Schedule 2
- x345 = Site-specific exception #345

### Design Guidelines — Key Standards

**Tall Building Design Guidelines:**
- Tower floor plate: maximum 750 sqm
- Tower separation: minimum 25m (tower to tower)
- Minimum 3-storey base building (podium)
- Tower stepback from podium: minimum 3m
- Angular plane from adjacent lower-scale areas
- Shadow: no net new shadow on parks/schools March-September

**Mid-Rise Building Performance Standards:**
- Maximum height = right-of-way width (1:1 ratio)
- Angular plane: 45 degrees from opposite side of the street
- Front facade: minimum 80% at the street wall
- Ground floor height: minimum 4.5m
- Rear transition: angular plane to protect rear neighbors

**Growing Up Guidelines:**
- Minimum 25% two-bedroom units
- Minimum 10% three-bedroom units
- Minimum unit sizes: 2-bed 87 sqm, 3-bed 100 sqm
- Functional layouts for families with children

---

## 5. Zoning Compliance Matrix Standards

### Required Provisions (every compliance table must include these)

| Provision | Typical By-law Section | Unit |
|-----------|----------------------|------|
| Maximum building height | Zone-specific | metres |
| Maximum number of storeys | Zone-specific | count |
| Maximum FSI (total) | Zone-specific | ratio |
| Maximum commercial FSI | Zone-specific (CR zones) | ratio |
| Maximum residential FSI | Zone-specific (CR zones) | ratio |
| Minimum lot area | Zone-specific | sqm |
| Minimum lot frontage | Zone-specific | metres |
| Maximum lot coverage | Zone-specific | % |
| Minimum front yard setback | Zone-specific | metres |
| Minimum rear yard setback | Zone-specific | metres |
| Minimum side yard setback (interior) | Zone-specific | metres |
| Minimum side yard setback (exterior) | Zone-specific | metres |
| Minimum building separation | Zone-specific | metres |
| Above-grade stepback (tower from base) | Zone-specific / guidelines | metres |
| Maximum tower floor plate | Guidelines | sqm |
| Minimum tower separation | Guidelines | metres |
| Minimum amenity space (indoor) | s.10-15 (zone-specific) | sqm/unit |
| Minimum amenity space (outdoor) | s.10-15 (zone-specific) | sqm/unit |
| Minimum parking — residents | Article 200 | spaces |
| Minimum parking — visitors | Article 200 | spaces |
| Minimum parking — commercial | Article 200 | spaces |
| Minimum accessible parking | Article 200 | spaces |
| Minimum bicycle parking — long-term | Article 220 | spaces |
| Minimum bicycle parking — short-term | Article 220 | spaces |
| Minimum loading spaces | Article 230 | spaces |
| Minimum landscape area | Zone-specific | sqm or % |
| Minimum soft landscape area | Zone-specific | sqm or % |

### Parking Standards (Article 200)

Toronto has **Policy Areas** that determine parking rates:

| Policy Area | Location | Residential Rate (per unit) |
|-------------|----------|---------------------------|
| Policy Area 1 | Downtown core | 0.0 - 0.5 (reduced) |
| Policy Area 2 | Inner city / transit-rich | 0.3 - 0.7 |
| Policy Area 3 | Midtown / urban | 0.5 - 1.0 |
| Policy Area 4 | Suburban | 0.8 - 1.25 |

Note: Toronto eliminated minimum parking requirements for most areas near rapid transit as of 2022. Parking is now often "market-driven" rather than mandatory.

Visitor parking: typically 0.1 spaces per unit
Accessible parking: 1 per 25 spaces (minimum)
Bicycle parking: 0.9 long-term per unit + 0.1 short-term per unit (typical)

### Shadow Study Standards

Test dates and times (Toronto standard):
- **March 21** (spring equinox)
- **June 21** (summer solstice)
- **September 21** (fall equinox)

Test times: **9:18 AM, 10:18 AM, 12:18 PM, 2:18 PM, 4:18 PM, 6:18 PM** (Eastern Daylight Time)

Key shadow protection policies:
- No net new shadow on public parks March 21 to September 21
- Neighbourhoods: protect private outdoor amenity from shadow
- Schoolyards and publicly accessible open spaces protected
- Child care outdoor play areas protected

### Toronto Green Standard (TGS)

**Tier 1 is mandatory** for all new development (Site Plan and above).

Key Tier 1 requirements:
- Air quality: ventilation standards, low-VOC materials
- Energy: Toronto's energy efficiency targets (above OBC minimum)
- Water: low-flow fixtures, stormwater retention
- Ecology: bird-friendly glazing, light pollution reduction, tree planting
- Solid waste: 3-stream waste collection, waste diversion plan

---

## 6. AI Safety & Liability Framework

### Professional Liability — Critical Issue

**Key finding: Planning rationales carry professional liability.** If a document contains errors that lead to a rejected application, delayed project, or adverse tribunal decision, there are real financial and legal consequences.

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Hallucinated citations | Document references non-existent bylaw sections | Citation verification against known policy database |
| Incorrect zoning standards | Compliance table shows wrong required values | Deterministic lookup from bylaw database, never AI-generated |
| Stale policy references | Cites PPS 2020 instead of PPS 2024 | Version-controlled policy database with effective dates |
| Missing required analysis | Omits required policy section from rationale | Checklist-driven generation — system knows what's required |
| Fabricated precedents | References non-existent approved applications | Only cite precedents from verified database records |
| Professional signature | AI cannot sign as RPP | Clear disclaimer: "draft for professional review" |

### Required Safeguards

1. **AI never generates final documents.** It generates **drafts for professional review.**
2. **Every factual claim must trace to a source.** No free-form AI generation of numbers, citations, or policy references.
3. **Compliance tables must be deterministic.** The zoning standards come from the database, not AI.
4. **Precedent citations must come from verified records.** Never let AI invent application numbers or decisions.
5. **Clear disclaimers on every generated document:**
   ```
   DRAFT — FOR PROFESSIONAL REVIEW ONLY
   This document was generated with AI assistance and has not been
   reviewed or signed by a Registered Professional Planner (RPP).
   All policy citations, zoning standards, and factual claims must
   be independently verified before submission to any government body.
   ```
6. **Confidence scoring per section.** Flag sections where data was incomplete or AI had to infer.
7. **Human review workflow.** Before any document can be marked "final," a human must approve it.
8. **Audit trail.** Every generated document must record: AI model used, prompt hash, source data version, generation timestamp.

### The Hallucination Problem — Lessons from Legal AI

The most cited cautionary example: **Mata v. Avianca** (2023) — a lawyer used ChatGPT to write a legal brief that cited six non-existent court cases. The lawyer was sanctioned by the judge.

**Our approach must prevent this:**
- Policy citations: looked up from a structured policy database, not generated by AI
- Zoning standards: computed deterministically from bylaw data
- Precedent applications: queried from a verified development applications database
- AI's role: prose composition, analysis narrative, and synthesis — NOT fact generation

### Recommended Architecture

```
FACTS (deterministic, from database):
├── Parcel geometry, area, frontage
├── Zoning code and permissions
├── Required setbacks, height, FSI from bylaw lookup
├── Compliance results (pass/fail per provision)
├── Precedent applications (real records)
└── Policy text (versioned, sourced)

AI GENERATES (with facts injected):
├── Narrative prose connecting facts
├── Policy analysis (interpreting how facts meet policy)
├── Planning opinion (professional judgement)
├── Synthesis and conclusions
└── Document formatting and structure

HUMAN REVIEWS:
├── Verify all citations are correct
├── Verify compliance table accuracy
├── Add professional judgement
├── Sign as RPP (if qualified)
└── Approve for submission
```

---

## 7. Implementation Recommendations

### Architecture: Template-First, AI-Assisted

Do NOT let AI generate documents from scratch. Instead:

1. **Hardcoded document structure** — every section, in order, is defined in templates
2. **Deterministic data injection** — zoning standards, compliance results, parcel data come from the database
3. **AI writes the prose** — given the facts and the section purpose, AI writes the narrative
4. **Citation verification** — every policy reference is checked against the policy database
5. **Human review required** — documents are marked as drafts until a human approves

### Data Dependencies (what we must have in the database)

| Data | Source | Status |
|------|--------|--------|
| Parcel boundaries + attributes | Toronto Open Data | Schema exists, need to load data |
| Zoning by-law permissions by zone | By-law 569-2013 | Need to parse and structure |
| Official Plan designations (map) | Toronto Open Data / GIS | Need to load spatial data |
| Official Plan policy text | toronto.ca | Need to ingest and version |
| Provincial Planning Statement 2024 | Ontario.ca | Need to ingest |
| Design guidelines (quantitative) | toronto.ca | Need to extract standards |
| Development applications | Toronto Open Data | Schema exists, need to load |
| Parking standards by policy area | By-law 569-2013 Art. 200 | Need to structure |
| TGS checklist requirements | toronto.ca | Need to structure |

### Phased Rollout

**Phase A: Deterministic compliance (no AI needed)**
- Zoning compliance table generated from bylaw data
- Pass/fail assessment for each provision
- This alone is enormously valuable and carries zero hallucination risk

**Phase B: Structured document assembly (minimal AI)**
- Template-driven document generation
- Facts from database, structure from templates
- AI only for transitional prose between sections
- All citations verified against database

**Phase C: Full planning rationale (AI-assisted)**
- AI writes policy analysis narrative
- Human-in-the-loop review before finalization
- Confidence scoring per section
- Professional disclaimer on all outputs

**Phase D: Precedent-grounded generation (RAG)**
- Ingest real planning rationales as reference examples
- AI generates content grounded in similar approved documents
- Citation chains back to real precedents
- Continuous improvement from review feedback

### RAG Implementation for Legal Documents

**Embedding model:** Use a legal/regulatory-tuned embedding model (or fine-tune). Standard embedding models may not capture bylaw semantics well.

**Chunk strategy for bylaws:**
- Chunk by section/subsection, not by token count
- Preserve section numbers and cross-references in metadata
- Store the full clause hierarchy (bylaw → chapter → section → subsection → clause)

**Retrieval strategy:**
- Hybrid: keyword search (BM25/tsvector) + semantic search (pgvector)
- Re-rank results by relevance to the specific parcel and zone
- Filter by jurisdiction and effective date
- Return full citation chain with every retrieved chunk

**Grounding verification:**
- After AI generates text, extract all policy references
- Verify each reference exists in the policy database
- Flag any reference that cannot be verified
- Reject documents with unverifiable citations

---

## 8. Risks and Open Questions

### High-Priority Risks

1. **Policy currency** — If our policy database is outdated, generated documents cite stale/repealed policies. Mitigation: automated refresh + effective date tracking.

2. **Zone-specific exceptions** — Toronto has hundreds of site-specific zoning exceptions. Missing one = wrong compliance analysis. Mitigation: comprehensive exception parsing.

3. **Municipal acceptance** — The City of Toronto may view AI-generated documents skeptically. Mitigation: position as "draft preparation tool for professionals," not as a replacement for professional planning services.

4. **Liability** — If a developer relies on our compliance analysis and it's wrong, we could face claims. Mitigation: clear terms of service, disclaimers, mandatory professional review.

### Open Questions

- Does the City of Toronto have a formal policy on AI-assisted submissions?
- What level of disclosure is required if AI was used in document preparation?
- How do OPPI professional standards apply to AI-assisted planning documents?
- What insurance coverage is appropriate for this type of software?
- Should we require RPP review integration (partnership with planning firms)?

---

## Sources and References

- City of Toronto — Development Application Submission Requirements: https://www.toronto.ca/city-government/planning-development/application-forms-fees/
- Ontario Planning Act, R.S.O. 1990, c. P.13
- Provincial Planning Statement 2024: https://www.ontario.ca/page/provincial-planning-statement
- City of Toronto Official Plan: https://www.toronto.ca/city-government/planning-development/official-plan-guidelines/official-plan/
- Toronto Zoning By-law 569-2013: https://www.toronto.ca/city-government/planning-development/zoning-by-law-preliminary-zoning-reviews/zoning-by-law-569-2013-2/
- Tall Building Design Guidelines: https://www.toronto.ca/city-government/planning-development/official-plan-guidelines/design-guidelines/tall-buildings/
- Growing Up Guidelines: https://www.toronto.ca/city-government/planning-development/official-plan-guidelines/design-guidelines/growing-up/
- Toronto Green Standard: https://www.toronto.ca/city-government/planning-development/official-plan-guidelines/toronto-green-standard/
- Bill 109 (More Homes for Everyone Act, 2022)
- Mata v. Avianca, Inc. (S.D.N.Y. 2023) — AI hallucination in legal documents
