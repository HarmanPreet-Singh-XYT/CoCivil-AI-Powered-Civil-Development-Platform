"""Download Toronto Open Data and seed into a self-hosted PostgreSQL database.

Designed for production use with a full Toronto dataset (no bounding box by default).

Features:
- Streaming download with progress reporting
- Chunked / streaming GeoJSON ingestion (handles 475 MB parcels without OOM)
- Resume support: skips already-downloaded files and completed ingestion steps
- Bbox filter available as an explicit opt-in (--bbox) for development/testing only
- Configurable batch sizes for self-hosted Postgres tuning

Usage:
    # Full Toronto (production)
    python scripts/railway_seed_full.py

    # Download only
    python scripts/railway_seed_full.py --download-only

    # Seed from already-downloaded files
    python scripts/railway_seed_full.py --seed-only

    # Development subset (central Toronto only)
    python scripts/railway_seed_full.py --bbox

    # Tune batch size for your hardware
    python scripts/railway_seed_full.py --batch-size 2000
"""
from __future__ import annotations
from fix_water_mains_download import get_download_url_safe
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import httpx

CKAN_BASE = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action"

# ---------------------------------------------------------------------------
# Central Toronto bounding box — development/testing use only
# Covers: waterfront to Eglinton, High Park to East York
# ---------------------------------------------------------------------------
BBOX_WEST = -79.50
BBOX_EAST = -79.30
BBOX_SOUTH = 43.62
BBOX_NORTH = 43.72

# ---------------------------------------------------------------------------
# Download manifest
# (package_name, resource_name_substring, local_filename, expected_min_mb)
# ---------------------------------------------------------------------------
DOWNLOADS = [
    ("property-boundaries",  "property boundaries - 4326.geojson",              "property-boundaries-4326.geojson",              400),
    ("zoning-by-law",        "zoning area - 4326.geojson",                       "zoning-area-4326.geojson",                       40),
    ("zoning-by-law",        "zoning height overlay - 4326.geojson",             "zoning-height-overlay-4326.geojson",              10),
    ("zoning-by-law",        "zoning building setback overlay - 4326.geojson",   "zoning-building-setback-overlay-4326.geojson",    10),
    ("development-applications", "development applications.json",                "development-applications.json",                    5),
    ("watermains",          "water mains - 4326.geojson",                       "water-mains-4326.geojson",                        20),
]

# ---------------------------------------------------------------------------
# Ingestion resume state file
# ---------------------------------------------------------------------------
RESUME_FILE = ".seed_resume.json"


def default_version_label() -> str:
    return datetime.now(timezone.utc).strftime("toronto-open-data-%Y%m%d-%H%M%S")


# ---------------------------------------------------------------------------
# CKAN helpers
# ---------------------------------------------------------------------------

def get_download_url_safe(
    package_name: str,
    preferred_format: str = "geojson",
    resource_name_match: str | None = None,
) -> str | None:
    resp = httpx.get(
        f"{CKAN_BASE}/package_show",
        params={"id": package_name},
        timeout=30,
    )
    resp.raise_for_status()
    resources = resp.json().get("result", {}).get("resources", [])

    if resource_name_match:
        needle = resource_name_match.lower()
        for r in resources:
            name = (r.get("name") or "").lower()
            if needle in name and r.get("url"):
                return r["url"]
        return None

    for r in resources:
        fmt = (r.get("format") or "").lower()
        name = (r.get("name") or "").lower()
        if preferred_format in fmt or preferred_format in name:
            return r["url"]

    for r in resources:
        if r.get("url"):
            return r["url"]
    return None


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------

