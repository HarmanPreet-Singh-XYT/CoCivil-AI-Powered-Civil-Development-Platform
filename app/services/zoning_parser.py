"""Parse Toronto By-law 569-2013 zone strings into structured components.

Zone strings follow the pattern:
  CATEGORY [density] [(cN; rN)] [HEIGHT_SUFFIX] [(xNNN)]

Examples:
  CR 3.0 (c2.0; r2.5) SS2 (x345)
  R (d0.6) (x123)
  RA 2.5
  CL 2.0 (x15)
  E 1.5
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.data.toronto_zoning import ZONE_STANDARDS


@dataclass(frozen=True)
class ZoneComponents:
    """Parsed components of a By-law 569-2013 zone string."""

    raw: str
    category: str  # e.g., "CR", "R", "RA"
    density: float | None = None  # max total FSI
    commercial_density: float | None = None  # max commercial FSI (CR zones)
    residential_density: float | None = None  # max residential FSI (CR zones)
    height_suffix: str | None = None  # e.g., "SS2" (site-specific height)
    exception_number: int | None = None  # e.g., 345 from (x345)


@dataclass
class ZoneStandards:
    """Deterministic zoning standards for a parsed zone, with by-law citations."""

    category: str
    label: str
    permitted_uses: list[str] = field(default_factory=list)
    max_height_m: float | None = None
    max_storeys: int | None = None
    max_fsi: float | None = None
    min_front_setback_m: float = 0.0
    min_rear_setback_m: float = 7.5
    min_interior_side_setback_m: float = 0.0
    min_exterior_side_setback_m: float = 0.0
    max_lot_coverage_pct: float = 100.0
    min_landscaping_pct: float = 0.0
    bylaw_section: str = ""
    exception_number: int | None = None
    has_site_specific_height: bool = False
    commercial_fsi: float | None = None
    residential_fsi: float | None = None


# Regex patterns
_CATEGORY_RE = re.compile(
    r"^(CR|CL|CG|RM|RA|EL|OR|OS|R|E|I|U)",
    re.IGNORECASE,
)
_DENSITY_RE = re.compile(r"(?:^|\s)([\d]+\.[\d]+|[\d]+)(?=\s|$|\()")
_SPLIT_DENSITY_RE = re.compile(
    r"\(\s*c\s*([\d.]+)\s*;\s*r\s*([\d.]+)\s*\)",
    re.IGNORECASE,
)
_RESIDENTIAL_DENSITY_RE = re.compile(
    r"\(\s*d\s*([\d.]+)\s*\)",
    re.IGNORECASE,
)
_HEIGHT_SUFFIX_RE = re.compile(r"\b(SS\d+)\b", re.IGNORECASE)
_EXCEPTION_RE = re.compile(r"\(\s*x\s*(\d+)\s*\)", re.IGNORECASE)


def parse_zone_string(zone_string: str) -> ZoneComponents:
    """Parse a By-law 569-2013 zone string into structured components."""
    if not zone_string or not zone_string.strip():
        raise ValueError("Zone string cannot be empty")

    raw = zone_string.strip()
    work = raw

    # Extract category
    match = _CATEGORY_RE.match(work)
    if not match:
        raise ValueError(f"Unrecognized zone category in '{raw}'")
    category = match.group(1).upper()

    # Extract exception number (x345)
    exception_number = None
    exc_match = _EXCEPTION_RE.search(work)
    if exc_match:
        exception_number = int(exc_match.group(1))
        work = work[: exc_match.start()] + work[exc_match.end() :]

    # Extract height suffix (SS2)
    height_suffix = None
    hs_match = _HEIGHT_SUFFIX_RE.search(work)
    if hs_match:
        height_suffix = hs_match.group(1).upper()
        work = work[: hs_match.start()] + work[hs_match.end() :]

    # Extract split density (c2.0; r2.5)
    commercial_density = None
    residential_density = None
    split_match = _SPLIT_DENSITY_RE.search(work)
    if split_match:
        commercial_density = float(split_match.group(1))
        residential_density = float(split_match.group(2))
        work = work[: split_match.start()] + work[split_match.end() :]

    # Extract residential density only (d0.6)
    if residential_density is None:
        rd_match = _RESIDENTIAL_DENSITY_RE.search(work)
        if rd_match:
            residential_density = float(rd_match.group(1))
            work = work[: rd_match.start()] + work[rd_match.end() :]

    # Extract total density (the number after the category)
    density = None
    remainder = work[len(category) :].strip()
    d_match = _DENSITY_RE.match(remainder)
    if d_match:
        density = float(d_match.group(1))

    return ZoneComponents(
        raw=raw,
        category=category,
        density=density,
        commercial_density=commercial_density,
        residential_density=residential_density,
        height_suffix=height_suffix,
        exception_number=exception_number,
    )


def get_zone_standards(components: ZoneComponents) -> ZoneStandards:
    """Look up deterministic standards for parsed zone components.

    Returns standards with bylaw_section citations. Zone-suffix density
    and height overrides are applied on top of base category standards.
    """
    base = ZONE_STANDARDS.get(components.category)
    if base is None:
        return ZoneStandards(
            category=components.category,
            label=f"Unknown ({components.category})",
            bylaw_section="",
            exception_number=components.exception_number,
        )

    side_setbacks = base.get("min_side_setback_m", {})
    interior = side_setbacks.get("interior", 0.0) if isinstance(side_setbacks, dict) else 0.0
    exterior = side_setbacks.get("exterior", 0.0) if isinstance(side_setbacks, dict) else 0.0

    # Start with base standards
    standards = ZoneStandards(
        category=components.category,
        label=base["label"],
        permitted_uses=list(base.get("permitted_uses", [])),
        max_height_m=base.get("max_height_m"),
        max_storeys=base.get("max_storeys"),
        max_fsi=base.get("max_fsi"),
        min_front_setback_m=base.get("min_front_setback_m", 0.0),
        min_rear_setback_m=base.get("min_rear_setback_m", 7.5),
        min_interior_side_setback_m=interior,
        min_exterior_side_setback_m=exterior,
        max_lot_coverage_pct=base.get("max_lot_coverage_pct", 100.0),
        min_landscaping_pct=base.get("min_landscaping_pct", 0.0),
        bylaw_section=base["bylaw_section"],
        exception_number=components.exception_number,
        has_site_specific_height=components.height_suffix is not None,
    )

    # Override FSI from zone suffix density
    if components.density is not None:
        standards.max_fsi = components.density

    if components.commercial_density is not None:
        standards.commercial_fsi = components.commercial_density
    if components.residential_density is not None:
        standards.residential_fsi = components.residential_density

    return standards
