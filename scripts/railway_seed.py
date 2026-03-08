"""Download Toronto Open Data and seed into Railway database.

Run inside Railway via:
    railway run --service Hack_Canada python scripts/railway_seed.py

Or for a bbox-filtered subset (recommended for Hobby plan):
    railway run --service Hack_Canada python scripts/railway_seed.py --bbox
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

CKAN_BASE = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action"

# Central Toronto bounding box (WGS84 lon/lat)
# Covers: waterfront to Eglinton, High Park to East York
BBOX_WEST = -79.50
BBOX_EAST = -79.30
BBOX_SOUTH = 43.62
BBOX_NORTH = 43.72

# (package_name, resource_name_substring, local_filename)
# resource_name_substring is matched case-insensitively against CKAN resource names.
# For packages with a single relevant resource, use None to grab the first geojson/json.
DOWNLOADS = [
    ("property-boundaries", None, "property-boundaries-4326.geojson"),
    ("zoning-by-law", "zoning area - 4326.geojson", "zoning-area-4326.geojson"),
    ("zoning-by-law", "zoning height overlay - 4326.geojson", "zoning-height-overlay-4326.geojson"),
    ("zoning-by-law", "zoning building setback overlay - 4326.geojson", "zoning-building-setback-overlay-4326.geojson"),
    ("development-applications", None, "development-applications.json"),
]


def default_version_label() -> str:
    return datetime.now(timezone.utc).strftime("toronto-open-data-%Y%m%d-%H%M%S")


def get_download_url(
    package_name: str,
    preferred_format: str = "geojson",
    resource_name_match: str | None = None,
) -> str | None:
    """Find the download URL for a CKAN package resource.

    If resource_name_match is provided, only return a resource whose name
    contains that substring (case-insensitive).
    """
    resp = httpx.get(f"{CKAN_BASE}/package_show", params={"id": package_name}, timeout=30)
    resp.raise_for_status()
    resources = resp.json().get("result", {}).get("resources", [])

    # If we have a specific resource name to match, find it first
    if resource_name_match:
        needle = resource_name_match.lower()
        for r in resources:
            name = (r.get("name") or "").lower()
            if needle in name and r.get("url"):
                return r["url"]
        # Not found by name
        return None

    # Prefer geojson/json format
    for r in resources:
        fmt = (r.get("format") or "").lower()
        name = (r.get("name") or "").lower()
        if preferred_format in fmt or preferred_format in name:
            return r["url"]

    # Fallback: first resource with a URL
    for r in resources:
        if r.get("url"):
            return r["url"]
    return None


def download_file(url: str, dest: Path) -> None:
    """Download a file with progress reporting."""
    print(f"  Downloading from: {url}")
    with httpx.stream("GET", url, timeout=300, follow_redirects=True) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        with open(dest, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=1024 * 256):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(
                        f"\r  {downloaded // (1024*1024)} MB / "
                        f"{total // (1024*1024)} MB ({pct}%)",
                        end="",
                        flush=True,
                    )
                else:
                    print(f"\r  {downloaded // (1024*1024)} MB downloaded", end="", flush=True)
    print()


def _coord_in_bbox(lon: float, lat: float) -> bool:
    return BBOX_WEST <= lon <= BBOX_EAST and BBOX_SOUTH <= lat <= BBOX_NORTH


def _feature_in_bbox(feature: dict) -> bool:
    """Check if any coordinate of a GeoJSON feature falls within the bounding box."""
    geom = feature.get("geometry")
    if not geom:
        return False

    def _check_coords(coords):
        if not coords:
            return False
        if isinstance(coords[0], (int, float)):
            return _coord_in_bbox(coords[0], coords[1])
        return any(_check_coords(c) for c in coords)

    return _check_coords(geom.get("coordinates", []))


def _feature_point_in_bbox(feature: dict) -> bool:
    """Check if a dev-application point feature falls within the bounding box."""
    geom = feature.get("geometry")
    if not geom:
        # Keep features without geometry (they might have address info)
        return True
    coords = geom.get("coordinates", [])
    if len(coords) >= 2:
        return _coord_in_bbox(float(coords[0]), float(coords[1]))
    return False


def filter_geojson_bbox(src: Path, dest: Path) -> int:
    """Stream-filter a GeoJSON FeatureCollection to only features in the bbox.

    Returns the number of features kept.
    """
    import ijson

    kept = 0
    with open(dest, "w") as out:
        out.write('{"type":"FeatureCollection","features":[\n')
        first = True
        with open(src, "rb") as f:
            for feature in ijson.items(f, "features.item"):
                if not _feature_in_bbox(feature):
                    continue
                if not first:
                    out.write(",\n")
                json.dump(feature, out, separators=(",", ":"))
                first = False
                kept += 1
                if kept % 5000 == 0:
                    print(f"\r  Kept {kept:,} features so far...", end="", flush=True)
        out.write("\n]}")
    print()
    return kept


def filter_dev_apps_bbox(src: Path, dest: Path) -> int:
    """Filter development applications JSON array to bbox."""
    with open(src) as f:
        data = json.load(f)

    # Handle both array and FeatureCollection formats
    if isinstance(data, dict) and "features" in data:
        features = [f for f in data["features"] if _feature_point_in_bbox(f)]
        data["features"] = features
        kept = len(features)
    elif isinstance(data, list):
        # Raw array — keep entries with coordinates in bbox
        filtered = []
        for item in data:
            lon = item.get("LONGITUDE") or item.get("longitude")
            lat = item.get("LATITUDE") or item.get("latitude")
            if lon and lat:
                try:
                    if _coord_in_bbox(float(lon), float(lat)):
                        filtered.append(item)
                        continue
                except (TypeError, ValueError):
                    pass
            # Keep items without coords (they might be matched by address later)
            filtered.append(item)
        data = filtered
        kept = len(data)
    else:
        print("  WARNING: Unrecognized dev applications format, keeping all")
        kept = len(data) if isinstance(data, list) else -1

    with open(dest, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    return kept


def download_all(data_dir: Path, *, use_bbox: bool = False) -> None:
    """Download all datasets into data_dir."""
    data_dir.mkdir(parents=True, exist_ok=True)

    for package_name, resource_match, filename in DOWNLOADS:
        dest = data_dir / filename
        if dest.exists() and dest.stat().st_size > 1000:
            print(f"[SKIP] {filename} already exists ({dest.stat().st_size // (1024*1024)} MB)")
            continue

        print(f"[DOWNLOAD] {package_name} -> {filename}")
        preferred = "json" if filename.endswith(".json") else "geojson"
        url = get_download_url(
            package_name,
            preferred_format=preferred,
            resource_name_match=resource_match,
        )
        if not url:
            print(f"  WARNING: No download URL found for {package_name} (match={resource_match!r}), skipping")
            continue

        try:
            download_file(url, dest)
            size_mb = dest.stat().st_size / (1024 * 1024)
            print(f"  Saved: {dest} ({size_mb:.1f} MB)")
        except Exception as e:
            print(f"  ERROR downloading {package_name}: {e}")

    if use_bbox:
        print("\n" + "-" * 60)
        print("BBOX FILTER: Cropping to central Toronto")
        print(f"  Bounds: W={BBOX_WEST} E={BBOX_EAST} S={BBOX_SOUTH} N={BBOX_NORTH}")
        print("-" * 60)

        # Filter parcels (the big one — 475 MB → ~30-50 MB)
        parcel_raw = data_dir / "property-boundaries-4326.geojson"
        if parcel_raw.exists():
            parcel_filtered = data_dir / "property-boundaries-4326-bbox.geojson"
            if parcel_filtered.exists() and parcel_filtered.stat().st_size > 1000:
                print(f"[SKIP] Parcels already filtered ({parcel_filtered.stat().st_size // (1024*1024)} MB)")
            else:
                print("[FILTER] Parcels...")
                kept = filter_geojson_bbox(parcel_raw, parcel_filtered)
                size_mb = parcel_filtered.stat().st_size / (1024 * 1024)
                print(f"  Kept {kept:,} parcels ({size_mb:.1f} MB)")
            # Replace the original with the filtered version for seeding
            parcel_filtered.rename(parcel_raw)

        # Filter zoning (49 MB — worth filtering too)
        zoning_raw = data_dir / "zoning-area-4326.geojson"
        if zoning_raw.exists():
            zoning_filtered = data_dir / "zoning-area-4326-bbox.geojson"
            if zoning_filtered.exists() and zoning_filtered.stat().st_size > 1000:
                print(f"[SKIP] Zoning already filtered ({zoning_filtered.stat().st_size // (1024*1024)} MB)")
            else:
                print("[FILTER] Zoning areas...")
                kept = filter_geojson_bbox(zoning_raw, zoning_filtered)
                size_mb = zoning_filtered.stat().st_size / (1024 * 1024)
                print(f"  Kept {kept:,} zones ({size_mb:.1f} MB)")
            zoning_filtered.rename(zoning_raw)

        # Filter dev applications
        dev_apps_raw = data_dir / "development-applications.json"
        if dev_apps_raw.exists():
            dev_apps_filtered = data_dir / "development-applications-bbox.json"
            if dev_apps_filtered.exists() and dev_apps_filtered.stat().st_size > 1000:
                print(f"[SKIP] Dev apps already filtered ({dev_apps_filtered.stat().st_size // (1024*1024)} MB)")
            else:
                print("[FILTER] Development applications...")
                kept = filter_dev_apps_bbox(dev_apps_raw, dev_apps_filtered)
                size_mb = dev_apps_filtered.stat().st_size / (1024 * 1024)
                print(f"  Kept {kept:,} applications ({size_mb:.1f} MB)")
            dev_apps_filtered.rename(dev_apps_raw)

        # Height/setback overlays are small (<16 MB), filter for consistency
        for overlay_name in ("zoning-height-overlay-4326.geojson", "zoning-building-setback-overlay-4326.geojson"):
            overlay_raw = data_dir / overlay_name
            if overlay_raw.exists():
                overlay_filtered = data_dir / overlay_name.replace(".geojson", "-bbox.geojson")
                if overlay_filtered.exists() and overlay_filtered.stat().st_size > 1000:
                    print(f"[SKIP] {overlay_name} already filtered")
                else:
                    print(f"[FILTER] {overlay_name}...")
                    kept = filter_geojson_bbox(overlay_raw, overlay_filtered)
                    size_mb = overlay_filtered.stat().st_size / (1024 * 1024)
                    print(f"  Kept {kept:,} features ({size_mb:.1f} MB)")
                overlay_filtered.rename(overlay_raw)


def seed_data(data_dir: Path, *, version_label: str) -> None:
    """Run the seed using the existing seed_toronto.py logic."""
    from app.config import settings
    from app.database import get_sync_db
    from app.devtools import redact_connection_url
    from app.services.geospatial_ingestion import (
        get_or_create_jurisdiction,
        ingest_development_applications,
        ingest_overlay_geojson,
        ingest_parcel_geojson,
        ingest_zoning_geojson,
        resolve_active_snapshot_id,
    )

    print(f"\nDatabase: {redact_connection_url(settings.DATABASE_URL_SYNC)}")
    db = get_sync_db()

    try:
        jurisdiction = get_or_create_jurisdiction(db, name="Toronto", province="Ontario", country="CA")
        db.commit()
        print(f"Jurisdiction: {jurisdiction.name} (id={jurisdiction.id})")

        publisher = "City of Toronto"
        source_base = "https://open.toronto.ca"
        # 1. Parcels
        parcel_file = data_dir / "property-boundaries-4326.geojson"
        if parcel_file.exists():
            print("\n[1/5] Seeding parcels...")
            snapshot, job = ingest_parcel_geojson(
                db,
                jurisdiction_id=jurisdiction.id,
                geojson_path=parcel_file,
                version_label=version_label,
                source_url=f"{source_base}/dataset/property-boundaries",
                publisher=publisher,
            )
            print(f"  Parcels: processed={job.records_processed} failed={job.records_failed} status={job.status}")
        else:
            print("[1/5] SKIP parcels - file not found")

        # 2. Zoning
        zoning_file = data_dir / "zoning-area-4326.geojson"
        if zoning_file.exists():
            print("\n[2/5] Seeding zoning...")
            parcel_snapshot_id = resolve_active_snapshot_id(
                db,
                jurisdiction_id=jurisdiction.id,
                snapshot_type="parcel_base",
            )
            snapshot, job = ingest_zoning_geojson(
                db,
                jurisdiction_id=jurisdiction.id,
                parcel_snapshot_id=parcel_snapshot_id,
                geojson_path=zoning_file,
                version_label=version_label,
                source_url=f"{source_base}/dataset/zoning-by-law-569-2013-area",
                publisher=publisher,
            )
            print(f"  Zoning: processed={job.records_processed} failed={job.records_failed} status={job.status}")
        else:
            print("[2/5] SKIP zoning - file not found")

        # 3. Height overlay
        height_file = data_dir / "zoning-height-overlay-4326.geojson"
        if height_file.exists():
            print("\n[3/5] Seeding height overlay...")
            snapshot, job = ingest_overlay_geojson(
                db,
                jurisdiction_id=jurisdiction.id,
                geojson_path=height_file,
                version_label=version_label,
                source_url=f"{source_base}/dataset/zoning-by-law-569-2013-height-overlay",
                publisher=publisher,
                layer_name="Zoning Height Overlay",
                layer_type="height_overlay",
            )
            print(f"  Height: processed={job.records_processed} failed={job.records_failed} status={job.status}")
        else:
            print("[3/5] SKIP height overlay - file not found")

        # 4. Setback overlay
        setback_file = data_dir / "zoning-building-setback-overlay-4326.geojson"
        if setback_file.exists():
            print("\n[4/5] Seeding setback overlay...")
            snapshot, job = ingest_overlay_geojson(
                db,
                jurisdiction_id=jurisdiction.id,
                geojson_path=setback_file,
                version_label=version_label,
                source_url=f"{source_base}/dataset/zoning-by-law-569-2013-setback-overlay",
                publisher=publisher,
                layer_name="Zoning Building Setback Overlay",
                layer_type="setback_overlay",
            )
            print(f"  Setback: processed={job.records_processed} failed={job.records_failed} status={job.status}")
        else:
            print("[4/5] SKIP setback overlay - file not found")

        # 5. Development applications
        dev_apps_file = data_dir / "development-applications.json"
        if dev_apps_file.exists():
            print("\n[5/5] Seeding development applications...")
            parcel_snapshot_id = None
            try:
                parcel_snapshot_id = resolve_active_snapshot_id(
                    db,
                    jurisdiction_id=jurisdiction.id,
                    snapshot_type="parcel_base",
                )
            except ValueError:
                pass
            snapshot, job = ingest_development_applications(
                db,
                jurisdiction_id=jurisdiction.id,
                json_path=dev_apps_file,
                version_label=version_label,
                source_url=f"{source_base}/dataset/development-applications",
                publisher=publisher,
                parcel_snapshot_id=parcel_snapshot_id,
            )
            print(f"  Dev apps: processed={job.records_processed} failed={job.records_failed} status={job.status}")
        else:
            print("[5/5] SKIP dev applications - file not found")

        db.commit()
        print("\nSeed complete!")

    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        db.close()


def seed_policies() -> None:
    """Seed policy documents (no files needed)."""
    print("\n[POLICIES] Seeding policy documents...")
    # Import and run inline to avoid import-time side effects
    import subprocess
    result = subprocess.run(
        [sys.executable, "scripts/seed_policies.py"],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode == 0:
        print("  Policies seeded OK")
    else:
        print(f"  Policy seed failed: {result.stderr[-500:]}")


def seed_reference_data() -> None:
    """Seed reference data (no files needed)."""
    print("\n[REFERENCE] Seeding reference data...")
    from app.database import get_sync_db
    from app.services.thin_slice_runtime import ensure_reference_data

    db = get_sync_db()
    try:
        ensure_reference_data(db)
        db.commit()
        print("  Reference data seeded OK")
    finally:
        db.close()


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Download Toronto Open Data and seed Railway database")
    parser.add_argument("--data-dir", type=Path, default=Path("/tmp/toronto-data"))
    parser.add_argument("--download-only", action="store_true", help="Only download, don't seed")
    parser.add_argument("--seed-only", action="store_true", help="Only seed (files must exist)")
    parser.add_argument("--skip-geo", action="store_true", help="Skip geospatial data, only seed policies + reference")
    parser.add_argument("--bbox", action="store_true", help="Filter datasets to central Toronto bounding box (recommended for Hobby plan)")
    parser.add_argument(
        "--version-label",
        default=default_version_label(),
        help="Snapshot version label to use for this run (defaults to a fresh UTC timestamp)",
    )
    args = parser.parse_args()

    if args.skip_geo:
        seed_policies()
        seed_reference_data()
        print("\nDone (policies + reference only)")
        return

    if not args.seed_only:
        print("=" * 60)
        print("STEP 1: Downloading Toronto Open Data")
        if args.bbox:
            print("  (will filter to central Toronto bounding box)")
        print("=" * 60)
        download_all(args.data_dir, use_bbox=args.bbox)

    if not args.download_only:
        print("\n" + "=" * 60)
        print("STEP 2: Seeding geospatial data")
        print("=" * 60)
        print(f"Using version label: {args.version_label}")
        seed_data(args.data_dir, version_label=args.version_label)

        print("\n" + "=" * 60)
        print("STEP 3: Seeding policies + reference data")
        print("=" * 60)
        seed_policies()
        seed_reference_data()

    print("\n" + "=" * 60)
    print("ALL DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
