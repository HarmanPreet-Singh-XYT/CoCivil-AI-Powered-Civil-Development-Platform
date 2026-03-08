---
name: infrastructure-assessment
version: "1.0"
description: "Evaluates the condition of municipal infrastructure assets (pipes, bridges, culverts, manholes) using inspection data, age, material, and failure history. This skill should be used when an asset ID or location is available and the pipeline needs a `condition_assessment.json` with condition rating, remaining useful life estimate, and rehabilitation priority."
source: "Ontario Provincial Standard Specifications (OPSS), CSA S6:19, MTO BIM, OSIM"
authority: "Province of Ontario, Ministry of Transportation Ontario, Canadian Standards Association"
data_as_of: "2026-03-08"
pipeline_position: 1
pipeline_outputs: "condition_assessment.json"
pipeline_downstream: "infrastructure-standards"
---

# Infrastructure Assessment

## Purpose

Produce a structured condition assessment for a municipal infrastructure asset. Evaluate physical condition indicators against applicable standards, estimate remaining useful life, and classify rehabilitation urgency. Do not design remediation here — only assess current state and flag deficiencies.

Keep this skill narrow:
- Collect and normalize inspection data
- Evaluate condition against applicable standards (OPSD, CSA S6, OSIM)
- Score condition and estimate remaining service life
- Flag critical deficiencies and safety concerns
- Hand off to `infrastructure-standards` for design-standard lookups if needed

## Use when

- An infrastructure asset needs a condition assessment
- Inspection data, age, material type, or failure history is available
- The next step needs a `condition_assessment.json`

## Do not use when

- The task is to design a new asset or select materials
- The task is to look up a specific standard requirement (use `infrastructure-standards`)
- The task is to produce a capital plan or budget estimate

## Inputs

```json
{
  "project_id": "uuid",
  "asset_type": "storm_sewer | sanitary_sewer | watermain | bridge | culvert | manhole | catchbasin",
  "asset_id": "municipal asset ID or null",
  "location": {
    "address": "123 Main St, Toronto ON",
    "coordinates": [43.6532, -79.3832],
    "road_name": "Main Street",
    "municipality": "Toronto"
  },
  "known_attributes": {
    "material": "concrete | PVC | HDPE | steel | cast_iron | ductile_iron | corrugated_steel_pipe",
    "diameter_mm": 600,
    "length_m": 120,
    "install_year": 1965,
    "depth_m": 3.0,
    "last_inspection_date": "2023-06-15",
    "inspection_type": "CCTV | visual | OSIM | load_test"
  },
  "inspection_data": {},
  "failure_history": []
}
```

Required fields:
- `asset_type`
- One of `asset_id` or `location`

Optional fields:
- `known_attributes` (improves assessment quality)
- `inspection_data` (raw inspection findings)
- `failure_history` (past breaks, collapses, or service disruptions)

## Outputs

Produce exactly one artifact: `condition_assessment.json`.

```json
{
  "project_id": "uuid",
  "asset_type": "storm_sewer",
  "asset_id": "municipal ID",
  "assessment_timestamp": "ISO datetime",
  "condition_rating": {
    "overall": 1,
    "structural": 2,
    "operational": 1,
    "scale": "1-5 (1=very good, 5=very poor)",
    "methodology": "PACP | OSIM | visual | estimated"
  },
  "remaining_useful_life_years": {
    "estimate": 15,
    "confidence": "high | medium | low",
    "basis": "age-based | condition-based | failure-rate"
  },
  "deficiencies": [
    {
      "deficiency_type": "structural_crack | joint_displacement | corrosion | scour | spalling | deformation | blockage | infiltration",
      "severity": "minor | moderate | severe | critical",
      "location_description": "At joint 3, 45m from upstream MH",
      "standard_reference": "OPSD 701.010",
      "requires_immediate_action": false
    }
  ],
  "rehabilitation_priority": "routine | planned | urgent | emergency",
  "material_condition": {
    "material": "concrete",
    "age_years": 61,
    "expected_service_life_years": 75,
    "corrosion_risk": "low | medium | high",
    "notes": ""
  },
  "hydraulic_adequacy": {
    "capacity_adequate": true,
    "basis": "design flow vs observed | Manning's calc | unknown"
  },
  "safety_flags": [],
  "facts": [],
  "inferences": [],
  "assumptions": [],
  "unknowns": [],
  "recommended_next_skill": "infrastructure-standards"
}
```

## Reference Router

Load only the reference file relevant to the current assessment:

| Asset Type | Load This Reference |
|------------|--------------------|
| **Pipes (storm, sanitary, watermain)** | `references/opsd-standards.md` |
| **Bridges and culverts** | `references/csa-s6-bridge-code.md` |
| **Both pipe and structure** | Both files |

