---
name: Required Studies Checklist
description: A list of all technical studies and reports that must be submitted with a development application.
---

## 15. Required Studies Checklist

### What It Is
A list of all technical studies and reports that must be submitted with a development application, based on the property location, proposal type, and municipal requirements.

### Why It Matters
- Applications are deemed "incomplete" without required studies
- Each study can cost $5,000-$50,000+ and take weeks to prepare
- Users need to know upfront what to budget for

### Governing Law
- **Planning Act, s. 22(5) and 34(10.1)** — Complete application requirements
- **O. Reg. 543/06** — Official plan and zoning by-law amendment application requirements
- **O. Reg. 544/06** — Plans of subdivision application requirements
- **Municipal complete application checklists** — Each municipality has its own

### How to Build It

```
REQUIRED STUDIES CHECKLIST

Trigger-based system: Each study is required based on specific triggers.

| Study | Trigger | Typical Cost | Typical Timeline | Who Prepares |
|-------|---------|-------------|------------------|--------------|
| Planning Rationale | All ZBA, OPA; most MV | $3,000-$15,000 | 2-4 weeks | Planner (RPP) |
| Arborist Report / Tree Preservation Plan | Any tree ≥30cm diameter on or adjacent to property (Toronto: ≥30cm private, any city tree) | $1,500-$5,000 | 1-2 weeks | Certified Arborist (ISA) |
| Traffic Impact Study | >100 peak hour trips generated, or municipality requires it | $10,000-$50,000 | 4-8 weeks | Traffic Engineer (P.Eng.) |
| Parking Study | Requesting reduced parking | $5,000-$15,000 | 2-4 weeks | Traffic Engineer (P.Eng.) |
| Stormwater Management Report | Any site plan application; any impervious surface increase | $5,000-$20,000 | 3-6 weeks | Civil Engineer (P.Eng.) |
| Geotechnical Investigation | New construction, especially with excavation or near water | $5,000-$15,000 | 2-4 weeks | Geotechnical Engineer (P.Eng.) |
| Phase 1 Environmental Site Assessment | Property on or near contaminated sites registry; former industrial/commercial use | $3,000-$8,000 | 2-3 weeks | Environmental Consultant (QP under O. Reg. 153/04) |
| Phase 2 ESA (if Phase 1 identifies potential contamination) | Triggered by Phase 1 findings | $10,000-$50,000 | 4-12 weeks | QP under O. Reg. 153/04 |
| Record of Site Condition | Change of use to more sensitive use (e.g., commercial → residential) per O. Reg. 153/04 | Included in Phase 2 | After Phase 2 | QP files with MECP |
| Hydrogeological Study | Near watercourses, high water table, or well-head protection areas | $10,000-$30,000 | 4-8 weeks | Hydrogeologist (P.Geo.) |
| Heritage Impact Assessment | Property on heritage register, adjacent to heritage property, or in HCD | $5,000-$20,000 | 3-6 weeks | Heritage Consultant |
| Noise and Vibration Study | Near major roads (>20,000 AADT), railways (within 300m), or airports | $5,000-$15,000 | 3-6 weeks | Acoustical Engineer |
| Wind Study | Tall buildings (typically >8 storeys) | $15,000-$40,000 | 4-8 weeks | Wind Engineer / Microclimate Consultant |
| Sun/Shadow Study | Any building that increases height | $3,000-$10,000 | 1-3 weeks | Architect or Planner |
| Urban Design Brief | ZBA for mid-rise or taller; municipal request | $5,000-$15,000 | 2-4 weeks | Architect or Urban Designer |
| Archaeological Assessment | In areas of archaeological potential (per municipal or provincial mapping) | $3,000-$15,000 (Stage 1-2) | 2-6 weeks | Licensed Archaeologist |
| Servicing Report (Functional) | Larger developments requiring new servicing | $10,000-$30,000 | 4-8 weeks | Civil Engineer (P.Eng.) |
| Grading and Drainage Plan | Most building permit applications | $3,000-$8,000 | 1-3 weeks | Civil Engineer or OLS |
| Survey / Topographic Plan | All applications (shows existing conditions, lot lines, elevations) | $3,000-$8,000 | 1-3 weeks | Ontario Land Surveyor (OLS) |
| Energy Efficiency Report (Toronto Green Standard) | All Toronto applications (Tier 1 mandatory, higher tiers voluntary) | $3,000-$10,000 | 2-4 weeks | Energy Consultant |
| Pedestrian Wind Assessment | Mid-rise and tall buildings | $5,000-$15,000 | 2-4 weeks | Wind Engineer |
| Rail Safety Study | Within 300m of railway corridor | $10,000-$25,000 | 4-8 weeks | Qualified Engineer |
| Vibration Study | Within 75m of subway or streetcar | $5,000-$15,000 | 3-6 weeks | Acoustical Engineer |

TRIGGER DETECTION LOGIC:
For each property, check:
1. Are there trees ≥30cm diameter? → Arborist Report
2. Is property within 300m of a rail corridor? → Rail Safety + Noise
3. Is property within 75m of subway/streetcar? → Vibration Study
4. Is property adjacent to heritage? → Heritage Impact Assessment
5. Is property on archaeological potential mapping? → Archaeological Assessment
6. Is property in a floodplain or near watercourse? → Hydrogeological Study
7. Was property previously industrial/commercial? → Phase 1 ESA
8. Is development >8 storeys? → Wind Study
9. Does development increase height? → Shadow Study
10. Does development generate >100 peak hour trips? → Traffic Study
11. Is parking reduction requested? → Parking Study
12. Is property in Toronto? → Toronto Green Standard

Output: Checked list with estimated costs and timelines,
plus recommended professionals.
```