def download_file(url: str, dest: Path, *, expected_min_mb: int = 0) -> None:
    """Stream-download a file with progress reporting and basic integrity check."""
    print(f"  URL: {url}")
    start = time.monotonic()

    with httpx.stream("GET", url, timeout=600, follow_redirects=True) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0

        with open(dest, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=512 * 1024):  # 512 KB chunks
                f.write(chunk)
                downloaded += len(chunk)
                elapsed = time.monotonic() - start
                speed_mb = (downloaded / (1024 * 1024)) / max(elapsed, 0.1)

                if total:
                    pct = downloaded * 100 // total
                    print(
                        f"\r  {downloaded // (1024*1024):,} MB / "
                        f"{total // (1024*1024):,} MB ({pct}%) "
                        f"— {speed_mb:.1f} MB/s",
                        end="",
                        flush=True,
                    )
                else:
                    print(
                        f"\r  {downloaded // (1024*1024):,} MB downloaded "
                        f"— {speed_mb:.1f} MB/s",
                        end="",
                        flush=True,
                    )

    print()
    size_mb = dest.stat().st_size / (1024 * 1024)
    elapsed = time.monotonic() - start
    print(f"  Saved: {dest} ({size_mb:.1f} MB in {elapsed:.0f}s)")

    if expected_min_mb and size_mb < expected_min_mb * 0.5:
        raise RuntimeError(
            f"Downloaded file is only {size_mb:.1f} MB, expected at least "
            f"{expected_min_mb * 0.5:.0f} MB. The file may be corrupt or incomplete."
        )


def download_all(data_dir: Path, *, use_bbox: bool = False) -> None:
    """Download all Toronto Open Data datasets."""
    data_dir.mkdir(parents=True, exist_ok=True)

    for package_name, resource_match, filename, expected_min_mb in DOWNLOADS:
        dest = data_dir / filename
        size_mb = dest.stat().st_size / (1024 * 1024) if dest.exists() else 0

        if dest.exists() and size_mb >= expected_min_mb * 0.5:
            print(f"[SKIP] {filename} already exists ({size_mb:.0f} MB)")
            continue

        print(f"\n[DOWNLOAD] {filename}")
        preferred = "json" if filename.endswith(".json") else "geojson"
        url = get_download_url_safe(package_name, preferred_format=preferred, resource_name_match=resource_match)

        if not url:
            print(f"  WARNING: No URL found for {package_name!r} (match={resource_match!r}), skipping")
            continue

        try:
            download_file(url, dest, expected_min_mb=expected_min_mb)
        except Exception as exc:
            print(f"  ERROR downloading {package_name}: {exc}")
            if dest.exists():
                dest.unlink()  # Remove partial download

    if use_bbox:
        _apply_bbox_filter(data_dir)


# ---------------------------------------------------------------------------
# Bbox filter (development only)
# ---------------------------------------------------------------------------

def _coord_in_bbox(lon: float, lat: float) -> bool:
    return BBOX_WEST <= lon <= BBOX_EAST and BBOX_SOUTH <= lat <= BBOX_NORTH


def _feature_in_bbox(feature: dict) -> bool:
    geom = feature.get("geometry")
    if not geom:
        return False

    def _check(coords):
        if not coords:
            return False
        if isinstance(coords[0], (int, float)):
            return _coord_in_bbox(coords[0], coords[1])
        return any(_check(c) for c in coords)

    return _check(geom.get("coordinates", []))


def _filter_geojson_bbox(src: Path, dest: Path) -> int:
    try:
        import ijson
    except ImportError:
        print("  WARNING: ijson not installed, skipping bbox filter for", src.name)
        import shutil
        shutil.copy2(src, dest)
        return -1

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
                    print(f"\r  Kept {kept:,} features...", end="", flush=True)
        out.write("\n]}")
    print()
    return kept


