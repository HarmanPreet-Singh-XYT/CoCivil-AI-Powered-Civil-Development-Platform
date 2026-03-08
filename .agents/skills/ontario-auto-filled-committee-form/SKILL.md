---
name: Auto-Filled Committee of Adjustment Application Form
description: A pre-filled application form for minor variance or consent, ready for signature and submission.
---

## 19. Auto-Filled Committee of Adjustment Application Form

### What It Is
A pre-filled application form for minor variance (Planning Act s. 45(1)) or consent (Planning Act s. 53), ready for the applicant's signature and submission.

### Why It Matters
- The application form is **the official document that initiates the legal process**
- Errors or omissions cause delays (deemed incomplete)
- Many applicants find the form confusing

### Governing Law
- **Planning Act, s. 45(1)** — Minor variance applications
- **Planning Act, s. 53** — Consent applications
- **O. Reg. 200/96** — Committee of Adjustment procedures
- **Municipal forms** — Each municipality has its own form but content is largely standardized

### How to Build It

```
AUTO-FILL COMMITTEE OF ADJUSTMENT FORM

Standard fields to populate (minor variance — Toronto Form):

SECTION A: SUBJECT PROPERTY
  - Municipal Address: [from property data]
  - Legal Description: [from title search / GIS]
  - Lot Frontage: [from survey / GIS]
  - Lot Depth: [from survey / GIS]
  - Lot Area: [from survey / GIS]
  - Assessment Roll Number: [from MPAC]
  - Ward Number: [from municipal GIS]

SECTION B: APPLICANT INFORMATION
  - Owner name(s): [user input]
  - Owner address: [user input]
  - Agent name (if applicable): [user input]
  - Agent address, phone, email: [user input]
  - Authorization: Owner must sign authorizing agent
    [generate authorization letter template]

SECTION C: EXISTING USE AND BUILDINGS
  - Current use of property: [from MPAC / user input]
  - Existing building type: [user input]
  - Year built: [from MPAC / user input]
  - Number of existing units: [user input]
  - Is property currently in compliance with by-law? [assessment]

SECTION D: PROPOSED DEVELOPMENT
  - Description of proposal: [auto-generated from compliance matrix]
  - Proposed use: [user input]
  - Proposed number of units: [user input]

SECTION E: VARIANCES REQUESTED
  [Auto-generated from compliance matrix]
  
  For each variance:
  - By-law number and section: [e.g., "By-law 569-2013,
    Section 10.20.40.70(1)"]
  - Standard: [e.g., "Maximum Building Height"]
  - Required: [e.g., "10.0 metres"]
  - Proposed: [e.g., "12.5 metres"]
  - Variance: [e.g., "An increase of 2.5 metres"]
  
  Wording format (Toronto standard):
  "Chapter [X], Section [Y] of Zoning By-law 569-2013
  requires a maximum [standard] of [required]. The proposed
  [standard] is [proposed], which does not comply with the
  by-law. A variance of [magnitude] is requested."

SECTION F: PREVIOUS APPLICATIONS
  - Any previous Committee of Adjustment applications
    for this property? [query municipal records]
  - File numbers and outcomes: [from records search]

SECTION G: SIGNATURE AND DECLARATION
  [Template for signature block — cannot be auto-signed]

SECTION H: REQUIRED MATERIALS CHECKLIST
  [Auto-checked based on proposal type]
  □ Completed application form (this document)
  □ Application fee ($[amount])
  □ Sketch / site plan showing existing and proposed conditions
  □ Survey (if available)
  □ Photographs of the property and surrounding area
  □ Planning rationale / letter of justification
  □ Owner's authorization (if agent is filing)
  □ Title search (some municipalities)
  □ [Additional studies as identified in Section 15]

TECHNICAL IMPLEMENTATION:
  1. Store municipal form templates as fillable PDFs
     (or recreate as HTML forms)
  2. Map data fields to form fields
  3. Use PDF library (pdf-lib, PyPDF2, or iText) to
     fill form fields programmatically
  4. Generate a completed PDF for download
  5. Highlight fields that require manual completion
     (signature, payment, etc.)
  
  For Toronto:
  - Minor Variance form: Available on toronto.ca
  - Consent form: Available on toronto.ca
  - Forms are updated periodically — maintain current versions
  
  For other municipalities:
  - Build a form template library organized by municipality
  - Start with the largest municipalities:
    Toronto, Ottawa, Mississauga, Brampton, Hamilton,
    Markham, Vaughan, Richmond Hill, Oakville, Burlington,
    London, Kitchener, Waterloo, Guelph, Barrie, Oshawa
```
