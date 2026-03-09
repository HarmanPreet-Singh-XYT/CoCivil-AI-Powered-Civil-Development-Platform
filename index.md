# CoCivil — AI-Powered Civil Development Platform

> **Auto-maintained**: Updated after every file edit/creation. See `.claude/CLAUDE.md` for rules.
> **Last updated**: 2026-03-08 (Celery migration) | **PRD**: [`.claude/docs/PRD.md`](.claude/docs/PRD.md)

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
│  18 API routers · 35 services · 9 background tasks      │
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
5. [Data & Infrastructure Files](#data--infrastructure-files)
6. [Config & DevOps](#config--devops)
7. [API Endpoint Reference](#api-endpoint-reference)

---

## Backend — `app/`

### Entry Points

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app factory, route registration, middleware |
| `app/config.py` | Settings (DB, AI provider, S3, Auth0) |
| `app/database.py` | SQLAlchemy engine & async session |
| `app/dependencies.py` | FastAPI dependency injection |

### Database Models (`app/models/`)

| File | Purpose |
|------|---------|
| `base.py` | Base model (timestamps, soft deletes) |
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
| `compliance.py` | `/api/v1/compliance` | Code compliance checks |
| `infrastructure.py` | `/api/v1/infrastructure` | Water/electrical/drainage |
| `geospatial.py` | `/api/v1/geospatial` | GIS operations |
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
| `zoning_service.py` | Zoning validation |
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
| `job_service.py` | Async task management |
| `storage.py` | File storage (S3 + local) |
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

17 Pydantic request/response schema files: `common.py`, `plan.py`, `entitlement.py`, `geospatial.py`, `finance.py`, `infrastructure.py`, etc.

### Celery App

| File | Purpose |
|------|---------|
| `app/celery_app.py` | Celery application config (broker=Redis, JSON serialization, autodiscover) |

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
| `src/index.css` | Global styles |
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
| `populate_rag.py` | Initial population script |
| `populate_direct.py` | Direct database population |
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

## Data & Infrastructure Files

| Path | Purpose |
|------|---------|
| `data/property-boundaries-4326.geojson` | Toronto property parcels (WGS84) |
| `data/zoning-area-4326.geojson` | Zoning designations |
| `data/zoning-building-setback-overlay-4326.geojson` | Setback overlays |
| `data/zoning-height-overlay-4326.geojson` | Height restriction overlays |
| `data/development-applications.json` | CoA/ZBA/OPA precedent records |
| `water-system-data/` | Water infrastructure GeoJSON + metadata |
| `water-policy/` | Water infrastructure policy documents |
| `Road/` | Road infrastructure data |
| `City-electric-charge/` | Electric charging infrastructure |

---

## Config & DevOps

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Local dev (Postgres + PostGIS + app) |
| `docker-compose.app.yml` | App-only compose |
| `Dockerfile` | Production build |
| `railway.toml` | Railway deployment config |
| `alembic.ini` | Alembic migration config |
| `alembic/` | Database migration versions |
| `pyproject.toml` | Python project config (uv) |
| `Makefile` | Build targets |
| `.env.example` | Environment variable template |

---

## API Endpoint Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/parcels/search` | Search parcels by address |
| `GET` | `/api/v1/parcels/{id}` | Get parcel details |
| `GET` | `/api/v1/parcels/{id}/policy-stack` | Get applicable policies (RAG) |
| `GET` | `/api/v1/parcels/{id}/overlays` | Get zoning overlays |
| `GET` | `/api/v1/parcels/{id}/zoning-analysis` | Full zoning analysis |
| `GET` | `/api/v1/parcels/{id}/nearby-applications` | Nearby dev applications |
| `GET` | `/api/v1/parcels/{id}/financial-summary` | Financial feasibility |
| `POST` | `/api/v1/plans` | Create development plan |
| `GET` | `/api/v1/plans/{id}` | Get plan status & data |
| `GET` | `/api/v1/plans/{id}/documents` | Get generated documents |
| `POST` | `/api/v1/plans/{id}/documents/{type}/regenerate` | Regenerate a document |
| `POST` | `/api/v1/assistant/chat` | AI chat with context |
| `POST` | `/api/v1/uploads` | Upload document for analysis |
| `GET` | `/api/v1/uploads/{id}` | Get upload status & extracts |
| `POST` | `/api/v1/ingestion/building-permits` | Ingest building permits |
| `POST` | `/api/v1/ingestion/coa-applications` | Ingest CoA applications |
| `GET` | `/api/health` | Health check |

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
