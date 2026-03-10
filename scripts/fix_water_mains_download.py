"""
Patch for railway_seed_full.py
-------------------------------
The Toronto Open Data CKAN package name for water mains is NOT "water-mains".
The correct slug is "watermains" (no hyphen).

This file provides:
1. The corrected DOWNLOADS list entry
2. A search-based get_download_url_safe() that falls back to package_search
   if package_show returns 404, so future renames don't break the script.

To apply:
  - Replace the water-mains entry in DOWNLOADS with the one below.
  - Replace get_download_url() in railway_seed_full.py with get_download_url_safe().
"""

# ---------------------------------------------------------------------------
# Corrected DOWNLOADS entry
# Replace the last tuple in DOWNLOADS with this:
# ---------------------------------------------------------------------------

WATER_MAINS_DOWNLOAD_ENTRY = (
    "watermains",                          # <-- correct CKAN package slug
    "water mains - 4326.geojson",          # resource name substring to match
    "water-mains-4326.geojson",            # local filename
    20,                                    # expected minimum size in MB
)

# Full corrected DOWNLOADS list (drop-in replacement):
DOWNLOADS = [
    ("property-boundaries",      "property boundaries - 4326.geojson",            "property-boundaries-4326.geojson",            400),
    ("zoning-by-law",            "zoning area - 4326.geojson",                     "zoning-area-4326.geojson",                     40),
    ("zoning-by-law",            "zoning height overlay - 4326.geojson",           "zoning-height-overlay-4326.geojson",           10),
    ("zoning-by-law",            "zoning building setback overlay - 4326.geojson", "zoning-building-setback-overlay-4326.geojson", 10),
    ("development-applications", "development applications.json",                  "development-applications.json",                 5),
    ("watermains",               "water mains - 4326.geojson",                     "water-mains-4326.geojson",                     20),
]


# ---------------------------------------------------------------------------
# Robust URL resolver — tries package_show first, falls back to package_search
# ---------------------------------------------------------------------------

import httpx

CKAN_BASE = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action"


def get_download_url_safe(
    package_name: str,
    preferred_format: str = "geojson",
    resource_name_match: str | None = None,
) -> str | None:
    """
    Find the download URL for a CKAN package resource.

    Tries package_show first (fast, exact match).
    If that returns 404, falls back to package_search so the script
    survives future package renames on the portal.
    """
    resources = _try_package_show(package_name)

    if resources is None:
        # package_show returned 404 — try a keyword search
        print(f"  package_show returned 404 for {package_name!r}, trying package_search...")
        resources = _try_package_search(package_name)

    if resources is None:
        print(f"  WARNING: Could not find package {package_name!r} via show or search")
        return None

    return _pick_resource_url(resources, preferred_format, resource_name_match)


def _try_package_show(package_name: str) -> list | None:
    """Return resource list from package_show, or None on 404."""
    try:
        resp = httpx.get(
            f"{CKAN_BASE}/package_show",
            params={"id": package_name},
            timeout=30,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json().get("result", {}).get("resources", [])
    except httpx.HTTPStatusError:
        return None


def _try_package_search(keyword: str) -> list | None:
    """
    Search for a package by keyword and return resources from the best match.
    Uses the CKAN package_search action.
    """
    try:
        resp = httpx.get(
            f"{CKAN_BASE}/package_search",
            params={"q": keyword, "rows": 5},
            timeout=30,
        )
        resp.raise_for_status()
        results = resp.json().get("result", {}).get("results", [])
        if not results:
            return None

        # Pick the result whose name most closely matches the keyword
        keyword_lower = keyword.lower().replace("-", "").replace("_", "")
        best = None
        for pkg in results:
            pkg_name = (pkg.get("name") or "").lower().replace("-", "").replace("_", "")
            if keyword_lower in pkg_name or pkg_name in keyword_lower:
                best = pkg
                break

        if best is None:
            best = results[0]  # fall back to first result

        print(f"  Found via search: {best.get('name')!r} (title: {best.get('title')!r})")
        return best.get("resources", [])

    except Exception as exc:
        print(f"  package_search failed: {exc}")
        return None


def _pick_resource_url(
    resources: list,
    preferred_format: str,
    resource_name_match: str | None,
) -> str | None:
    """Pick the best resource URL from a list of CKAN resource dicts."""
    # Try exact name match first
    if resource_name_match:
        needle = resource_name_match.lower()
        for r in resources:
            name = (r.get("name") or "").lower()
            if needle in name and r.get("url"):
                return r["url"]
        # Name match failed — fall through to format match
        print(f"  No resource matched name {resource_name_match!r}, trying format match...")

    # Try format match
    for r in resources:
        fmt = (r.get("format") or "").lower()
        name = (r.get("name") or "").lower()
        if preferred_format in fmt or preferred_format in name:
            return r["url"]

    # Last resort: first resource with a URL
    for r in resources:
        if r.get("url"):
            return r["url"]

    return None


# ---------------------------------------------------------------------------
# Quick test — run this file directly to verify the water mains URL resolves
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Testing water mains URL resolution...")
    url = get_download_url_safe(
        "watermains",
        preferred_format="geojson",
        resource_name_match="water mains - 4326.geojson",
    )
    if url:
        print(f"OK — resolved URL: {url}")
    else:
        print("FAILED — could not resolve URL")
        print("\nTrying package_search fallback with 'water mains'...")
        url = get_download_url_safe("water mains", preferred_format="geojson")
        print(f"Fallback result: {url}")