def _apply_bbox_filter(data_dir: Path) -> None:
    print("\n" + "-" * 60)
    print("BBOX FILTER (development mode): cropping to central Toronto")
    print(f"  Bounds: W={BBOX_WEST} E={BBOX_EAST} S={BBOX_SOUTH} N={BBOX_NORTH}")
    print("-" * 60)

    geojson_files = [
        "property-boundaries-4326.geojson",
        "zoning-area-4326.geojson",
        "zoning-height-overlay-4326.geojson",
        "zoning-building-setback-overlay-4326.geojson",
        "water-mains-4326.geojson",
    ]
    for filename in geojson_files:
        src = data_dir / filename
        if not src.exists():
            continue
        tmp = data_dir / (filename + ".bbox_tmp")
        print(f"[FILTER] {filename}...")
        kept = _filter_geojson_bbox(src, tmp)
        size_mb = tmp.stat().st_size / (1024 * 1024)
        print(f"  Kept {kept:,} features ({size_mb:.1f} MB)")
        tmp.rename(src)

    # Dev applications (JSON array format)
    dev_apps = data_dir / "development-applications.json"
    if dev_apps.exists():
        print("[FILTER] development-applications.json...")
        with open(dev_apps) as f:
            data = json.load(f)
        if isinstance(data, list):
            filtered = [
                item for item in data
                if _coord_in_bbox(
                    float(item.get("LONGITUDE") or item.get("longitude") or 0),
                    float(item.get("LATITUDE") or item.get("latitude") or 0),
                )
            ]
            kept = len(filtered)
        elif isinstance(data, dict) and "features" in data:
            filtered_features = [f for f in data["features"] if _feature_in_bbox(f)]
            data["features"] = filtered_features
            filtered = data
            kept = len(filtered_features)
        else:
            filtered = data
            kept = -1
        with open(dev_apps, "w") as f:
            json.dump(filtered, f, separators=(",", ":"))
        print(f"  Kept {kept:,} records")


# ---------------------------------------------------------------------------
# Resume state helpers
# ---------------------------------------------------------------------------

def _load_resume(data_dir: Path) -> dict:
    path = data_dir / RESUME_FILE
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {"completed_steps": []}


def _mark_complete(data_dir: Path, step: str) -> None:
    state = _load_resume(data_dir)
    if step not in state["completed_steps"]:
        state["completed_steps"].append(step)
    (data_dir / RESUME_FILE).write_text(json.dumps(state, indent=2))


def _is_complete(data_dir: Path, step: str) -> bool:
    return step in _load_resume(data_dir).get("completed_steps", [])


# ---------------------------------------------------------------------------
# Streaming GeoJSON feature iterator (handles files too large to load at once)
# ---------------------------------------------------------------------------

def stream_geojson_features(path: Path) -> Iterator[dict]:
    """Yield GeoJSON features one at a time using ijson for memory efficiency."""
    try:
        import ijson
        with open(path, "rb") as f:
            yield from ijson.items(f, "features.item")
    except ImportError:
        # Fallback: load whole file (only safe for small files)
        print(f"  WARNING: ijson not installed — loading {path.name} entirely into memory")
        with open(path) as f:
            data = json.load(f)
        yield from data.get("features", [])


# ---------------------------------------------------------------------------
# Seeding — geospatial data
# ---------------------------------------------------------------------------

