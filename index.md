# CoCivil — AI-Powered Civil Development Platform

> **Auto-maintained**: Updated after every file edit/creation. See `.claude/CLAUDE.md` for rules.
> **Last updated**: 2026-03-10 (full index audit) | **PRD**: [`.claude/docs/PRD.md`](.claude/docs/PRD.md)

---

## Product Description

**CoCivil** is an AI-powered due-diligence and design platform for land development in Ontario, Canada. It turns a plain-English development query into a complete planning submission package — compliance matrices, planning rationales, precedent reports, massing models, floor plans, and infrastructure designs — in minutes instead of weeks.

### What It Does

- **Parcel Intelligence** — Search any Toronto address. Instantly retrieve zoning (By-law 569-2013), Official Plan designation, overlays, setbacks, height limits, and lot coverage from live Toronto Open Data.
- **AI Planning Assistant** — Chat with an AI agent grounded in Ontario planning law (Planning Act, PPS 2024, O.Reg 462/24, Bills 23/185/60). It answers zoning questions, proposes variance strategies, and identifies approval pathways.
- **Automated Document Generation** — Generate planning rationales, compliance reports, shadow studies, and submission packages. Every document is grounded in cited policy and flagged for professional review.
- **3D Massing & Floor Plans** — Describe a building in plain English; CoCivil generates a 3D massing model (Three.js) and editable floor plans (Konva.js) with real-time OBC compliance checking.
- **Infrastructure Design** — Upload pipeline DXFs or describe infrastructure; get 3D pipe network visualization, OPSD-compliant specs, and condition assessments.
- **Precedent Research** — AI-powered search of Committee of Adjustment, Ontario Land Tribunal, and CanLII decisions for comparable approvals/refusals near the site.
- **Policy RAG Engine** — Fine-tuned retrieval-augmented generation over Ontario planning documents, zoning by-laws, and building code references via ChromaDB vector search.

### Who It's For

