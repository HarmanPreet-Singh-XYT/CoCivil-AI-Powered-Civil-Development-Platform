# ApplicationAI Platform — Full Codebase Index

> **Auto-maintained**: This file is updated automatically after any file edit or creation. See `.claude/CLAUDE.md` for update rules.
> **Last updated**: 2026-03-08 (water pipeline DXF support: parser, auto-detect, 3D viewer, sample generator) | **PRD**: [`.claude/docs/PRD.md`](.claude/docs/PRD.md)

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Backend — app/](#backend--app)
   - [Entry Points](#entry-points)
   - [Database Models](#database-models)
   - [API Routes](#api-routes)
   - [Services](#services)
   - [Background Tasks](#background-tasks)
   - [Data & Policy References](#data--policy-references)
   - [Schemas](#schemas)
   - [Middleware & Dependencies](#middleware--dependencies)
   - [AI Provider Layer](#ai-provider-layer)
4. [Frontend — frontend-react/](#frontend--frontend-react)
   - [Entry & Root](#entry--root)
   - [Components](#components)
   - [Utilities](#utilities)
   - [Styling](#styling)
5. [Config & Infrastructure](#config--infrastructure)
   - [Docker & Environment](#docker--environment)
   - [Database Migrations](#database-migrations)
   - [Scripts](#scripts)
   - [Data Files](#data-files)
6. [.claude/ Skills Pipeline](#claude-skills-pipeline)
7. [Tests](#tests)
8. [Known Issues & Incomplete Features](#known-issues--incomplete-features)
9. [API Endpoint Reference](#api-endpoint-reference)

---

## Project Overview

**ApplicationAI** — Land-development due diligence platform for Toronto/Ontario. Generates planning submission packages (planning rationale, compliance matrix, precedent report, etc.) from plain-English development queries.

| Attribute | Value |
|-----------|-------|
| App Name | `applicationai` v0.1.0 |
| Backend | FastAPI + SQLAlchemy async + PostgreSQL + PostGIS |
| Background Tasks | threading (in-process) |
| Frontend | React 19 + Vite |
| AI | Claude (primary) or OpenAI (configurable via `AI_PROVIDER`) |
| Spatial | GeoAlchemy2, PostGIS, pyproj |
| Auth | JWT (backend) + Auth0 (frontend) |
| Storage | MinIO (S3-compatible) |

---

## Architecture

```
┌────────────────────────────────────────────────────────┐
│  Frontend (React 19 + Vite, port 5173)                 │
│  Auth0 → JWT → api.js → /api/v1/* (proxied to :8000)  │
└────────────────────────────────────────────────────────┘
                          │
┌────────────────────────────────────────────────────────┐
│  FastAPI Backend (port 8000)                           │
│  Routers → Services → SQLAlchemy (async)               │
│  Background threads for long-running work               │
└────────────────────────────────────────────────────────┘
         │                │               │
   PostgreSQL+PostGIS   Redis          MinIO (S3)
   (port 5432)         (port 6379)    (port 9000/9001)
```

**Pipeline flow** (plan generation):
```
User query → plans/generate → background thread → query_parsing →
parcel_lookup → policy_resolution → massing → layout →
finance → entitlement → precedent_search → document_generation
→ SubmissionDocument rows
```

---

## Backend — app/

### Entry Points

| File | Purpose |
|------|---------|
| `app/__init__.py` | Package version (0.1.0) |
| `app/main.py` | FastAPI init, router registration (incl. design_versions), CORS + RequestID middleware |
| `app/config.py` | Pydantic Settings: DB URLs, S3, JWT, AI provider config |
| `app/database.py` | Async/sync SQLAlchemy engine factories, session makers, Redis connection |
| `app/dependencies.py` | FastAPI DI: `get_db_session`, `get_current_user`, `get_optional_user`, `get_optional_idempotency_key` |

---

### Database Models

#### `app/models/base.py`
- `Base` — SQLAlchemy declarative base
- `UUIDPrimaryKey` — Mixin: UUID primary key with server default
- `TimestampMixin` — Mixin: `created_at` / `updated_at`
- `GovernanceMixin` — Mixin: license_status, redistribution_allowed, retention_policy, license_expires_at

#### `app/models/tenant.py`
| Model | Key Fields |
|-------|-----------|
| `Organization` | slug, settings (JSON) |
| `User` | email, password_hash, is_active |
| `WorkspaceMember` | org → user link, role (owner/editor/viewer) |
| `Project` | name, org, creator, asset_type (building/pipeline/bridge) |
| `ProjectShare` | per-user/project permissions |
| `ScenarioRun` | modeling run; input_hash for dedup; pipeline_status; snapshot_manifests |
| `AnalysisSnapshotManifest` | links scenario to 5 data snapshots (parcel/policy/overlay/precedent/market) |

#### `app/models/plan.py`
| Model | Key Fields |
|-------|-----------|
| `DevelopmentPlan` | State machine: `draft→parsing→parsed→needs_clarification→running→generating→completed/failed`; original_query, parsed_parameters, pipeline_progress JSON, summary JSON |
| `SubmissionDocument` | Doc type (planning_rationale, compliance_matrix, etc.); content; S3 object_key; review status; disclaimer |

#### `app/models/geospatial.py`
| Model | Key Fields |
|-------|-----------|
| `Jurisdiction` | City/region bbox geometry, timezone |
| `Parcel` | MultiPolygon geom, PIN, address, lot metrics |
| `ParcelMetric` | Computed metrics keyed by type |
| `ParcelAddress` | Multiple addresses; canonical flag; match method/confidence |
| `ParcelZoningAssignment` | Parcel → zone feature; overlap area; assignment method (spatial_contains/centroid_fallback/manual_review) |
| `ProjectParcel` | Links project to parcel with role (primary/context) |

#### `app/models/entitlement.py`
| Model | Key Fields |
|-------|-----------|
| `DevelopmentApplication` | app_number, status, decision, proposed_height/units/FSI, ward, decision_date; governance fields |
| `ApplicationDocument` | Supporting docs; extraction status; pgvector(384) embedding |
| `RationaleExtract` | Extracted text; confidence score; embedding |
| `BuildingPermit` | Permit records linked to applications/parcels |
| `PrecedentSearch` | Search params, status, result count |
| `PrecedentMatch` | rank, score, distance_m, matched_permit_count, score_breakdown JSON |

#### `app/models/dataset.py`
| Model | Key Fields |
|-------|-----------|
| `DatasetLayer` | Zoning/overlay layer; refresh_frequency; license |
| `DatasetFeature` | Individual geometry feature; attributes JSON |
| `FeatureToParcelLink` | Spatial relationship (intersects/contains) |

#### `app/models/ingestion.py`
| Model | Key Fields |
|-------|-----------|
| `SourceSnapshot` | Versioned snapshot; extractor_version; is_active |
| `IngestionJob` | job_type, status, records_processed, error_message, validation_summary |
| `SnapshotManifest` | Hash of parser + model versions; links multiple SourceSnapshots |
| `SnapshotManifestItem` | Role of each snapshot; is_required |
| `ParseArtifact` | Generated artifacts (GeoJSON, extracted text, compliance reports) |
| `ReviewQueueItem` | QA items flagged during ingestion |
| `RefreshSchedule` | Scheduled refresh cadence per source |

#### `app/models/simulation.py`
| Model | Key Fields |
|-------|-----------|
| `MassingTemplate` | Reusable building envelope template |
| `Massing` | GFA, GLA, storeys, height, lot_coverage, FSI, 2D envelope geom, compliance JSON |
| `UnitType` | Reference unit types (1BR, 2BR, accessible); area ranges |
| `LayoutRun` | Unit mix optimization; objective (max_revenue/units/affordable); result JSON |

#### `app/models/finance.py`
| Model | Key Fields |
|-------|-----------|
| `MarketComparable` | Sale price, rent/sqft, absorption rate; governance fields |
| `FinancialAssumptionSet` | Construction cost/sqft, cap rate, absorption rate; is_default; org-specific or global |
| `FinancialRun` | total_revenue, total_cost, NOI, valuation, residual_land_value, IRR% |

#### `app/models/policy.py`
| Model | Key Fields |
|-------|-----------|
| `PolicyDocument` | Source doc; source_url; file_hash; parse_status; lineage_json |
| `PolicyVersion` | clause_count; confidence; is_active |
| `PolicyClause` | section_ref, page_ref, raw_text, normalized_json, confidence; pgvector(384) embedding; review workflow |
| `PolicyReference` | Cross-references between clauses |
| `PolicyApplicabilityRule` | Zone/use/geometry filters |
| `PolicyReviewItem` | QA items for human review |

#### `app/models/export.py`
| Model | Key Fields |
|-------|-----------|
| `ExportJob` | governance_status (pending/approved/blocked); applied_controls_json; S3 object_key; signed_url; expiry |
| `AuditEvent` | All material actions: user, event_type, entity_id, payload, IP, timestamp |

#### `app/models/design_version.py`
| Model | Key Fields |
|-------|-----------|
| `DesignBranch` | project_id, organization_id, name, created_by; has many DesignVersions |
| `DesignVersion` | branch_id, parent_version_id, version_number, floor_plans (JSON), model_params (JSON), compliance_status, compliance_details, variance_items, blocking_issues, message, change_summary |

#### `app/models/infrastructure.py`
| Model | Key Fields |
|-------|-----------|
| `PipelineAsset` | jurisdiction_id, source_snapshot_id, asset_id, pipe_type (water_main/sanitary_sewer/storm_sewer/gas_line), material, diameter_mm, install_year, depth_m, slope_pct, geom (LineString 4326), attributes_json |
| `BridgeAsset` | jurisdiction_id, source_snapshot_id, asset_id, bridge_type (road_bridge/pedestrian_bridge/culvert/overpass), structure_type, span_m, deck_width_m, clearance_m, year_built, condition_rating, road_name, crossing_name, geom (Point 4326), geom_line (LineString 4326), attributes_json |

#### `app/models/upload.py`
| Model | Key Fields |
|-------|-----------|
| `UploadedDocument` | file metadata; extraction state; compliance findings; AI provider metadata; page_classifications; floor_plan_data (DXF/PDF vector geometry) |
| `DocumentPage` | Page-level extraction (text, analysis JSON); image dims; S3 object_key |

---

### API Routes

#### Authentication — `app/routers/auth.py`
| Method | Route | Purpose |
|--------|-------|---------|
| POST | `/api/v1/auth/register` | Create org + user + membership; return JWT |
| POST | `/api/v1/auth/login` | Authenticate; return JWT with organization_id claim |

#### Plans — `app/routers/plans.py`
| Method | Route | Purpose |
|--------|-------|---------|
| POST | `/api/v1/plans/generate` | Submit query → 202 + plan_id; queues `run_plan_generation` |
| GET | `/api/v1/plans` | List plans for org |
| GET | `/api/v1/plans/{plan_id}` | Fetch plan + documents |
| GET | `/api/v1/plans/{plan_id}/readiness` | Submission readiness checklist |
| POST | `/api/v1/plans/{plan_id}/clarify` | Resume pipeline with clarification answers |
| GET | `/api/v1/plans/{plan_id}/documents` | List documents |
| GET | `/api/v1/plans/{plan_id}/documents/{doc_id}` | Get single document |
| POST | `/api/v1/plans/{plan_id}/documents/{doc_id}/submit-review` | Mark for review |
| POST | `/api/v1/plans/{plan_id}/documents/{doc_id}/approve` | Approve |
| POST | `/api/v1/plans/{plan_id}/documents/{doc_id}/reject` | Reject |
| POST | `/api/v1/plans/{plan_id}/generate-document/{doc_type}` | Generate/regenerate single doc from completed plan |
| GET | `/api/v1/plans/{plan_id}/documents/{doc_id}/download` | Download doc as markdown/html/docx |
| POST | `/api/v1/plans/{plan_id}/export` | Export all docs as single DOCX |

#### Chat Assistant — `app/routers/assistant.py`
| Method | Route | Purpose |
|--------|-------|---------|
| POST | `/api/v1/assistant/chat` | Multi-turn chat; returns message + optional ProposedAction |
| POST | `/api/v1/assistant/parse-model` | Parse natural-language building description → ModelParseResponse (storeys, height_m, typology, setback_m, unit_width, tower_shape, warnings); zoning-aware clamping when zone_code provided |

#### Parcels — `app/routers/parcels.py`
| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/api/v1/parcels/search` | Full-text/bbox search |
| GET | `/api/v1/parcels/{parcel_id}` | Single parcel details |
| GET | `/api/v1/parcels/{parcel_id}/policy-stack` | Policy hierarchy for parcel |
| GET | `/api/v1/parcels/{parcel_id}/overlays` | GIS overlays (heritage, flood, etc.) |
| GET | `/api/v1/parcels/{parcel_id}/nearby-applications` | Spatial search for development applications within radius (default 2km) |
| GET | `/api/v1/parcels/{parcel_id}/zoning-analysis` | Full zoning analysis with standards, parking, amenity |
| GET | `/api/v1/parcels/{parcel_id}/financial-summary` | Quick pro forma estimate (rental + condo) with nearby market comps |

#### Projects — `app/routers/projects.py`
| Method | Route | Purpose |
|--------|-------|---------|
| POST | `/api/v1/projects` | Create project |
| GET | `/api/v1/projects` | List projects |
| GET | `/api/v1/projects/{id}` | Fetch project |
| PATCH | `/api/v1/projects/{id}` | Update name/description |
| POST | `/api/v1/projects/{id}/parcels` | Link parcel (role: primary/context) |
| DELETE | `/api/v1/projects/{id}/parcels/{parcel_id}` | Unlink parcel |

#### Scenarios — `app/routers/scenarios.py`
| Method | Route | Purpose |
|--------|-------|---------|
| POST | `/api/v1/projects/{id}/scenarios` | Create scenario; computes input_hash |
| GET | `/api/v1/scenarios/{id}` | Fetch scenario |
| GET | `/api/v1/scenarios/{id}/compare/{other_id}` | **TODO** — returns empty deltas |

#### Entitlement & Precedent — `app/routers/entitlement.py`
| Method | Route | Purpose |
|--------|-------|---------|
| POST | `/api/v1/scenarios/{id}/entitlement-runs` | Compliance check → 202; queues `run_entitlement_check` |
| GET | `/api/v1/entitlement-runs/{run_id}` | Fetch entitlement result |
| POST | `/api/v1/scenarios/{id}/precedent-searches` | Find similar applications → 202 |
| GET | `/api/v1/precedent-searches/{id}` | Fetch precedent results |

#### Simulation — `app/routers/simulation.py`
| Method | Route | Purpose |
|--------|-------|---------|
| POST | `/api/v1/scenarios/{id}/massings` | Create massing |
| GET | `/api/v1/massings/{id}` | Fetch massing result |
| GET | `/api/v1/reference/massing-templates` | List templates |
| GET | `/api/v1/reference/unit-types` | List unit types |
| POST | `/api/v1/massings/{id}/layout-runs` | Optimize unit mix |
| GET | `/api/v1/layout-runs/{id}` | Fetch layout result |

#### Finance — `app/routers/finance.py`
| Method | Route | Purpose |
|--------|-------|---------|
| POST | `/api/v1/scenarios/{id}/financial-runs` | Run pro forma |
| GET | `/api/v1/financial-runs/{run_id}` | Fetch financial result |
| GET | `/api/v1/reference/financial-assumption-sets` | List assumption sets |

#### Uploads — `app/routers/uploads.py`
| Method | Route | Purpose |
|--------|-------|---------|
| POST | `/api/v1/uploads` | Upload file → 202; queues `analyze_document` |
| GET | `/api/v1/uploads` | List uploads |
| GET | `/api/v1/uploads/{id}` | Fetch upload + status |
| GET | `/api/v1/uploads/{id}/pages` | Page images (presigned URLs) |
| GET | `/api/v1/uploads/{id}/analysis` | Extracted data + compliance findings |
| POST | `/api/v1/uploads/{id}/generate-plan` | Feed upload into plan pipeline |
| POST | `/api/v1/uploads/{id}/generate-response` | Generate response doc from findings |

#### Compliance — `app/routers/compliance.py`
| Method | Route | Purpose |
|--------|-------|---------|
| POST | `/api/v1/compliance/interior` | Run OBC interior compliance checks on a floor plan (deterministic, no auth required) |

#### Design Versions — `app/routers/design_versions.py`
| Method | Route | Purpose |
|--------|-------|---------|
| POST | `/api/v1/designs/{project_id}/branches` | Create design branch (optionally fork from existing version) |
| GET | `/api/v1/designs/{project_id}/branches` | List branches for project |
| DELETE | `/api/v1/designs/{project_id}/branches/{branch_id}` | Delete branch and all versions |
| POST | `/api/v1/designs/branches/{branch_id}/commit` | Commit new version with compliance check |
| GET | `/api/v1/designs/branches/{branch_id}/versions` | List versions on branch |
| GET | `/api/v1/designs/branches/{branch_id}/latest` | Get latest version on branch |
| GET | `/api/v1/designs/versions/{version_id}` | Get specific version |

#### Ingestion — `app/routers/ingestion.py`
| Method | Route | Purpose |
|--------|-------|---------|
| POST | `/api/v1/admin/ingest/building-permits` | Trigger permit ingestion from CKAN |
| POST | `/api/v1/admin/ingest/coa-applications` | Trigger COA app ingestion from CKAN |
| POST | `/api/v1/admin/ingest/water-mains` | Trigger water main ingestion from CKAN |
| POST | `/api/v1/admin/ingest/sanitary-sewers` | Trigger sanitary sewer ingestion from CKAN |
| POST | `/api/v1/admin/ingest/storm-sewers` | Trigger storm sewer ingestion from CKAN |
| POST | `/api/v1/admin/ingest/bridges` | Trigger bridge inventory ingestion |
| GET | `/api/v1/admin/ingest/status` | Counts + last job status |

#### Infrastructure — `app/routers/infrastructure.py`
| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/api/v1/infrastructure/pipelines/nearby` | Find pipeline assets within radius of lat/lng |
| GET | `/api/v1/infrastructure/bridges/nearby` | Find bridge assets within radius of lat/lng |
| POST | `/api/v1/infrastructure/compliance/pipeline` | Deterministic pipeline compliance check |
| POST | `/api/v1/infrastructure/compliance/bridge` | Deterministic bridge compliance check |

---

### Services

| File | Purpose |
|------|---------|
| `app/services/design_version_service.py` | Design version control: create/list/delete branches, commit versions with auto-compliance check against parcel zoning + OBC interior checks, change summary generation |
| `app/services/compliance_engine.py` | **Deterministic, no AI.** Rule-by-rule compliance matrix (lot coverage, FSI, height, setbacks, parking, amenity space). O.Reg 462/24 (45% lot coverage for ≤3 unit multiplex), Bill 185 (zero parking for ≤10 unit residential). Returns `ComplianceResult` with variances needed. |
| `app/services/infrastructure_compliance.py` | **Deterministic, no AI.** Pipeline compliance: min diameter, cover depth, slope (Manning's), velocity, manhole spacing, material suitability, water main separation. Bridge compliance: deck width, clearance, barrier height, span range, structural depth (L/D ratio), culvert cover. Reuses `ComplianceRule`/`ComplianceResult` from compliance_engine. |
| `app/services/infrastructure_ingestion.py` | CKAN ingestion for infrastructure: water mains, sanitary sewers, storm sewers (Toronto Open Data), bridge inventory (MTO/Ontario). Follows ckan_ingestion.py patterns. |
| `app/services/interior_compliance.py` | **Deterministic, no AI.** OBC Part 9 interior compliance: bedroom area/dimension/egress, hallway width, door width, ceiling height, fire travel, ventilation warnings, load-bearing wall detection, room enclosure check. Computes area from polygon fallback. Spatial opening-to-room linkage via wall geometry. Returns `InteriorComplianceResult` with `description` field per rule. |
| `app/services/zoning_service.py` | `ZoningAnalysis` builder; normalize zone codes; extract params from map labels |
| `app/services/zoning_parser.py` | Parse zone strings like `RD(f12.0; a370; d0.6)` into structured standards |
| `app/services/overlay_service.py` | Fetch GIS overlays (heritage, flood, TRCA, railway, etc.) for a parcel |
| `app/services/policy_stack.py` | Build policy hierarchy for parcel (PlanningAct→PPS→Greenbelt→OP→SASP→Zoning→SPC) |
| `app/services/precedent.py` | `score_precedent_match()` weighted scoring: distance(30%), type(15%), height(20%), units(10%), FSI(10%), decision(10%), permit_bonus(5%) |
| `app/services/geospatial.py` | Parcel search queries, resolve_active_parcel_by_address, list_active_snapshot_ids |
| `app/services/access_control.py` | Org ownership checks for all resource types |
| `app/services/idempotency.py` | Cache job responses by Idempotency-Key header (Redis) |
| `app/services/storage.py` | S3/MinIO: upload_file, generate_presigned_url, ensure_bucket_exists |
| `app/services/dxf_parser.py` | DXF floor plan parsing using ezdxf; extracts walls, rooms, doors/windows, columns, ceiling heights; now also exports `detect_dxf_type()` which scans layer names to classify a DXF as `"building"` or `"pipeline"` |
| `app/services/pipeline_dxf_parser.py` | **NEW** — Civil pipeline DXF parser; detects PIPE/WATER/SEWER/STORM/MAIN/MANHOLE/VALVE/HYDRANT layers; extracts `PipeSegment`, `ManholeNode`, `ValveNode`, `HydrantNode`, `FittingNode`; reads block attributes for diameter/material/depth/invert; outputs centred metre coordinates with summary stats |
| `app/services/document_processor.py` | PDF parsing, page extraction, OCR, DXF file classification, PDF vector geometry extraction |
| `app/services/document_analyzer.py` | AI-powered analysis: extract dims, unit mix, compliance issues from docs |
| `app/services/thin_slice_runtime.py` | `ensure_reference_data()` — seed massing templates, unit types, assumptions |
| `app/services/simulation_runtime.py` | Parametric massing envelope; unit mix layout optimization |
| `app/services/ckan_ingestion.py` | Toronto Open Data CKAN API client; download + parse permits & COA applications |
| `app/services/geospatial_ingestion.py` | Ingest GeoJSON datasets (parcels, zoning, overlays, dev applications) |
| `app/services/contractor_trades.py` | Pure function mapping doc types + massing typology → Google Places trade search terms (max 4) |
| `app/services/submission/templates.py` | `DOCUMENT_TEMPLATES`: 19 AI templates (system/user prompts + max_tokens) per doc type; embeds SAFETY_PREAMBLE + _GROUNDING_INSTRUCTION |
| `app/services/submission/context_builder.py` | Build context dict (parcel, policy, compliance, precedents, financials, approval pathway, due diligence flags, OLT grounds, PAC requirements) for doc generation |
| `app/services/submission/readiness.py` | `evaluate_submission_readiness()` — checklist scoring; `EXTENDED_ESSENTIAL_TYPES` for 27-doc plans (backward-compatible) |
| `app/services/submission/document_selector.py` | `select_documents_for_project()` — deterministic selection of which docs to generate based on compliance, massing, overlays, precedents; returns doc list + `SelectionReason` audit trail |
| `app/services/submission/review.py` | Doc review state machine: submit_for_review, approve_document, reject_document |
| `app/services/submission/generator.py` | Main doc generation orchestrator: `generate_document()` (AI), `generate_rule_based_document()` (5 deterministic renderers: as-of-right check, required studies, timeline/cost, building permit checklist, professional referral) |
| `app/services/governance.py` | Data governance checks |
| `app/services/validation.py` | Input validation helpers |
| `app/services/benchmarks.py` | Market comparison logic |

---

### Background Tasks

| File | Task | Purpose |
|------|------|---------|
| `app/tasks/plan.py` | `run_plan_generation` | Full plan pipeline: query_parsing → parcel_lookup → policy_resolution → massing → layout → finance → entitlement → precedent → doc_generation. 27 document types (12 AI, 5 rule-based, 10 core). Supports `generate_subset` for targeted doc generation. AI generation with stub fallback. |
| `app/tasks/entitlement.py` | `run_entitlement_check` | Compliance check; returns compliant/non_compliant/variances_needed + matrix |
| `app/tasks/entitlement.py` | `run_precedent_search` | Spatial + attribute search; scores matches via `precedent.py`; stores PrecedentMatch rows |
| `app/tasks/massing.py` | `run_massing` | Generate 3D envelope: height, storeys, GFA, lot_coverage, FSI, 2D geom |
| `app/tasks/layout.py` | `run_layout` | Optimize unit mix; outputs unit breakdown, total_units, total_area |
| `app/tasks/finance.py` | `run_financial_analysis` | Pro forma: revenue, costs, NOI, valuation, residual land value, IRR |
| `app/tasks/document_analysis.py` | `analyze_document` | DXF floor plan parsing, PDF page extraction + vector geometry, AI analysis; populate extracted_data, compliance_findings, floor_plan_data |
| `app/tasks/ingestion.py` | `ingest_building_permits_task` | Fetch + upsert permits from Toronto CKAN |
| `app/tasks/ingestion.py` | `ingest_coa_applications_task` | Fetch + upsert COA apps from CKAN |
| `app/tasks/infrastructure_ingestion.py` | `ingest_water_mains_task`, `ingest_sanitary_sewers_task`, `ingest_storm_sewers_task`, `ingest_bridges_task` | Infrastructure data ingestion from CKAN/MTO |
| `app/tasks/export.py` | Export task | Apply governance controls; generate signed URL |

---

### Data & Policy References

| File | Purpose |
|------|---------|
| `app/data/toronto_zoning.py` | `ZONE_STANDARDS` dict — hardcoded By-law 569-2013 standards: R, RM, RA, CR, CL, DL, IH, IO, IE, IL. Each zone: permitted_uses, max_height, max_storeys, setbacks, lot_coverage, FSI, bylaw_section. Also: `AMENITY_SPACE`, `BICYCLE_PARKING` requirements. **Deterministic, no AI.** |
| `app/data/ontario_policy.py` | `ONTARIO_POLICY_HIERARCHY`, `TORONTO_OP_DESIGNATIONS`, `TORONTO_ZONING_KEY_RULES`, `MINOR_VARIANCE_FOUR_TESTS`, `OREG_462_24`, `RECENT_LEGISLATION` (Bills 23/97/109/185/60). Embedded in AI system prompts as grounding context. |
| `app/data/obc_interior_standards.py` | `OBC_INTERIOR_RULES` dict — OBC Part 9 interior standards: bedroom area/dimension, egress window, hallway width, door width, ceiling height, fire travel, fire access. `OBC_SECTIONS` section references. `OBC_DESCRIPTIONS` human-readable policy descriptions. **Deterministic, no AI.** |
| `app/data/civil_standards.py` | `PIPE_MATERIALS`, `PIPE_TYPE_STANDARDS`, `SANITARY_MIN_SLOPE`, `MANHOLE_STANDARDS`, `BRIDGE_TYPE_STANDARDS`, `BRIDGE_STRUCTURE_TYPES`, `CL_625_LOADING` — hardcoded OPSD/OPSS/CSA S6/MTO civil infrastructure standards. **Deterministic, no AI.** |
| `app/data/infrastructure_policy.py` | `ONTARIO_INFRASTRUCTURE_HIERARCHY`, `INFRASTRUCTURE_APPROVAL_PROCESS` — policy constants for AI grounding on infrastructure projects (OWRA, EPA, Safe Drinking Water Act, TSSA, CSA S6). |

---

### Schemas

| File | Key Schemas |
|------|------------|
| `app/schemas/auth.py` | LoginRequest, RegisterRequest, TokenResponse, UserInfo |
| `app/schemas/plan.py` | PlanGenerateRequest (generate_subset), PlanGenerateDocumentRequest (extra_context), PlanResponse, PlanListResponse, SubmissionDocumentResponse, PlanSubmissionReadinessResponse, ContractorResult, ContractorRecommendationsResponse |
| `app/schemas/assistant.py` | AssistantChatRequest, AssistantChatResponse, ProposedAction (doc_types), ModelParseRequest (zone_code, lot_area_m2), ModelParseResponse (unit_width, tower_shape, warnings), InfraModelParseRequest, InfraModelParseResponse, InfraModelUpdate |
| `app/schemas/infrastructure.py` | PipelineComplianceRequest, BridgeComplianceRequest, PipelineAssetResponse, BridgeAssetResponse — Pydantic schemas for infrastructure endpoints |
| `app/schemas/geospatial.py` | ParcelResponse, ParcelDetailResponse, ParcelSearchParams, PolicyStackResponse, ParcelOverlaysResponse |
| `app/schemas/entitlement.py` | EntitlementRunRequest/Response, PrecedentSearchRequest/Response |
| `app/schemas/simulation.py` | MassingRequest/Response, LayoutRunRequest/Response, UnitTypeReferenceResponse |
| `app/schemas/finance.py` | FinancialRunRequest/Response, FinancialAssumptionSetReferenceResponse |
| `app/schemas/design_version.py` | BranchCreate, BranchResponse, CommitRequest, VersionResponse |
| `app/schemas/upload.py` | UploadResponse, UploadDetail (+ page_classifications, floor_plan_data), UploadListItem, PageDetail |
| `app/schemas/tenant.py` | ProjectCreate/Response, ScenarioCreate/Response, AddParcelRequest |
| `app/schemas/common.py` | JobAccepted, ErrorResponse |

---

### Middleware & Dependencies

| File | Purpose |
|------|---------|
| `app/middleware/request_id.py` | Attaches unique X-Request-ID to every request |
| `app/dependencies.py` | `get_db_session()`, `get_current_user()` (JWT decode + org lookup), `get_optional_user()`, `get_optional_idempotency_key()` |

---

### AI Provider Layer

| File | Purpose |
|------|---------|
| `app/ai/base.py` | `AIProvider` abstract interface: `generate()`, `generate_structured()`, `embed()` |
| `app/ai/factory.py` | `get_ai_provider()` — loads Claude or OpenAI based on `AI_PROVIDER` env var |
| `app/ai/claude_provider.py` | Claude implementation: calls `/v1/messages`; strips markdown fences for structured; embeddings raise NotImplementedError |
| `app/ai/openai_provider.py` | OpenAI stub implementation |
| `app/ai/query_parser.py` | Parse natural language query into structured development parameters |

---

## Frontend — frontend-react/

### Entry & Root

| File | Purpose |
|------|---------|
| `src/main.jsx` | React 19 mount; Auth0Provider with hardcoded domain/clientId; localstorage token cache |
| `src/App.jsx` | Root orchestrator; routing via `currentPage` state ('landing'/'dashboard'); auth gate; multi-component layout; floorPlans + pipelineData + projectId state; `handleUploadAnalyzed` routes pipeline DXF uploads to InfrastructureViewer and building DXFs to ModelViewer; assetType state ('building'/'pipeline'/'bridge') for conditional viewer rendering |
| `src/api.js` | HTTP wrapper; base `/api/v1`; reads `localStorage['token']` for Bearer auth; all backend endpoints including design version control, getNearbyApplications, generatePlan (with generateSubset), regeneratePlanDocument, downloadPlanDocument, exportPlan; infrastructure endpoints: getNearbyPipelines, getNearbyBridges, checkPipelineCompliance, checkBridgeCompliance, parseInfraModel, triggerWaterMainIngestion, triggerSanitarySewerIngestion, triggerStormSewerIngestion, triggerBridgeIngestion |

**App.jsx key state:**
```
currentPage, selectedParcel, isPanelOpen, isSidebarCollapsed,
activeNav, savedParcels, showHistory, searchHistory (localStorage per user),
assetType ('building' | 'pipeline' | 'bridge')
```

---

### Components

| File | Purpose | Key Features |
|------|---------|--------------|
| `src/components/MapView.jsx` | MapLibre GL map; Toronto center | Imperative handle API: `flyTo()`, `setMarker()`, `setParcel()`, `setProposedMassing()`. Layers: osm-buildings-3d, parcel-fill, parcel-line, proposed-massing-extrusion (3D). Pitch 60° when massing shown. Shows "Model" button when parcel resolved. |
| `src/components/ModelViewer.jsx` | Full-screen 3D building model modal | Three.js/R3F Canvas; OrbitControls; typology-dispatched floor-plate geometry (midrise, tower_on_podium, point_tower, townhouse, slab, mixed_use_midrise); floor gaps between slabs; architectural detail layer (window strips, balcony slabs+railings, ground-floor storefronts+canopies, roof parapet caps, floor edge lines); zoning warning display in info bar. View modes (massing/interior/blueprint/floorplan), floor selector, room info panel, version control bar (branch selector, commit/discard, history panel). Floorplan mode renders FloorPlanEditor (2D Konva). Lazy-loaded. |
| `src/components/FloorPlanView.jsx` | 3D interior floor plan renderer | R3F component; renders rooms as extruded polygons with type-based colors (imported from floorPlanHelpers), walls as boxes; floor slab per level; click-to-select rooms with gold emissive highlight; per-floor Y spacing. |
| `src/components/floorplan/FloorPlanEditor.jsx` | 2D Konva-based floor plan editor container | Pan/zoom Stage, minimal toolbar (select/wall/door/window/delete), undo/redo (Ctrl+Z), debounced compliance API calls, wall center drag (move entire walls), delete tool (press X), collapsible compliance panel (press C), imports real layer components (WallLayer/RoomLayer/OpeningLayer/DimensionLayer) plus ComplianceBadgeLayer. |
| `src/components/floorplan/FloorPlanEditor.css` | Floor plan editor styles | Flex layout, toolbar (48px left), canvas (center), compliance panel (320px right), scale calibration modal. Uses design system CSS vars. |
| `src/components/floorplan/layers/WallLayer.jsx` | Konva wall rendering layer | Renders walls as Rects with rotation; exterior (8px, #333) / interior (4px, #555); load-bearing dashed/dotted; selected gold stroke; click-to-select; hover visual feedback; center circle drag handle (move entire wall), endpoint circles (adjust wall length/angle). |
| `src/components/floorplan/layers/RoomLayer.jsx` | Konva room rendering layer | Renders rooms as closed Line polygons with semi-transparent ROOM_COLORS fill; centroid text labels (name + area in m2/sqft); selected gold stroke. |
| `src/components/floorplan/layers/OpeningLayer.jsx` | Konva opening rendering layer | Renders doors (Arc swing + Line leaf) and windows (parallel Lines); positioned on parent wall via wall_id + offset; click-to-select. |
| `src/components/floorplan/layers/DimensionLayer.jsx` | Konva dimension annotation layer | Auto-generated wall dimension annotations: extension lines, dimension line with arrowheads, length labels in metres; font adjusts with zoom; muted #78716c color. |
| `src/components/floorplan/layers/ComplianceBadgeLayer.jsx` | Konva compliance badge layer | Circle badges at element centroids: red (error), yellow (warning), green (pass); badge count for multiple violations; click-to-highlight in CompliancePanel. |
| `src/components/floorplan/panels/CompliancePanel.jsx` | OBC compliance sidebar | Right-side panel listing all OBC rule check results; grouped by element with expandable detail (OBC section, required vs actual); click rule to highlight element on canvas. |
| `src/components/floorplan/panels/EditorToolbar.jsx` | Editor tool palette | Compact vertical toolbar with SVG icons: Select (V), Wall (W), Door (D), Window (O), Delete (X); undo/redo buttons (Ctrl+Z/Ctrl+Y); active tool highlighted with gold accent. |
| `src/components/floorplan/panels/ScaleCalibration.jsx` | Scale calibration modal | Manual metres_per_unit input or two-point calibration; skip option defaults to 1.0 scale; shown before editing if uncalibrated. |
| `src/components/floorplan/panels/RoomTypeSelector.jsx` | Room type popover | Grid of room type buttons with ROOM_COLORS swatches; click to change room type and trigger compliance re-check. |
| `src/components/floorplan/panels/WallProperties.jsx` | Wall inspector panel | Load-bearing toggle (Unknown/Yes/No), wall type (Interior/Exterior), thickness slider, delete with load-bearing safety check. |
| `src/components/BlueprintOverlay.jsx` | Blueprint image overlay | R3F component; loads blueprint page images as textured planes at floor Y offsets; supports per-floor or all-floors display. |
| `src/components/SearchBar.jsx` | Address search + geocoding | 350ms debounce; Nominatim OSM API scoped to Toronto; 6 suggestions max; Enter/Escape keyboard support |
| `src/components/Sidebar.jsx` | Left nav panel | Asset type selector (Buildings/Pipelines/Bridges) at top. Dynamic nav items per asset type: Building (Overview/Finances/Policies/Datasets/Precedents), Pipeline (Overview/Standards/Network/Datasets/Inspections), Bridge (Overview/Standards/Load Analysis/Datasets/Condition). History panel. Collapsed/expanded state. Resizable via `useResizable` hook. |
| `src/components/PolicyPanel.jsx` | Right-side multi-tab panel | Building tabs: Overview (zoning summary + file upload zone), Policies (accordion), Datasets (overlays), Precedents (live nearby applications with distance/decision), Finances (pro forma estimates, assessed value, market comps with tenure toggle), Documents (gallery with grouped list, preview, regenerate). Infrastructure tabs: Standards (CSA/OPSD/ECA standards by asset type), Network (pipeline network overview), Inspections (CCTV/maintenance records), Load Analysis (CSA S6 bridge loading), Condition (OSIM bridge condition assessment). Resizable via `useResizable` hook. |
| `src/components/DocumentGallery.jsx` | Document gallery with sidebar + viewer | Grouped doc list (5 categories: Core Submission, Variance & Compliance, Pathway & Process, Appeals & Responses, Community & Readiness). Status dots. Export All button. |
| `src/components/DocumentViewer.jsx` | Markdown document viewer | ReactMarkdown rendering, safety preamble banner, download (md/html/docx), regenerate button, review status workflow (submit/approve/reject). |
| `src/components/ContractorCards.jsx` | Horizontal scrollable row of gold-accent contractor recommendation cards (name, rating, phone, website, trade badge) |
| `src/components/ChatPanel.jsx` | AI assistant + file upload; chat with `/assistant/chat`; plan polling; smart doc routing; file upload + drag-and-drop; upload polling (40 attempts × 3s); **pipeline DXF path**: when analyzed upload has `pipeline_network`, shows pipe count/total length/manhole count instead of building fields; infrastructure command handling |
| `src/components/LandingPage.jsx` | Marketing homepage | Auth0 login/logout. Typewriter effect (10 dev queries, 45ms/char). MapLibre preview. Hero → Story → Vision → Footer. |
| `src/components/UserBubble.jsx` | Animated user bubble (bottom-right) | Hover expand (44px→260px, 0.45s). Breathing pulse. User avatar + online dot + sign out. |
| `src/components/InfrastructureLayerControl.jsx` | Infrastructure data layer toggle panel | Toggleable panel with categorized checkboxes for Roads (reconstruction), Water System (watermains, hydrants, valves, fittings, drinking sources, distribution), and EV Charging layers. Lazy-loads GeoJSON on first toggle, caches data, manages MapLibre sources/layers. Popups on point features. |
| `src/components/LoginPage.jsx` | Legacy login form | **Unused** — replaced by Auth0. Still in codebase. |
| `src/components/InfrastructureViewer.jsx` | Full-screen 3D infrastructure viewer; R3F Canvas for pipeline/bridge 3D visualization; view modes: model_3d, plan, profile, cross_section; edit mode; version control bar; **now also handles uploaded `pipelineData` prop**: renders DXF pipe networks with click-to-edit panel for diameter/material/pipe_type/depth and per-manhole depth/elevation editing, stats bar showing total length and segment counts by type |
| `src/components/infrastructure/PipeNetworkEditor.jsx` | 2D Konva pipe network editor | Tools: select, pipe_run, manhole, fitting, delete, measure. Grid snap + endpoint snap. Auto-manhole placement (OPSD 120m max spacing). Per-segment properties. Flow direction arrows. Undo/redo (50 snapshots). Keyboard shortcuts: V/P/M/F/X. Debounced compliance check. |
| `src/components/infrastructure/BridgeEditor.jsx` | 2D Konva bridge component editor | Tools: select, deck, girder, abutment, pier, barrier, delete, measure. Component placement by click. Property editing via BridgeProperties panel. Undo/redo (50 snapshots). |
| `src/components/infrastructure/PipeProperties.jsx` | Pipe segment property panel | Edit pipe type, diameter, material, slope, invert elevation for selected segment |
| `src/components/infrastructure/BridgeProperties.jsx` | Bridge component property panel | Edit properties by component type: deck (width/depth), girder (type/depth), pier (height/width), barrier (type) |
| `src/components/infrastructure/InfrastructureCompliancePanel.jsx` | Infrastructure compliance results display | Shows pass/warning/fail rules with status dots and detail text |
| `src/components/infrastructure/ProfileView.jsx` | Longitudinal profile for pipe networks | Canvas-rendered chainage vs elevation profile with grid, legends, and pipe-type coloring |
| `src/components/infrastructure/CrossSectionView.jsx` | Transverse cross-section for bridges | Canvas-rendered bridge cross section with deck, girders, barriers, pier, and dimension annotations. Station slider. |
| `src/components/infrastructure/InfrastructureCatalog.jsx` | Drag-and-drop component catalog | Draggable pipe types, fittings, and bridge components organized by section |

---

### Hooks

| File | Purpose |
|------|---------|
| `src/hooks/useResizable.js` | Reusable panel-resize hook: drag handles for any edge, CSS variable sync, transition suppression during drag. Used by Sidebar, PolicyPanel, ChatPanel |

### Utilities

| File | Purpose |
|------|---------|
| `src/lib/parcelState.js` | Parcel shape builders: `buildParcelState()`, `isResolvedParcel()`, `isUnresolvedParcel()`, `formatParcelContext()`, `normalizeZoneCode()` (extracts leading alpha prefix e.g. `"CR 4.0..."` → `"CR"`) |
| `src/lib/chatCommands.js` | Regex command parser: `PLAN_FROM_UPLOAD_RE`, `RESPONSE_FROM_UPLOAD_RE`, `PLAN_RE`, `EDIT_FLOOR_RE`, `MODEL_RE`, `FLOOR_RE`, `VIEW_MODE_RE`, `COMMIT_RE`, `BRANCH_RE`, `HISTORY_RE`, `INFRA_MODEL_RE`, `BRIDGE_MODEL_RE` → `{type, query/floor/mode/message/name/diameter_mm/infraType/crossing}` |
| `src/lib/floorPlanHelpers.js` | Shared constants (ROOM_COLORS) and utilities (generateId, computeCentroid, ensureIds) for floor plan editing |
| `src/lib/wallGeometry.js` | Wall/room geometry utilities: snap-to-grid, wall-to-rect, shoelace area, point-in-polygon, room polygon updates |
| `src/lib/buildingGeometry.js` | GeoJSON polygon → local metres; polygon shrink; `extractFootprint()`; `makeCircularFootprint()` for point towers; `subdivideFootprintIntoUnits()` for townhouse rows |
| `src/lib/infrastructureGeometry.js` | Infrastructure geometry: `alignmentToLocal()` (geo/metric coords to local offsets), `generatePipeSegment()` (CylinderGeometry between points), `generateManhole()` (vertical shaft), `generateFitting()` (elbow/tee/reducer) |
| `src/lib/bridgeGeometry.js` | Bridge geometry: `generateBridgeDeck()` (BoxGeometry), `generateGirder()` (I-beam/box ExtrudeGeometry), `generateAbutment()`, `generatePier()`, `generateBarrier()` |
| `src/lib/parcelState.test.js` | Node native test runner unit tests for parcelState |
| `src/lib/chatCommands.test.js` | Unit tests for chatCommands |

---

### Styling

| File | Purpose |
|------|---------|
| `src/ModelViewer.css` | 3D model modal styles: dark overlay, header, canvas, controls bar, "Model" map button, version control bar, view mode toggle, floor selector, room info panel, commit modal, history panel |
| `src/InfrastructureViewer.css` | Infrastructure viewer styles: overlay, canvas area, controls row, view toggle, edit toggle, profile/cross-section views, compliance panel, properties panels, component catalog |
| `src/components/infrastructure/PipeNetworkEditor.css` | Pipe editor styles: toolbar (left), canvas (center), tool buttons, flow arrows, undo/redo group |
| `src/index.css` | 52KB global design system: dark theme, gold accent (#c8a55c), Inter font, sidebar/panel/chat/searchbar/button styles. Layout states via body classes: `.sidebar-collapsed`, `.panel-open`, `.lp-active` |
| `src/landing.css` | 554 lines marketing page styles: navbar, hero, typewriter, map preview, address bar, sections, footer |
| `src/UserBubble.css` | Bubble animations: width expansion, pulse breathing, content reveal |

**Design tokens:**
- Colors: `#1a1a1a` (dark bg), `#242424` (secondary), `#c8a55c` (gold), `#f0ece4` (text)
- Sidebar: 160px (52px collapsed), Panel: 380px

---

## Config & Infrastructure

### Docker & Environment

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Services: db (PostGIS 16), redis (7), minio, api (port 8000). Volumes: pgdata, minio_data. Health checks on all services. |
| `Dockerfile` | Python 3.11-slim; geospatial libs (libgdal, libgeos, libproj, gcc); uvicorn port 8000 |
| `railway.toml` | Railway deploy config for the API service: Dockerfile, start command (alembic upgrade + uvicorn), healthcheck /api/v1/health |
| `.railwayignore` | Files excluded from Railway builds: data/, *.dump, *.sql, .env, frontend/node_modules, dist |
| `.gitignore` | Git exclusions for local caches, node_modules, oversized Toronto GIS source extracts, and generated UI captures |
| `.env.example` | Template: DATABASE_URL, REDIS_URL, MINIO settings, JWT_SECRET, AI_PROVIDER, ANTHROPIC_API_KEY |
| `.env` | Live localhost config; **contains real API key** |
| `pyproject.toml` | Project: `arterial` v0.1.0, Python ≥3.11. Deps: FastAPI, SQLAlchemy, asyncpg, GeoAlchemy2, pgvector, Redis, Pydantic, ezdxf, python-docx, markdown. Dev: pytest, ruff. |
| `alembic.ini` | Alembic migration config; script location `./alembic`; logging |
| `scripts/init-extensions.sql` | PostgreSQL init: uuid-ossp, postgis, vector extensions |

---

### Database Migrations

| File | Purpose |
|------|---------|
| `alembic/env.py` | Alembic env config; loads SQLAlchemy URL from settings; offline/online modes |
| `alembic/versions/001_initial_schema.py` | Initial schema (48KB) |
| `alembic/versions/002_full_schema_evolution.py` | Full schema evolution (45KB) |
| `alembic/versions/003_add_uploaded_documents.py` | Adds UploadedDocument + DocumentPage tables (3KB) |
| `alembic/versions/004_add_policy_versions_created_at.py` | Adds created_at to policy_versions |
| `alembic/versions/005_add_design_versions.py` | Adds design_branches + design_versions tables; floor plan columns on uploaded_documents |
| `alembic/versions/006_add_infrastructure_assets.py` | Adds pipeline_assets + bridge_assets tables (PostGIS geometry); adds asset_type column to projects |

---

### Scripts

| File | Purpose |
|------|---------|
| `scripts/seed_policies.py` | Seeds 10 zoning + 6 OP policy clauses via raw SQL |
| `scripts/seed_reference_data.py` | Calls `ensure_reference_data()` to seed templates/unit-types/assumptions |
| `scripts/seed_toronto.py` | Bulk ingests 5 Toronto Open Data datasets: parcels, zoning, height overlay, setback overlay, dev applications |
| `scripts/ingest_toronto_tracks_1_2.py` | CLI for individual dataset ingestion: `parcel-base`, `address-linkage`, `zoning-geometry`, `dev-applications`, `overlay` |
| `scripts/generate_sample_dxf.py` | Generates a rich 6-storey mixed-use sample DXF with structural/partition/exterior wall layers, door/window blocks with sill/head height attributes, ceiling height annotations, balcony polygons, structural columns; outputs `sample_building.dxf` |
| `scripts/generate_sample_pipeline_dxf.py` | **NEW** — Generates a sample water main DXF (`sample_pipeline.dxf`) with 10 pipe segments, 6 manholes (MANHOLE blocks with ID/DEPTH/RIM/INVERT attribs), 3 gate valves, 2 fire hydrants on standard civil layers (WATER-MAIN, WATER-MH, WATER-VALVE, WATER-HYDRANT) |

---

### Data Files

| File | Size | Purpose |
|------|------|---------|
| `data/development-applications.json` | 26.6 MB | Toronto development applications (Toronto Open Data) |
| `data/property-boundaries-4326.geojson` | 498 MB | Toronto parcel boundaries (WGS84) |
| `data/zoning-area-4326.geojson` | 51.5 MB | Toronto zoning area polygons |
| `data/zoning-height-overlay-4326.geojson` | 16.5 MB | Height overlay restrictions |
| `data/zoning-building-setback-overlay-4326.geojson` | 317 KB | Setback overlay restrictions |

---

## RAG System — fine-tuned-RAG/

ChromaDB-backed retrieval-augmented generation for Ontario planning and water policy questions.

| File | Purpose |
|------|---------|
| `fine-tuned-RAG/config.py` | Shared config: `DOCS_DIR`, `EXTRA_DOCS_DIRS`, embedding model, ChromaDB path |
| `fine-tuned-RAG/ingest.py` | Multi-directory ingestion pipeline (PDF, MD, JSON, PNG captioning via GPT-4o Vision). Supports `--add` (incremental) and `--dir <path>` (single directory) |
| `fine-tuned-RAG/retriever.py` | Vector store search (similarity + MMR) and collection stats |
| `fine-tuned-RAG/rag_chain.py` | LangChain RAG chain with citation-aware system prompt |
| `fine-tuned-RAG/api.py` | FastAPI endpoints for RAG queries |
| `fine-tuned-RAG/get_context.py` | Standalone context retrieval utility |
| `fine-tuned-RAG/test_ask.py` | Quick test harness for RAG questions |

### Document Sources

| Directory | Content |
|-----------|---------|
| `../Hack Canada` (DOCS_DIR) | Toronto Official Plan, zoning by-laws, secondary plans, planning maps |
| `../water-policy` (EXTRA_DOCS_DIRS) | Ontario water legislation (Safe Drinking Water Act, O.Reg 170/03, 169/03), water meter/billing policy, source protection, MTU replacement zones |

---

## .claude/ Skills Pipeline

6-stage modular agent pipeline for Ontario site feasibility research.

```
Address/Parcel Input
       │
       ▼
source-discovery          → source_bundle.json
       │
       ▼
parcel-zoning-research    → normalized_data.json
       │
    ┌──┴──┐
    ▼     ▼
buildability-analysis     precedent-research    → precedent_packet.json
       │                        │
       ▼                        ▼
constraints-red-flags     approval-pathway      → approval_pathway.json
       │                        │
       └──────────┬─────────────┘
                  ▼
          report-generator      → final_report.md
```

| Skill | Input | Output | References |
|-------|-------|--------|-----------|
| `source-discovery` | Address/parcel | `source_bundle.json` | toronto-open-data.md, ontario-data-portals.md |
| `parcel-zoning-research` | source_bundle.json | `normalized_data.json` | ontario-policy-framework.md, toronto-zoning-guide.md |
| `buildability-analysis` | normalized_data.json + concept | `analysis_packet.json` | analysis-framework.md |
| `precedent-research` | normalized_data.json + concept | `precedent_packet.json` | toronto-planning-sources.md, project-history-risk-patterns.md |
| `constraints-red-flags` | All upstream artifacts | `constraints_packet.json` | obc-hard-constraints.md, construction-risk-red-flags.md |
| `approval-pathway` | normalized, analysis, precedent | `approval_pathway.json` | planning-approvals-process.md, building-permit-process.md, external-approvals.md |
| `report-generator` | All upstream artifacts | `final_report.md` | None (synthesis only) |
| `infrastructure-assessment` | Asset ID or location | Condition assessment JSON | opsd-standards.md, csa-s6-bridge-code.md |
| `infrastructure-standards` | Standard reference or question | Standard details | mto-drainage-manual.md |

---

## Tests

Located in `tests/` — 19 pytest modules:

| File | Tests |
|------|-------|
| `test_health.py` | Health check endpoint |
| `test_parcels.py` | Parcel lookup and queries |
| `test_geospatial_services.py` | Geospatial ingestion + spatial queries |
| `test_zoning_parser.py` | Zoning standard parsing |
| `test_policy_stack.py` | Policy hierarchy application |
| `test_compliance_engine.py` | Deterministic compliance rules |
| `test_overlay_service.py` | GIS overlay intersection |
| `test_thin_slice_runtime.py` | Simulation and massing runtime |
| `test_assistant_router.py` | AI assistant endpoint |
| `test_context_builder.py` | Report context assembly |
| `test_submission_readiness.py` | Submission readiness validation |
| `test_governance.py` | Data governance and lineage |
| `test_citation_verifier.py` | Citation and source provenance |
| `test_job_service.py` | Async job status + task management |
| `test_benchmarks.py` | Performance benchmarks |
| `test_validation.py` | Input validation + error handling |
| `test_dependencies.py` | DI and FastAPI dependency tests |
| `conftest.py` | Fixtures and shared test configuration |

---

## Known Issues & Incomplete Features

### Backend
| Issue | Location | Severity |
|-------|---------|----------|
| Scenario comparison returns empty deltas | `app/routers/scenarios.py:50-64` | Medium — TODO |
| Admin ingestion has no role check | `app/routers/ingestion.py` | Medium — security gap |
| Plans can be created with dummy UUIDs (anonymous) | `app/routers/plans.py` | Medium — `get_optional_user` allows anon |
| Embedding generation missing | `app/models/entitlement.py`, `policy.py` | High — pgvector columns exist, no generation code |
| Doc review has no role-based state transition check | `app/services/submission/review.py` | Medium |
| Background tasks have no retry / dead-letter queue | `app/tasks/*` | Medium |
| Building permit ↔ DevelopmentApplication auto-linking missing | `app/tasks/ingestion.py` | Low |

### Frontend
| Issue | Location | Severity |
|-------|---------|----------|
| Auth0 credentials hardcoded | `src/main.jsx` | High — should use env vars |
| `LoginPage.jsx` unused but still in codebase | `src/components/LoginPage.jsx` | Low — dead code |
| ~~Finances tab not wired to backend~~ | `src/components/PolicyPanel.jsx` | Fixed — shows pro forma, assessed value, market comps |
| ~~Precedents tab requires scenario creation~~ | `src/components/PolicyPanel.jsx` | Fixed — now fetches from `/nearby-applications` |
| Poll loops not cancellable (memory leak risk) | `src/components/ChatPanel.jsx` | Medium |
| ZONING_DATA duplicated from backend | `src/components/PolicyPanel.jsx` | Medium — sync drift risk |
| Silent `searchParcels` error suppression | `src/api.js` | Medium — no user feedback |
| No TypeScript / Zod validation | Entire frontend | Medium |

---

## API Endpoint Reference

Full table — all routes across all routers:

| Method | Route | Auth | Async | Status |
|--------|-------|------|-------|--------|
| POST | `/api/v1/auth/register` | No | No | ✓ |
| POST | `/api/v1/auth/login` | No | No | ✓ |
| POST | `/api/v1/plans/generate` | Optional | Yes (background) | ✓ |
| GET | `/api/v1/plans` | Yes | No | ✓ |
| GET | `/api/v1/plans/{id}` | Yes | No | ✓ |
| GET | `/api/v1/plans/{id}/readiness` | Yes | No | ✓ |
| POST | `/api/v1/plans/{id}/clarify` | Yes | No | ✓ |
| GET | `/api/v1/plans/{id}/documents` | Yes | No | ✓ |
| GET | `/api/v1/plans/{id}/documents/{doc_id}` | Yes | No | ✓ |
| POST | `/api/v1/plans/{id}/documents/{doc_id}/submit-review` | Yes | No | ✓ |
| POST | `/api/v1/plans/{id}/documents/{doc_id}/approve` | Yes | No | ✓ |
| POST | `/api/v1/plans/{id}/documents/{doc_id}/reject` | Yes | No | ✓ |
| POST | `/api/v1/plans/{id}/generate-document/{doc_type}` | Yes | No | ✓ |
| GET | `/api/v1/plans/{id}/documents/{doc_id}/download?format=` | Yes | No | ✓ |
| POST | `/api/v1/plans/{id}/export` | Yes | No | ✓ |
| GET | `/api/v1/plans/{id}/contractors?lat=&lng=` | Yes | No | ✓ |
| POST | `/api/v1/assistant/chat` | Yes | No | ✓ |
| GET | `/api/v1/parcels/search` | Yes | No | ✓ |
| GET | `/api/v1/parcels/{id}` | Yes | No | ✓ |
| GET | `/api/v1/parcels/{id}/policy-stack` | Yes | No | ✓ |
| GET | `/api/v1/parcels/{id}/overlays` | Yes | No | ✓ |
| POST | `/api/v1/projects` | Yes | No | ✓ |
| GET | `/api/v1/projects` | Yes | No | ✓ |
| GET | `/api/v1/projects/{id}` | Yes | No | ✓ |
| PATCH | `/api/v1/projects/{id}` | Yes | No | ✓ |
| POST | `/api/v1/projects/{id}/parcels` | Yes | No | ✓ |
| DELETE | `/api/v1/projects/{id}/parcels/{parcel_id}` | Yes | No | ✓ |
| POST | `/api/v1/projects/{id}/scenarios` | Yes | No | ✓ |
| GET | `/api/v1/scenarios/{id}` | Yes | No | ✓ |
| GET | `/api/v1/scenarios/{id}/compare/{other}` | Yes | No | ⚠️ TODO |
| POST | `/api/v1/scenarios/{id}/massings` | Yes | Yes | ✓ |
| GET | `/api/v1/massings/{id}` | Yes | No | ✓ |
| GET | `/api/v1/reference/massing-templates` | Yes | No | ✓ |
| GET | `/api/v1/reference/unit-types` | Yes | No | ✓ |
| POST | `/api/v1/massings/{id}/layout-runs` | Yes | Yes | ✓ |
| GET | `/api/v1/layout-runs/{id}` | Yes | No | ✓ |
| POST | `/api/v1/scenarios/{id}/financial-runs` | Yes | Yes | ✓ |
| GET | `/api/v1/financial-runs/{id}` | Yes | No | ✓ |
| GET | `/api/v1/reference/financial-assumption-sets` | Yes | No | ✓ |
| POST | `/api/v1/scenarios/{id}/entitlement-runs` | Yes | Yes | ✓ |
| GET | `/api/v1/entitlement-runs/{id}` | Yes | No | ✓ |
| POST | `/api/v1/scenarios/{id}/precedent-searches` | Yes | Yes | ✓ |
| GET | `/api/v1/precedent-searches/{id}` | Yes | No | ✓ |
| POST | `/api/v1/uploads` | Yes | Yes | ✓ |
| GET | `/api/v1/uploads` | Yes | No | ✓ |
| GET | `/api/v1/uploads/{id}` | Yes | No | ✓ |
| GET | `/api/v1/uploads/{id}/pages` | Yes | No | ✓ |
| GET | `/api/v1/uploads/{id}/analysis` | Yes | No | ✓ |
| POST | `/api/v1/uploads/{id}/generate-plan` | Yes | Yes | ✓ |
| POST | `/api/v1/uploads/{id}/generate-response` | Yes | No | ✓ |
| POST | `/api/v1/designs/{project_id}/branches` | Yes | No | ✓ |
| GET | `/api/v1/designs/{project_id}/branches` | Yes | No | ✓ |
| DELETE | `/api/v1/designs/{project_id}/branches/{branch_id}` | Yes | No | ✓ |
| POST | `/api/v1/designs/branches/{branch_id}/commit` | Yes | No | ✓ |
| GET | `/api/v1/designs/branches/{branch_id}/versions` | Yes | No | ✓ |
| GET | `/api/v1/designs/branches/{branch_id}/latest` | Yes | No | ✓ |
| GET | `/api/v1/designs/versions/{version_id}` | Yes | No | ✓ |
| POST | `/api/v1/compliance/interior` | No | No | ✓ |
| POST | `/api/v1/admin/ingest/building-permits` | Yes | Yes | ✓ |
| POST | `/api/v1/admin/ingest/coa-applications` | Yes | Yes | ✓ |
| GET | `/api/v1/admin/ingest/status` | Yes | No | ✓ |

---

*Last updated: 2026-03-08 (27-document catalog: AI generation wiring, compliance engine fixes (O.Reg 462/24, Bill 185), 17 new doc types, assistant doc_types routing, on-demand regeneration endpoint, document gallery/viewer UI, DOCX download/export; PRD link added)*
