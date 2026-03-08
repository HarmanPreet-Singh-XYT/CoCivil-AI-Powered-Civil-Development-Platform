---
name: Ontario Planning Appendices and Reference Data
description: General references for Ontario planning law, including regulatory updates, municipal fees, standard zoning abbreviations, OLT case law themes, data architecture, and QA.
---

## Appendix A: Ontario Regulation Quick Reference

### O. Reg. 299/19 — Additional Residential Units
```
Key provisions:
- Permits up to 2 additional residential units as-of-right
  on lots zoned for residential use
- One unit may be in the primary dwelling
  (e.g., basement apartment)
- One unit may be in an accessory building
  (e.g., laneway suite, garden suite)
- Municipal zoning cannot prohibit these units if the
  lot is zoned residential
- Units must comply with OBC, fire code, and applicable
  municipal standards for size, parking, etc.
- Municipality CAN set standards for ARUs (setbacks, height,
  etc.) but CANNOT prohibit them entirely
- Servicing: lot must be on municipal water and sewer
  for accessory building unit (or demonstrate adequate
  private services)
```

### O. Reg. 462/24 — As-of-Right Fourplexes
```
Key provisions (verify current text — regulation is new):
- Permits up to 4 residential units on lots in settlement
  areas zoned for residential use
- Applies in municipalities above certain population thresholds
- Overrides municipal zoning to the extent of the regulation
- Municipality cannot require:
  - More than 1 parking space per unit (or 0 within 800m
    of higher-order transit — check exact provision)
  - Application fees for these units
- Units must comply with OBC
- Maximum height and other standards may be specified
  in the regulation
- Does NOT override Official Plan designations that
  prohibit residential use (e.g., employment lands)
```

### Bill 185 (2024) Key Planning Changes
```
- Third-party appeals: Only applicant, municipality, or
  specified public bodies can appeal minor variance and
  consent decisions to OLT
- No more neighbour appeals for minor variances
- Parking: Province removed authority for municipalities
  to require minimum parking near major transit stations
  (within 800m of higher-order transit station)
- Site plan control: Already limited by Bill 23 to exclude
  ≤10 residential units; Bill 185 continues this direction
- Community benefits: CBC framework continues
- OLT: Enhanced case management and mediation
```

### Bill 23 (2022) Key Planning Changes Still in Effect
```
- Site plan control: Exempt for ≤10 residential units
- Conservation authorities: Scope limited to natural hazards
  (flooding, erosion); no longer comment on planning policy
- Heritage: 2-year limit on listing properties on heritage
  register without designation; limited interior designation
- Parkland dedication: Alternative rate caps
- Development charges: Phased-in DC for certain building types
  (5-year phase-in for purpose-built rental, affordable,
  institutional, non-profit)
- Section 37: Replaced with Community Benefits Charges
  (applicable to ≥10 units and ≥5 storeys)
```

---

## Appendix B: Municipal Fee Reference (Selected Municipalities — 2024 Approximate)
```
Note: Fees change annually. Always verify with the municipality.

TORONTO:
| Application | Fee (2024 approx.) |
|------------|-------------------|
| Minor Variance (residential) | $3,800-$5,800 |
| Consent (severance) | $5,000-$8,000 |
| ZBA (small residential) | $18,000-$25,000 |
| ZBA (large) | $35,000-$85,000 |
| OPA | $28,000-$75,000 |
| Site Plan (small) | $5,000-$12,000 |
| Site Plan (large) | $15,000-$60,000 |
| Building Permit | ~$12-$22/sq m |
| Pre-consultation | $500-$2,000 |

OTTAWA:
| Application | Fee (2024 approx.) |
|------------|-------------------|
| Minor Variance | $1,500-$3,500 |
| ZBA | $12,000-$30,000 |
| Site Plan | $5,000-$25,000 |

MISSISSAUGA:
| Application | Fee (2024 approx.) |
|------------|-------------------|
| Minor Variance | $2,000-$4,000 |
| ZBA | $15,000-$35,000 |
| Site Plan | $8,000-$30,000 |
```

---

## Appendix C: Standard Zoning Abbreviations (Toronto By-law 569-2013)
```
RESIDENTIAL ZONES:
RD — Residential Detached
RS — Residential Semi-Detached
RT — Residential Townhouse
RM — Residential Multiple Dwelling
RA — Residential Apartment
R — Residential (general)

COMMERCIAL/MIXED USE ZONES:
CR — Commercial Residential
CL — Commercial Local
CRE — Commercial Residential Employment

EMPLOYMENT ZONES:
E — Employment Industrial
EL — Employment Light Industrial
EH — Employment Heavy Industrial
EO — Employment Office

INSTITUTIONAL ZONES:
I — Institutional

OPEN SPACE ZONES:
O — Open Space
ON — Open Space Natural
OR — Open Space Recreation

UTILITY ZONES:
UT — Utility and Transportation

ZONE EXCEPTIONS:
Shown as number after zone (e.g., RD (f12.0; a450; d0.6))
  f = minimum lot frontage (metres)
  a = minimum lot area (sq m)
  d = maximum floor space index (density)

OVERLAY ZONES:
HCD — Heritage Conservation District
PMT — Protected Major Transit Station Area
FP — Floodplain
```