- Land developers evaluating site feasibility
- Urban planners preparing submission packages
- Architects exploring massing and floor plan options
- Civil engineers designing infrastructure networks
- Municipal staff reviewing applications

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (React 19 + Vite)                             │
│  MapLibre GL · Three.js · Konva.js · Auth0              │
├─────────────────────────────────────────────────────────┤
│  Backend (FastAPI + SQLAlchemy async)                    │
│  18 API routers · 81 endpoints · 30+ services · 9 tasks  │
├─────────────────────────────────────────────────────────┤
│  PostgreSQL + PostGIS    │  ChromaDB (RAG vectors)      │
│  Toronto Open Data CKAN  │  Claude / OpenAI LLM         │
└─────────────────────────────────────────────────────────┘
```

| Layer | Tech |
|-------|------|
| Frontend | React 19, Vite, MapLibre GL, Three.js, Konva.js, Auth0 |
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic 2.7+, Structlog |
| Database | PostgreSQL + PostGIS, GeoAlchemy2, Alembic migrations |
| AI | Claude (primary), OpenAI (fallback), ChromaDB RAG |
| Task Queue | Celery 5.3+ with Redis broker |
| Deploy | Docker, Railway, AWS S3 |

---

## Table of Contents

1. [Backend — `app/`](#backend--app)
2. [Frontend — `frontend-react/`](#frontend--frontend-react)
3. [Fine-Tuned RAG — `fine-tuned-RAG/`](#fine-tuned-rag--fine-tuned-rag)
4. [Skills Pipeline — `.claude/skills/`](#skills-pipeline--claudeskills)
5. [Agent Skills — `.agents/skills/`](#agent-skills--agentsskills)
6. [Scripts — `scripts/`](#scripts--scripts)
7. [Tests — `tests/`](#tests--tests)
8. [Documentation — `docs/`](#documentation--docs)
9. [Data & Infrastructure Files](#data--infrastructure-files)
10. [Config & DevOps](#config--devops)
11. [API Endpoint Reference](#api-endpoint-reference)

---

## Backend — `app/`

### Entry Points

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app factory, route registration, middleware |
| `app/config.py` | Settings (DB, AI provider, S3, Auth0) via Pydantic BaseSettings |
| `app/database.py` | SQLAlchemy dual async/sync engines & session factories |
| `app/dependencies.py` | FastAPI dependency injection (JWT auth, multi-tenant org scoping) |
| `app/devtools.py` | Preflight connectivity checks (DB, Redis, S3, Docker) |
| `app/celery_app.py` | Celery application config (broker=Redis, JSON serialization, 9 task modules) |

### Middleware (`app/middleware/`)

| File | Purpose |
|------|---------|
| `request_id.py` | Assigns/propagates X-Request-ID header per request |
| `idempotency.py` | Redis-backed idempotency key enforcement (24h TTL) |

### Database Models (`app/models/`)

| File | Purpose |
|------|---------|
| `base.py` | Base model (UUIDPrimaryKey, TimestampMixin, GovernanceMixin) |
| `plan.py` | Development plan |
| `geospatial.py` | Parcel, zoning, overlay |
| `entitlement.py` | Variances, approvals |
| `infrastructure.py` | Water, electrical, drainage assets |
| `finance.py` | Development cost models |
| `policy.py` | Policy references & citations |
| `ingestion.py` | Data ingestion tracking |
| `upload.py` | File upload records |
| `export.py` | Document export records |
| `dataset.py` | Dataset catalog |
| `design_version.py` | Design version tracking |
| `simulation.py` | Scenario simulation |
| `tenant.py` | Multi-tenant isolation |

### API Routes (`app/routers/`)

| File | Endpoint | Purpose |
|------|----------|---------|
| `plans.py` | `/api/v1/plans` | Plan CRUD + generation |
| `parcels.py` | `/api/v1/parcels` | Parcel data & search |
| `entitlement.py` | `/api/v1/entitlements` | Zoning approvals |
| `compliance.py` | `/api/v1/compliance` | OBC interior compliance checks |
| `infrastructure.py` | `/api/v1/infrastructure` | Pipeline assets, watermains, compliance |
| `finance.py` | `/api/v1/finance` | Pro formas, cost estimates |
| `assistant.py` | `/api/v1/assistant` | AI chat |
| `exports.py` | `/api/v1/exports` | PDF/Docx generation |
| `ingestion.py` | `/api/v1/ingestion` | CKAN/GeoJSON import |
| `uploads.py` | `/api/v1/uploads` | File upload handling |
| `auth.py` | `/api/v1/auth` | Authentication |
| `jobs.py` | `/api/v1/jobs` | Async task tracking |
| `projects.py` | `/api/v1/projects` | Project CRUD |
| `scenarios.py` | `/api/v1/scenarios` | Scenario modeling |
| `simulation.py` | `/api/v1/simulation` | Run simulations |
| `design_versions.py` | `/api/v1/design-versions` | Version control |
| `governance.py` | `/api/v1/governance` | Permissions |
| `policy.py` | `/api/v1/policy` | Policy data |
| `health.py` | `/api/health` | Health check |

### Services (`app/services/`)

| File | Purpose |
|------|---------|
| `compliance_engine.py` | Deterministic zoning compliance (no AI) |
| `interior_compliance.py` | OBC interior code checking |
| `infrastructure_compliance.py` | Infrastructure standard compliance |
| `zoning_service.py` | Zoning analysis orchestrator (deterministic) |
| `zoning_parser.py` | By-law 569-2013 zone string parser (regex-based) |
| `policy_stack.py` | RAG-backed policy retrieval (ChromaDB) |
| `geospatial_ingestion.py` | GeoJSON import |
| `ckan_ingestion.py` | Toronto Open Data CKAN integration |
| `geospatial.py` | PostGIS spatial operations |
| `overlay_service.py` | Zoning overlay analysis |
| `dxf_parser.py` | Building floor plan DXF parsing |
| `pipeline_dxf_parser.py` | Pipeline network DXF parsing |
| `document_analyzer.py` | AI document understanding |
| `document_processor.py` | Text extraction |
| `thin_slice_runtime.py` | Fast feasibility checks |
| `simulation_runtime.py` | Simulation execution |
| `contractor_trades.py` | Contractor specialty matching |
| `precedent.py` | Planning precedent scoring |
| `benchmarks.py` | Development benchmarks |
| `design_version_service.py` | Design version management |
| `governance.py` | Role/permission management |
| `access_control.py` | Fine-grained access control |
| `job_service.py` | Unified job status lookup across 7 async tables |
| `storage.py` | File storage (S3/MinIO via boto3) |
| `validation.py` | Data validation for source metadata, policy, precedent, finance |
| `reference_data.py` | DB-backed reference data management (templates, unit types) |
| `idempotency.py` | Pydantic-aware wrapper over Redis idempotency cache |
| `infrastructure_ingestion.py` | CKAN ingestion for water mains, sewers, bridges |
| `submission/templates.py` | Document templates & AI prompts |
| `submission/context_builder.py` | Submission context assembly |
| `submission/generator.py` | AI-driven document generation |
| `submission/review.py` | Submission review & QA |
| `submission/readiness.py` | Readiness checks |
| `submission/citation_verifier.py` | Citation validation |
| `submission/document_selector.py` | Document selection logic |

### Data & Policy (`app/data/`)

| File | Purpose |
|------|---------|
| `toronto_zoning.py` | By-law 569-2013 standards (hardcoded) |
| `ontario_policy.py` | Policy hierarchy, PPS 2024, OP designations, legislation |
| `toronto_policy_seed.py` | Toronto-specific policy seed data |
| `civil_standards.py` | Civil infrastructure standards |
| `infrastructure_policy.py` | Infrastructure policy rules |
| `obc_interior_standards.py` | Ontario Building Code interior standards |

### Schemas (`app/schemas/`)

| File | Purpose |
|------|---------|
| `common.py` | HealthResponse, JobAccepted, PaginationParams, Citation |
| `plan.py` | PlanGenerateRequest, PlanResponse, SubmissionDocumentResponse, readiness |
| `entitlement.py` | EntitlementRunRequest/Response, PrecedentSearchRequest/Response |
| `geospatial.py` | ParcelSearchParams, ParcelResponse, PolicyStackResponse, ZoningAnalysisResponse |
| `assistant.py` | AssistantChatRequest/Response, ModelParseRequest, InfraModelParseRequest |
| `finance.py` | FinancialRunRequest/Response, FinancialAssumptionSetReferenceResponse |
| `infrastructure.py` | PipelineComplianceRequest, BridgeComplianceRequest, NearbyPipelineRequest |
| `simulation.py` | MassingRequest/Response, LayoutRunRequest/Response, UnitTypeReferenceResponse |
| `tenant.py` | ProjectCreate/Response, ScenarioCreate/Response, AddParcelRequest |
| `job.py` | JobStatusResponse (unified across all async job types) |
| `auth.py` | RegisterRequest, LoginRequest, TokenResponse |
| `upload.py` | UploadResponse, UploadDetail, GenerateResponseRequest |
| `export.py` | ExportRequest/Response |
| `governance.py` | SnapshotManifestResponse, ReviewQueueItemResponse |
| `design_version.py` | BranchCreate/Response, CommitRequest, VersionResponse |
| `policy.py` | PolicySearchParams, PolicyClauseResponse |

### Background Tasks (`app/tasks/`) — Celery tasks

| File | Purpose |
|------|---------|
| `plan.py` | Main plan generation pipeline |
| `ingestion.py` | CKAN/GeoJSON import |
| `entitlement.py` | Entitlement analysis |
| `infrastructure_ingestion.py` | Infrastructure data import |
| `massing.py` | 3D massing generation |
| `layout.py` | Layout optimization |
| `finance.py` | Financial modeling |
| `export.py` | Document export |
| `document_analysis.py` | Document parsing |

### AI Provider (`app/ai/`)

| File | Purpose |
|------|---------|
| `base.py` | Abstract AI provider interface |
| `claude_provider.py` | Anthropic Claude integration |
| `openai_provider.py` | OpenAI fallback |
| `query_parser.py` | Intent detection & query parsing |
| `factory.py` | Provider factory |

---

## Frontend — `frontend-react/`

### Entry & Config

| File | Purpose |
|------|---------|
| `src/main.jsx` | React root, Auth0 provider |
| `src/App.jsx` | Main app shell |
| `src/api.js` | API client (all backend calls) |
| `src/index.css` | Global styles + CSS custom properties (--sidebar-width, --panel-width, --chat-height) |
| `src/landing.css` | Landing page styles |
| `src/ModelViewer.css` | 3D viewer overlay styles |
| `src/InfrastructureViewer.css` | Infrastructure viewer styles |
| `src/UserBubble.css` | User bubble expand/collapse animations |
| `index.html` | HTML entry point |
| `vite.config.js` | Vite bundler config |

### Components (`src/components/`)

| File | Purpose |
|------|---------|
| `LandingPage.jsx` | Home page / onboarding |
| `LoginPage.jsx` | Auth0 login flow |
| `MapView.jsx` | Interactive parcel/zoning map (MapLibre GL) |
| `SearchBar.jsx` | Address/parcel search |
| `Sidebar.jsx` | Navigation & context panel |
| `ChatPanel.jsx` | AI assistant chat (renders HTML directly from fine-tuned AI) |
| `PolicyPanel.jsx` | Policy extracts, overlays, datasets, uploads, zoning analysis |
| `DocumentViewer.jsx` | Markdown document viewer (ReactMarkdown + remark-gfm) |
| `DocumentGallery.jsx` | Document library UI |
| `ModelViewer.jsx` | 3D building massing viewer (Three.js) |
| `FloorPlanView.jsx` | 2D floor plan view (Konva.js) |
| `InfrastructureViewer.jsx` | 3D pipeline network viewer |
| `ContractorCards.jsx` | Contractor/trade recommendation cards |
| `BlueprintOverlay.jsx` | Blueprint display overlay |
| `InfrastructureLayerControl.jsx` | Floating layer toggle panel (Roads, Water, EV) |
| `UserBubble.jsx` | User profile menu |

### Floor Plan Editor (`src/components/floorplan/`)

| File | Purpose |
|------|---------|
| `FloorPlanEditor.jsx` | Main floor plan canvas |
| `WallLayer.jsx` | Wall rendering & editing |
| `RoomLayer.jsx` | Room zones |
| `DimensionLayer.jsx` | Dimension annotations |
| `OpeningLayer.jsx` | Door/window openings |
| `ComplianceBadgeLayer.jsx` | OBC compliance violation badges |
| `EditorToolbar.jsx` | Tool selection, undo/redo |
| `WallProperties.jsx` | Wall parameter panel |
| `CompliancePanel.jsx` | Code violation list |
| `RoomTypeSelector.jsx` | Room type catalog |
| `DragDropCatalog.jsx` | Component palette |
| `ScaleCalibration.jsx` | Scale/unit setup |

### Infrastructure Viewer (`src/components/infrastructure/`)

| File | Purpose |
|------|---------|
| `PipeNetworkEditor.jsx` | Pipe network editing (Konva) |
| `InfrastructureLayerControl.jsx` | Layer toggles |
| `InfrastructureCatalog.jsx` | Pipe catalog |
| `InfrastructureCompliancePanel.jsx` | Infrastructure compliance checks |
| `PipeProperties.jsx` | Pipe parameter editor |
| `ProfileView.jsx` | Elevation profile view |

### Hooks (`src/hooks/`)

| File | Purpose |
|------|---------|
| `useResizable.js` | Resizable panel hook |

### Utilities (`src/lib/`)

| File | Purpose |
|------|---------|
| `buildingGeometry.js` | 3D building geometry helpers |
| `wallGeometry.js` | Wall geometry calculations |
| `floorPlanHelpers.js` | Floor plan utilities |
| `infrastructureGeometry.js` | Pipeline geometry math |
| `parcelState.js` | Parcel data state management |
| `chatCommands.js` | Chat command parsing |
| `watermainStandards.js` | Water main diameter/depth rules |
| `chatCommands.test.js` | Tests for chat command parsing |
| `parcelState.test.js` | Tests for parcel state functions |

### Dev Harness (`src/dev/`)

| File | Purpose |
|------|---------|
| `ModelViewerHarness.jsx` | Isolated 3D viewer testing (loaded via `?viewerHarness=1`) |
| `modelViewerHarnessData.js` | Sample parcel, model params, floor plans for harness |

---

## Fine-Tuned RAG — `fine-tuned-RAG/`

| File | Purpose |
|------|---------|
| `config.py` | RAG configuration (embedding model, ChromaDB settings) |
| `retriever.py` | Vector search & context retrieval |
| `rag_chain.py` | RAG pipeline (query → retrieval → LLM) |
| `api.py` | FastAPI endpoints for RAG service |
| `ingest.py` | Load documents into ChromaDB |
| `fast_ingest.py` | Optimized bulk ingestion |
| `populate_rag.py` | Parallel population via API (ThreadPoolExecutor) |
| `populate_direct.py` | Direct in-process population (targeted subtopics) |
| `get_context.py` | CLI debug tool — retrieve and print context for a query |
| `run_batch.py` | Batch inspection of retriever results |
| `test_ask.py` | Smoke test — single hardcoded question |
| `check_empty.py` | Audit — count entries missing output |
| `fix_one.py` | One-shot repair for a single entry |
| `chroma_db/` | ChromaDB vector database storage |

---

## Skills Pipeline — `.claude/skills/`

Sequential AI research pipeline for Ontario site-feasibility:

```
Address → source-discovery → parcel-zoning-research → buildability-analysis → approval-pathway
                                                    → precedent-research   → constraints-red-flags
                                                                           → report-generator
