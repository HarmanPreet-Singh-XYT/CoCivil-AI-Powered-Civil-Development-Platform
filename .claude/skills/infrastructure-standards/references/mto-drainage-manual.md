---
title: "MTO Drainage Management Manual — Storm Sewer Design and Hydrology"
category: infrastructure
relevance: "Load when performing drainage design calculations, selecting storm sewer sizes, determining design flows, or applying hydrological methods for Ontario municipal infrastructure."
key_topics: "Manning's equation, rational method, IDF curves, storm sewer sizing, inlet capacity, detention/retention, SWM, minimum grades, time of concentration"
---

# MTO Drainage Management Manual — Storm Sewer Design and Hydrology

The MTO Drainage Management Manual is the primary reference for drainage design methodology in Ontario. Municipal standards typically adopt MTO methods with local modifications (design storm frequencies, IDF curves, runoff coefficients). This reference covers the core design parameters and methods used for storm sewer and stormwater management design.

---

## 1. Design Storm Frequencies

### Standard Return Periods

| Infrastructure Type | Minimum Design Storm |
|--------------------|---------------------|
| Minor system — storm sewers (local roads) | 1:5 year |
| Minor system — storm sewers (collector roads) | 1:10 year |
| Minor system — storm sewers (arterial roads) | 1:10 year |
| Minor system — expressway drainage | 1:25 year |
| Major system — overland flow (all roads) | 1:100 year |
| Culverts — municipal roads | 1:25 to 1:100 year (varies by road class) |
| Culverts — provincial highways | 1:100 year |
| Bridges — provincial highways | 1:100 year design, 1:300 year check |
| SWM facility — quantity control | 1:2 to 1:100 year (per municipality) |
| SWM facility — quality control | 80% long-term average event (TSS removal) |

**Municipal override note**: Toronto requires 1:10 year for minor storm sewers on all road classifications and uses Toronto-specific IDF curves.

---

## 2. Rational Method

The rational method is the standard approach for estimating peak runoff from small drainage areas (typically < 50 ha).

### Formula

```
Q = C * i * A / 360
```

Where:
- **Q** = peak runoff (m3/s)
- **C** = runoff coefficient (dimensionless)
- **i** = rainfall intensity (mm/hr) for the design storm at the time of concentration
- **A** = drainage area (ha)
- **360** = unit conversion constant

### Runoff Coefficients (C Values)

| Land Use | C Value (1:5 year) | C Value (1:100 year) |
|----------|-------------------|---------------------|
| Paved surfaces (roads, parking) | 0.90 | 0.95 |
| Rooftops | 0.85 | 0.90 |
| Gravel surfaces | 0.50 | 0.60 |
| Lawns — sandy soil, flat (<2%) | 0.10 | 0.15 |
| Lawns — sandy soil, steep (>7%) | 0.20 | 0.30 |
| Lawns — clay soil, flat (<2%) | 0.17 | 0.25 |
| Lawns — clay soil, steep (>7%) | 0.35 | 0.45 |
| Parks and open space | 0.15 | 0.25 |
| Single-family residential (40% impervious) | 0.40 | 0.55 |
| Semi-detached residential (55% impervious) | 0.55 | 0.65 |
| Townhouse (65% impervious) | 0.60 | 0.70 |
| Apartment/commercial (80% impervious) | 0.75 | 0.85 |
| Industrial (90% impervious) | 0.85 | 0.90 |
| Central business district | 0.85 | 0.95 |

### Composite Runoff Coefficient

For mixed land-use areas, calculate a weighted composite:

```
C_composite = (C1*A1 + C2*A2 + ... + Cn*An) / (A1 + A2 + ... + An)
```

---

## 3. Time of Concentration

### Definition

Time of concentration (Tc) is the time for runoff to travel from the hydraulically most remote point in the drainage area to the point of interest. It determines the rainfall intensity for the rational method.

### Components

```
Tc = t_overland + t_gutter + t_pipe
```

### Overland Flow Time

Use the Airport (FAA) or Kerby-Hathaway method:

**Airport method:**
```
t = 0.0195 * (0.395 * L)^0.77 / S^0.385
```

Where:
- t = overland flow time (minutes)
- L = flow length (m) — maximum 150 m for overland flow
- S = average slope (m/m)

### Gutter Flow Time

```
t_gutter = L / V
```

Where V is estimated from Manning's equation for the gutter cross-section.

### Pipe Flow Time

```
t_pipe = L / V_full
```

Where V_full is the full-pipe velocity from Manning's equation.

### Minimum Time of Concentration

| Condition | Minimum Tc |
|-----------|-----------|
| Fully developed urban area | 10 minutes |
| Catch basin inlet time | 5 minutes (standard assumption) |