def seed_geospatial(data_dir: Path, *, version_label: str, batch_size: int = 1000) -> None:
    from app.config import settings
    from app.database import get_sync_db
    from app.devtools import redact_connection_url
    from app.services.geospatial_ingestion import (
        get_or_create_jurisdiction,
        ingest_development_applications,
        ingest_overlay_geojson,
        ingest_parcel_geojson,
        ingest_zoning_geojson,
        ingest_water_mains_geojson,
        resolve_active_snapshot_id,
    )

    print(f"Database: {redact_connection_url(settings.DATABASE_URL_SYNC)}")
    db = get_sync_db()

    try:
        jurisdiction = get_or_create_jurisdiction(db, name="Toronto", province="Ontario", country="CA")
        db.commit()
        print(f"Jurisdiction: {jurisdiction.name} (id={jurisdiction.id})")

        publisher = "City of Toronto"
        source_base = "https://open.toronto.ca"

        # ── Step 1: Parcels ───────────────────────────────────────────────────
        step = "parcels"
        if _is_complete(data_dir, step):
            print("\n[1/6] Parcels: already complete, skipping")
        else:
            parcel_file = data_dir / "property-boundaries-4326.geojson"
            if parcel_file.exists():
                print(f"\n[1/6] Seeding parcels (batch_size={batch_size})...")
                print(f"  File size: {parcel_file.stat().st_size / (1024*1024):.0f} MB")
                snapshot, job = ingest_parcel_geojson(
                    db,
                    jurisdiction_id=jurisdiction.id,
                    geojson_path=parcel_file,
                    version_label=version_label,
                    source_url=f"{source_base}/dataset/property-boundaries",
                    publisher=publisher,
                    batch_size=batch_size,
                    feature_iterator=stream_geojson_features(parcel_file),
                )
                print(f"  processed={job.records_processed:,} failed={job.records_failed:,} status={job.status}")
                _mark_complete(data_dir, step)
            else:
                print(f"\n[1/6] SKIP parcels — {parcel_file} not found")

        # ── Step 2: Zoning ────────────────────────────────────────────────────
        step = "zoning"
        if _is_complete(data_dir, step):
            print("\n[2/6] Zoning: already complete, skipping")
        else:
            zoning_file = data_dir / "zoning-area-4326.geojson"
            if zoning_file.exists():
                print(f"\n[2/6] Seeding zoning areas (batch_size={batch_size})...")
                parcel_snapshot_id = resolve_active_snapshot_id(
                    db, jurisdiction_id=jurisdiction.id, snapshot_type="parcel_base"
                )
                snapshot, job = ingest_zoning_geojson(
                    db,
                    jurisdiction_id=jurisdiction.id,
                    parcel_snapshot_id=parcel_snapshot_id,
                    geojson_path=zoning_file,
                    version_label=version_label,
                    source_url=f"{source_base}/dataset/zoning-by-law-569-2013-area",
                    publisher=publisher,
                    batch_size=batch_size,
                    feature_iterator=stream_geojson_features(zoning_file),
                )
                print(f"  processed={job.records_processed:,} failed={job.records_failed:,} status={job.status}")
                _mark_complete(data_dir, step)
            else:
                print(f"\n[2/6] SKIP zoning — {zoning_file} not found")

        # ── Step 3: Height overlay ────────────────────────────────────────────
        step = "height_overlay"
        if _is_complete(data_dir, step):
            print("\n[3/6] Height overlay: already complete, skipping")
        else:
            height_file = data_dir / "zoning-height-overlay-4326.geojson"
            if height_file.exists():
                print("\n[3/6] Seeding height overlay...")
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
                print(f"  processed={job.records_processed:,} failed={job.records_failed:,} status={job.status}")
                _mark_complete(data_dir, step)
            else:
                print(f"\n[3/6] SKIP height overlay — {height_file} not found")

        # ── Step 4: Setback overlay ───────────────────────────────────────────
        step = "setback_overlay"
        if _is_complete(data_dir, step):
            print("\n[4/6] Setback overlay: already complete, skipping")
        else:
            setback_file = data_dir / "zoning-building-setback-overlay-4326.geojson"
            if setback_file.exists():
                print("\n[4/6] Seeding setback overlay...")
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
                print(f"  processed={job.records_processed:,} failed={job.records_failed:,} status={job.status}")
                _mark_complete(data_dir, step)
            else:
                print(f"\n[4/6] SKIP setback overlay — {setback_file} not found")

        # ── Step 5: Development applications ─────────────────────────────────
        step = "dev_applications"
        if _is_complete(data_dir, step):
            print("\n[5/6] Dev applications: already complete, skipping")
        else:
            dev_apps_file = data_dir / "development-applications.json"
            if dev_apps_file.exists():
                print("\n[5/6] Seeding development applications...")
                parcel_snapshot_id = None
                try:
                    parcel_snapshot_id = resolve_active_snapshot_id(
                        db, jurisdiction_id=jurisdiction.id, snapshot_type="parcel_base"
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
                print(f"  processed={job.records_processed:,} failed={job.records_failed:,} status={job.status}")
                _mark_complete(data_dir, step)
            else:
                print(f"\n[5/6] SKIP dev applications — {dev_apps_file} not found")

        # ── Step 6: Water mains ───────────────────────────────────────────────
        step = "water_mains"
        if _is_complete(data_dir, step):
            print("\n[6/6] Water mains: already complete, skipping")
        else:
            water_file = data_dir / "water-mains-4326.geojson"
            if water_file.exists():
                print(f"\n[6/6] Seeding water mains (batch_size={batch_size})...")
                print(f"  File size: {water_file.stat().st_size / (1024*1024):.0f} MB")
                snapshot, job = ingest_water_mains_geojson(
                    db,
                    jurisdiction_id=jurisdiction.id,
                    geojson_path=water_file,
                    version_label=version_label,
                    source_url=f"{source_base}/dataset/water-mains",
                    publisher=publisher,
                    batch_size=batch_size,
                    feature_iterator=stream_geojson_features(water_file),
                )
                print(f"  processed={job.records_processed:,} failed={job.records_failed:,} status={job.status}")
                _mark_complete(data_dir, step)
            else:
                print(f"\n[6/6] SKIP water mains — {water_file} not found")
                print("  Note: add 'water-mains' to DOWNLOADS or run with --include-water-mains")

        db.commit()
        print("\nGeospatial seed complete!")

    except Exception as exc:
        db.rollback()
        print(f"\nERROR: {exc}")
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Seeding — policies and reference data
# ---------------------------------------------------------------------------

def seed_policies() -> None:
    print("\n[POLICIES] Seeding policy documents...")
    import subprocess
    result = subprocess.run(
        [sys.executable, "scripts/seed_policies.py"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode == 0:
        print("  Policies seeded OK")
        if result.stdout.strip():
            print(f"  {result.stdout.strip()}")
    else:
        print(f"  Policy seed failed:\n{result.stderr[-1000:]}")


def seed_reference_data() -> None:
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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download Toronto Open Data and seed a self-hosted PostgreSQL database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("/tmp/toronto-data"),
        help="Local directory for downloaded files (default: /tmp/toronto-data)",
    )
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Download files only — do not seed the database",
    )
    parser.add_argument(
        "--seed-only",
        action="store_true",
        help="Seed from existing files — skip downloading",
    )
    parser.add_argument(
        "--skip-geo",
        action="store_true",
        help="Skip geospatial data — only seed policies and reference data",
    )
    parser.add_argument(
        "--bbox",
        action="store_true",
        help=(
            "DEVELOPMENT ONLY: filter all datasets to central Toronto bounding box. "
            "Do NOT use in production — you will lose ~90%% of Toronto."
        ),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help=(
            "Number of features per database batch insert. "
            "Increase (e.g. 2000–5000) on a powerful self-hosted instance. "
            "Decrease if you see memory pressure. (default: 1000)"
        ),
    )
    parser.add_argument(
        "--clear-resume",
        action="store_true",
        help="Ignore the resume state file and re-run all steps from scratch",
    )
    parser.add_argument(
        "--version-label",
        default=default_version_label(),
        help="Snapshot version label for this run (default: auto-generated timestamp)",
    )
    args = parser.parse_args()

    if args.bbox:
        print("=" * 60)
        print("WARNING: --bbox is active — dataset will be limited to central Toronto")
        print("This is intended for development and testing only.")
        print("=" * 60)

    if args.clear_resume:
        resume_file = args.data_dir / RESUME_FILE
        if resume_file.exists():
            resume_file.unlink()
            print(f"Cleared resume state: {resume_file}")

    if args.skip_geo:
        seed_policies()
        seed_reference_data()
        print("\nDone (policies + reference only)")
        return

    if not args.seed_only:
        print("=" * 60)
        print("STEP 1: Downloading Toronto Open Data")
        print(f"  Data directory: {args.data_dir.resolve()}")
        if args.bbox:
            print("  Mode: BBOX filter (development subset)")
        else:
            print("  Mode: FULL TORONTO (production)")
        print("=" * 60)
        download_all(args.data_dir, use_bbox=args.bbox)

    if not args.download_only:
        print("\n" + "=" * 60)
        print("STEP 2: Seeding geospatial data")
        print(f"  Version label: {args.version_label}")
        print(f"  Batch size: {args.batch_size}")
        print("=" * 60)
        seed_geospatial(
            args.data_dir,
            version_label=args.version_label,
            batch_size=args.batch_size,
        )

        print("\n" + "=" * 60)
        print("STEP 3: Seeding policies + reference data")
        print("=" * 60)
        seed_policies()
        seed_reference_data()

    print("\n" + "=" * 60)
    print("ALL DONE")
    if not args.bbox:
        print("Full Toronto dataset seeded.")
    else:
        print("Development subset (central Toronto bbox) seeded.")
    print("=" * 60)


if __name__ == "__main__":
    main()