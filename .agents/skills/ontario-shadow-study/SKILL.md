---
name: Shadow Study Data
description: An analysis of shadows cast by the proposed development on surrounding properties, streets, parks, and other sensitive areas.
---

## 9. Shadow Study Data

### What It Is
An analysis of shadows cast by the proposed development on surrounding properties, streets, parks, and other sensitive areas.

### Why It Matters
- Official Plan policies protect sunlight access, especially for parks, schools, and residential properties
- Required for most applications involving increased height
- Committee of Adjustment and OLT consider shadow impact when evaluating the "desirable development" test

### Governing Law
- **Official Plan policies on sun/shadow** (e.g., Toronto OP Section 3.1.2(b)(iv) — "adequate light")
- **Urban Design Guidelines** — specific shadow requirements
- **Zoning by-law angular plane provisions** — partly designed to limit shadows
- **Provincial Planning Statement** — general livability principles

### How to Build It

```
Shadow analysis is typically performed at specific dates and times
prescribed by the municipality.

Toronto standard test dates and times:
  - March 21 / September 21 (equinoxes): 9:18 AM, 12:18 PM, 3:18 PM, 6:18 PM
  - June 21 (summer solstice): 9:18 AM, 12:18 PM, 3:18 PM, 6:18 PM
  - December 21 (winter solstice): 9:18 AM, 12:18 PM, 3:18 PM (sunset ~4:44 PM)

Note: Times are Eastern Standard Time (EST); some municipalities use
Eastern Daylight Time (EDT) for spring/summer dates.

Process:
1. Model the proposed building and surrounding buildings in 3D
2. Set the geographic coordinates (latitude/longitude)
3. For each test date/time, calculate sun position
   (azimuth and altitude angles)
4. Project shadows from the building onto the ground plane
   and adjacent buildings
5. Identify impacts on:
   - Public parks and open spaces (especially concerning)
   - Residential rear yards and windows
   - School yards
   - Sidewalks and public realm
   - Heritage properties

Output:
SHADOW STUDY SUMMARY

Test Results:
| Date | Time | Shadow Length | Key Impacts |
|------|------|-------------|-------------|
| Mar 21 | 9:18 AM | Xm NW | Shadow reaches [location] |
| Mar 21 | 12:18 PM | Xm N | No impact on park |
| Mar 21 | 3:18 PM | Xm NE | Shadow reaches [location] |

Net New Shadow:
[Difference between existing condition shadow and proposed condition shadow]

Impact Assessment:
- Parks: [X hours of sunlight maintained? / Y hours of new shadow]
  Toronto standard: minimum 5 hours of sunlight on parks
  between 10 AM and 4 PM on September 21
- Residential properties: [description of impact]
- Streetscape: [description of impact]

Mitigation (if needed):
- Height reduction at [location]
- Stepback at [level]
- Building orientation adjustment
```

### Computational Approach
```
For basic shadow analysis without full 3D modeling:
1. Sun position: Calculate solar azimuth and altitude for
   latitude 43.65°N (Toronto) at each test time
2. Shadow length = Building height / tan(solar altitude)
3. Shadow direction = opposite of solar azimuth
4. Shadow footprint = project building outline using
   shadow vector
5. Compare footprint to sensitive receptor locations

For accurate analysis:
  - Use 3D modeling software (Rhino, SketchUp, Revit)
  - Import surrounding context buildings
  - Run shadow simulation at specified dates/times
  - Generate shadow diagrams (plan view)
```
