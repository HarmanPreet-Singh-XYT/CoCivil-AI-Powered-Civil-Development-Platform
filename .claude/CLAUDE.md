# Hack Canada — CoCivil Platform

## Auto-Update Rule for index.md

**After every file edit, creation, or deletion**, update `index.md` at the project root to reflect the change. The update should:
- Add new files with their path and a 1-line purpose description in the appropriate section
- Update the entry for modified files if their purpose or API surface changed
- Remove entries for deleted files
- Keep the "Last updated" date current
- Do NOT rewrite the whole file — only edit the relevant section(s)

This rule applies to all agents and Claude sessions working on this codebase.

Land-development due diligence platform for Toronto / Ontario.
Generates planning submission packages (planning rationale, compliance matrix, precedent report, etc.) from a plain-English development query.

---

## Project Structure

```
app/
  data/           toronto_zoning.py (hardcoded By-law 569-2013 standards)
                  ontario_policy.py (policy hierarchy, OP designations, OBC, four tests, legislation)
  models/         entitlement.py, geospatial.py, plan.py, ingestion.py
  routers/        plans, entitlement, ingestion, auth, assistant, uploads
  services/       geospatial_ingestion.py, ckan_ingestion.py, compliance_engine.py,
                  thin_slice_runtime.py, zoning_service.py
                  submission/ (templates.py, context_builder.py, review.py)
  tasks/          plan.py (main pipeline), ingestion.py (CKAN tasks)
frontend-react/   React frontend (Vite)
```

## Tech Stack

- **Backend**: FastAPI + SQLAlchemy (async) + PostgreSQL + PostGIS
- **Background Tasks**: threading (in-process)
- **Frontend**: React + Vite
- **AI**: Claude (primary) or OpenAI (configurable via AI_PROVIDER)
- **Spatial**: GeoAlchemy2, PostGIS, pyproj

---

## Skills System

The `.claude/skills/` directory contains a structured pipeline for Ontario site-feasibility research. Each skill is a self-contained agent instruction with defined inputs, outputs, and reference files.

### When to Use Skills

Use skills when you need to **research a real parcel** beyond what's in the database — fetching live data from official sources, interpreting policy, or classifying an approval pathway.

Skills are invoked by loading the relevant `SKILL.md` as context and following its workflow. Each skill produces a JSON artifact consumed by the next.

### Pipeline Order

```
Address / Parcel Input
        │
        ▼
  source-discovery          → source_bundle.json
  (finds official URLs)
        │
        ▼
  parcel-zoning-research    → normalized_data.json
  (extracts zone, OP, overlays)
        │
        ├─────────────────────────────┐
        ▼                             ▼
  buildability-analysis     precedent-research    → precedent_packet.json
  (feasibility verdict)     (AIC, OLT, CanLII)
        │                             │
        ▼                             ▼
  constraints-red-flags     approval-pathway      → approval_pathway.json
  (OBC, risk flags)         (route + timeline)
        │                             │
        └──────────────┬──────────────┘
                       ▼
               report-generator      → final_report.md
```

### Skill Reference

| Skill | When to Use | Key Output |
|-------|------------|------------|
| `source-discovery` | New project, need official source URLs | `source_bundle.json` |
| `parcel-zoning-research` | Extract zone code, OP designation, overlays | `normalized_data.json` |
| `buildability-analysis` | Feasibility verdict + compliance gaps | `analysis_packet.json` |
| `precedent-research` | Find comparable CoA/ZBA decisions nearby | `precedent_packet.json` |
| `constraints-red-flags` | OBC hard constraints, risk flags | `constraints_packet.json` |
| `approval-pathway` | Classify route (as-of-right / CoA / ZBA / OPA) | `approval_pathway.json` |
| `report-generator` | Assemble final client-facing report | `final_report.md` |

### How to Invoke a Skill

Read the relevant `SKILL.md` from `.claude/skills/<name>/SKILL.md`, follow its workflow, and load only the reference files it specifies in its Reference Router table. Do not load all reference files — load only what the current task requires.

**Example**: To research 100 King St W:
1. Run `source-discovery` → get URLs for parcel data, zoning, OP, AIC
2. Run `parcel-zoning-research` with those URLs → get zone code, OP designation, overlays
3. Run `buildability-analysis` → get feasibility verdict and compliance gaps
4. Run `approval-pathway` → classify the entitlement route and estimate timeline

### Reference Files

Each skill has a `references/` subdirectory with policy and data documents:

| File | What It Contains |
|------|-----------------|
| `parcel-zoning-research/references/ontario-policy-framework.md` | Full Ontario policy hierarchy, PPS 2024, OP designations, O.Reg 462/24, Bills 23/185/60 |
| `parcel-zoning-research/references/toronto-zoning-guide.md` | By-law 569-2013 standards by zone type, Chapter 900, hatched areas, CR mid-rise formula |
| `constraints-red-flags/references/obc-hard-constraints.md` | OBC requirements CoA cannot vary: fire access, limiting distances, Part 9/3 thresholds |
| `constraints-red-flags/references/construction-risk-red-flags.md` | Subcontractor default signals, DSC risk, scope creep, stop-work triggers |
| `approval-pathway/references/planning-approvals-process.md` | Full approval decision tree, four statutory tests, timelines, Bill 60 (2025) |
| `approval-pathway/references/building-permit-process.md` | Building permit process detail |
| `approval-pathway/references/external-approvals.md` | TRCA, heritage, conservation authority processes |
| `precedent-research/references/toronto-planning-sources.md` | AIC, OLT, CanLII, TLAB — how to find and read decisions |
| `precedent-research/references/project-history-risk-patterns.md` | Risk signals from permit history |
| `source-discovery/references/toronto-open-data.md` | Toronto CKAN API endpoints, package IDs, geocoding |
| `source-discovery/references/ontario-data-portals.md` | Ontario portal patterns, LIO, MPAC, TRCA, OnLand |
| `buildability-analysis/references/analysis-framework.md` | Dimensional compliance checklist, confidence scoring |

---

