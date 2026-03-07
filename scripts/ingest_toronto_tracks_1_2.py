import argparse
import uuid
from pathlib import Path

from app.database import get_sync_db
from app.services.geospatial_ingestion import (
    get_or_create_jurisdiction,
    ingest_development_applications,
    ingest_overlay_geojson,
    ingest_parcel_geojson,
    ingest_zoning_geojson,
    link_address_file,
    resolve_active_snapshot_id,
)


def _add_shared_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--jurisdiction-name", default="Toronto")
    parser.add_argument("--province", default="Ontario")
    parser.add_argument("--country", default="CA")
    parser.add_argument("--version-label", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--publisher", default="City of Toronto")


def _resolve_parcel_snapshot_id(args: argparse.Namespace, jurisdiction_id: uuid.UUID, db) -> uuid.UUID:
    if args.parcel_snapshot_id:
        return uuid.UUID(args.parcel_snapshot_id)
    return resolve_active_snapshot_id(db, jurisdiction_id=jurisdiction_id, snapshot_type="parcel_base")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Toronto Tracks 1-2 geospatial datasets into Arterial")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parcel_parser = subparsers.add_parser("parcel-base", help="Ingest parcel polygons from GeoJSON")
    _add_shared_args(parcel_parser)
    parcel_parser.add_argument("--geojson", required=True, type=Path)

    address_parser = subparsers.add_parser("address-linkage", help="Link address points/rows to parcel snapshot")
    _add_shared_args(address_parser)
    address_parser.add_argument("--source-file", required=True, type=Path)
    address_parser.add_argument("--parcel-snapshot-id")

    zoning_parser = subparsers.add_parser("zoning-geometry", help="Ingest zoning polygons and assign primary zones")
    _add_shared_args(zoning_parser)
    zoning_parser.add_argument("--geojson", required=True, type=Path)
    zoning_parser.add_argument("--parcel-snapshot-id")
    zoning_parser.add_argument("--layer-name", default="Toronto Zoning By-law 569-2013")

    dev_apps_parser = subparsers.add_parser("dev-applications", help="Ingest development applications from JSON")
    _add_shared_args(dev_apps_parser)
    dev_apps_parser.add_argument("--json-file", required=True, type=Path)
    dev_apps_parser.add_argument("--parcel-snapshot-id")

    overlay_parser = subparsers.add_parser("overlay", help="Ingest overlay GeoJSON as DatasetLayer")
    _add_shared_args(overlay_parser)
    overlay_parser.add_argument("--geojson", required=True, type=Path)
    overlay_parser.add_argument("--layer-name", required=True)
    overlay_parser.add_argument("--layer-type", required=True)

    args = parser.parse_args()
    db = get_sync_db()
    try:
        jurisdiction = get_or_create_jurisdiction(
            db,
            name=args.jurisdiction_name,
            province=args.province,
            country=args.country,
        )

        if args.command == "parcel-base":
            snapshot, job = ingest_parcel_geojson(
                db,
                jurisdiction_id=jurisdiction.id,
                geojson_path=args.geojson,
                version_label=args.version_label,
                source_url=args.source_url,
                publisher=args.publisher,
            )
        elif args.command == "address-linkage":
            parcel_snapshot_id = _resolve_parcel_snapshot_id(args, jurisdiction.id, db)
            snapshot, job = link_address_file(
                db,
                jurisdiction_id=jurisdiction.id,
                parcel_snapshot_id=parcel_snapshot_id,
                source_path=args.source_file,
                version_label=args.version_label,
                source_url=args.source_url,
                publisher=args.publisher,
            )
        elif args.command == "zoning-geometry":
            parcel_snapshot_id = _resolve_parcel_snapshot_id(args, jurisdiction.id, db)
            snapshot, job = ingest_zoning_geojson(
                db,
                jurisdiction_id=jurisdiction.id,
                parcel_snapshot_id=parcel_snapshot_id,
                geojson_path=args.geojson,
                version_label=args.version_label,
                source_url=args.source_url,
                publisher=args.publisher,
                layer_name=args.layer_name,
            )
        elif args.command == "dev-applications":
            parcel_snapshot_id = None
            if getattr(args, "parcel_snapshot_id", None):
                parcel_snapshot_id = uuid.UUID(args.parcel_snapshot_id)
            else:
                try:
                    parcel_snapshot_id = resolve_active_snapshot_id(
                        db, jurisdiction_id=jurisdiction.id, snapshot_type="parcel_base"
                    )
                except ValueError:
                    pass
            snapshot, job = ingest_development_applications(
                db,
                jurisdiction_id=jurisdiction.id,
                json_path=args.json_file,
                version_label=args.version_label,
                source_url=args.source_url,
                publisher=args.publisher,
                parcel_snapshot_id=parcel_snapshot_id,
            )
        else:
            snapshot, job = ingest_overlay_geojson(
                db,
                jurisdiction_id=jurisdiction.id,
                geojson_path=args.geojson,
                version_label=args.version_label,
                source_url=args.source_url,
                publisher=args.publisher,
                layer_name=args.layer_name,
                layer_type=args.layer_type,
            )

        print(
            {
                "snapshot_id": str(snapshot.id),
                "snapshot_type": snapshot.snapshot_type,
                "job_id": str(job.id),
                "status": job.status,
                "records_processed": job.records_processed,
                "records_failed": job.records_failed,
            }
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
