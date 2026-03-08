"""Seed all 5 Toronto Open Data files in one shot.

Usage:
    python scripts/seed_toronto.py --data-dir data/
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.database import get_sync_db
from app.devtools import (
    raise_for_failed_checks,
    redact_connection_url,
    render_preflight_checks,
    run_preflight_checks,
)
from app.services.geospatial_ingestion import (
    get_or_create_jurisdiction,
    ingest_development_applications,
    ingest_overlay_geojson,
    ingest_parcel_geojson,
    ingest_zoning_geojson,
    link_address_file,
    resolve_active_snapshot_id,
)

PUBLISHER = "City of Toronto"
SOURCE_BASE = "https://open.toronto.ca"
ADDRESS_SOURCE_URL = f"{SOURCE_BASE}/dataset/address-points-municipal-toronto-one-address-repository"
ADDRESS_FILE_CANDIDATES = (
    "address-points-4326.geojson",
    "address-points-4326.csv",
    "address_points_4326.geojson",
    "address_points_4326.csv",
    "address-points.geojson",
    "address-points.csv",
    "address_points.geojson",
    "address_points.csv",
)
REQUIRED_DATA_FILES = (
    "property-boundaries-4326.geojson",
    "zoning-area-4326.geojson",
    "zoning-height-overlay-4326.geojson",
    "zoning-building-setback-overlay-4326.geojson",
    "development-applications.json",
)


def _print_result(label: str, snapshot, job) -> None:
    print(
        f"  {label}: snapshot={snapshot.id}  "
        f"processed={job.records_processed}  failed={job.records_failed}  status={job.status}"
    )


def _resolve_address_file(data_dir: Path, explicit_path: Path | None) -> Path | None:
    if explicit_path is not None:
        return explicit_path

    for candidate in ADDRESS_FILE_CANDIDATES:
        path = data_dir / candidate
        if path.exists():
            return path
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Toronto Open Data into Arterial")
    parser.add_argument("--data-dir", required=True, type=Path, help="Directory containing downloaded data files")
    parser.add_argument("--jurisdiction-name", default="Toronto")
    parser.add_argument("--province", default="Ontario")
    parser.add_argument("--country", default="CA")
    parser.add_argument(
        "--version-label",
        default=datetime.now(timezone.utc).strftime("toronto-open-data-%Y%m%d-%H%M%S"),
    )
    parser.add_argument("--address-file", type=Path, default=None, help="Optional Toronto address-points GeoJSON/CSV")
    args = parser.parse_args()

    data_dir = args.data_dir
    required_paths = [data_dir / filename for filename in REQUIRED_DATA_FILES]
    if args.address_file is not None:
        required_paths.append(args.address_file)

    print(f"Database target: {redact_connection_url(settings.DATABASE_URL_SYNC)}")
    print(f"Data directory: {data_dir.resolve()}")
    checks = run_preflight_checks(required_paths=required_paths)
    print(render_preflight_checks(checks))
    try:
        raise_for_failed_checks(checks)
    except RuntimeError as exc:
        raise SystemExit(f"Preflight failed: {exc}") from exc

    db = get_sync_db()
    try:
        jurisdiction = get_or_create_jurisdiction(
            db, name=args.jurisdiction_name, province=args.province, country=args.country
        )
        jid = jurisdiction.id

        # 1 — Property boundaries (parcels)
        print("[1/6] Ingesting property boundaries ...")
        snap_p, job_p = ingest_parcel_geojson(
            db,
            jurisdiction_id=jid,
            geojson_path=data_dir / "property-boundaries-4326.geojson",
            version_label=args.version_label,
            source_url=f"{SOURCE_BASE}/dataset/property-boundaries",
            publisher=PUBLISHER,
        )
        _print_result("parcels", snap_p, job_p)

        parcel_snapshot_id = resolve_active_snapshot_id(db, jurisdiction_id=jid, snapshot_type="parcel_base")
        address_file = _resolve_address_file(data_dir, args.address_file)

        if address_file is not None:
            print("[2/6] Linking address points ...")
            snap_a, job_a = link_address_file(
                db,
                jurisdiction_id=jid,
                parcel_snapshot_id=parcel_snapshot_id,
                source_path=address_file,
                version_label=args.version_label,
                source_url=ADDRESS_SOURCE_URL,
                publisher=PUBLISHER,
            )
            _print_result("address linkage", snap_a, job_a)
        else:
            print("[2/6] Linking address points ...")
            print("  address linkage: skipped  no address-points file found in data directory")

        # 2 — Zoning areas
        print("[3/6] Ingesting zoning areas ...")
        snap_z, job_z = ingest_zoning_geojson(
            db,
            jurisdiction_id=jid,
            parcel_snapshot_id=parcel_snapshot_id,
            geojson_path=data_dir / "zoning-area-4326.geojson",
            version_label=args.version_label,
            source_url=f"{SOURCE_BASE}/dataset/zoning-by-law-569-2013-area",
            publisher=PUBLISHER,
        )
        _print_result("zoning", snap_z, job_z)

        # 3 — Height overlay
        print("[4/6] Ingesting height overlay ...")
        snap_h, job_h = ingest_overlay_geojson(
            db,
            jurisdiction_id=jid,
            geojson_path=data_dir / "zoning-height-overlay-4326.geojson",
            version_label=args.version_label,
            source_url=f"{SOURCE_BASE}/dataset/zoning-by-law-569-2013-height-overlay",
            layer_name="Toronto Height Overlay",
            layer_type="height_overlay",
            publisher=PUBLISHER,
        )
        _print_result("height overlay", snap_h, job_h)

        # 4 — Setback overlay
        print("[5/6] Ingesting setback overlay ...")
        snap_s, job_s = ingest_overlay_geojson(
            db,
            jurisdiction_id=jid,
            geojson_path=data_dir / "zoning-building-setback-overlay-4326.geojson",
            version_label=args.version_label,
            source_url=f"{SOURCE_BASE}/dataset/zoning-by-law-569-2013-setback-overlay",
            layer_name="Toronto Building Setback Overlay",
            layer_type="setback_overlay",
            publisher=PUBLISHER,
        )
        _print_result("setback overlay", snap_s, job_s)

        # 5 — Development applications
        print("[6/6] Ingesting development applications ...")
        snap_d, job_d = ingest_development_applications(
            db,
            jurisdiction_id=jid,
            json_path=data_dir / "development-applications.json",
            version_label=args.version_label,
            source_url=f"{SOURCE_BASE}/dataset/development-applications",
            publisher=PUBLISHER,
            parcel_snapshot_id=parcel_snapshot_id,
        )
        _print_result("dev applications", snap_d, job_d)

        print("\nDone — Toronto seed run completed.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
