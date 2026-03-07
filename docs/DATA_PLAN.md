# Data Plan

> Reality-checked data plan for the Toronto MVP, focused on what the current repo can support, what the product actually needs first, and what should wait.

## 1. Purpose

This document narrows the broader implementation docs into a practical data plan:

- what data is truly required for a trustworthy MVP
- how each data family flows through the pipeline
- what should be treated as authoritative vs. enrichment
- where the current schema is strong
- where the current schema is still too thin for production-quality data work

This is intentionally more skeptical than the broader product plans. The goal is not to list every useful dataset. The goal is to identify the minimum set of data needed to produce defendable outputs.

## Priority Research Tracks

These are the eight things we need to research first for the Toronto MVP:

1. Parcel and address research.
   Confirm the best parcel boundary source, address linkage quality, identifiers, CRS handling, refresh cadence, and completeness.

2. Zoning geometry research.
   Confirm the authoritative zoning polygon source, zone code structure, exceptions, overlays, and parcel-to-zone edge cases.

3. Policy source and rule extraction research.
   Confirm which policy documents are authoritative, how amendments and effective dates work, and which rule types we normalize first.

4. Hard overlay research.
   Confirm which overlays are legally material for MVP, especially heritage, floodplain, and ravine constraints, and how they affect parcel eligibility or massing.

5. Simulation default research.
   Define the internal reference data the product needs to run even when source data is incomplete, including unit types, massing defaults, and policy-to-geometry assumptions.

6. Precedent and permit research.
   Confirm the best public development application and permit feeds, key fields, status normalization, parcel linkage, and document availability.

7. Provenance and governance research.
   Define the metadata, lineage, license, retention, and export-control rules we must store for every source to keep outputs reproducible and legally safe.

8. QA benchmark research.
   Build a hand-checked Toronto benchmark set for address -> parcel -> zoning -> policy stack -> scenario validation.

## 2. Challenge To The Current Assumptions

### 2.1 We do not need every Toronto dataset on day 1

The current docs list many potentially useful sources. That is directionally correct, but too broad for MVP execution.

For a working first pipeline, the true critical path is:

1. parcel geometry + address resolution
2. zoning geometry + policy text
3. policy applicability logic
4. a small set of hard constraint overlays
5. basic precedent metadata
6. internal simulation defaults

Without those, extra datasets add complexity without improving the core output.

### 2.2 Not all data is equal

We should classify data into four roles:

- `blocking_authority`: without it, we cannot produce a defensible answer
- `hard_constraint`: not the main policy source, but can invalidate a scenario
- `scoring_enrichment`: improves ranking, context, or confidence
- `licensed_optional`: valuable, but should not block MVP because of legal or operational risk

### 2.3 The current repo does not yet store all promised source metadata

The docs call for source metadata such as:

- publisher
- acquisition timestamp
- parser version
- extraction confidence
- lineage chain
- redistribution rules

The current models partially support this, but not fully across datasets. For example, `dataset_layers` currently stores only a subset of the needed metadata and is not yet enough for full lineage, legal controls, or reproducibility.

### 2.4 A single `source_snapshot_id` is probably too coarse

`scenario_runs.source_snapshot_id` is a good start, but one ID is unlikely to be enough once parcel, policy, overlay, precedent, and market data refresh independently.

For real reproducibility, we likely need a snapshot manifest or snapshot set per analysis, for example:

- parcel snapshot version
- policy snapshot version
- overlay snapshot version
- precedent snapshot version
- market snapshot version
- parser/model versions used

### 2.5 `dataset_features` should not become a dumping ground

`dataset_layers` and `dataset_features` are useful for generic GIS overlays. They should not become the storage pattern for every source.

Good fit:

- heritage polygons
- floodplain layers
- transit stops
- parks

Poor fit as the primary model:

- normalized policy rules
- development application metadata
- market comparables
- curated financial assumptions

Those deserve their own typed tables and quality rules.

## 3. Data Tiers

### Tier 0: Must-Have For A Defensible MVP

### 3.1 Parcel base data

Role: `blocking_authority`

Needed data:

- parcel boundaries
- parcel identifiers
- addresses or address linkage
- lot area, frontage, depth
- jurisdiction linkage

Why it matters:

- drives parcel lookup
- anchors every spatial join
- provides the base geometry for massing and rule application

