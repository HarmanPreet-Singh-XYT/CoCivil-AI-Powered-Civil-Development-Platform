# Research Notes: Tracks 5 and 6

> Focused research notes for `docs/DATA_PLAN.md` research tracks 5 and 6: simulation defaults, and precedent/permit data.

## Track 5: Simulation Default Research

### Goal

Define the internal reference data the app needs so massing, layout, and finance can run deterministically even when external source data is incomplete.

### What the app already has

The repo already has the core containers for simulation defaults:

- `MassingTemplate` in `app/models/simulation.py`
- `UnitType` in `app/models/simulation.py`
- `FinancialAssumptionSet` in `app/models/finance.py`

The API and task surfaces that will consume these defaults already exist, but are still mostly untyped and stubbed:

- `app/routers/simulation.py`
- `app/routers/finance.py`
- `app/tasks/massing.py`
- `app/tasks/layout.py`
- `app/tasks/finance.py`
- `app/tasks/plan.py`

### What is missing

The app is missing the actual Toronto-ready default data and a stable constraint vocabulary.

Minimum missing default groups:

- massing typology defaults
- policy-to-geometry defaults
- unit library defaults
- layout constraint defaults
- finance assumption defaults

Minimum missing parameter families:

- floor-to-floor heights by use
- tower / mid-rise / townhouse typology assumptions
- core-loss and efficiency assumptions
- amenity ratios
- parking defaults
- accessibility defaults
- frontage and depth heuristics
- unit-mix targets
- rent / sale assumptions
- hard and soft costs
- vacancy, cap rate, financing, contingency assumptions

### Toronto sources that should inform defaults

These sources should inform the defaults, but the defaults should still be stored internally and versioned as simulation assumptions rather than source facts.

- Tall Buildings guidance:
  https://www.toronto.ca/city-government/planning-development/official-plan-guidelines/design-guidelines/tall-buildings/
- Mid-Rise Building Design Guidelines:
  https://www.toronto.ca/city-government/planning-development/official-plan-guidelines/design-guidelines/mid-rise-buildings/
- Townhouse & Low-Rise Apartment Guidelines:
  https://www.toronto.ca/city-government/planning-development/official-plan-guidelines/design-guidelines/townhouse-and-low-rise-apartments/
- Growing Up: Planning for Children in New Vertical Communities:
  https://www.toronto.ca/city-government/planning-development/planning-studies-initiatives/growing-up-planning-for-children-in-new-vertical-communities/
- Toronto Green Standard:
  https://www.toronto.ca/city-government/planning-development/official-plan-guidelines/toronto-green-standard/
- Zoning By-law 569-2013:
  https://www.toronto.ca/zoning/

### Recommended MVP seed set

For a Toronto MVP, the smallest useful seed set is:

1. Three to four `MassingTemplate` records.
   Example typologies: `tower_on_podium`, `midrise`, `townhouse`, `mixed_use_midrise`.

2. A Toronto `UnitType` library.
   Example types: studio, one-bed, two-bed, three-bed, plus accessible variants.

3. Typed geometry defaults by typology.
   Example: residential floor height, retail floor height, podium assumptions, core efficiency range, amenity ratio, parking ratio, frontage heuristics.

4. Two `FinancialAssumptionSet` records.
   Example: `toronto_rental_base` and `toronto_condo_base`.

### App connection

- `app/models/simulation.py` already stores templates, unit types, and layout runs.
- `app/models/finance.py` already stores assumption sets and financial runs.
- `app/schemas/simulation.py` and `app/schemas/finance.py` still take loose `dict` params, so defaults are not yet discoverable or validated at the API boundary.
- `app/tasks/massing.py`, `app/tasks/layout.py`, and `app/tasks/finance.py` need these defaults before they can become deterministic engines instead of placeholder tasks.

### Research conclusion

Track 5 is less about finding more public data and more about turning Toronto planning guidance into a versioned internal seed library that the app can execute against reproducibly.

## Track 6: Precedent and Permit Research

### Goal

