# Data Research Team Plan

> Research workstream split for the Toronto MVP, based on `docs/DATA_PLAN.md`.

## Goal

Prepare 5-6 parallel research tracks that validate the real data acquisition path for the MVP without duplicating work.

The team should answer:

- what the authoritative source is
- how to access it
- what format it comes in
- whether it is current, retired, or replaced
- what fields matter
- how it maps into the existing schema
- what quality and legal risks exist

## Recommended Team Split

Run **6 parallel research tracks**. This is the cleanest split with the least overlap.

### Team 1: Parcel + Address Base

Scope:

- property boundaries
- parcel identifiers
- address points / address linkage
- jurisdiction linkage

Research questions:

- What are the authoritative Toronto sources for parcel boundaries and address points?
- Are the datasets current, retired, or superseded?
- What identifiers exist: PIN, municipal address ID, roll number, internal IDs?
- Can address points be reliably linked to parcels?
- What geometry quality or CRS issues exist?

Expected outputs:

- source inventory with URLs
- format list
- update cadence
- key fields
- parcel-to-address linking strategy
- mapping into `jurisdictions`, `parcels`, and derived `parcel_metrics`

### Team 2: Zoning Geometry

Scope:

- zoning polygons
- zone codes
- map-based exceptions tied to zoning layers

Research questions:

- What is the authoritative zoning geometry source for Toronto MVP?
- Are there zone variants, amendments, or exceptions embedded in attributes?
- What parcel-to-zoning join strategy is required?
- Do we need one zone per parcel, or multi-zone support from day 1?

Expected outputs:

- zoning source inventory
- key attributes and geometry notes
- zone-code normalization notes
- parcel join strategy
- mapping into `dataset_layers`, `dataset_features`, and parcel-level zoning references

### Team 3: Policy Text + Rule Extraction

Scope:

- zoning by-law text
- official plan
- secondary plans
- amendments
- site-specific exceptions

Research questions:

- What policy sources are required for a defensible Toronto as-of-right result?
- In what format do they exist: HTML, PDF, scanned PDF, tables?
- What document structure exists: sections, clauses, schedules, tables, cross-references?
- Which sources are highest priority for first extraction?
- What fields must be captured for citation and reproducibility?

Expected outputs:

- prioritized source list
- document-format inventory
- clause segmentation strategy
- proposed rule types for MVP extraction
- mapping into `policy_documents`, `policy_versions`, `policy_clauses`, `policy_references`, `policy_applicability_rules`

### Team 4: Hard Constraint Overlays

Scope:

- heritage
- floodplain
- ravine / natural feature protection
- any other legally material Toronto overlay needed for MVP

Research questions:

- Which overlays can materially invalidate or alter a scenario?
- Which sources are authoritative versus informational only?
- What geometry format and parcel-link strategy are needed?
- Which overlay attributes should be materialized into parcel flags or metrics?

Expected outputs:

- overlay source inventory
- authority ranking for each overlay
- parcel-link method
- required MVP attributes
- mapping into `dataset_layers`, `dataset_features`, `feature_to_parcel_links`, and selected `parcel_metrics`

### Team 5: Development Applications + Precedents

Scope:

- development applications
- committee decisions
- tribunal decisions
- permit metadata
- staff reports and rationale documents where allowed

Research questions:

- What open Toronto sources exist for application and decision history?
- How complete are status, decision, and location fields?
- Can records be linked to parcels, addresses, or coordinates?
- Which documents are legally and operationally safe to ingest for MVP?
- What minimum precedent data supports useful approval-risk context?

Expected outputs:

- precedent source inventory
- key IDs and deduplication strategy
- location-linkage strategy
- document availability notes
- mapping into `development_applications`, `application_documents`, and `rationale_extracts`

### Team 6: Data Governance + Source Operations

Scope:

- source metadata
- licensing
- refresh cadence
- lineage
- snapshot design
- review workflow

Research questions:

- What metadata do we need to store for every source family?
- Which sources are open, restricted, retired, or unclear?
- What refresh frequency makes sense by source type?
- What does a usable snapshot manifest need to include?
- What review queue artifacts are needed for policy extraction and data QA?

Expected outputs:

- canonical metadata schema recommendation
- source licensing matrix
- refresh schedule proposal
- multi-snapshot manifest recommendation
- review workflow requirements
- gap list against current models

## Deliverable Format For Every Team

Each team should return the same structure:

1. Source list
2. Authority assessment
3. Access method
4. File/API format
5. Key fields
6. Refresh/update notes
7. Risks and blockers
8. Proposed schema mapping
9. MVP recommendation: use now, use later, or avoid

## Definition Of Done

A research track is complete when it gives enough detail that engineering can:

- fetch the source
- store the raw artifact
- map it to the schema
- define validation checks
- decide whether it is safe and useful for MVP

## Recommended Execution Order

Even if the teams run in parallel, engineering should consume them in this order:

1. Team 1: Parcel + Address Base
2. Team 2: Zoning Geometry
3. Team 3: Policy Text + Rule Extraction
4. Team 4: Hard Constraint Overlays
5. Team 5: Development Applications + Precedents
6. Team 6: Data Governance + Source Operations

## Notes

- Team 1, Team 2, and Team 3 are the critical path.
- Team 4 should stay limited to legally material overlays, not every GIS layer.
- Team 5 should focus on basic precedent metadata before full document ingestion.
- Team 6 should be treated as platform quality control, not optional paperwork.