Likely storage:

- `jurisdictions`
- `parcels`
- `parcel_metrics`
- `project_parcels`

### 3.2 Zoning geometry

Role: `blocking_authority`

Needed data:

- zoning polygons
- zone codes
- overlays or exceptions tied directly to zoning maps

Why it matters:

- connects the parcel to the correct rule family
- drives the first-pass policy applicability filter

Likely storage:

- geospatial layer in `dataset_layers` / `dataset_features`
- plus normalized references in policy applicability logic

### 3.3 Policy text and normalized policy rules

Role: `blocking_authority`

Needed data:

- zoning by-law text
- official plan
- secondary plans
- amendments and effective dates
- site-specific exceptions

Why it matters:

- zoning polygons alone are not enough
- the product promise depends on citations and normalized rules, not just a zone code

Likely storage:

- `policy_documents`
- `policy_versions`
- `policy_clauses`
- `policy_references`
- `policy_applicability_rules`

### 3.4 Hard constraint overlays

Role: `hard_constraint`

Needed data:

- heritage
- ravine / natural feature protection
- floodplain / conservation constraints
- other legally material overlays for Toronto MVP

Why it matters:

- these can invalidate or materially change a scenario even if zoning is otherwise permissive

Likely storage:

- `dataset_layers`
- `dataset_features`
- `feature_to_parcel_links`
- selected `parcel_metrics`

### 3.5 Internal simulation reference data

Role: `blocking_authority`

Needed data:

- unit types
- massing templates
- default policy-to-geometry assumptions
- default financial assumption sets

Why it matters:

- the simulation pipeline cannot run on external data alone
- some inputs must be curated internally before optimization is meaningful

Likely storage:

- `massing_templates`
- `unit_types`
- `financial_assumption_sets`

### Tier 1: High-Value Soon After Core

### 3.6 Development applications and permit metadata

Role: `scoring_enrichment`

Needed data:

- application number
- location
- status
- decision
- proposed height / units / FSI
- parcel linkage where possible

Why it matters:

- improves precedent search
- supports approval-risk reasoning
- provides market signal around nearby development intensity

Likely storage:

- `development_applications`
- `application_documents`
- `rationale_extracts`

### 3.7 Road, frontage, and transit context

Role: `scoring_enrichment`

Needed data:

- road centreline
- transit stops / routes
- street classification or frontage context

Why it matters:

- improves parcel context
- can affect built form assumptions and opportunity ranking

Likely storage:

- `dataset_layers`
- `dataset_features`
- derived `parcel_metrics`

### Tier 2: Useful But Not Core To First Release

### 3.8 Amenity and neighborhood context

Role: `scoring_enrichment`

Needed data:

- parks
- neighborhood boundaries
- wards
- schools / services

Why it matters:

- good for screening and reporting
- not required to generate the first defensible as-of-right result

### 3.9 3D existing massing

Role: `scoring_enrichment`

Why it matters:

- useful for later shadow/context analysis
- not required to launch the first deterministic pipeline

### Tier 3: Restricted Or High-Risk Data

### 3.10 Licensed market and comparable data

Role: `licensed_optional`

Examples:

- MLS / TRREB
- MPAC
- CoStar
- Altus
- private rent / sales feeds

Why it matters:

- highly valuable for finance
- high legal and operational risk
- should not block MVP

Requirement:

- no ingestion or export without explicit license review and downstream-use rules

## 4. How Each Data Family Enters The Pipeline

### 4.1 Parcel and address data flow

Input:

- parcel geometry files
- address point or address linkage files

Pipeline:

1. Acquire raw source files and compute immutable file hash.
2. Create ingestion job record.
3. Validate CRS, required columns, geometry type, and uniqueness of parcel identifiers.
4. Normalize into `parcels`.
5. Compute derived parcel metrics such as area, frontage, and depth.
6. Publish parcel snapshot.
7. Use in parcel search, project assembly, policy resolution, and massing.

Primary downstream consumers:

- parcel search API
- project parcel assembly
- policy applicability
- massing engine

### 4.2 Zoning geometry flow

Input:

- zoning polygon layers
- zone code mapping metadata

Pipeline:

