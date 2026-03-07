# Track 3-4 Research Handoff

> Research synthesis for `docs/DATA_PLAN.md` Track 3 and Track 4.
>
> Date: 2026-03-07

## Scope

- Track 3: Policy Text + Rule Extraction
- Track 4: Hard Constraint Overlays

This handoff combines:

- local repo and schema review
- `docs/DATA_PLAN.md`
- `docs/DATA_RESEARCH_TEAM_PLAN.md`
- `docs/IMPLEMENTATION_PLAN.md`
- current official Toronto and TRCA source validation

## Track 3: Policy Text + Rule Extraction

### Main conclusion

For the Toronto MVP, policy should be implemented as a **versioned citation graph**, not as free-form document search and not as an LLM-only interpretation layer.

The MVP should start with a **small authoritative subset**:

1. Zoning By-law 569-2013 text
2. amendments affecting the pilot geography
3. site-specific exceptions
4. intersecting secondary plans
5. only the Official Plan provisions needed for parcel-level interpretation

### Recommended authoritative sources

- Zoning By-law 569-2013
  - https://www.toronto.ca/city-government/planning-development/zoning-by-law-preliminary-zoning-reviews/zoning-by-law-569-2013-2/
- Official Plan
  - https://www.toronto.ca/city-government/planning-development/official-plan-guidelines/official-plan/
- Secondary Plans
  - https://www.toronto.ca/city-government/planning-development/official-plan-guidelines/official-plan/chapter-6-secondary-plans/
- Site & Area Specific Policies
  - https://www.toronto.ca/city-government/planning-development/official-plan-guidelines/official-plan/chapter-7-site-and-area-specific-policies/
- Official Plan Maps
  - https://www.toronto.ca/city-government/planning-development/official-plan-guidelines/official-plan/chapter-8-maps/
- Former Municipal Zoning By-laws
  - https://www.toronto.ca/city-government/planning-development/zoning-by-law-preliminary-zoning-reviews/former-municipal-zoning-by-laws/

### Expected source formats

- HTML pages
- text PDFs
- scanned PDFs
- schedules and map references
- standards tables
- clause cross-references

### MVP extraction strategy

1. Store each raw source immutably with file hash.
2. Parse into document -> section -> subsection -> clause -> table row.
3. Segment by headings and section-reference patterns, not token windows.
4. Run LLM extraction only on clause-sized chunks or normalized table rows.
5. Require strict JSON output for extracted rules.
6. Validate rules against schema before publish.
7. Build clause-to-clause references explicitly.
8. Publish only reviewed and versioned policy snapshots.

### Rule types to extract first

- permitted uses
- max height
- FAR / FSI
- front / rear / side setbacks
- lot coverage
- stepbacks
- lot frontage minimum
- lot area minimum

These are the best first set because they directly support parcel screening and first-pass envelope generation.

### Schema mapping

Primary mapping:

- `policy_documents`
- `policy_versions`
- `policy_clauses`
- `policy_references`
- `policy_applicability_rules`

Current model fit is strong in:

- separating raw text from normalized rule output
- modeling clause references
- storing applicability filters
- keeping review flags

Current gaps:

- richer source metadata
- explicit parse artifacts
- explicit review queue entities
- snapshot manifest across policy + parcel + overlays

### Main risks

- amendment timing and effective-date conflicts
- site-specific exceptions overriding base rules
- table extraction errors
- scanned or low-quality PDFs
- unresolved clause cross-references
- narrative policy language that is hard to normalize deterministically

### Recommendation

Do not try to ingest all Toronto planning policy at once. Build one strong, audited pipeline around zoning text, amendments, exceptions, and intersecting secondary plans first.

## Track 4: Hard Constraint Overlays

### Main conclusion

Track 4 should stay very narrow. For MVP, only ingest overlays that can directly invalidate or materially alter a scenario.

Recommended MVP overlay subset:

- heritage
- floodplain / conservation constraints
- ravine / natural feature protection

Transit, parks, roads, neighborhoods, and context layers should wait.

### Recommended authoritative sources

