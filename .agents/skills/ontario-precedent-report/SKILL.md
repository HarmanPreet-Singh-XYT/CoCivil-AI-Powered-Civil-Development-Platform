---
name: Precedent Report
description: A compilation of past decisions for similar applications in the same neighbourhood.
---

## 5. Precedent Report

### What It Is
A compilation of past decisions (from the Committee of Adjustment, OLT, or Council) for similar applications in the same neighbourhood, demonstrating that the requested variances or amendments have been approved before.

### Why It Matters
- **Committees of Adjustment** heavily rely on consistency — if a similar variance was approved nearby, it strengthens the case
- **OLT** considers precedent in applying the four tests
- Demonstrates the proposal is not unusual for the area

### Governing Law
- **Planning Act, s. 45(1)** — Four tests for minor variances (precedent informs "minor" and "desirable")
- **Ontario Land Tribunal Act, 2021** — OLT procedures
- **Statutory Powers Procedure Act, R.S.O. 1990, c. S.22** — Governs quasi-judicial proceedings

### Data Sources

| Source | What It Contains | How to Access |
|---|---|---|
| Toronto Committee of Adjustment Decisions | All minor variance decisions with file numbers, addresses, outcomes, conditions | Toronto Open Data or AIC |
| Toronto TMMIS | Council decisions on ZBAs and OPAs | `app.toronto.ca/tmmis` |
| Ontario Land Tribunal (CanLII) | OLT and former OMB decisions | `canlii.ca/en/on/onlt/` |
| Municipal Application Tracking | Active and past applications | Municipality website |
| PlanningAlliance / Zoocasa / Other aggregators | Development application summaries | Various |

### How to Build It — Step by Step

**Step 1: Define the search parameters**
```
From the subject application, extract:
  - Address (for geographic proximity search)
  - Zoning category (for comparable zone)
  - Type of variance(s) requested
  - Magnitude of each variance
  - Building type (e.g., detached, semi, multiplex, mid-rise)

Search radius:
  - For Committee of Adjustment: 250–500m
  - For OLT/OMB: broader area (same neighbourhood or city-wide
    for novel issues)
```

**Step 2: Query past decisions**
```
For each variance type:
1. Search for past applications with the same type of variance
   (e.g., "maximum height" variance in R zone within 500m)
2. Filter by:
   - Outcome: Approved (focus on approved cases)
   - Date: Last 5 years preferred (more recent = more relevant)
   - Zone: Same or similar zoning category
3. Extract:
   - File number and address
   - Date of decision
   - What was requested
   - What was approved (with conditions)
   - Distance from subject property
```

**Step 3: Analyze comparability**
```
For each precedent case:
1. Compare the zone, lot size, and building type
2. Compare the magnitude of variance
   (was the precedent variance larger, smaller, or similar?)
3. Note any conditions imposed
4. Identify if the same panel or planner was involved
   (relevant for Committee of Adjustment)
```

**Step 4: Generate the report**
```
PRECEDENT REPORT
Property: [Address]
Application: [Type and File Number]
Prepared: [Date]

1. INTRODUCTION
   - Purpose of this report
   - Search methodology (radius, date range, source)

2. SUMMARY TABLE
| # | Address | File No. | Date | Zone | Variance Type | Requested | Approved | Distance |
|---|---------|----------|------|------|---------------|-----------|----------|----------|
| 1 | 123 Oak | A0001/24 | 2024-03-15 | RD | Max Height | 11.5m (10.0m permitted) | Yes, with conditions | 150m |
| 2 | 456 Elm | A0002/23 | 2023-11-20 | RD | Max FSI | 0.75 (0.60 permitted) | Yes | 200m |

3. DETAILED ANALYSIS
   [For each precedent, 1-2 paragraphs explaining relevance]

4. CONCLUSIONS
   - The requested variances are consistent with an
     established pattern of approvals in the neighbourhood
   - [X] of [Y] comparable applications were approved
   - Average approved variance magnitude was [Z]
```
