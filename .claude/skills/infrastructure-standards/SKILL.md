---
name: infrastructure-standards
version: "1.0"
description: "Looks up and interprets Ontario Provincial Standard Drawings (OPSD), Ontario Provincial Standard Specifications (OPSS), CSA standards, and MTO design guidelines for municipal infrastructure. This skill should be used when a design question, standard reference, or material selection needs authoritative Ontario infrastructure standards."
source: "OPSD, OPSS, CSA S6:19, MTO Drainage Management Manual, MTO Geometric Design Standards"
authority: "Province of Ontario, Ministry of Transportation Ontario, Canadian Standards Association"
data_as_of: "2026-03-08"
pipeline_position: 2
pipeline_inputs: "condition_assessment.json (optional)"
pipeline_outputs: "standards_lookup.json"
pipeline_upstream: "infrastructure-assessment"
pipeline_downstream: "report-generator"
---

# Infrastructure Standards

## Purpose

Retrieve and interpret the correct Ontario and Canadian infrastructure design standards for a given question, asset type, or design scenario. Provide the authoritative standard reference, key requirements, and applicable design parameters. Do not perform the engineering design — provide the standard requirements that a designer needs.

Keep this skill narrow:
- Identify the applicable standard (OPSD, OPSS, CSA, MTO manual)
- Extract the relevant requirements and parameters
- Note exceptions, recent amendments, and jurisdiction-specific overrides
- Provide the standard reference for traceability

## Use when

- A design question requires an Ontario infrastructure standard lookup
- Material selection needs OPSD/OPSS guidance
- Drainage design needs MTO manual parameters
- Bridge design needs CSA S6 requirements
- A condition assessment references a standard that needs interpretation

## Do not use when

- The task is to assess existing asset condition (use `infrastructure-assessment`)
- The task is to produce a final engineering design (outside scope — requires P.Eng.)
- The task is a planning or zoning question (use planning skills)

## Inputs

```json
{
  "project_id": "uuid",
  "query_type": "standard_lookup | material_selection | design_parameter | specification_check",
  "asset_type": "storm_sewer | sanitary_sewer | watermain | bridge | culvert | manhole | catchbasin | road | sidewalk",
  "query": "What is the minimum cover for a 600mm storm sewer under a municipal road?",
  "context": {
    "municipality": "Toronto",
    "road_classification": "local | collector | arterial | expressway",
    "design_flow_m3s": null,
    "pipe_material": null,
    "span_m": null,
    "conditions": []
  },
  "condition_assessment_path": "condition_assessment.json (optional)"
}
```

Required fields:
- `query_type`
- `query` (natural language question or standard reference number)

Optional fields:
- `asset_type` (improves lookup accuracy)
- `context` (provides design scenario details)
- `condition_assessment_path` (links to upstream assessment)

## Outputs

Produce `standards_lookup.json`.

```json
{
  "project_id": "uuid",
  "lookup_timestamp": "ISO datetime",
  "query": "original query",
  "applicable_standards": [
    {
      "standard_id": "OPSD 802.010",
      "title": "Bedding and Cover for Flexible and Rigid Pipes",
      "category": "OPSD | OPSS | CSA | MTO",
      "version": "November 2019",
      "requirements": [
        {
          "parameter": "Minimum cover — rigid pipe under roadway",
          "value": "1.2 m",
          "conditions": "Measured from top of pipe to finished road surface",
          "exceptions": "May be reduced to 0.6m with engineered concrete encasement"
        }
      ],
      "related_standards": ["OPSS 410", "OPSD 802.030"],
      "notes": ""
    }
  ],
  "design_parameters": {},
  "municipality_overrides": [],
  "facts": [],
  "inferences": [],
  "assumptions": [],
  "unknowns": []
}
```

## Reference Router

Load only the reference file relevant to the query:

| Query Topic | Load This Reference |
|-------------|--------------------|
| **Pipe standards, manholes, catchbasins** | `../infrastructure-assessment/references/opsd-standards.md` |
| **Bridge and culvert design** | `../infrastructure-assessment/references/csa-s6-bridge-code.md` |
| **Drainage design, hydrology, stormwater** | `references/mto-drainage-manual.md` |
| **Multiple topics** | Load only the relevant files — never load all |

