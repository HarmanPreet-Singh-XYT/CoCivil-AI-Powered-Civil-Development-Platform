# CoCivil — AI-Powered Civil Development Platform

**CoCivil** is an advanced AI-powered due-diligence and design platform tailored for land development in Ontario, Canada. It bridges the gap between plain-English development queries and complete planning submission packages (compliance matrices, rationales, precedent reports, massing models, and floor plans) in a fraction of the usual time.

---

# 🚀 Core Features & Capabilities

## Parcel Intelligence & Geospatial Search
- Search any Toronto address or parcel PIN.
- Instantly retrieve zoning information from **Zoning By-law 569-2013**, including:
  - Official Plan designations
  - Overlays
  - Setbacks
  - Height limits
  - Lot coverage
- Data is sourced directly from **Toronto Open Data**.
- Performs adjacency analysis, frontage detection, and spatial joins for full site context evaluation.

---

## AI Planning Assistant
- Conversational chat interface with an AI agent trained on **Ontario planning law**.
- Grounded in key legislation and policy frameworks including:
  - Planning Act
  - Provincial Planning Statement (PPS 2024)
  - Ontario Regulation 462/24
- Capabilities include:
  - Answering complex zoning questions
  - Proposing variance strategies
  - Identifying optimal approval pathways.

---

## Automated Document & Report Generation
Automatically generates development documentation including:

- Planning rationales
- Compliance matrices
- Shadow studies
- Planning submission packages

Outputs are:
- Auditable
- Grounded in cited planning policies
- Flagged for professional review.

---

## 3D Massing & Floor Plan Editor

### Text-to-3D Massing
- Describe a building in plain English.
- Generates a **3D massing model** using Three.js.

### 2D Floor Plan Editor
- Interactive floor plan editing powered by Konva.js.
- Real-time **Ontario Building Code (OBC)** compliance checking.
- Violations are highlighted instantly.

---

## Infrastructure Design & Assessment
Supports planning and analysis for municipal infrastructure systems.

Features include:
- Upload pipeline **DXF files**.
- 3D visualization of pipe networks.
- OPSD-compliant specifications.
- Infrastructure condition assessments.

Supported systems:
- Water
- Electrical
- Stormwater and drainage networks.

---

## Precedent Research & Entitlement Scoring
AI-powered precedent discovery across:

- Committee of Adjustment decisions
- Ontario Land Tribunal (OLT)
- CanLII legal databases

Capabilities:
- Identifies comparable approvals and refusals near the subject site
- Calculates **entitlement risk scores** based on:
  - Compliance gaps
  - Variance magnitudes
  - Policy conflicts.

---

## Financial Pro Forma & Layout Optimization
Automatically evaluates development feasibility.

Features include:
- Unit mix and floor area allocation
- Layout optimization
- Construction cost estimation
- Revenue modeling
- Net Operating Income (NOI) projections
- Property valuation estimates

Also supports **Variance Simulation**, allowing users to fork policy scenarios and test development outcomes under different approval assumptions.

---

## Policy RAG (Retrieval-Augmented Generation) Engine
Fine-tuned RAG pipeline for policy and legal retrieval.

Capabilities:
- Vector search using **ChromaDB**
- Searches across:
  - Ontario planning documents
  - Zoning by-laws
  - Building code references
- Extracts and cites exact legal clauses and normalized regulatory rules.

---

# 🏗️ Technical Architecture

CoCivil is structured as a **modular monolith** optimized for asynchronous analysis workflows and spatial data processing.

---

## 1. Frontend (`frontend-react/`)

**Framework**
- React 19 + Vite

**Mapping & Visualization**
- MapLibre GL for GIS mapping
- Three.js for 3D building and infrastructure massing
- Konva.js for:
  - 2D floor plan editing
  - Pipe network editing

**Authentication**
- Auth0

**Key UI Components**
- `ChatPanel`
- `PolicyPanel`
- `ModelViewer`
- `FloorPlanEditor`
- `InfrastructureViewer`

---

## 2. Backend (`app/`)

**Framework**
- FastAPI (Python)

Functions as:
- API Gateway
- Orchestration layer

**Database**
- PostgreSQL 16
- PostGIS for geospatial operations
- SQLAlchemy 2.0 (async)
- Alembic for database migrations

**Task Queue**
- Celery 5.3+
- Redis message broker

Used for long-running tasks such as:
- OCR processing
- Massing model generation
- Financial modeling workflows.

**AI Integration**
- Claude (primary)
- OpenAI (fallback)

Design principle:
- Deterministic compliance engines first
- AI used for extraction, reasoning, and summarization.

---

## 3. RAG Pipeline (`fine-tuned-RAG/`)

Components include:
- Document ingestion pipeline
- Semantic chunking and segmentation
- Vector indexing

Supported inputs:
- PDF documents
- HTML planning policies
- GIS data layers

Vector storage is handled by **ChromaDB**.

---

## 4. Skills Pipeline (`.claude/skills/`)

Sequential AI research pipeline designed for Ontario site feasibility.

Workflow chain:
Source Discovery\
↓\
Parcel Zoning\
↓\
Buildability Analysis\
↓\
Approval Pathway\
↓\
Precedent Research\
↓\
Constraints & Flags\
↓\
Report Generation

Each stage feeds structured outputs into the next stage to produce a final planning report.

---

# 📊 Data Domains & Processing

The system strictly **versions all data and outputs** to ensure deterministic and reproducible results.

### Geospatial Domain
Manages:
- Parcel boundaries
- Addresses
- Current land uses
- Planning overlays (transit, heritage, floodplains).

### Policy Domain
Separates:
- Raw legislative text
- Normalized structured regulatory rules

Example normalized rule:
max_height_m = 36

### Simulation Domain
Generates buildable envelopes using:
- Parcel geometry
- Zoning and policy constraints.

### Export Domain
Produces reproducible artifacts including:

- PDFs
- CSV files
- spreadsheets
- 3D models.

---

# 👥 Target Audience

### Land Developers
Rapid evaluation of site feasibility and financial viability.

### Urban Planners
Preparation of zoning research and planning submission packages.

### Architects
Quick generation of massing options and floor plan layouts.

### Civil Engineers
Infrastructure network design and gap analysis.

### Municipal Staff
Application review with standardized compliance checks.


---
```
./scripts/bootstrap_data.sh 
```
for Adding data to DB