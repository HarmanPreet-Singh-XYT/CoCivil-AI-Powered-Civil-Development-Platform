# Arterial — Land Development Due Diligence Platform

> Backend API for parcel discovery, policy resolution, building simulation, financial modeling, and entitlement assessment. Toronto MVP.

---

## Quick Start

```bash
# 1. Copy local config once
cp .env.example .env

# 2. Start local infrastructure
make infra-up

# 3. Verify targets and connectivity
make doctor

# 4. Run database migrations
make migrate

# 5. Start the API in another terminal
make run-api

# 6. Verify
curl http://localhost:8000/api/v1/health
# → {"status":"healthy","database":"ok","redis":"ok","version":"0.1.0"}

# 7. Browse API docs
open http://localhost:8000/docs
```

---

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   FastAPI    │────▶│   Celery     │────▶│  PostgreSQL  │
│   API (8000) │     │   Workers    │     │  + PostGIS   │
└──────┬───────┘     └──────┬───────┘     │  + pgvector  │
       │                    │             └──────────────┘
       │                    │
       ▼                    ▼
┌─────────────┐     ┌─────────────┐
│    Redis     │     │    MinIO     │
│  Cache/Queue │     │  Object Store│
└─────────────┘     └─────────────┘
```

| Service | Port | Purpose |
|---------|------|---------|
| API | 8000 | FastAPI application server (local by default) |
| PostgreSQL + PostGIS | 5432 | Spatial database with vector search |
| Redis | 6379 | Cache, message broker, idempotency store |
| MinIO | 9000 / 9001 | S3-compatible document and artifact storage |
| Celery Worker | — | Async job processing (local by default) |
| Celery Beat | — | Optional scheduled task runner |

---

## Project Structure

```
Hack_Canada/
├── app/
│   ├── main.py              # FastAPI app factory
│   ├── config.py             # Environment settings (Pydantic)
│   ├── database.py           # Async + sync DB engines, Redis
│   ├── worker.py             # Celery app + beat schedule
│   ├── dependencies.py       # Shared FastAPI deps (auth, DB session)
│   ├── middleware/            # Request ID, idempotency
│   ├── models/               # SQLAlchemy 2.0 ORM models (34 tables)
│   ├── schemas/              # Pydantic v2 request/response schemas
│   ├── routers/              # API endpoint handlers
│   ├── services/             # Business logic (job status lookup)
│   └── tasks/                # Celery task stubs (massing, layout, etc.)
├── alembic/                  # Database migrations
├── tests/                    # Pytest async test suite
├── scripts/                  # Dev, seed, and audit entrypoints
├── docker-compose.yml        # Infra-only compose (db, redis, minio)
├── docker-compose.app.yml    # Optional containerized app services
├── Makefile                  # Blessed local dev commands
├── Dockerfile                # Python 3.11 + GDAL/GEOS/PROJ
└── pyproject.toml            # PEP 621 project config
```

---

## API Endpoints

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | DB + Redis connectivity check |

### Projects

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/projects` | Create project |
| GET | `/api/v1/projects` | List projects |
| GET | `/api/v1/projects/{id}` | Get project |
| PATCH | `/api/v1/projects/{id}` | Update project |
| POST | `/api/v1/projects/{id}/parcels` | Add parcel to project |
| DELETE | `/api/v1/projects/{id}/parcels/{parcel_id}` | Remove parcel |

### Parcels

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/parcels/search` | Search by address, PIN, zoning, bbox |
| GET | `/api/v1/parcels/{id}` | Parcel detail |
| GET | `/api/v1/parcels/{id}/policy-stack` | Applicable policies (stub) |
| GET | `/api/v1/parcels/{id}/overlays` | GIS overlays (stub) |

### Scenarios

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/projects/{id}/scenarios` | Create scenario (base/variance/what_if) |
| GET | `/api/v1/scenarios/{id}` | Get scenario |
| GET | `/api/v1/scenarios/{id}/compare/{other_id}` | Compare two scenarios (stub) |

### Simulation (async — returns 202)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/scenarios/{id}/massings` | Generate building massing |
| GET | `/api/v1/massings/{id}` | Get massing result |
| POST | `/api/v1/massings/{id}/layout-runs` | Run unit mix optimization |
| GET | `/api/v1/layout-runs/{id}` | Get layout result |

### Finance (async — returns 202)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/scenarios/{id}/financial-runs` | Run pro forma analysis |
| GET | `/api/v1/financial-runs/{id}` | Get financial result |

### Entitlement (async — returns 202)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/scenarios/{id}/entitlement-runs` | Run compliance check |
| GET | `/api/v1/entitlement-runs/{id}` | Get entitlement result |
| POST | `/api/v1/scenarios/{id}/precedent-searches` | Search precedent applications |
| GET | `/api/v1/precedent-searches/{id}` | Get search results |

### Policy

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/policies/search` | Search policy clauses (stub) |
| POST | `/api/v1/scenarios/{id}/policy-overrides` | Override policy for variance (stub) |

### Exports (async — returns 202)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/exports` | Generate export (PDF/CSV/XLSX) |
| GET | `/api/v1/exports/{id}` | Get export status + download link |