```

| Skill | Output | Purpose |
|-------|--------|---------|
| `source-discovery` | `source_bundle.json` | Find official data source URLs |
| `parcel-zoning-research` | `normalized_data.json` | Extract zone code, OP designation, overlays |
| `buildability-analysis` | `analysis_packet.json` | Feasibility verdict + compliance gaps |
| `precedent-research` | `precedent_packet.json` | Comparable CoA/ZBA/OLT decisions |
| `constraints-red-flags` | `constraints_packet.json` | OBC hard constraints, risk flags |
| `approval-pathway` | `approval_pathway.json` | Route classification + timeline |
| `report-generator` | `final_report.md` | Client-facing report |
| `infrastructure-assessment` | `condition_assessment.json` | Asset condition rating & rehab priority |
| `infrastructure-standards` | — | OPSD/CSA/MTO standard lookups |

---

## Agent Skills — `.agents/skills/`

29 self-contained agent skill definitions for Ontario planning document generation. Each directory contains a `SKILL.md` with inputs, outputs, workflow, and governing law references.

### Data & Research Skills

| Skill | Section | Purpose |
|-------|---------|---------|
| `neon-postgres` | — | Neon serverless Postgres reference guide |
| `ontario-planning-framework` | 1 | Foundational legal hierarchy and data sources |
| `ontario-planning-appendices` | 15 | Reference compendium (11 appendices: legislation, fees, glossary, QA) |

### Compliance & Analysis Skills

| Skill | Section | Purpose |
|-------|---------|---------|
| `ontario-compliance-matrix` | 2 | Zoning standards comparison table (required vs proposed) |
| `ontario-as-of-right-checker` | 14 | Determine if development needs no planning application |
| `ontario-required-studies` | 15 | Trigger-based checklist of 22 required technical studies |
| `ontario-upload-analysis` | 12 | Extract dimensions from uploaded PDF/DXF drawings |

### Document Generation Skills

| Skill | Section | Purpose |
|-------|---------|---------|
| `ontario-planning-rationale` | 3 | Full 15–40 page planning rationale report |
| `ontario-cover-letter` | 4 | Formal application cover letter |
| `ontario-precedent-report` | 5 | CoA/OLT comparable decisions report |
| `ontario-financial-feasibility` | 6 | Development cost/revenue pro forma |
| `ontario-massing-built-form` | 7 | Built form description + guideline compliance |
| `ontario-unit-mix-layout` | 8 | Unit distribution + Growing Up Guidelines check |
| `ontario-shadow-study` | 9 | Shadow analysis (Toronto standard test dates) |
| `ontario-public-benefit` | 10 | Public benefit statement (housing, sustainability) |
| `ontario-site-plan-data` | 11 | Site plan data summary tables |
| `ontario-correction-response` | 13 | Response letter to municipal staff comments |
| `ontario-due-diligence` | 16 | Consolidated pre-acquisition due diligence report |

### Approval & Legal Skills

| Skill | Section | Purpose |
|-------|---------|---------|
| `ontario-approval-pathway` | 17 | Approval process classification (as-of-right/MV/ZBA/OPA) |
| `ontario-timeline-fee-estimator` | 18 | Timeline + government/consultant fee estimates |
| `ontario-four-statutory-tests` | 20 | s.45(1) four-test analysis for minor variance |
| `ontario-variance-justification-table` | 21 | Per-variance justification table for CoA package |
| `ontario-building-permit-checklist` | 22 | Post-approval building permit readiness checklist |
| `ontario-olt-appeal-strategy` | 24 | OLT appeal strategy brief (PROCEED/REVISE/SETTLE) |

### Application Packaging Skills

| Skill | Section | Purpose |
|-------|---------|---------|
| `ontario-auto-filled-committee-form` | 19 | Pre-populated CoA application form |
| `ontario-neighbour-support-letter` | 23 | Neighbour info letter + support letter template |
| `ontario-site-photo-checklist` | 25 | Required photographs checklist by proposal type |
| `ontario-pre-application-consultation` | 26 | Pre-consultation meeting package |
| `ontario-professional-referral-matcher` | 27 | Match project to required professionals (RPP, OAA, P.Eng, etc.) |

---

## Scripts — `scripts/`

| File | Purpose |
|------|---------|
| `seed_toronto.py` | Quick 6-step Toronto data seed (parcels, zoning, overlays, dev apps) |
| `seed_toronto_detailed.py` | Full 17-step Toronto seed with per-step control and progress reporting |
| `seed_policies.py` | Seed curated Toronto MVP policy corpus (5 docs, 15 clauses) |
| `seed_reference_data.py` | Seed massing templates, unit types, financial assumptions |
| `railway_seed.py` | Railway deployment seed (downloads from CKAN, supports bbox filter) |
| `ingest_toronto_tracks_1_2.py` | CLI for manual geospatial dataset ingestion (5 subcommands) |
| `audit_toronto_seed.py` | Audit DB state + run benchmark suite against real parcel data |
| `dev_doctor.py` | Preflight connectivity check for local dev environment |
| `generate_sample_dxf.py` | Generate rich sample building DXF (6-storey mixed-use) |
| `generate_sample_pipeline_dxf.py` | Generate sample water main DXF (3x2 junction grid) |
| `test_search.py` | Ad-hoc parcel search test against live DB |
| `init-extensions.sql` | PostgreSQL init (uuid-ossp, postgis, pgvector extensions) |

---

## Tests — `tests/`

24+ test files with pytest + httpx AsyncClient.

| File | Coverage |
|------|----------|
| `conftest.py` | Shared fixtures (httpx AsyncClient via ASGITransport) |
| `test_compliance_engine.py` | Deterministic compliance: FSI, height, lot coverage, parking, angular plane, minor variance |
| `test_zoning_parser.py` | Zone string parsing (12 categories) + standards lookup |
| `test_thin_slice_runtime.py` | Massing, layout, financial models + precedent scoring |
| `test_context_builder.py` | Template placeholder completeness + missing data markers |
| `test_document_selector.py` | Conditional document selection (as-of-right, MV, ZBA, refusal) |
| `test_citation_verifier.py` | By-law section validation + strip unverified citations |
| `test_submission_readiness.py` | Readiness evaluation (blocking issues, placeholders, approval status) |
| `test_geospatial_services.py` | Address normalization, parcel search, canonical address selection |
| `test_geospatial_ingestion.py` | Zone code picking, decision normalization, geometry parsing |
| `test_overlay_service.py` | Overlay dedup, metric sorting, 404 on missing parcel |
| `test_policy_stack.py` | Policy ordering by override level, snapshot dedup |
| `test_policy_seed.py` | Curated corpus structure (5 docs, 15 clauses, 5 override levels) |
| `test_benchmarks.py` | Benchmark fixture loading, case evaluation, suite summarization |
| `test_governance.py` | Manifest hash stability, export control decisions |
| `test_validation.py` | Source metadata, policy rule, precedent, finance record validation |
| `test_dependencies.py` | JWT auth: DB role overrides JWT claim, multi-org 403 |
| `test_assistant_router.py` | Chat endpoint: 503 without key, prompt structure verification |
| `test_plans.py` | Plan generation auth guard (401 without token) |
| `test_health.py` | Health endpoint returns status + version |
| `test_parcels.py` | Parcel search validation + zoning analysis payload structure |
| `test_job_service.py` | Job status serialization across async tables |
| `test_dev_architecture.py` | Docker compose structure, .env.example validation |
| `test_audit_toronto_seed.py` | Benchmark suite execution without DB |
| `fixtures/benchmarks/` | 3 fixture files: toronto_core.json, toronto_phase2.json, toronto_showcase.json |

---

## Documentation — `docs/`

| File | Purpose |
|------|---------|
| `index.md` | Documentation overview (29 endpoints, 34 tables, implementation status) |
| `arterial_backend_clone_analysis.md` | Reverse-engineering analysis of Arterial.design (founding blueprint) |
| `DATA_PLAN.md` | MVP data plan: 4 dataset tiers, 9-stage ingestion pipeline |
| `DATA_RESEARCH_TEAM_PLAN.md` | 6 parallel research tracks for Toronto MVP |
| `IMPLEMENTATION_PLAN.md` | Full technical spec: schema DDL, algorithms, phase breakdown |
| `SUBMISSION_RESEARCH.md` | Toronto application requirements, document types, policy framework |
| `RAG_LEGAL_DOCUMENT_GENERATION_RESEARCH.md` | RAG architecture research: embeddings, chunking, hallucination prevention |
| `TRACK_3_4_RESEARCH.md` | Research for Policy Text + Hard Constraint Overlays tracks |
| `TRACK_5_6_RESEARCH.md` | Research for Simulation Defaults + Precedent/Permit tracks |

---

## Data & Infrastructure Files

| Path | Purpose |
|------|---------|
| `data/property-boundaries-4326.geojson` | Toronto property parcels (WGS84) |
| `data/zoning-area-4326.geojson` | Zoning designations |
| `data/zoning-building-setback-overlay-4326.geojson` | Setback overlays |
| `data/zoning-height-overlay-4326.geojson` | Height restriction overlays |
| `data/development-applications.json` | CoA/ZBA/OPA precedent records (UTM coords) |
| `data/test_floor_plan.dxf` | Sample DXF for parser testing |
| `water-system-data/` | 7 files: watermain networks, hydrants, valves, fittings, fountains, waterbodies shapefile |
| `water-policy/` | 13 markdown docs + 20 PDF references (Ontario regs, MECP procedures, MTU zone maps) |
| `Road/` | Road Reconstruction Program GeoJSON (LineString) |
| `City-electric-charge/` | City-operated EV charging stations GeoJSON (Point) |

---

## Config & DevOps

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Infra-only compose: PostGIS 16, Redis 7, MinIO |
| `docker-compose.app.yml` | App compose override: Celery worker + API (containerized) |
| `Dockerfile` | Two-stage build: Node 20 frontend + Python 3.11 backend |
| `railway.toml` | Railway config (pre-deploy: alembic migrate, health: /api/v1/health) |
| `alembic.ini` | Alembic migration config |
| `alembic/` | 6 migrations: initial 34-table schema → infrastructure assets |
| `pyproject.toml` | Python project config (uv), Python ≥3.11, pytest asyncio_mode=auto |
| `Makefile` | 12 targets: infra-up/down, doctor, migrate, run-api/frontend, seed, test |
| `.env.example` | Environment variable template (localhost targets) |
| `PLAN.md` | Architecture design document (995 lines, 5 backend systems) |
| `FLOOR_PLAN_EDITOR_IMPROVEMENTS.md` | Floor plan editor feature documentation |
| `TOOLBAR_VISUAL_GUIDE.txt` | ASCII art toolbar reference |
| `skills-lock.json` | Claude skills lock file (neon-postgres) |
| `uv.lock` | UV dependency lock file |

---

## API Endpoint Reference (81 endpoints)

### Auth & Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Register user + org, returns JWT |
| `POST` | `/api/v1/auth/login` | Login, returns JWT |
| `GET` | `/api/v1/health` | DB + Redis + Celery liveness check |

### Parcels (7 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/parcels/search` | Search parcels by address/bbox/zone |
| `GET` | `/api/v1/parcels/{id}` | Get parcel detail with GeoJSON |
| `GET` | `/api/v1/parcels/{id}/zoning-analysis` | Full zoning analysis (components, standards, overlays) |
| `GET` | `/api/v1/parcels/{id}/policy-stack` | Applicable policy stack (ChromaDB RAG) |
| `GET` | `/api/v1/parcels/{id}/overlays` | Overlay layers intersecting parcel |
| `GET` | `/api/v1/parcels/{id}/nearby-applications` | Dev applications within radius |
| `GET` | `/api/v1/parcels/{id}/financial-summary` | Quick financial feasibility snapshot |

