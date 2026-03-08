---
name: Upload Analysis (PDF/DXF Compliance Review)
description: Automated review of uploaded architectural drawings to extract measurements and compare them against zoning requirements.
---

## 12. Upload Analysis (PDF/DXF Compliance Review)

### What It Is
Automated review of uploaded architectural drawings (PDF or DXF format) to extract dimensions, setbacks, heights, and other metrics, then compare them against zoning requirements.

### Why It Matters
- Replaces manual measurement of drawings
- Catches discrepancies between drawings and application forms
- Speeds up compliance checking

### How to Build It

```
Process:
1. PARSE THE UPLOADED FILE
   PDF: Use OCR + layout analysis to extract:
     - Title block information (project name, address, scale, date)
     - Dimension annotations
     - Area calculations
     - Room labels and uses
     - North arrow and scale
   DXF: Parse layers and entities:
     - Extract polylines for building footprint
     - Extract dimension entities
     - Extract text annotations
     - Identify layers (walls, setbacks, lot lines, etc.)

2. EXTRACT KEY METRICS
   From site plan drawings:
     - Lot dimensions (from lot line entities)
     - Building footprint (from building outline entities)
     - Setbacks (from dimension annotations between
       building and lot lines)
     - Driveway width and location
     - Parking space count and dimensions
   
   From floor plan drawings:
     - GFA per floor
     - Room sizes
     - Unit count and sizes
   
   From elevation drawings:
     - Building height to highest point
     - Storey heights
     - Grade relationship

3. COMPARE TO ZONING
   Feed extracted metrics into the Compliance Matrix generator
   (Section 2 above)

4. GENERATE REPORT
   - List of extracted metrics with confidence scores
   - Comparison to zoning standards
   - Flagged discrepancies between drawings
     (e.g., site plan shows 1.5m side setback,
     but floor plan shows 1.2m)
   - Recommendation for corrections

Technical implementation:
  - PDF parsing: pdf.js, pdfplumber, or Tabula
  - DXF parsing: ezdxf (Python) or dxf-parser (JS)
  - OCR: Tesseract or cloud OCR service
  - Dimension extraction: regex patterns for
    common dimension formats (e.g., "7500" = 7.5m)
  - Scale detection: look for scale bar or title block scale
```
