"""Download Toronto Open Data and seed into Railway database.

Run inside Railway via: railway ssh -s Hack_Canada -- python scripts/railway_seed.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import httpx

CKAN_BASE = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action"

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
                    print(f"\r  {downloaded // (1024*1024)} MB / {total // (1024*1024)} MB ({pct}%)", end="", flush=True)
                else:
                    print(f"\r  {downloaded // (1024*1024)} MB downloaded", end="", flush=True)
    print()


def download_all(data_dir: Path) -> None:
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


def seed_data(data_dir: Path) -> None:
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
        version_label = "toronto-open-data-2024"

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
            parcel_snapshot_id = resolve_active_snapshot_id(db, jurisdiction_id=jurisdiction.id, snapshot_type="parcel_base")
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
                parcel_snapshot_id = resolve_active_snapshot_id(db, jurisdiction_id=jurisdiction.id, snapshot_type="parcel_base")
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
    args = parser.parse_args()

    if args.skip_geo:
        seed_policies()
        seed_reference_data()
        print("\nDone (policies + reference only)")
        return

    if not args.seed_only:
        print("=" * 60)
        print("STEP 1: Downloading Toronto Open Data")
        print("=" * 60)
        download_all(args.data_dir)

    if not args.download_only:
        print("\n" + "=" * 60)
        print("STEP 2: Seeding geospatial data")
        print("=" * 60)
        seed_data(args.data_dir)

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