1. Acquire raw geometry source.
2. Validate CRS, geometry validity, and non-null zone identifiers.
3. Normalize into dataset layer + features.
4. Spatially join parcels to zoning polygons.
5. Store parcel-level zoning references or metrics.
6. Publish zoning snapshot.
7. Use to seed policy stack resolution.

Primary downstream consumers:

- parcel detail
- policy stack resolver
- entitlement checks

### 4.3 Policy text and rule extraction flow

Input:

- zoning by-law text
- official plan documents
- secondary plans
- amendments
- site-specific policy documents

Pipeline:

1. Acquire raw documents and store immutable object keys and file hashes.
2. Create policy document record with effective dates and source metadata.
3. Parse into sections or clauses.
4. Normalize each clause into machine-readable rule structures.
5. Attach confidence scores and review flags.
6. Build clause-to-clause references and applicability rules.
7. Publish policy version.
8. Resolve parcel-specific policy stacks with citations.

Primary downstream consumers:

- policy search
- parcel policy stack API
- entitlement engine
- submission/report generation

Important note:

LLM extraction can help, but normalized rules must not be treated as authoritative until they pass deterministic validation or review.

### 4.4 Overlay data flow

Input:

- heritage
- floodplain
- ravine
- transit
- roads
- other GIS layers

Pipeline:

1. Acquire layer.
2. Validate geometry, CRS, and required attributes.
3. Load into `dataset_layers` and `dataset_features`.
4. Spatially link to parcels.
5. Materialize key parcel metrics or flags.
6. Publish overlay snapshot.
7. Use in policy resolution, hard constraint checks, and parcel scoring.

Primary downstream consumers:

- parcel overlays endpoint
- massing constraint builder
- opportunity screening

### 4.5 Development application and precedent flow

Input:

- application metadata feeds
- permit feeds
- committee or tribunal decisions
- staff reports and planning rationales

Pipeline:

1. Acquire structured application feed.
2. Deduplicate by jurisdiction + application number.
3. Normalize metadata into `development_applications`.
4. Link to parcels or coordinates.
5. Ingest associated documents when legally allowed.
6. Extract rationale snippets and embeddings.
7. Publish precedent snapshot.
8. Use in precedent search and approval-risk features.

Primary downstream consumers:

- precedent search
- entitlement scoring
- report generation

### 4.6 Market and finance data flow

Input:

- curated internal assumption sets
- open market data where allowed
- licensed comparables where allowed

Pipeline:

1. Separate open data from licensed data at ingest time.
2. Store legal restrictions with the source.
3. Normalize structured comparable fields.
4. Publish finance snapshot.
5. Use only approved data at the finance stage.
6. Enforce export restrictions when generating downstream artifacts.

Primary downstream consumers:

- financial runs
- sensitivity analysis
- export generation

## 5. Recommended Pipeline Architecture

For every source family, the pipeline should follow the same shape:

1. `register`
   Record source identity, publisher, URL, license status, and refresh policy.
2. `land_raw`
   Store immutable raw file or API payload plus file hash.
3. `validate_raw`
   Check schema completeness, geometry validity, CRS, duplicates, and required identifiers.
4. `normalize`
   Convert raw source into typed tables or controlled generic layers.
5. `quality_gate`
   Reject, quarantine, or route low-confidence or malformed records for review.
6. `publish_snapshot`
   Atomically mark a snapshot as active only after validation passes.
7. `precompute`
   Build parcel links, parcel metrics, search indexes, and embeddings.
8. `serve`
   Use only published snapshots for APIs and downstream scenario generation.
9. `trace`
   Record exactly which snapshot versions were used in every analysis.

## 6. MVP Build Order

This is the recommended order for implementation, not just documentation priority.

1. Parcel boundaries and address linkage
2. Zoning geometry
3. Zoning by-law text and normalized rules
4. Policy applicability resolution with citations
5. Hard constraint overlays: heritage, floodplain, ravine
6. Basic development applications feed
7. Internal unit types and financial assumption sets
8. Road and transit enrichment
9. Document-level precedent extraction
10. Licensed market data

## 7. Quality Gates By Data Family

### 7.1 Parcel data

- geometry must be valid
- identifiers must be unique within jurisdiction
- addresses must be non-null when the source promises them
- CRS must be normalized before publish

### 7.2 Zoning and overlays

