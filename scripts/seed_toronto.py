"""Seed all 5 Toronto Open Data files in one shot.

Usage:
    python scripts/seed_toronto.py --data-dir data/
"""
from __future__ import annotations

import argparse
from pathlib import Path

from app.database import get_sync_db
from app.services.geospatial_ingestion import (
    get_or_create_jurisdiction,
    ingest_development_applications,
    ingest_overlay_geojson,
    ingest_parcel_geojson,
    ingest_zoning_geojson,
    resolve_active_snapshot_id,
)

PUBLISHER = "City of Toronto"
SOURCE_BASE = "https://open.toronto.ca"


def _print_result(label: str, snapshot, job) -> None:
    print(
        f"  {label}: snapshot={snapshot.id}  "
        f"processed={job.records_processed}  failed={job.records_failed}  status={job.status}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Toronto Open Data into Arterial")
    parser.add_argument("--data-dir", required=True, type=Path, help="Directory containing downloaded data files")
    parser.add_argument("--jurisdiction-name", default="Toronto")
    parser.add_argument("--province", default="Ontario")
    parser.add_argument("--country", default="CA")
    parser.add_argument("--version-label", default="toronto-open-data-2024")
    args = parser.parse_args()

    data_dir = args.data_dir
    db = get_sync_db()
    try:
        jurisdiction = get_or_create_jurisdiction(
            db, name=args.jurisdiction_name, province=args.province, country=args.country
        )
        jid = jurisdiction.id

        # 1 — Property boundaries (parcels)
        print("[1/5] Ingesting property boundaries ...")
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

        # 2 — Zoning areas
        print("[2/5] Ingesting zoning areas ...")
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
        print("[3/5] Ingesting height overlay ...")
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
        print("[4/5] Ingesting setback overlay ...")
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
        print("[5/5] Ingesting development applications ...")
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

        print("\nDone — all 5 datasets ingested.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
