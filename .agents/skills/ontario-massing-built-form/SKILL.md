---
name: Massing and Built Form Summary
description: A description of the proposed building's physical form — its height, width, depth, stepbacks, articulation, and relationship to surrounding buildings and the street.
---

## 7. Massing and Built Form Summary

### What It Is
A description of the proposed building's physical form — its height, width, depth, stepbacks, articulation, and relationship to surrounding buildings and the street.

### Why It Matters
- Official Plans contain **built form policies** that proposals must conform to
- Urban design guidelines (municipal) govern massing relationships
- Committee of Adjustment and OLT evaluate whether the built form is "desirable for the appropriate development of the land"

### Governing Law
- **Official Plan built form policies** (e.g., Toronto OP Sections 3.1.1, 3.1.2, 3.1.3)
- **Urban Design Guidelines** (municipal — e.g., Toronto Tall Building Guidelines, Mid-Rise Guidelines, Townhouse Guidelines, Infill Guidelines)
- **Zoning by-law angular plane requirements** (e.g., 45-degree angular plane from certain boundaries)
- **Ontario Building Code** — fire separation, spatial separation requirements

### Data Required
```
From the proposal:
  - Building height (in metres and storeys)
  - Building footprint dimensions
  - Floor plates by storey
  - Stepbacks (e.g., above 3rd storey, setback 3m from street wall)
  - Relationship to lot lines
  - Separation distances from adjacent buildings
  - Street wall height
  - Ground floor height / active frontage

From context:
  - Heights of adjacent buildings
  - Prevailing street wall conditions
  - Street width (right-of-way)
  - Applicable urban design guidelines
```

### How to Build It

**Step 1: Describe the building form**
```
Generate a structured description:
- Overall height and storeys
- Base/middle/top articulation (for mid-rise and tall buildings)
- Street wall relationship
- Stepback locations and dimensions
- Ground floor conditions (grade relationship, entrance locations)
```

**Step 2: Evaluate against built form policies**
```
For each applicable policy:

Toronto Mid-Rise Guidelines (example):
  - Maximum height = right-of-way width (1:1 ratio)
  - Minimum 5.5m stepback above street wall (typically 4th storey)
  - Front face angular plane from opposite side of right-of-way
  - Rear angular plane: 45 degrees from 10.5m height at rear lot line
  - Minimum ground floor height: 4.5m

Toronto Tall Building Guidelines (example):
  - Maximum tower floor plate: 750 sq m
  - Minimum 25m separation between towers
  - Minimum 12.5m setback from side and rear lot lines (tower)
  - Base building: 80% of frontage, max 6 storeys
  - Minimum 3m stepback above base
```

**Step 3: Generate angular plane analysis**
```
For each applicable angular plane:
1. Identify the origin point and angle
2. Calculate the maximum height at each setback distance
3. Determine if the building fits within the angular plane
4. If it doesn't, calculate the required stepback or height reduction
```

**Step 4: Generate output**
```
MASSING AND BUILT FORM SUMMARY

Building Description:
[Narrative description]

Key Metrics:
| Metric | Value |
|--------|-------|
| Total Height | X m (Y storeys) |
| Street Wall Height | X m (Y storeys) |
| Tower Floor Plate | X sq m |
| Tower Stepback from Base | X m |
| Rear Stepback | X m above Y storey |
| Separation Distance | X m to nearest building |

Built Form Policy Compliance:
| Policy | Requirement | Proposed | Status |
|--------|-------------|----------|--------|
| Mid-Rise 1:1 height | 20m (on 20m ROW) | 18m | COMPLIES |
| Rear angular plane | 45° from 10.5m at rear | [check] | COMPLIES/VARIES |
| Ground floor height | Min 4.5m | 4.0m | DEFICIENT |

Shadow Impact: [Reference shadow study]
Wind Impact: [Reference wind study if applicable]
```
