---
title: "CSA S6:19 — Canadian Highway Bridge Design Code (Key Requirements)"
category: infrastructure
relevance: "Load when assessing bridge or culvert condition, evaluating load capacity, or checking design compliance against CSA S6:19 requirements."
key_topics: "CL-625 loading, bridge evaluation, clearances, deck widths, barriers, culvert design, OSIM condition states, load posting"
---

# CSA S6:19 — Canadian Highway Bridge Design Code (Key Requirements)

CSA S6:19 is the national standard for the design, evaluation, and rehabilitation of highway bridges in Canada. It is adopted by reference in Ontario through the Ontario Highway Bridge Design Code (OHBDC) and is the authority standard for all publicly owned bridges and culverts in the province. The Ontario Structure Inspection Manual (OSIM) references CSA S6 for evaluation and load rating.

---

## 1. Design Loading — CL-625

The CL-625 design truck is the standard live load for Canadian highway bridges.

### CL-625 Truck Configuration

| Axle | Load (kN) | Spacing from Previous (m) |
|------|-----------|--------------------------|
| 1 (steering) | 50 | — |
| 2 | 125 | 3.6 |
| 3 | 125 | 1.2 |
| 4 | 175 | 6.6 |
| 5 | 150 | 6.6 |

- **Total truck weight**: 625 kN
- **Design lane load**: 9 kN/m uniformly distributed (applied with or without the truck, whichever governs)
- **Dynamic load allowance (DLA)**: Applied as a fraction of static load, varies by span length and component

### Dynamic Load Allowance

| Span Length | DLA Factor |
|-------------|-----------|
| Up to 6 m | 0.40 |
| 6 m to 12 m | Linear interpolation |
| Over 12 m | 0.25 |
| Buried structures (>0.6 m cover) | Reduced per Section 7 |

### Multiple Presence Factors

| Number of Loaded Lanes | Factor |
|------------------------|--------|
| 1 | 1.00 |
| 2 | 0.90 |
| 3 | 0.80 |
| 4 | 0.70 |
| 5 | 0.60 |
| 6+ | 0.55 |

---

## 2. Geometric Requirements

### Minimum Clear Roadway Width

| Road Classification | Minimum Clear Width |
|--------------------|-------------------|
| Expressway / Freeway | Two lanes + shoulders (min 13.4 m between barriers) |
| Arterial (new construction) | Two lanes minimum (min 10.0 m between barriers) |
| Collector | 8.0 m minimum between barriers |
| Local road | 7.5 m minimum between barriers |
| Single-lane bridge (low volume) | 5.0 m minimum (with traffic signals or sight distance) |

### Minimum Vertical Clearance

| Crossing Type | Minimum Clearance |
|--------------|-------------------|
| Over provincial highway | 5.0 m (MTO requirement) |
| Over municipal road | 4.5 m minimum |
| Over railway (CN/CP) | 7.0 m (railway authority requirement) |
| Pedestrian underpass | 2.5 m minimum |
| Over navigable waterway | Per Transport Canada requirements |

### Bridge Deck Geometry

| Parameter | Requirement |
|-----------|-------------|
| Lane width | 3.5 m to 3.7 m |
| Shoulder width (expressway) | 2.5 m to 3.0 m minimum |
| Sidewalk width | 1.5 m minimum (2.0 m preferred) |
| Cross slope | 2% typical crown section |
| Superelevation | Maximum 6% |

---

## 3. Barriers and Railings

### Performance Levels

CSA S6 defines barrier performance levels based on road characteristics:

| Performance Level | Application | Test Impact |
|------------------|-------------|-------------|
| PL-1 | Low-speed, low-volume roads | 820 kg vehicle at 50 km/h, 25 degrees |
| PL-2 | Moderate-speed urban and suburban | 2000 kg vehicle at 70 km/h, 25 degrees |
| PL-3 | High-speed highways, freeways | 8000 kg vehicle at 80 km/h, 15 degrees |

### Barrier Height Requirements

| Performance Level | Minimum Height |
|------------------|---------------|
| PL-1 | 680 mm |
| PL-2 | 800 mm |
| PL-3 | 1070 mm |

### Pedestrian Railing

| Parameter | Requirement |
|-----------|-------------|
| Height | 1070 mm minimum above sidewalk |
| Opening size | Maximum 150 mm (to prevent child climbing/passage) |
| Top rail | Must be continuous and graspable |
| Bicycle railing | 1370 mm minimum height where cycling is permitted |

---

## 4. Structural Design Requirements

### Load Combinations (Limit States Design)

CSA S6 uses limit states design with the following primary combinations:

| Limit State | Key Load Factors |
|-------------|-----------------|
| ULS-1 | 1.2D + 1.7L (primary) |
| ULS-2 | 1.2D + 1.4L + environmental |
| SLS-1 | 1.0D + 0.9L (deflection and vibration control) |
| FLS | Fatigue limit state — single truck passage |

### Deflection Limits

| Structure Type | Maximum Live Load Deflection |
|---------------|----------------------------|
| Steel beam/girder bridge | Span/800 (highway), Span/1000 (pedestrian) |
| Concrete bridge | Span/800 |
| Timber bridge | Span/400 |
| Cantilever spans | Span/300 |

### Minimum Concrete Cover

| Exposure Condition | Cover (mm) |
|-------------------|-----------|
| Bridge deck — top surface | 70 mm (with waterproofing), 90 mm (without) |
| Bridge deck — bottom | 40 mm |
| Substructure (splash zone) | 70 mm |
| Foundation (cast against earth) | 75 mm |
| Interior girders | 40 mm |