---

## Appendix D: Key OLT Case Law Themes for AI Training
```
When building the AI's ability to analyze and cite precedent,
train on these common OLT themes:

1. MINOR VARIANCE — HEIGHT
   Key principle: Height is evaluated relative to neighbouring
   heights, not in a vacuum. A 15% height variance may be minor
   on a street with varied heights but not minor where all
   houses are uniform.

2. MINOR VARIANCE — FSI/DENSITY
   Key principle: FSI is a proxy for building bulk. The actual
   impact matters more than the percentage increase. Built form
   and compatibility analysis is critical.

3. MINOR VARIANCE — SETBACKS
   Key principle: Setback variances are evaluated based on
   impact on adjacent properties — privacy, overlook, light
   access, and streetscape consistency.

4. MINOR VARIANCE — PARKING
   Key principle: Post-Bill 185 and PPS 2024, reduced parking
   is increasingly supported near transit. TDM measures
   strengthen the case. Car ownership data is relevant.

5. FOUR TESTS — GENERAL APPROACH
   Key principle: All four tests must be met. The tests are
   not a checklist but an integrated assessment. The OLT
   weighs all evidence and makes its own determination —
   it does not simply review the Committee's decision.

6. GOOD PLANNING
   Key principle: For ZBAs, the OLT asks whether the proposal
   represents "good planning." This requires demonstrating
   conformity with the policy framework AND that the proposal
   is appropriate for the site.

7. PLANNING EVIDENCE
   Key principle: OLT gives the most weight to qualified
   planning opinion evidence. Lay testimony is considered
   but does not outweigh professional opinion unless the
   professional evidence is weak.
```

---

## Appendix E: Data Architecture Recommendation
```
LAYER 1: STATIC LEGAL DATA (update annually or when legislation changes)
  - Provincial statutes (Planning Act, Building Code Act, etc.)
  - Regulations (O. Reg. 299/19, 462/24, 332/12, etc.)
  - Provincial Planning Statement 2024
  - Growth Plan 2020

LAYER 2: MUNICIPAL POLICY DATA (update when amended)
  - Official Plans (full text, indexed by section)
  - Secondary Plans (linked to geographic areas)
  - Urban Design Guidelines
  - Zoning By-laws (full text + spatial data)

LAYER 3: PROPERTY-SPECIFIC DATA (queried per request)
  - Parcel boundaries, zoning, assessment, title
  - Existing building footprint

LAYER 4: PRECEDENT DATA (continuously updated)
  - Committee of Adjustment decisions
  - OLT/OMB decisions (from CanLII)
  - Council decisions on ZBAs and OPAs

LAYER 5: MARKET DATA (updated quarterly or monthly)
  - Appraisals, construction costs, cap rates

LAYER 6: CONTEXTUAL/GEOGRAPHIC DATA (updated periodically)
  - Transit routes, schools, parks, utilities, natural heritage
```

---

## Appendix F: Quality Assurance Framework
```
LEVEL 1: AUTOMATED CHECKS
- Factual Accuracy: Check zoning, references, math
- Completeness: All requirements/sections
- Consistency: Numbers match
- Format: Professional formatting

LEVEL 2: AI SELF-REVIEW
- No hallucinated policies/citations
- Professional tone, no legal advice, appropriate disclaimers

LEVEL 3: USER REVIEW PROMPTS
- Verify address, owner details, variances

LEVEL 4: PROFESSIONAL REVIEW DISCLAIMER
- Disclaimer reminding users to consult planners/lawyers.
```

---

## Appendix G: Glossary of Ontario Planning Terms
(See full documentation for comprehensive definitions: Angular Plane, As-of-Right, CBC, Committee of Adjustment, Conformity, Consent, Density, FSI, GFA, Holding Provision, MTSA, OLT, OPA, PPS, Prevailing, ROW, RPP, Section 37, Setback, Site Plan Control, Stepback, ZBA, Zone.)

---

## Appendix H: Sample Prompt Templates for AI Document Generation
Provides structured AI prompts for generating:
- Planning Rationale
- Four Tests Analysis
- Cover Letter
- OLT Appeal Strategy
- Precedent Report

---

## Appendix I: Regulatory Update Monitoring
Guidelines on watching e-Laws, ERO, Municipal agendas, and CanLII to keep the app current with ever-changing planning regulations in Ontario.

---

## Appendix J: Testing Protocol
Standard test cases for system validation: Simple Homeowner Addition, Laneway Suite, Multiplex Conversion, Mid-Rise Development, Lot Severance, Refused Application/Appeal, Heritage Property.

## Appendix K: Ethical and Legal Considerations
Ensuring the app avoids Unauthorized Practice of Law or Unauthorized Practice of Professional Planning by focusing on analysis and document generation, backed by strong disclaimers requiring user/professional verification.
