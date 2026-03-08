---
name: Professional Referral Matcher
description: A system that matches users with the appropriate professionals needed for their specific project, based on the required studies and approval pathway identified by the app.
---

## 27. Professional Referral Matcher

### What It Is
A system that matches users with the appropriate professionals needed for their specific project, based on the required studies and approval pathway identified by the app.

### Why It Matters
- Users often don't know what professionals they need
- Different professionals have different licensing requirements in Ontario
- Matching the right professional to the task saves time and money

### Governing Law and Licensing

| Professional | Licensing Body | Designation | When Required |
|---|---|---|---|
| Planner | Ontario Professional Planners Institute (OPPI) | RPP (Registered Professional Planner) | Planning rationale, OLT testimony, policy analysis |
| Architect | Ontario Association of Architects (OAA) | Licensed Architect | Building design for Part 3 buildings (>600 sq m or >3 storeys) |
| Building Designer | Ministry of Municipal Affairs (BCIN) | BCIN (Building Code Identification Number) | Building design for Part 9 buildings (houses, small buildings) |
| Civil Engineer | Professional Engineers Ontario (PEO) | P.Eng. | Grading, drainage, servicing, stormwater management |
| Structural Engineer | PEO | P.Eng. | Structural design, foundation design |
| Geotechnical Engineer | PEO | P.Eng. | Soil testing, foundation recommendations |
| Traffic Engineer | PEO | P.Eng. | Traffic impact studies, parking studies |
| Environmental Consultant | MECP Qualified Person (QP) | QP under O. Reg. 153/04 | Phase 1 and Phase 2 ESAs, Record of Site Condition |
| Ontario Land Surveyor | Association of Ontario Land Surveyors (AOLS) | OLS | Legal surveys, topographic plans, reference plans for severance |
| Arborist | International Society of Arboriculture (ISA) | ISA Certified Arborist | Tree inventory, preservation plans, injury reports |
| Archaeologist | Ministry of Citizenship and Multiculturalism | Licensed (Class 1-4) | Archaeological assessments |
| Heritage Consultant | Canadian Association of Heritage Professionals (CAHP) | CAHP member | Heritage Impact Assessments |
| Acoustical Engineer | PEO (or specialized firm) | P.Eng. or equivalent | Noise and vibration studies |
| Energy Consultant | Various certifications | CET, LEED AP, Passive House | Energy efficiency, Toronto Green Standard |
| Landscape Architect | Ontario Association of Landscape Architects (OALA) | Full Member OALA | Landscape plans for site plan approval |
| Lawyer | Law Society of Ontario (LSO) | Licensed Lawyer or Paralegal | Title searches, OLT representation, agreements, opinion letters |
| Hydrogeologist | Professional Geoscientists Ontario (PGO) | P.Geo. | Groundwater studies, well-head protection |

### How to Build It

```
PROFESSIONAL REFERRAL MATCHER

Input: Required studies checklist (from Section 15) +
       Approval pathway (from Section 17)

Logic:
For each required study/document, identify:
1. What professional designation is required
2. What licensing body governs them
3. Estimated cost range
4. Estimated timeline
5. How to find them

Output:

PROFESSIONAL REQUIREMENTS FOR YOUR PROJECT

| # | Study/Document | Professional Needed | Licensing | Est. Cost | Est. Time | How to Find |
|---|---------------|--------------------|-----------|-----------|-----------|----|
| 1 | Planning Rationale | RPP | OPPI | $3,000-$15,000 | 2-4 weeks | oppi.ca/find-a-planner |
| 2 | Architectural Drawings | OAA Architect or BCIN Designer | OAA / MMAH | $5,000-$50,000 | 3-8 weeks | oaa.on.ca/find-architect |
| 3 | Survey | OLS | AOLS | $3,000-$8,000 | 1-3 weeks | aols.org/find-surveyor |
| 4 | Arborist Report | ISA Certified Arborist | ISA | $1,500-$5,000 | 1-2 weeks | isa-arbor.com/findanarborist |
| 5 | Grading Plan | P.Eng. (Civil) | PEO | $3,000-$8,000 | 1-3 weeks | peo.on.ca |

NOTES:
- BCIN designers can design Part 9 buildings (most houses
  and small buildings ≤600 sq m, ≤3 storeys)
- OAA architects are required for Part 3 buildings
  (larger and more complex buildings)
- Some firms offer multiple services (e.g., planning +
  architecture, or civil engineering + geotechnical)
- Get multiple quotes — fees vary significantly
- Confirm professional insurance (errors & omissions)
- Verify current license/certification status with the
  relevant licensing body

OPTIONAL ADVANCED FEATURE:
- Build a directory of professionals who have opted in
- Filter by: location, specialty, project size, availability
- Show past projects and reviews
- Enable direct quote requests through the app
```