---

## Workflow

### 1. Identify the asset and collect attributes

- Confirm asset type and location
- Gather material, age, diameter/span, depth, and installation year
- If asset_id is provided, look up municipal records
- If only location is provided, identify assets from spatial data

### 2. Review inspection data

For pipes (CCTV inspection):
- Apply PACP (Pipeline Assessment Certification Program) grading where available
- Grade structural defects: cracks, fractures, deformation, joint displacement, collapse
- Grade operational defects: roots, deposits, infiltration, exfiltration
- Note defect location by distance from upstream manhole

For bridges and culverts (OSIM inspection):
- Apply Ontario Structure Inspection Manual condition states (1-4)
- Evaluate: deck/top slab, soffit, walls/abutments, bearings, foundations, waterway adequacy
- Check for scour, spalling, reinforcement exposure, bearing failure

### 3. Evaluate material condition

Use age-based deterioration curves when inspection data is insufficient:

| Material | Expected Service Life |
|----------|----------------------|
| Concrete pipe (non-reinforced) | 50-75 years |
| Reinforced concrete pipe | 75-100 years |
| PVC pipe | 75-100 years |
| HDPE pipe | 50-75 years |
| Vitrified clay pipe | 75-100+ years |
| Corrugated steel pipe | 25-50 years |
| Cast iron watermain | 75-100 years |
| Ductile iron watermain | 75-100+ years |
| Concrete bridge deck | 50-75 years |
| Steel bridge superstructure | 75-100 years |

Adjust for:
- Soil conditions (corrosive soils reduce life by 20-40%)
- Traffic loading (heavy truck routes accelerate deterioration)
- Water chemistry (aggressive water reduces pipe life)
- Maintenance history (regular cleaning extends operational life)

### 4. Assess hydraulic adequacy

For pipes:
- Compare design capacity against current service demand
- Flag undersized infrastructure based on current IDF curves
- Note if upstream development has increased flows beyond design

For bridges:
- Check waterway adequacy for design flood
- Assess freeboard requirements

### 5. Rate overall condition

Apply a 1-5 condition rating:

| Rating | Condition | Description |
|--------|-----------|-------------|
| 1 | Very Good | New or recently rehabilitated, no defects |
| 2 | Good | Minor deterioration, fully functional, routine maintenance only |
| 3 | Fair | Moderate deterioration, functional but approaching planned intervention |
| 4 | Poor | Significant deterioration, rehabilitation needed within 5 years |
| 5 | Very Poor | Failed or imminent failure, emergency intervention required |

### 6. Classify rehabilitation priority

| Priority | Criteria |
|----------|----------|
| Routine | Condition 1-2, no safety concerns |
| Planned | Condition 3, schedule for capital program |
| Urgent | Condition 4, prioritize in next budget cycle |
| Emergency | Condition 5, immediate action required |

### 7. Flag safety concerns

Always check for:
- Structural collapse risk (condition 5 structural)
- Sinkhole potential (pipe failure under roadway)
- Bridge load posting requirements (reduced load capacity)
- Environmental release risk (sanitary sewer failure near watercourse)
- Public safety hazards (exposed reinforcement, barrier failure)

## Quality Bar

- Never assign condition rating 1-2 without supporting inspection data or known recent rehabilitation
- Age alone is insufficient for a rating worse than 3 — require deficiency evidence for ratings 4-5
- Always distinguish between facts (inspection results) and inferences (age-based estimates)
- Flag every assumption explicitly

## Stop Conditions

Stop and return a partial artifact when:
- Asset type cannot be determined
- No inspection data and no installation date are available
- Location is ambiguous and multiple assets could match
- Inspection data format is unrecognizable

## Reference Files

| File | Description | Key Topics |
|------|-------------|------------|
| `references/opsd-standards.md` | Ontario Provincial Standard Drawings for pipes and manholes | OPSD 701, 702, 704 series; standard dimensions, materials, installation requirements |
| `references/csa-s6-bridge-code.md` | CSA S6:19 Canadian Highway Bridge Design Code | CL-625 loading, design criteria, clearances, deck widths, evaluation procedures |

Read only the reference file relevant to the asset type being assessed.

## External References

| Source | URL | Use |
|--------|-----|-----|
| Ontario Structure Inspection Manual (OSIM) | https://www.ontario.ca/page/ontario-structure-inspection-manual | Bridge and culvert inspection methodology |
| NASSCO PACP | https://www.nassco.org/pacp | Pipeline Assessment Certification Program |
| Ontario Provincial Standards | https://www.ontario.ca/page/provincial-standards | OPSD and OPSS lookup |
| CSA Group Standards | https://www.csagroup.org/ | CSA S6 and other infrastructure standards |