---

## 4. Manning's Equation

### Formula (SI Units)

```
V = (1/n) * R^(2/3) * S^(1/2)
Q = V * A
```

Where:
- **V** = velocity (m/s)
- **n** = Manning's roughness coefficient
- **R** = hydraulic radius (m) = A/P (cross-sectional area / wetted perimeter)
- **S** = slope of energy grade line (m/m) — typically equals pipe slope for uniform flow
- **Q** = flow rate (m3/s)
- **A** = cross-sectional flow area (m2)

### Manning's n Values — Pipes

| Pipe Material | Manning's n |
|--------------|-------------|
| Concrete pipe (new) | 0.013 |
| Concrete pipe (aged, in service) | 0.015 |
| PVC pipe | 0.011 |
| HDPE pipe (smooth interior) | 0.011 |
| HDPE pipe (corrugated interior) | 0.020 |
| Corrugated steel pipe (CSP) | 0.024 |
| Corrugated steel pipe (paved invert) | 0.020 |
| Vitrified clay pipe | 0.013 |
| Ductile iron pipe (cement lined) | 0.012 |
| Brick sewer | 0.015 |

### Manning's n Values — Open Channels

| Channel Type | Manning's n |
|-------------|-------------|
| Concrete-lined channel | 0.013 |
| Grouted riprap | 0.025 |
| Unlined earth channel (clean) | 0.025 |
| Earth channel (weedy) | 0.035 |
| Grass-lined channel (short grass) | 0.030 |
| Grass-lined channel (tall grass) | 0.040 |
| Natural stream (clean, straight) | 0.030 |
| Natural stream (with pools/riffles) | 0.040 |
| Riprap-lined channel | 0.035 |

---

## 5. Storm Sewer Design Parameters

### Minimum Pipe Diameter

| Application | Minimum Diameter |
|-------------|-----------------|
| Storm sewer — mainline | 300 mm (250 mm in some municipalities) |
| Storm sewer — catchbasin lead | 200 mm |
| Sanitary sewer — mainline | 200 mm |
| Sanitary sewer — lateral | 125 mm (150 mm preferred) |

### Minimum and Maximum Velocities

| Condition | Velocity |
|-----------|----------|
| Minimum velocity (self-cleansing) — storm | 0.6 m/s at full flow |
| Minimum velocity (self-cleansing) — sanitary | 0.6 m/s at design flow |
| Maximum velocity — concrete pipe | 4.5 m/s |
| Maximum velocity — PVC pipe | 4.5 m/s |
| Maximum velocity — CSP | 3.0 m/s |
| Maximum velocity — unlined channel | 1.5 m/s |

### Minimum Pipe Grades

| Pipe Diameter (mm) | Minimum Grade (%) |
|--------------------|------------------|
| 200 | 1.00 |
| 250 | 0.67 |
| 300 | 0.50 |
| 375 | 0.40 |
| 450 | 0.33 |
| 525 | 0.25 |
| 600 | 0.22 |
| 675 | 0.20 |
| 750 | 0.18 |
| 900 | 0.15 |
| 1050 | 0.12 |
| 1200 | 0.10 |

**Design note**: These minimum grades produce approximately 0.6 m/s at full flow. Steeper grades are preferred where available to improve self-cleansing.

---

## 6. Pipe Capacity Tables (Full Flow)

### Concrete Pipe (n = 0.013)

| Diameter (mm) | Slope (%) | Full Flow Q (L/s) | Full Flow V (m/s) |
|--------------|-----------|-------------------|-------------------|
| 300 | 0.50 | 28 | 0.39 |
| 300 | 1.00 | 39 | 0.55 |
| 375 | 0.40 | 42 | 0.38 |
| 450 | 0.33 | 64 | 0.40 |
| 525 | 0.25 | 82 | 0.38 |
| 600 | 0.22 | 111 | 0.39 |
| 750 | 0.18 | 181 | 0.41 |
| 900 | 0.15 | 274 | 0.43 |
| 1050 | 0.12 | 367 | 0.42 |
| 1200 | 0.10 | 472 | 0.42 |
| 1500 | 0.08 | 742 | 0.42 |

### PVC Pipe (n = 0.011)

| Diameter (mm) | Slope (%) | Full Flow Q (L/s) | Full Flow V (m/s) |
|--------------|-----------|-------------------|-------------------|
| 200 | 1.00 | 16 | 0.51 |
| 250 | 0.67 | 25 | 0.51 |
| 300 | 0.50 | 33 | 0.47 |
| 375 | 0.40 | 49 | 0.45 |
| 450 | 0.33 | 76 | 0.48 |
| 600 | 0.22 | 131 | 0.46 |