### Plans (14 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/plans/generate` | Submit NL query, enqueue plan pipeline |
| `GET` | `/api/v1/plans` | List all plans for org |
| `GET` | `/api/v1/plans/{id}` | Get plan with documents |
| `GET` | `/api/v1/plans/{id}/readiness` | Submission readiness assessment |
| `POST` | `/api/v1/plans/{id}/clarify` | Answer clarification questions |
| `GET` | `/api/v1/plans/{id}/documents` | List submission documents |
| `GET` | `/api/v1/plans/{id}/documents/{doc_id}` | Get single document |
| `POST` | `/api/v1/plans/{id}/documents/{doc_id}/submit-review` | Send doc to human review |
| `POST` | `/api/v1/plans/{id}/documents/{doc_id}/approve` | Approve reviewed document |
| `POST` | `/api/v1/plans/{id}/documents/{doc_id}/reject` | Reject reviewed document |
| `POST` | `/api/v1/plans/{id}/generate-document/{type}` | Generate/regenerate one document type |
| `GET` | `/api/v1/plans/{id}/documents/{doc_id}/download` | Download as markdown/html/docx |
| `POST` | `/api/v1/plans/{id}/export` | Export all plan docs as DOCX |
| `GET` | `/api/v1/plans/{id}/contractors` | Recommend local contractors (Google Places) |