---

## Workflow

### 1. Parse the query

- Identify the asset type and design scenario
- Determine whether the question is about a specific standard number or a general design requirement
- If a standard number is provided (e.g., "OPSD 701.010"), go directly to that standard
- If a general question, identify the applicable standard category

### 2. Identify applicable standards

Follow the Ontario infrastructure standards hierarchy:

| Priority | Standard | Scope |
|----------|----------|-------|
| 1 | Municipal design standards | Local overrides (Toronto, Peel, etc.) |
| 2 | OPSD (Drawings) | Standard details and dimensions |
| 3 | OPSS (Specifications) | Materials, construction methods, testing |
| 4 | CSA Standards | National performance and design standards |
| 5 | MTO Manuals | Design methodology and parameters |
| 6 | TAC Guidelines | Transportation Association of Canada guidance |

Municipal standards override provincial where they exist. Always note when a municipal override applies.

### 3. Extract requirements

For each applicable standard:
- State the exact requirement with units
- Note conditions and exceptions
- Identify the standard version and date
- List related standards the designer should also consult
- Flag any recent amendments

### 4. Check for municipal overrides

Common Toronto-specific overrides:
- Toronto Wet Weather Flow Management Guidelines (supersedes MTO for SWM)
- Toronto Green Standard (additional requirements beyond OPSD/OPSS)
- Toronto Development Infrastructure Policy and Standards (DIPS)
- City of Toronto Road Classification System (affects design parameters)

### 5. Note design parameters

When the query involves design calculations, provide the applicable parameters:

For drainage:
- Manning's n values by pipe material
- Rational method C values by land use
- IDF curve references for the municipality
- Minimum pipe grades by diameter

For structures:
- Design loading (CL-625 for bridges)
- Clearance requirements
- Barrier and railing standards

### 6. Flag jurisdictional nuances

- Note when standards are in transition (e.g., metric conversion issues)
- Flag differences between MTO standards (provincial highways) and municipal standards
- Note when CSA standards have been adopted with Ontario-specific modifications

## Quality Bar

- Always cite the specific standard number and version
- Never provide a requirement without its source standard
- Distinguish between mandatory requirements ("shall") and recommendations ("should")
- Note when multiple standards apply and which takes precedence
- Flag when a standard is under review or recently revised

## Stop Conditions

Stop and return a partial artifact when:
- The query is outside Ontario/Canadian infrastructure standards scope
- The specific standard cannot be identified from available references
- The query requires engineering judgment beyond standard lookup (flag for P.Eng. review)
- The municipality has unpublished standards that override provincial ones

## Reference Files

| File | Description | Key Topics |
|------|-------------|------------|
| `../infrastructure-assessment/references/opsd-standards.md` | Ontario Provincial Standard Drawings for pipes and manholes | OPSD 701, 702, 704, 802 series; dimensions, materials, installation |
| `../infrastructure-assessment/references/csa-s6-bridge-code.md` | CSA S6:19 Canadian Highway Bridge Design Code | CL-625 loading, evaluation, clearances, barriers |
| `references/mto-drainage-manual.md` | MTO Drainage Management Manual | Storm sewer design, Manning's equation, IDF curves, rational method |

Read only the reference file relevant to the current query.

## External References

| Source | URL | Use |
|--------|-----|-----|
| Ontario Provincial Standards | https://www.ontario.ca/page/provincial-standards | OPSD and OPSS index |
| CSA Group | https://www.csagroup.org/ | CSA S6, CSA A23, CSA B182 |
| MTO Drainage Management Manual | https://www.ontario.ca/document/drainage-management-manual | Hydrology and hydraulics |
| MTO Structural Manual | https://www.ontario.ca/page/bridge-structures | Bridge design and evaluation |
| City of Toronto Engineering Standards | https://www.toronto.ca/services-payments/building-construction/infrastructure-city-construction/technical-standards/ | Municipal overrides |