- Heritage Register
  - https://open.toronto.ca/dataset/heritage-register/
- Ravine and Natural Feature Protection
  - https://open.toronto.ca/dataset/ravine-and-natural-feature-protection/
- TRCA Flood Plain Map Viewer
  - https://trca.ca/conservation/flood-risk-management/flood-plain-map-viewer/
- City of Toronto GIS Services
  - https://gis.toronto.ca/arcgis/rest/services

Also relevant in the City GIS layer stack:

- Heritage District layer
- Natural Heritage System polygon layer
- Secondary Plan and SASP polygons where needed for geometry-linked policy applicability

### Legally material vs informational

Legally material:

- heritage
- floodplain / conservation
- ravine / natural feature protection

Informational only for MVP:

- transit
- roads / frontage context
- parks / amenities
- neighborhood boundaries
- 3D context layers

### Expected source formats

- SHP
- GeoJSON
- WMS / GIS service layers
- ArcGIS REST feature/map services

### MVP overlay pipeline

1. Acquire raw layer.
2. Validate CRS, geometry, and required attributes.
3. Load into generic overlay storage.
4. Spatially link features to parcels.
5. Materialize parcel-level flags and key percentages.
6. Publish overlay snapshot.

### Parcel-link strategy

Use precomputed parcel joins:

- `intersects`
- `contains`
- `within`

Materialize these parcel metrics first:

- `heritage_flag`
- `floodplain_flag`
- `ravine_flag`
- `floodplain_coverage_pct`
- `overlay_feature_count`

### Schema mapping

Primary mapping:

- `dataset_layers`
- `dataset_features`
- `feature_to_parcel_links`
- selected `parcel_metrics`
- `source_snapshots`
- `ingestion_jobs`

Important rule:

`dataset_features` is a good home for GIS overlays, but not for normalized policy rules.

### Main risks

- over-ingesting non-critical overlays too early
- weak dataset/source metadata
- geometry or CRS drift
- treating generic GIS storage as a dumping ground
- not versioning overlay refreshes separately from policy refreshes

### Recommendation

Keep Track 4 extremely tight. Ingest only heritage, floodplain, and ravine layers first, then precompute parcel joins and parcel flags.

## Engineering Implications

Track 3 needs:

- ingestion for policy documents
- clause segmentation pipeline
- JSON-schema validation for rule extraction
- review workflow for low-confidence policy clauses
- stronger source metadata around policy inputs

Track 4 needs:

- ingestion for overlay layers
- spatial validation
- feature-to-parcel join job
- parcel metric materialization
- a real implementation of `/parcels/{parcel_id}/overlays`

## Recommended Build Order Across These Tracks

1. Zoning by-law text ingestion
2. Policy clause normalization + citations
3. Site-specific exception handling
4. Heritage overlay ingestion
5. Ravine overlay ingestion
6. Floodplain overlay ingestion
7. Parcel policy stack resolution
8. Parcel overlay endpoint and parcel flags

## Repo References

- [DATA_PLAN.md](/Users/elliot18/Desktop/Hack_Canada/docs/DATA_PLAN.md)
- [DATA_RESEARCH_TEAM_PLAN.md](/Users/elliot18/Desktop/Hack_Canada/docs/DATA_RESEARCH_TEAM_PLAN.md)
- [IMPLEMENTATION_PLAN.md](/Users/elliot18/Desktop/Hack_Canada/docs/IMPLEMENTATION_PLAN.md)
- [PLAN.md](/Users/elliot18/Desktop/Hack_Canada/PLAN.md)
- [policy.py](/Users/elliot18/Desktop/Hack_Canada/app/models/policy.py)
- [dataset.py](/Users/elliot18/Desktop/Hack_Canada/app/models/dataset.py)
- [geospatial.py](/Users/elliot18/Desktop/Hack_Canada/app/models/geospatial.py)
- [ingestion.py](/Users/elliot18/Desktop/Hack_Canada/app/models/ingestion.py)
- [parcels.py](/Users/elliot18/Desktop/Hack_Canada/app/routers/parcels.py)