### Assistant (3 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/assistant/chat` | Multi-turn planning chat (RAG + fine-tuned model) |
| `POST` | `/api/v1/assistant/parse-model` | Parse NL building description into 3D params |
| `POST` | `/api/v1/assistant/parse-infra-model` | Parse NL infrastructure description into params |

### Projects & Scenarios (9 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/projects` | Create project |
| `GET` | `/api/v1/projects` | List projects for org |
| `GET` | `/api/v1/projects/{id}` | Get project |
| `PATCH` | `/api/v1/projects/{id}` | Update project |
| `POST` | `/api/v1/projects/{id}/parcels` | Link parcel to project |
| `DELETE` | `/api/v1/projects/{id}/parcels/{parcel_id}` | Unlink parcel |
| `POST` | `/api/v1/projects/{id}/scenarios` | Create scenario run |
| `GET` | `/api/v1/scenarios/{id}` | Get scenario |
| `GET` | `/api/v1/scenarios/{id}/compare/{other_id}` | Compare two scenarios |

### Simulation (6 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/scenarios/{id}/massings` | Start massing generation |
| `GET` | `/api/v1/massings/{id}` | Get massing result |
| `GET` | `/api/v1/reference/massing-templates` | List massing templates |
| `GET` | `/api/v1/reference/unit-types` | List unit types |
| `POST` | `/api/v1/massings/{id}/layout-runs` | Start layout optimization |
| `GET` | `/api/v1/layout-runs/{id}` | Get layout result |

