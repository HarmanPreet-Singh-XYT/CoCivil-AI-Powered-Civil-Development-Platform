---
name: Compliance Matrix
description: A structured table comparing a proposed development's metrics against all applicable zoning standards.
---

## 2. Compliance Matrix

### What It Is
A structured table comparing a proposed development's metrics against all applicable zoning standards. Every quantitative standard is checked: height, setbacks, lot coverage, FSI/density, parking, landscaping, angular planes, etc.

### Why It Matters
- Required to identify whether a proposal is **as-of-right** or needs **variances/amendments**
- Forms the backbone of every planning rationale and application
- Committee of Adjustment and municipal planners use this to evaluate applications

### Governing Law
- **Planning Act, s. 34** — Zoning by-laws
- **Municipal zoning by-law** (e.g., Toronto By-law 569-2013)
- **Former by-laws** (e.g., Toronto former City of York By-law 1-83, North York By-law 7625) — many properties still governed by these
- **Official Plan** — may impose additional density or height limits

### Data Required

| Data Point | Source |
|---|---|
| Zoning category (e.g., RD, RM, CR, etc.) | Zoning by-law + zoning map |
| Lot dimensions (frontage, depth, area) | Survey, MPAC, GIS data |
| Proposed building metrics (height, setbacks, GFA, lot coverage) | User input or uploaded drawings |
| Zone-specific development standards | Zoning by-law tables (e.g., By-law 569-2013, Chapter 10 for residential) |
| Overlay zones (heritage, flood plain, UTFA, etc.) | Municipal GIS layers |
| Prevailing by-law exceptions | Schedule "A" exceptions in older by-laws |

### How to Build It — Step by Step

**Step 1: Identify the applicable zoning**
```
Input: Property address or legal description
Process:
  1. Geocode the address to get coordinates
  2. Query the municipal zoning GIS layer to identify:
     - Primary zone category (e.g., RD (f12.0; a450; d0.6))
     - Any overlay zones
     - Any site-specific by-law amendments
  3. Determine if the property is under the new harmonized by-law
     or a former municipality by-law
Output: Zone code + applicable by-law reference
```

**Step 2: Extract development standards**
```
For Toronto By-law 569-2013, standards are in:
  - Chapter 5: Residential zones
  - Chapter 10: Residential zone standards (lot-by-lot)
  - Chapter 15: Parking
  - Chapter 40-80: Zone-specific standards
  - Chapter 150: Defined terms

For each zone, extract:
  - Maximum height (metres and/or storeys)
  - Maximum FSI (Floor Space Index) or GFA
  - Minimum lot frontage
  - Minimum lot area
  - Minimum front yard setback
  - Minimum rear yard setback
  - Minimum side yard setbacks (interior and exterior)
  - Maximum lot coverage
  - Minimum landscaped open space
  - Minimum parking spaces (note: Bill 185 eliminated minimums
    for properties near major transit stations)
  - Minimum bicycle parking
  - Angular plane requirements
  - Amenity space requirements (if applicable)
```

**Step 3: Collect proposal metrics**
```
From user input or uploaded drawings:
  - Proposed building height
  - Proposed number of storeys
  - Proposed GFA (above grade and below grade)
  - Proposed setbacks (all sides)
  - Proposed lot coverage
  - Proposed number of units
  - Proposed number of parking spaces
  - Proposed landscaped area
```

**Step 4: Generate comparison table**
```
| Standard              | Required       | Proposed       | Status     | Variance Needed |
|-----------------------|----------------|----------------|------------|-----------------|
| Max Height            | 10.0 m         | 12.5 m         | EXCEEDS    | +2.5 m          |
| Max FSI               | 0.6            | 0.85           | EXCEEDS    | +0.25           |
| Min Front Setback     | 6.0 m          | 6.0 m          | COMPLIES   | —               |
| Min Rear Setback      | 7.5 m          | 5.0 m          | DEFICIENT  | -2.5 m          |
| Min Interior Side     | 1.2 m          | 0.9 m          | DEFICIENT  | -0.3 m          |
| Max Lot Coverage      | 35%            | 42%            | EXCEEDS    | +7%             |
| Min Parking           | 2 spaces       | 1 space        | DEFICIENT  | -1 space        |
| Min Landscaping       | 30%            | 28%            | DEFICIENT  | -2%             |
```

**Step 5: Flag variances**
```
For each non-compliant standard:
  1. Identify the specific by-law section being varied
     (e.g., "Section 10.20.40.70(1) — Maximum Height")
  2. Calculate the magnitude of variance
  3. Classify severity: minor (≤10%), moderate (10-25%), major (>25%)
  4. Flag whether this is a minor variance (Committee of Adjustment)
     or requires a zoning by-law amendment (Council/OLT)
```

### Output Format
- Machine-readable JSON for internal processing
- PDF table for human review and inclusion in application packages
- Highlighted cells: green (complies), yellow (minor variance), red (major variance or amendment needed)

### Special Considerations for Ontario
- **Performance standards vs. prescriptive standards**: Some zones have alternative compliance paths
- **Section 37 / Community Benefits Charges**: For buildings over certain thresholds (Bill 23 replaced s.37 with CBCs)
- **Holding provisions (H)**: Some zones have holding symbols that must be removed before building permits
- **Interim control by-laws**: Temporary freezes on development in study areas — must check
- **Heritage Conservation Districts**: Additional design standards apply