---

## 5. Culvert Design Requirements

### Structural Culverts (CSA S6 Section 7)

| Parameter | Requirement |
|-----------|-------------|
| Minimum span | Defined as a "bridge" when span > 3.0 m |
| Design loading | CL-625 with reduced DLA based on depth of cover |
| Minimum cover | 0.6 m above crown for rigid culverts under roadway |
| Fill height limits | Per manufacturer tables for flexible culverts (CSP, HDPE) |
| End treatment | Headwalls, wingwalls, or bevelled ends — must resist hydraulic and earth loads |

### Hydraulic Design

| Parameter | Requirement |
|-----------|-------------|
| Design flood | 1:100 year for provincial highways, 1:25 to 1:100 for municipal (varies) |
| Freeboard | 0.3 m minimum above design HWL to low point of road |
| Inlet control | Check using performance curves (HW/D ratio) |
| Outlet control | Check tailwater effects and outlet velocity |
| Scour protection | Required at outlet — riprap sizing per MTO Drainage Manual |

### Culvert Materials

| Material | Typical Span Range | Service Life |
|----------|-------------------|-------------|
| Reinforced concrete box | 1.0 m to 12.0 m | 75-100 years |
| Precast concrete pipe | 0.3 m to 3.6 m | 75-100 years |
| Corrugated steel pipe/plate | 0.3 m to 12.0 m | 25-75 years (coating dependent) |
| Structural plate (steel) | 2.0 m to 12.0 m | 40-75 years |
| HDPE pipe | 0.1 m to 1.5 m | 50-75 years |
| Aluminium structural plate | 2.0 m to 10.0 m | 50-75 years |

---

## 6. Bridge Evaluation and Load Rating

### Evaluation Levels

CSA S6 Section 14 defines three evaluation levels:

| Level | Purpose | Approach |
|-------|---------|----------|
| Level 1 | General screening | Simplified — uses design assumptions |
| Level 2 | Refined analysis | Uses measured dimensions and material properties |
| Level 3 | Proof load test | Physical load testing to confirm capacity |

### Load Rating Results

| Rating | Meaning | Action |
|--------|---------|--------|
| RF >= 1.0 | Adequate for full CL-625 loading | No restrictions |
| 0.7 <= RF < 1.0 | Below design but serviceable | Monitor, consider restrictions |
| RF < 0.7 | Significantly deficient | Load posting or restriction required |
| RF < 0.3 | Critical deficiency | Closure or emergency shoring |

RF = Resistance Factor (ratio of available capacity to required capacity for CL-625)

### Load Posting

When a bridge cannot carry full legal loads, CSA S6 Section 14 requires posting:
- Gross Vehicle Weight (GVW) limit
- Single axle limit
- Axle group limits
- Speed restriction (reduces DLA)
- Lane restriction (reduces simultaneous loading)

---

## 7. OSIM Condition States

The Ontario Structure Inspection Manual uses a 4-level condition state system aligned with CSA S6 evaluation:

| Condition State | Description | Typical Action |
|----------------|-------------|----------------|
| 1 — New/Excellent | As-built condition, no deterioration | Routine inspection |
| 2 — Good/Minor deterioration | Surface defects, minor cracking | Monitor, routine maintenance |
| 3 — Fair/Moderate deterioration | Significant cracking, section loss, delamination | Plan rehabilitation |
| 4 — Poor/Severe deterioration | Structural concern, exposed reinforcement, major section loss | Urgent repair or replacement |

### OSIM Inspection Components

Each component is rated independently:

| Component | What to Inspect |
|-----------|----------------|
| Deck/top slab | Cracking, spalling, delamination, potholing, waterproofing |
| Soffit | Cracking, efflorescence, reinforcement exposure, staining |
| Girders/beams | Section loss, cracking, bearing condition, paint condition |
| Abutments | Cracking, movement, drainage, bearing seats |
| Piers | Cracking, scour, collision damage, movement |
| Wingwalls | Cracking, rotation, settlement |
| Bearings | Corrosion, displacement, elastomer condition |
| Joints | Seal condition, debris accumulation, leakage |
| Barriers/railings | Impact damage, corrosion, anchor condition |
| Embankment/slope | Erosion, settlement, drainage |
| Waterway | Scour, debris, channel alignment, riprap condition |

---

## 8. Rehabilitation Thresholds

### When to Rehabilitate vs. Replace

| Indicator | Rehabilitation | Replacement |
|-----------|---------------|-------------|
| Deck condition | Isolated spalling, delamination <30% | Widespread deterioration >50% of deck area |
| Superstructure | Section loss <20%, isolated corrosion | Section loss >30%, multiple member deficiency |
| Substructure | Surface repairs, grout injection | Foundation failure, major scour |
| Load rating | RF 0.5-0.9 (can be improved with repair) | RF <0.5 (fundamental capacity issue) |
| Service life remaining | >20 years after rehab | <10 years even with rehab |
| Functional adequacy | Meets current geometric standards | Substandard width, clearance, or alignment |

---

## Key References

- **CSA S6:19**: https://www.csagroup.org/ (purchase required)
- **Ontario Structure Inspection Manual**: https://www.ontario.ca/page/ontario-structure-inspection-manual
- **MTO Bridge Structures**: https://www.ontario.ca/page/bridge-structures
- **MTO Structural Financial Analysis Manual**: For lifecycle cost comparison of rehabilitation vs. replacement
- **Ontario Regulation 104/97**: Bridge and structural culvert inspection requirements