---

## 7. Intensity-Duration-Frequency (IDF) Curves

### How to Use IDF Curves

1. Determine the time of concentration (Tc) for the drainage area
2. Select the design return period (e.g., 1:5 year)
3. Read the rainfall intensity (mm/hr) from the IDF curve at duration = Tc
4. Apply to the rational method formula

### IDF Curve Sources

| Source | Coverage | Format |
|--------|----------|--------|
| Environment Canada IDF tables | Canada-wide stations | Online tables (idf_cc_v4) |
| MTO IDF curves | Provincial highways | MTO drainage manual appendix |
| Municipal IDF curves | City-specific | Published in municipal design standards |
| Toronto IDF | Toronto | City of Toronto Wet Weather Flow Management Guidelines |

### Climate Change Adjustment

Current practice in Ontario:
- Apply a **climate change factor** to historical IDF data
- Typical factor: **1.2 to 1.4** multiplier on rainfall intensity (varies by municipality and study)
- Toronto uses IDF_CC (climate-adjusted) curves published by the University of Western Ontario
- Some municipalities require sensitivity analysis at both current and future-climate IDF

---

## 8. Stormwater Management (SWM) Design Criteria

### Quantity Control

| Control Level | Target |
|--------------|--------|
| Pre-development flow matching | Post-development peak flow must not exceed pre-development for 1:2 through 1:100 year storms |
| Controlled release | Typically via dry or wet detention pond, rooftop storage, or underground tank |
| Regional facility | May serve multiple developments — capacity allocation required |

### Quality Control

| Target | Method |
|--------|--------|
| 80% TSS removal (long-term average) | Enhanced swale, wet pond, bioretention, OGS (oil-grit separator) |
| 70% TSS removal | Standard wet pond or constructed wetland |
| Pre-treatment (basic) | OGS alone (sediment and floatables only) |

### Water Balance

| Requirement | Target |
|-------------|--------|
| Groundwater recharge | Maintain pre-development infiltration volumes |
| Method | Infiltration trenches, bioretention, permeable pavement |
| Constraint | Not permitted in contaminated soil areas or near wellhead protection zones |

---

## 9. Inlet Capacity

### Catchbasin Grate Capacity

Inlet capacity depends on grate type, road grade, and cross-slope. Standard OPSD grates have the following approximate capacities:

| Condition | Single Grate Capacity (L/s) |
|-----------|---------------------------|
| Flat grade (0.5%), 2% cross-slope | 12-15 |
| Moderate grade (2%), 2% cross-slope | 8-12 |
| Steep grade (5%), 2% cross-slope | 5-8 |
| Sag point (low point) | 20-25 (limited by grate area and head) |

### Inlet Spacing

| Road Classification | Maximum Spacing |
|--------------------|----------------|
| Local road | 100-120 m |
| Collector road | 80-100 m |
| Arterial road | 60-80 m |

**Design rule**: Spread width in the gutter must not exceed half the driving lane width. At sag points, provide a minimum of two catchbasins.

---

## 10. Common Design Checks

### Hydraulic Grade Line (HGL) Analysis

Required for all storm sewer systems to verify:
- Pipe capacity is adequate at each segment
- HGL does not rise above the gutter line (surcharging)
- Energy losses at manholes are accounted for (bend losses, junction losses)

### Manhole Losses

| Condition | Head Loss Coefficient (K) |
|-----------|--------------------------|
| Straight through (no diameter change) | 0.15 |
| 45-degree bend | 0.30 |
| 90-degree bend | 0.50 |
| Junction (two pipes converging) | 0.50-1.00 |
| Drop manhole (>0.6 m drop) | 0.00 (energy dissipated in drop) |

### Minimum Cover Requirements

| Pipe Type | Under Roadway | Outside Roadway |
|-----------|--------------|----------------|
| Rigid pipe (concrete) | 1.2 m | 0.6 m |
| Flexible pipe (PVC, HDPE) | 0.9 m | 0.6 m |
| Watermain | 1.5 m (frost protection) | 1.5 m |

---

## Key References

- **MTO Drainage Management Manual**: https://www.ontario.ca/document/drainage-management-manual
- **Environment Canada IDF Tables**: https://climate-change.canada.ca/climate-data/
- **City of Toronto Wet Weather Flow Management Guidelines**: https://www.toronto.ca/services-payments/water-environment/managing-rain-melted-snow/
- **Ontario Provincial Standards (OPSS/OPSD)**: https://www.ontario.ca/page/provincial-standards
- **MOE Stormwater Management Planning and Design Manual (2003)**: https://www.ontario.ca/document/stormwater-management-planning-and-design-manual