- geometry validity
- non-null layer type and source metadata
- valid attribute presence for rule-driving fields
- parcel linkage counts should be monitored for suspicious drops

### 7.3 Policy data

- every parsed clause must have a section reference
- effective dates must be preserved
- normalized rules must pass schema validation
- low-confidence extractions must be reviewable

### 7.4 Precedent data

- application IDs must deduplicate cleanly
- status and decision vocabularies must be normalized
- coordinates or parcel linkage must be validated

### 7.5 Finance data

- legal status must be explicit
- export permissions must be explicit
- units, dates, and geography must be normalized

## 8. Schema Gaps To Address

These are the most important mismatches between the current repo and the desired data operating model.

1. Add richer source metadata.
   The current schema should be expanded to capture at least:
   - publisher
   - acquisition timestamp
   - parser version for non-policy extractors
   - extraction confidence
   - redistribution / export permissions
   - lineage chain
   - schema version
   Recommended MVP implementation:
   - expand `dataset_layers` with `publisher`, `acquired_at`, `source_schema_version`, `lineage_chain_json`, `redistribution_allowed`, `export_allowed`, `retention_policy`, and `source_metadata_json`
   - expand `policy_documents` with `publisher`, `acquired_at`, `lineage_chain_json`, `redistribution_allowed`, `export_allowed`, and `retention_policy`
   - expand `market_comparables` with `source_url`, `publisher`, `acquired_at`, `source_schema_version`, `lineage_chain_json`, `redistribution_allowed`, `export_allowed`, and `retention_policy`
   - expand `source_snapshots` or `ingestion_jobs` with `extractor_version`, `extraction_confidence`, and `validation_summary_json`
   Modeling guidance:
   - keep legal and export controls as typed columns
   - keep lineage and source-specific extras in JSON
   - do not duplicate parser/confidence fields on every row when a version-level field already exists

2. Add a snapshot manifest model.
   Current state:
   - scenarios point to one `source_snapshot_id`
   Recommended direction:
   - add an analysis input manifest or snapshot set table
   - allow one analysis to reference multiple published snapshots
   - record parser/model versions alongside data snapshot versions
   Recommended MVP implementation:
   - add `snapshot_manifests` with `jurisdiction_id`, `manifest_hash`, `parser_versions_json`, and `model_versions_json`
   - add `snapshot_manifest_items` with `manifest_id`, `source_snapshot_id`, `snapshot_role`, and `is_required`
   - add `scenario_runs.snapshot_manifest_id` while keeping `scenario_runs.source_snapshot_id` temporarily as a legacy field
   - treat `source_snapshots` as atomic published units and manifests as frozen analysis input sets composed from them
   Migration guidance:
   - backfill one manifest per existing scenario that has a legacy `source_snapshot_id`
   - create one manifest item for that legacy snapshot, mapping `snapshot_type` into a role where possible
   - switch readers and writers to prefer `snapshot_manifest_id`
   - remove legacy single-snapshot fields only after the code path no longer depends on them

3. Add raw and review artifacts.
   The docs mention concepts such as:
   - parse artifacts
   - review queue items
   - refresh schedules
   Those should become real models or explicit backlog items if we expect controlled ingestion and human review.

4. Add typed source controls for licensed data.
   Finance and precedent sources need more than `license_status = unknown/open/restricted`.
   We should also capture:
   - whether internal storage is allowed
   - whether derived values may be exported
   - whether user-visible outputs must be aggregated
   - expiration or retention rules

## 9. What We Should Not Do Yet

To keep quality high, we should avoid these traps early:

- ingesting many enrichment layers before policy resolution works
- treating `dataset_features` as the storage pattern for every source
- mixing authoritative rules with model-generated interpretations
- using private comparables before legal controls exist
- publishing scenario outputs as `completed` when upstream data is still stubbed

## 10. Near-Term Execution Recommendation

If we want the best quality with the least wasted effort, the immediate data focus should be:

1. Build one strong Toronto parcel + address ingestion path.
2. Build one strong zoning geometry ingestion path.
3. Build one strong policy text normalization path with citations.
4. Resolve parcel -> zoning -> policy stack deterministically.
5. Add only the hard overlay layers needed to invalidate or materially alter a scenario.
6. Add precedents after the core as-of-right pipeline is trustworthy.

That order gives us a reliable spine for every later data product.
