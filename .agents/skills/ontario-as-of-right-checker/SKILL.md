---
name: As-of-Right Eligibility Checker
description: A determination of whether a proposed development complies fully with all applicable zoning standards.
---

## 14. As-of-Right Eligibility Checker

### What It Is
A determination of whether a proposed development **complies fully with all applicable zoning standards**, meaning no variance or amendment is needed — the owner can proceed directly to a building permit.

### Why It Matters
- Many homeowners don't realize their project might be as-of-right
- Under **O. Reg. 299/19**, up to 2 additional residential units are permitted as-of-right province-wide
- Under **O. Reg. 462/24**, up to 4 units on residential lots may be permitted as-of-right
- Saves thousands of dollars and months of time if no planning application is needed

### Governing Law
- **Planning Act, s. 34** — Zoning by-laws
- **O. Reg. 299/19** — Additional residential units (2 additional units)
- **O. Reg. 462/24** — As-of-right up to 4 units (effective 2024)
- **Municipal zoning by-laws** — Specific standards that must be met
- **Ontario Building Code** — Still need building permit even if as-of-right

### How to Build It

```
AS-OF-RIGHT ELIGIBILITY CHECKER

Input: Property address + proposed development description

Step 1: IDENTIFY APPLICABLE ZONE AND STANDARDS
  [Same as Compliance Matrix Steps 1-2]

Step 2: ASSESS O. REG. 299/19 ELIGIBILITY
  Check if the proposal involves additional residential units:
  - Is the property zoned to permit residential use? [Y/N]
  - Are you adding up to 2 additional units? [Y/N]
  - Is one unit in/attached to the primary dwelling? [Y/N]
  - Is one unit in an accessory building? [Y/N]
  If all yes → O. Reg. 299/19 may apply
  
  Standards still apply:
  - Units must comply with Ontario Building Code
  - Municipal servicing requirements must be met
  - Maximum 1 unit in accessory building
  - Lot must be serviced by municipal water and sewer
    (or adequate private services)

Step 3: ASSESS O. REG. 462/24 ELIGIBILITY
  Check if as-of-right fourplex provisions apply:
  - Is the lot in a municipality with population ≥ [threshold]?
  - Is the lot zoned for residential use?
  - Is the lot in a settlement area?
  - How many units are proposed? (max 4 under regulation)
  - Does the lot meet minimum size requirements?
  - Are height and density within the regulation's limits?
  Note: O. Reg. 462/24 has specific standards that
  override municipal zoning for eligible properties.

Step 4: CHECK FULL ZONING COMPLIANCE
  Run the Compliance Matrix (Section 2)
  
  If ALL standards are met → AS-OF-RIGHT
  If ANY standard is not met → VARIANCE NEEDED

Step 5: CHECK FOR ADDITIONAL CONSTRAINTS
  - Is the property subject to a heritage designation? [Y/N]
  - Is it in a floodplain or regulated area? [Y/N]
  - Are there conservation authority requirements? [Y/N]
  - Is there a holding provision on the zoning? [Y/N]
  - Is it subject to site plan control? [Y/N]

Step 6: GENERATE OUTPUT

AS-OF-RIGHT ELIGIBILITY REPORT

Property: [Address]
Proposal: [Description]

ELIGIBILITY DETERMINATION: [AS-OF-RIGHT / VARIANCE REQUIRED / AMENDMENT REQUIRED]

If AS-OF-RIGHT:
  "The proposed development complies with all applicable
  zoning standards under By-law [X]. No planning application
  is required. You may proceed directly to the building
  permit stage."
  
  Applicable regulation: [O. Reg. 299/19 / O. Reg. 462/24 / 
  Standard zoning compliance]
  
  Next steps:
  1. Engage an architect to prepare permit drawings
  2. Obtain required reports (e.g., grading plan)
  3. Apply for a building permit
  4. Estimated building permit processing time: 10-20 business days

If VARIANCE REQUIRED:
  "The proposed development requires the following variances
  from By-law [X]. A minor variance application to the
  Committee of Adjustment is likely needed."
  
  [List variances]
  
  Estimated timeline: 2-4 months
  Estimated cost: $X (application fee) + $X (consultant fees)

If AMENDMENT REQUIRED:
  "The proposed development requires a Zoning By-law Amendment
  because [reason — e.g., use not permitted, variances too
  substantial for minor variance]. This is a more complex
  process requiring Council approval."
  
  Estimated timeline: 6-18 months
  Estimated cost: $X (application fee) + $X (consultant fees)
```