### Jobs

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/jobs/{id}` | Universal job status polling |

---

## Database Schema

34 tables across 10 domains:

### Tenant & Project
`organizations` · `users` · `workspace_members` · `projects` · `project_shares` · `scenario_runs`

### Geospatial
`jurisdictions` · `parcels` · `parcel_metrics` · `project_parcels`

### Policy
`policy_documents` · `policy_versions` · `policy_clauses` · `policy_references` · `policy_applicability_rules`

### Dataset
`dataset_layers` · `dataset_features` · `feature_to_parcel_links`

### Simulation
`massing_templates` · `massings` · `unit_types` · `layout_runs`

### Finance
`market_comparables` · `financial_assumption_sets` · `financial_runs`

### Entitlement & Precedent
`entitlement_results` · `precedent_searches` · `development_applications` · `application_documents` · `rationale_extracts`

### Export & Audit
`export_jobs` · `audit_events`

### Ingestion
`source_snapshots` · `ingestion_jobs`

### Key Database Features
- **PostGIS** geometry columns (MultiPolygon, Point, Polygon) with GIST indexes
- **pgvector** `Vector(384)` columns for semantic search with IVFFlat indexes
- **GIN indexes** on tsvector for full-text search (addresses, policy text)
- **UUID primary keys** on all tables via `uuid-ossp`
- **Timestamp mixins** (`created_at`, `updated_at`) on all tables

---

## Async Job Pattern

All heavy operations follow the same pattern:

```
Client                    API                     Celery Worker
  │                        │                           │
  │  POST /scenarios/X/massings                        │
  │───────────────────────▶│                           │
  │                        │  create DB record         │
  │                        │  dispatch task ──────────▶│
  │  202 Accepted          │                           │
  │  {job_id, location}   ◀│                           │
  │◀───────────────────────│                           │
  │                        │                           │  process...
  │  GET /jobs/{job_id}    │                           │
  │───────────────────────▶│                           │
  │  {status: "pending"}  ◀│                           │
  │◀───────────────────────│                           │
  │                        │         update status ◀───│
  │  GET /jobs/{job_id}    │                           │
  │───────────────────────▶│                           │
  │  {status: "completed"} │                           │
  │◀───────────────────────│                           │
```

---

## Configuration

Local development reads `.env`. `.env.example` is a template for `.env`, not a live runtime env file for containerized app services.

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql+asyncpg://arterial:arterial@localhost:5432/arterial` | Async DB connection |
| `DATABASE_URL_SYNC` | `postgresql+psycopg2://arterial:arterial@localhost:5432/arterial` | Sync DB (Celery/Alembic) |
| `REDIS_URL` | `redis://localhost:6379/0` | Cache and idempotency |
| `S3_ENDPOINT_URL` | `http://localhost:9000` | Object storage |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | `minioadmin` | MinIO credentials |
| `JWT_SECRET_KEY` | `change-me-in-production` | Auth token signing |
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | Task queue broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | Task result store |
| `API_V1_PREFIX` | `/api/v1` | API route prefix |

---

## Development

```bash
# Install locally
pip install -e ".[dev]"

# Start infra
make infra-up

# Verify connectivity
make doctor

# Run the API / worker / frontend locally
make run-api
make run-worker
make run-frontend

# Run migrations
make migrate

# Seed and audit Toronto data
make seed-toronto
make seed-policies
make audit-toronto

# Run tests
make test-backend
make test-frontend
```

Optional full-container app mode:

```bash
docker compose -f docker-compose.yml -f docker-compose.app.yml up --build api worker

# If you need the scheduler too
docker compose -f docker-compose.yml -f docker-compose.app.yml --profile scheduler up beat
```

---

## What's Implemented vs. Stubbed

| Component | Status | Notes |
|-----------|--------|-------|
| Docker stack | Done | Infra-only by default; optional app compose available |
| Database schema | Done | 34 tables with spatial + vector indexes |
| API routing | Done | 29 endpoints, Swagger docs |
| Auth | **Stubbed** | Returns mock user; real JWT next |
| Massing algorithm | **Stubbed** | Celery task logs start/end |
| Layout optimizer | **Stubbed** | Celery task logs start/end |
| Financial pro forma | **Stubbed** | Celery task logs start/end |
| Entitlement engine | **Stubbed** | Celery task logs start/end |
| Precedent search | **Stubbed** | Celery task logs start/end |
| Export generation | **Stubbed** | Celery task logs start/end |
| Policy extraction | **Stubbed** | Search returns empty |
| Data ingestion | **Stubbed** | Tables exist, no pipelines |

---

## Related Docs

- [Implementation Plan](./IMPLEMENTATION_PLAN.md) — full technical spec with schema DDL, algorithms, and phase breakdown
- [Data Plan](./DATA_PLAN.md) — reality-checked MVP data plan, source priorities, pipeline flow, and schema gaps
- [Track 5-6 Research](./TRACK_5_6_RESEARCH.md) — focused research notes for simulation defaults and precedent/permit data
- [Backend Analysis](./arterial_backend_clone_analysis.md) — analysis of the Arterial product architecture
