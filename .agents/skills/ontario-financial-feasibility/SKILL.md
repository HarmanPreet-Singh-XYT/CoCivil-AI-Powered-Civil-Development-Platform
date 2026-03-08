---
name: Financial Feasibility Summary
description: A high-level financial analysis estimating whether a proposed development is economically viable.
---

## 6. Financial Feasibility Summary

### What It Is
A high-level financial analysis estimating whether a proposed development is economically viable. It includes estimated construction costs, development charges, fees, potential revenue, and return metrics.

### Why It Matters
- Investors and developers need this before committing to a project
- Some planning rationales reference financial feasibility to demonstrate the proposal is achievable
- Helps users understand the total cost of development beyond just the building

### Governing Law
- **Development Charges Act, 1997** — Municipality-specific development charges
- **Planning Act, s. 37 / Community Benefits Charges (s. 37.1)** — Charges for increased density (Bill 23 replaced old s.37 with CBCs)
- **Municipal by-laws** — Application fees, building permit fees, parkland dedication or cash-in-lieu
- **O. Reg. 509/20** — Community Benefits Charges

### Data Required

| Data Point | Source |
|---|---|
| Development charges per unit | Municipal DC by-law and rate schedule |
| Building permit fees | Municipal fee schedule |
| Planning application fees | Municipal fee schedule |
| Parkland dedication / cash-in-lieu rates | Municipal parkland by-law |
| Construction cost per sq ft | Industry sources (Altus Group, RSMeans, Rider Levett Bucknall) |
| Comparable sale prices / rents | MPAC, Realtor.ca, CMHC, Rentals.ca |
| HST implications | CRA rules on new residential |
| Community Benefits Charges | Municipal CBC rate (if applicable — applies to buildings >10 units and ≥5 storeys) |

### How to Build It

**Step 1: Calculate hard costs**
```
Hard costs = Proposed GFA × construction cost per sq ft

Typical Ontario ranges (2024):
  - Low-rise residential: $200-$350/sq ft
  - Mid-rise (4-8 storeys): $300-$450/sq ft
  - High-rise (9+ storeys): $350-$550/sq ft
  - Laneway suite / garden suite: $250-$400/sq ft
```

**Step 2: Calculate soft costs**
```
Soft costs typically = 15-25% of hard costs
Include:
  - Architectural and engineering fees
  - Planning consultant fees
  - Legal fees
  - Survey costs
  - Arborist reports
  - Environmental assessments
  - Geotechnical studies
  - Project management
```

**Step 3: Calculate government fees and charges**
```
Development charges:
  Toronto 2024 rates (example):
  - Single/semi-detached: ~$55,000-$75,000 per unit
  - Apartment (≥2 bedrooms): ~$45,000-$65,000 per unit
  - Apartment (<2 bedrooms): ~$30,000-$45,000 per unit
  Note: Rates vary significantly by municipality

Building permit fees:
  - Typically $10-$25 per sq m of GFA

Planning application fees:
  - Minor variance: $500-$6,000 depending on municipality
  - ZBA: $10,000-$50,000+
  - OPA: $15,000-$75,000+
  - Site plan: $5,000-$30,000+

Parkland dedication or cash-in-lieu:
  - Varies by municipality (Toronto: alternative rate cap
    applies under Bill 23)

Community Benefits Charges:
  - Applies to ≥5 storeys and ≥10 units
  - Rate set by municipal CBC by-law
  - Capped at 4% of land value
```

**Step 4: Estimate revenue**
```
For-sale:
  Revenue = Number of units × average sale price per unit
  (based on comparable sales in the area)

Rental:
  Revenue = Number of units × average monthly rent × 12
  Net Operating Income = Revenue - Operating Expenses (typically 35-45% of revenue)
  Cap rate analysis: Value = NOI / Cap Rate
```

**Step 5: Generate summary**
```
FINANCIAL FEASIBILITY SUMMARY

Project: [Address]
Type: [Description]

COST SUMMARY
| Category | Estimate |
|----------|----------|
| Land Cost | $X (user input or MPAC assessment) |
| Hard Costs | $X |
| Soft Costs | $X |
| Development Charges | $X |
| Building Permit Fees | $X |
| Planning Fees | $X |
| Parkland Cash-in-Lieu | $X |
| Community Benefits Charges | $X (if applicable) |
| HST (net of rebate) | $X |
| Contingency (10%) | $X |
| **TOTAL PROJECT COST** | **$X** |

REVENUE ESTIMATE
| Unit Type | Count | Avg Price/Rent | Total |
|-----------|-------|----------------|-------|
| [Type 1] | X | $X | $X |
| [Type 2] | X | $X | $X |
| **TOTAL REVENUE** | | | **$X** |

KEY METRICS
| Metric | Value |
|--------|-------|
| Profit Margin | X% |
| Return on Investment | X% |
| Cost per Unit | $X |
| Cost per Square Foot | $X |

DISCLAIMER: This is a preliminary estimate for planning purposes only.
Actual costs and revenues may vary. Consult qualified professionals
before making financial decisions.
```