### Entitlement & Precedent (4 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/scenarios/{id}/entitlement-runs` | Start entitlement check |
| `GET` | `/api/v1/entitlement-runs/{id}` | Poll entitlement result |
| `POST` | `/api/v1/scenarios/{id}/precedent-searches` | Start precedent search |
| `GET` | `/api/v1/precedent-searches/{id}` | Poll precedent result |

### Finance (3 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/scenarios/{id}/financial-runs` | Start financial analysis |
| `GET` | `/api/v1/financial-runs/{id}` | Get financial result |
| `GET` | `/api/v1/reference/financial-assumption-sets` | List assumption sets |

### Uploads (7 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/uploads` | Upload file (DXF parsed inline, others via Celery) |
| `GET` | `/api/v1/uploads` | List uploads for org |
| `GET` | `/api/v1/uploads/{id}` | Get upload status + extracted data |
| `GET` | `/api/v1/uploads/{id}/pages` | Get page images as presigned S3 URLs |
| `GET` | `/api/v1/uploads/{id}/analysis` | Get extracted data + compliance findings |
| `POST` | `/api/v1/uploads/{id}/generate-plan` | Feed extracted data into plan pipeline |
| `POST` | `/api/v1/uploads/{id}/generate-response` | Generate response doc from findings |

### Ingestion (7 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/admin/ingest/building-permits` | Trigger building permit CKAN ingestion |
| `POST` | `/api/v1/admin/ingest/coa-applications` | Trigger CoA application ingestion |
| `POST` | `/api/v1/admin/ingest/water-mains` | Trigger water main ingestion |
| `POST` | `/api/v1/admin/ingest/sanitary-sewers` | Trigger sanitary sewer ingestion |
| `POST` | `/api/v1/admin/ingest/storm-sewers` | Trigger storm sewer ingestion |
| `POST` | `/api/v1/admin/ingest/bridges` | Trigger bridge inventory ingestion |
| `GET` | `/api/v1/admin/ingest/status` | Ingestion status + dataset counts |