Identify the best public Toronto precedent and permit sources, the key normalized fields they provide, and the minimum ingestion order needed to support precedent search and approval-risk analysis.

### What the app already has

The repo already models:

- `PrecedentSearch`
- `DevelopmentApplication`
- `ApplicationDocument`
- `RationaleExtract`

Relevant files:

- `app/models/entitlement.py`
- `app/routers/entitlement.py`
- `app/schemas/entitlement.py`
- `app/tasks/entitlement.py`
- `app/tasks/plan.py`
- `app/services/submission/generator.py`

### What is missing

The main gaps are:

- no dedicated permit model
- no typed precedent match / ranking table
- `PrecedentSearch.results_json` is still unstructured
- weak provenance fields on `DevelopmentApplication`
- no strong normalization for authority, stage, outcome, and document types
- no ingestion pipeline yet for application documents or rationale extraction

### Best current public Toronto sources

1. Application Information Centre.
   This is the strongest first source for active planning, Committee of Adjustment, and TLAB applications.
   https://www.toronto.ca/city-government/planning-development/application-information-centre/

2. Application Information Centre User Guide.
   This confirms AIC exposes application details, milestone status, related applications, and downloadable supporting documents when available.
   https://www.toronto.ca/city-government/planning-development/application-information-centre/application-information-centre-user-guide/

3. Committee of Adjustment application information.
   This confirms active CoA applications are public in AIC, but only about 90 days of final-and-binding decisions remain public there; older decisions are available through a paid research portal.
   https://www.toronto.ca/city-government/planning-development/committee-of-adjustment/more-information-about-application/

4. Building Permit Application & Inspection Status.
   This is the best current public permit-status surface and is updated as of the previous business day for active permits up to 10 years old.
   https://www.toronto.ca/services-payments/building-construction/search-the-status-of-a-building-permit-application/

5. City of Toronto Open Data blog on cleared permits.
   This is useful evidence that the City has published active and cleared permit datasets, even though the current operational public entry point is the permit-status tool.
   https://open.toronto.ca/exploring-cleared-building-permits/

6. Ontario Land Tribunal decisions and orders.
   This is a later-phase precedent text source for appealed or major decisions.
   https://olt.gov.on.ca/appeals-process/decisions-orders/

### Recommended MVP ingestion order

1. Application Information Centre metadata.
   Use this first for active development applications, milestone status, application type, application number, address, ward, and document links.

2. Committee of Adjustment metadata.
   Use this second because it adds variance/consent history, but public retention is limited and older records are not freely available.

3. Building permit status and permit datasets.
   Use this third for issued/active/closed permit context and basic downstream activity signal.

4. Supporting application documents from AIC.
   Use these fourth for text extraction, rationale retrieval, and richer precedent explanations.

5. OLT / tribunal decisions.
   Use these later for appealed cases and higher-value textual precedent evidence.

### Minimum normalized fields to capture first

For `DevelopmentApplication`:

- source system
- source URL
- app number / file number
- authority
- application type
- address
- parcel linkage or point geometry
- ward / district
- submitted date
- current stage
- decision
- decision date
- proposed height
- proposed units
- proposed FSI
- supporting document count

For permits:

- permit number
- permit type
- permit status
- application date
- issue date
- completion / closed date when available
- address
- geospatial link to parcel if possible

For documents:

- document type
- document URL
- download status
- extracted text status
- citation metadata

### App connection

- `app/models/entitlement.py` already has the core precedent tables but needs stronger normalization and provenance.
- `app/routers/entitlement.py` already creates precedent searches asynchronously.
- `app/tasks/entitlement.py` is the main place where spatial retrieval, ranking, and rationale extraction logic will land.
- `app/tasks/plan.py` and the submission generator already expect precedent context, so the data path is architecturally useful even before scoring is sophisticated.

### Research conclusion

Track 6 should start with public application metadata and permit status, not full-text precedent AI, because the app first needs a trustworthy, normalized precedent backbone before text similarity or approval scoring will be reliable.