### Infrastructure (3 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/infrastructure/pipelines/nearby` | Nearby pipeline assets (GeoJSON) |
| `POST` | `/api/v1/infrastructure/compliance/pipeline` | Pipeline compliance check |
| `GET` | `/api/v1/infrastructure/watermains/bbox` | Watermain segments in viewport |

### Compliance, Exports, Design, Governance, Policy, Jobs (12 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/compliance/interior` | OBC interior compliance check |
| `POST` | `/api/v1/exports` | Create export job |
| `GET` | `/api/v1/exports/{id}` | Get export result |
| `POST` | `/api/v1/designs/{project_id}/branches` | Create design branch |
| `GET` | `/api/v1/designs/{project_id}/branches` | List branches |
| `DELETE` | `/api/v1/designs/{project_id}/branches/{id}` | Delete branch |
| `POST` | `/api/v1/designs/branches/{id}/commit` | Commit version |
| `GET` | `/api/v1/designs/branches/{id}/versions` | List versions |
| `GET` | `/api/v1/designs/branches/{id}/latest` | Get latest version |
| `GET` | `/api/v1/designs/versions/{id}` | Get specific version |
| `GET` | `/api/v1/snapshot-manifests/{id}` | Get manifest (admin) |
| `GET` | `/api/v1/review-queue` | List review items (admin) |
| `GET` | `/api/v1/policies/search` | Policy search (stub) |
| `POST` | `/api/v1/scenarios/{id}/policy-overrides` | Policy overrides (stub) |
| `GET` | `/api/v1/jobs/{id}` | Generic job status polling |

---

## Running Locally

```bash
# Backend
uvicorn app.main:app --reload

# Frontend
cd frontend-react && npm run dev

# RAG (optional, for policy retrieval)
cd fine-tuned-RAG && python api.py
```
