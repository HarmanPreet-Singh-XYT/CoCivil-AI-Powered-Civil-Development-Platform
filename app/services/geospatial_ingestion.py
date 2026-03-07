from __future__ import annotations

import csv
import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from geoalchemy2 import WKTElement
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.dataset import DatasetFeature, DatasetLayer
from app.models.entitlement import DevelopmentApplication
from app.models.geospatial import Jurisdiction, Parcel, ParcelAddress, ParcelZoningAssignment
from app.models.ingestion import IngestionJob, SourceSnapshot
from app.services.geospatial import (
    AddressCandidate,
    ZoningAssignmentCandidate,
    choose_canonical_address,
    choose_primary_zoning_assignment,
)

INGESTION_VERSION = "tracks_1_2_v1"

PARCEL_PIN_FIELDS = ("pin", "PIN", "parcel_id", "PARCEL_ID", "roll_number", "PARCELID")
PARCEL_ADDRESS_FIELDS = ("address", "ADDRESS", "municipal_address", "MUNICIPAL_ADDRESS", "LINEAR_NAME_FULL")
PARCEL_LOT_AREA_FIELDS = ("lot_area_m2", "LOT_AREA_M2", "lot_area", "AREA", "STATEDAREA")
PARCEL_FRONTAGE_FIELDS = ("lot_frontage_m", "LOT_FRONTAGE_M", "frontage")
PARCEL_DEPTH_FIELDS = ("lot_depth_m", "LOT_DEPTH_M", "depth")
PARCEL_CURRENT_USE_FIELDS = ("current_use", "CURRENT_USE", "land_use")

ADDRESS_TEXT_FIELDS = ("address_text", "ADDRESS_FULL", "full_address", "ADDRESS")
ADDRESS_PIN_FIELDS = ("pin", "PIN", "parcel_pin", "parcel_id")
ADDRESS_LAT_FIELDS = ("lat", "LAT", "latitude", "LATITUDE", "y", "Y")
ADDRESS_LON_FIELDS = ("lon", "LON", "longitude", "LONGITUDE", "x", "X")

ZONING_CODE_FIELDS = ("zone_code", "ZONE_CODE", "zone", "ZONE", "label", "LABEL", "ZN_ZONE", "ZN_STRING", "GEN_ZONE")


@dataclass
class IngestionSummary:
    processed: int = 0
    failed: int = 0
    issues: list[dict[str, Any]] | None = None

    def as_json(self) -> dict[str, Any]:
        return {
            "processed": self.processed,
            "failed": self.failed,
            "issues": self.issues or [],
        }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _coerce_float(value: Any) -> float | None:
    if value in (None, "", "null"):
        return None
    if isinstance(value, str):
        value = re.sub(r"\s*(sq\.?m|m2|m²|ft2|ft²|acres?).*$", "", value, flags=re.IGNORECASE).strip()
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pick(properties: dict[str, Any], aliases: Iterable[str]) -> Any:
    for alias in aliases:
        if alias in properties and properties[alias] not in (None, ""):
            return properties[alias]
    return None


def _coords_to_wkt(coords: Any) -> str:
    if isinstance(coords, (list, tuple)):
        if coords and isinstance(coords[0], (list, tuple)):
            return ", ".join(_coords_to_wkt(item) for item in coords)
        return " ".join(str(value) for value in coords)
    raise ValueError("Invalid coordinate structure")


def geojson_to_wkt(geometry: dict[str, Any]) -> str:
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates")
    if geom_type == "Point":
        return f"POINT ({_coords_to_wkt(coords)})"
    if geom_type == "Polygon":
        rings = ", ".join(f"({_coords_to_wkt(ring)})" for ring in coords)
        return f"POLYGON ({rings})"
    if geom_type == "MultiPolygon":
        polygons = ", ".join(f"(({', '.join(f'({_coords_to_wkt(ring)})' for ring in polygon)}))" for polygon in coords)
        return f"MULTIPOLYGON ({polygons})"
    raise ValueError(f"Unsupported geometry type: {geom_type}")


def _read_geojson(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text())
    if payload.get("type") != "FeatureCollection":
        raise ValueError(f"{path} must be a GeoJSON FeatureCollection")
    return payload.get("features", [])


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def get_or_create_jurisdiction(
    db: Session,
    *,
    name: str,
    province: str = "Ontario",
    country: str = "CA",
) -> Jurisdiction:
    jurisdiction = db.execute(
        select(Jurisdiction).where(
            Jurisdiction.name == name,
            Jurisdiction.province == province,
            Jurisdiction.country == country,
        )
    ).scalars().first()
    if jurisdiction:
        return jurisdiction

    jurisdiction = Jurisdiction(name=name, province=province, country=country)
    db.add(jurisdiction)
    db.flush()
    return jurisdiction


def create_snapshot(
    db: Session,
    *,
    jurisdiction_id: uuid.UUID,
    snapshot_type: str,
    version_label: str,
    source_url: str,
    publisher: str | None,
    file_hash: str,
    acquired_at: datetime | None = None,
    schema_version: str | None = None,
) -> SourceSnapshot:
    snapshot = SourceSnapshot(
        jurisdiction_id=jurisdiction_id,
        snapshot_type=snapshot_type,
        version_label=version_label,
        extractor_version=INGESTION_VERSION,
        extraction_confidence=1.0,
        validation_summary_json={},
        created_at=_now(),
    )
    if hasattr(snapshot, "source_url"):
        snapshot.source_url = source_url
    if hasattr(snapshot, "publisher"):
        snapshot.publisher = publisher
    if hasattr(snapshot, "file_hash"):
        snapshot.file_hash = file_hash
    if hasattr(snapshot, "acquired_at"):
        snapshot.acquired_at = acquired_at or _now()
    if hasattr(snapshot, "schema_version"):
        snapshot.schema_version = schema_version

    db.add(snapshot)
    db.flush()
    return snapshot


def create_ingestion_job(
    db: Session,
    *,
    jurisdiction_id: uuid.UUID,
    source_url: str,
    source_snapshot_id: uuid.UUID,
    job_type: str,
) -> IngestionJob:
    job = IngestionJob(
        jurisdiction_id=jurisdiction_id,
        source_url=source_url,
        source_snapshot_id=source_snapshot_id,
        source_type=job_type,
        job_type=job_type,
        parser_version=INGESTION_VERSION,
        status="running",
        started_at=_now(),
        validation_summary_json={},
    )
    db.add(job)
    db.flush()
    return job


def publish_snapshot(db: Session, snapshot: SourceSnapshot, *, validation_summary: dict[str, Any]) -> None:
    db.execute(
        select(SourceSnapshot)
        .where(
            SourceSnapshot.jurisdiction_id == snapshot.jurisdiction_id,
            SourceSnapshot.snapshot_type == snapshot.snapshot_type,
            SourceSnapshot.is_active.is_(True),
        )
    )
    db.query(SourceSnapshot).filter(
        SourceSnapshot.jurisdiction_id == snapshot.jurisdiction_id,
        SourceSnapshot.snapshot_type == snapshot.snapshot_type,
        SourceSnapshot.is_active.is_(True),
        SourceSnapshot.id != snapshot.id,
    ).update({"is_active": False, "published_at": None}, synchronize_session=False)
    snapshot.is_active = True
    snapshot.published_at = _now()
    snapshot.validation_summary_json = validation_summary


def _finalize_job(job: IngestionJob, summary: IngestionSummary, *, error: str | None = None) -> None:
    job.records_processed = summary.processed
    job.records_failed = summary.failed
    job.validation_summary_json = summary.as_json()
    job.status = "failed" if error else "completed"
    job.error_message = error
    job.completed_at = _now()


def ingest_parcel_geojson(
    db: Session,
    *,
    jurisdiction_id: uuid.UUID,
    geojson_path: Path,
    version_label: str,
    source_url: str,
    publisher: str | None = None,
) -> tuple[SourceSnapshot, IngestionJob]:
    features = _read_geojson(geojson_path)
    snapshot = create_snapshot(
        db,
        jurisdiction_id=jurisdiction_id,
        snapshot_type="parcel_base",
        version_label=version_label,
        source_url=source_url,
        publisher=publisher,
        file_hash=_sha256_file(geojson_path),
        schema_version="geojson-feature-collection",
    )
    job = create_ingestion_job(
        db,
        jurisdiction_id=jurisdiction_id,
        source_url=source_url,
        source_snapshot_id=snapshot.id,
        job_type="parcel_base",
    )

    summary = IngestionSummary(issues=[])
    seen_pins: set[str] = set()
    try:
        for index, feature in enumerate(features):
            properties = feature.get("properties") or {}
            geometry = feature.get("geometry") or {}
            pin = _pick(properties, PARCEL_PIN_FIELDS)
            if pin in seen_pins:
                summary.failed += 1
                summary.issues.append({"row": index, "reason": "duplicate_pin", "pin": pin})
                continue
            if not pin:
                summary.failed += 1
                summary.issues.append({"row": index, "reason": "missing_pin"})
                continue

            seen_pins.add(str(pin))
            address = _pick(properties, PARCEL_ADDRESS_FIELDS)
            if not address or address == _pick(properties, ("LINEAR_NAME_FULL",)):
                addr_num = properties.get("ADDRESS_NUMBER") or ""
                street = properties.get("LINEAR_NAME_FULL") or ""
                composed = f"{addr_num} {street}".strip()
                if composed:
                    address = composed
            parcel = Parcel(
                jurisdiction_id=jurisdiction_id,
                source_snapshot_id=snapshot.id,
                pin=str(pin),
                address=address,
                geom=WKTElement(geojson_to_wkt(geometry), srid=4326),
                lot_area_m2=_coerce_float(_pick(properties, PARCEL_LOT_AREA_FIELDS)),
                lot_frontage_m=_coerce_float(_pick(properties, PARCEL_FRONTAGE_FIELDS)),
                lot_depth_m=_coerce_float(_pick(properties, PARCEL_DEPTH_FIELDS)),
                current_use=_pick(properties, PARCEL_CURRENT_USE_FIELDS),
            )
            db.add(parcel)
            summary.processed += 1

        publish_snapshot(db, snapshot, validation_summary=summary.as_json())
        _finalize_job(job, summary)
    except Exception as exc:
        summary.failed += 1
        summary.issues.append({"reason": "exception", "detail": str(exc)})
        _finalize_job(job, summary, error=str(exc))
        raise

    db.commit()
    return snapshot, job


def link_address_file(
    db: Session,
    *,
    jurisdiction_id: uuid.UUID,
    parcel_snapshot_id: uuid.UUID,
    source_path: Path,
    version_label: str,
    source_url: str,
    publisher: str | None = None,
) -> tuple[SourceSnapshot, IngestionJob]:
    snapshot = create_snapshot(
        db,
        jurisdiction_id=jurisdiction_id,
        snapshot_type="address_linkage",
        version_label=version_label,
        source_url=source_url,
        publisher=publisher,
        file_hash=_sha256_file(source_path),
        schema_version=source_path.suffix.lower().lstrip(".") or "unknown",
    )
    job = create_ingestion_job(
        db,
        jurisdiction_id=jurisdiction_id,
        source_url=source_url,
        source_snapshot_id=snapshot.id,
        job_type="address_linkage",
    )

    rows = _read_geojson(source_path) if source_path.suffix.lower() in {".geojson", ".json"} else _read_csv(source_path)
    summary = IngestionSummary(issues=[])
    linked_candidates: dict[uuid.UUID, list[AddressCandidate]] = {}

    try:
        for index, row in enumerate(rows):
            properties = row.get("properties") if isinstance(row, dict) and "properties" in row else row
            geometry = row.get("geometry") if isinstance(row, dict) and "geometry" in row else None
            source_record_id = str(row.get("id") or _pick(properties, ("id", "ID", "OBJECTID")) or index)
            address_text = _pick(properties, ADDRESS_TEXT_FIELDS)
            if not address_text:
                summary.failed += 1
                summary.issues.append(
                    {
                        "row": index,
                        "reason": "missing_address_text",
                        "source_record_id": source_record_id,
                    }
                )
                continue

            parcels: list[Parcel] = []
            pin = _pick(properties, ADDRESS_PIN_FIELDS)
            if pin:
                parcels = db.execute(
                    select(Parcel).where(
                        Parcel.jurisdiction_id == jurisdiction_id,
                        Parcel.source_snapshot_id == parcel_snapshot_id,
                        Parcel.pin == str(pin),
                    )
                ).scalars().all()

            point_geom = None
            if not parcels:
                if geometry:
                    point_geom = WKTElement(geojson_to_wkt(geometry), srid=4326)
                else:
                    lat = _coerce_float(_pick(properties, ADDRESS_LAT_FIELDS))
                    lon = _coerce_float(_pick(properties, ADDRESS_LON_FIELDS))
                    if lat is not None and lon is not None:
                        point_geom = WKTElement(f"POINT ({lon} {lat})", srid=4326)

                if point_geom is not None:
                    parcels = db.execute(
                        select(Parcel).where(
                            Parcel.jurisdiction_id == jurisdiction_id,
                            Parcel.source_snapshot_id == parcel_snapshot_id,
                            func.ST_Contains(Parcel.geom, point_geom),
                        )
                    ).scalars().all()

            if len(parcels) != 1:
                summary.failed += 1
                summary.issues.append(
                    {
                        "row": index,
                        "reason": "ambiguous_address_match" if len(parcels) > 1 else "address_match_not_found",
                        "source_record_id": source_record_id,
                    }
                )
                continue

            parcel = parcels[0]
            match_method = "source_key" if pin else "spatial_contains"
            match_confidence = 1.0 if pin else 0.9
            parcel_address = ParcelAddress(
                parcel_id=parcel.id,
                source_snapshot_id=snapshot.id,
                source_record_id=source_record_id,
                address_text=str(address_text),
                address_point_geom=point_geom,
                match_method=match_method,
                match_confidence=match_confidence,
                is_canonical=False,
            )
            db.add(parcel_address)
            linked_candidates.setdefault(parcel.id, []).append(
                AddressCandidate(
                    address_text=str(address_text),
                    match_method=match_method,
                    match_confidence=match_confidence,
                    source_record_id=source_record_id,
                )
            )
            summary.processed += 1

        db.flush()
        for parcel_id, candidates in linked_candidates.items():
            canonical = choose_canonical_address(candidates)
            if canonical is None:
                continue

            db.execute(
                select(ParcelAddress)
                .where(ParcelAddress.parcel_id == parcel_id, ParcelAddress.source_snapshot_id == snapshot.id)
            )
            addresses = db.execute(
                select(ParcelAddress).where(
                    ParcelAddress.parcel_id == parcel_id,
                    ParcelAddress.source_snapshot_id == snapshot.id,
                )
            ).scalars().all()
            for address in addresses:
                address.is_canonical = address.address_text == canonical.address_text and (
                    address.source_record_id == canonical.source_record_id
                )

            parcel = db.get(Parcel, parcel_id)
            if parcel:
                parcel.address = canonical.address_text

        publish_snapshot(db, snapshot, validation_summary=summary.as_json())
        _finalize_job(job, summary)
    except Exception as exc:
        summary.failed += 1
        summary.issues.append({"reason": "exception", "detail": str(exc)})
        _finalize_job(job, summary, error=str(exc))
        raise

    db.commit()
    return snapshot, job


def ingest_zoning_geojson(
    db: Session,
    *,
    jurisdiction_id: uuid.UUID,
    parcel_snapshot_id: uuid.UUID,
    geojson_path: Path,
    version_label: str,
    source_url: str,
    publisher: str | None = None,
    layer_name: str = "Toronto Zoning By-law 569-2013",
) -> tuple[SourceSnapshot, IngestionJob]:
    features = _read_geojson(geojson_path)
    snapshot = create_snapshot(
        db,
        jurisdiction_id=jurisdiction_id,
        snapshot_type="zoning_geometry",
        version_label=version_label,
        source_url=source_url,
        publisher=publisher,
        file_hash=_sha256_file(geojson_path),
        schema_version="geojson-feature-collection",
    )
    job = create_ingestion_job(
        db,
        jurisdiction_id=jurisdiction_id,
        source_url=source_url,
        source_snapshot_id=snapshot.id,
        job_type="zoning_geometry",
    )
    layer = DatasetLayer(
        jurisdiction_id=jurisdiction_id,
        source_snapshot_id=snapshot.id,
        name=layer_name,
        layer_type="zoning",
        source_url=source_url,
        publisher=publisher,
        acquired_at=_now(),
        source_schema_version="geojson-feature-collection",
        last_refreshed=_now(),
        published_at=None,
    )
    db.add(layer)
    db.flush()

    summary = IngestionSummary(issues=[])
    try:
        for index, feature in enumerate(features):
            properties = feature.get("properties") or {}
            geometry = feature.get("geometry") or {}
            zone_code = _pick(properties, ZONING_CODE_FIELDS)
            if not zone_code:
                summary.failed += 1
                summary.issues.append({"row": index, "reason": "missing_zone_code"})
                continue

            dataset_feature = DatasetFeature(
                dataset_layer_id=layer.id,
                source_record_id=str(feature.get("id") or _pick(properties, ("id", "ID", "OBJECTID")) or index),
                geom=WKTElement(geojson_to_wkt(geometry), srid=4326),
                attributes_json={**properties, "zone_code": str(zone_code)},
            )
            db.add(dataset_feature)
            summary.processed += 1

        db.flush()
        parcels = db.execute(
            select(Parcel).where(
                Parcel.jurisdiction_id == jurisdiction_id,
                Parcel.source_snapshot_id == parcel_snapshot_id,
            )
        ).scalars().all()

        for parcel in parcels:
            overlap_area = func.ST_Area(func.ST_Transform(func.ST_Intersection(DatasetFeature.geom, parcel.geom), 3857))
            overlapping = db.execute(
                select(DatasetFeature, overlap_area.label("overlap_area"))
                .join(DatasetLayer, DatasetFeature.dataset_layer_id == DatasetLayer.id)
                .where(
                    DatasetLayer.id == layer.id,
                    func.ST_Intersects(DatasetFeature.geom, parcel.geom),
                )
                .order_by(
                    func.ST_Area(
                        func.ST_Transform(func.ST_Intersection(DatasetFeature.geom, parcel.geom), 3857)
                    ).desc()
                )
            ).all()

            candidates: list[ZoningAssignmentCandidate] = []
            assignments: list[ParcelZoningAssignment] = []

            for dataset_feature, overlap in overlapping:
                zone_code = str(dataset_feature.attributes_json.get("zone_code"))
                candidates.append(
                    ZoningAssignmentCandidate(
                        dataset_feature_id=dataset_feature.id,
                        zone_code=zone_code,
                        assignment_method="max_overlap",
                        overlap_area_m2=float(overlap) if overlap is not None else None,
                    )
                )
                assignments.append(
                    ParcelZoningAssignment(
                        parcel_id=parcel.id,
                        dataset_feature_id=dataset_feature.id,
                        source_snapshot_id=snapshot.id,
                        zone_code=zone_code,
                        overlap_area_m2=float(overlap) if overlap is not None else None,
                        assignment_method="max_overlap",
                        is_primary=False,
                    )
                )

            if not candidates:
                centroid = func.ST_Centroid(parcel.geom)
                fallback_rows = db.execute(
                    select(DatasetFeature)
                    .join(DatasetLayer, DatasetFeature.dataset_layer_id == DatasetLayer.id)
                    .where(
                        DatasetLayer.id == layer.id,
                        func.ST_Contains(DatasetFeature.geom, centroid),
                    )
                ).scalars().all()
                for dataset_feature in fallback_rows:
                    zone_code = str(dataset_feature.attributes_json.get("zone_code"))
                    candidates.append(
                        ZoningAssignmentCandidate(
                            dataset_feature_id=dataset_feature.id,
                            zone_code=zone_code,
                            assignment_method="centroid_fallback",
                            overlap_area_m2=None,
                        )
                    )
                    assignments.append(
                        ParcelZoningAssignment(
                            parcel_id=parcel.id,
                            dataset_feature_id=dataset_feature.id,
                            source_snapshot_id=snapshot.id,
                            zone_code=zone_code,
                            overlap_area_m2=None,
                            assignment_method="centroid_fallback",
                            is_primary=False,
                        )
                    )

            primary = choose_primary_zoning_assignment(candidates)
            if primary is None:
                summary.failed += 1
                summary.issues.append({"parcel_id": str(parcel.id), "reason": "zoning_assignment_ambiguous_or_missing"})
                for assignment in assignments:
                    db.add(assignment)
                continue

            for assignment in assignments:
                if assignment.dataset_feature_id == primary.dataset_feature_id:
                    assignment.is_primary = True
                    parcel.zone_code = assignment.zone_code
                db.add(assignment)

        layer.published_at = _now()
        publish_snapshot(db, snapshot, validation_summary=summary.as_json())
        _finalize_job(job, summary)
    except Exception as exc:
        summary.failed += 1
        summary.issues.append({"reason": "exception", "detail": str(exc)})
        _finalize_job(job, summary, error=str(exc))
        raise

    db.commit()
    return snapshot, job


def resolve_active_snapshot_id(db: Session, *, jurisdiction_id: uuid.UUID, snapshot_type: str) -> uuid.UUID:
    snapshot = db.execute(
        select(SourceSnapshot)
        .where(
            SourceSnapshot.jurisdiction_id == jurisdiction_id,
            SourceSnapshot.snapshot_type == snapshot_type,
            SourceSnapshot.is_active.is_(True),
        )
        .order_by(SourceSnapshot.created_at.desc())
    ).scalars().first()
    if not snapshot:
        raise ValueError(f"No active snapshot found for snapshot_type={snapshot_type}")
    return snapshot.id


def ingest_overlay_geojson(
    db: Session,
    *,
    jurisdiction_id: uuid.UUID,
    geojson_path: Path,
    version_label: str,
    source_url: str,
    layer_name: str,
    layer_type: str,
    publisher: str | None = None,
) -> tuple[SourceSnapshot, IngestionJob]:
    features = _read_geojson(geojson_path)
    snapshot = create_snapshot(
        db,
        jurisdiction_id=jurisdiction_id,
        snapshot_type=f"overlay_{layer_type}",
        version_label=version_label,
        source_url=source_url,
        publisher=publisher,
        file_hash=_sha256_file(geojson_path),
        schema_version="geojson-feature-collection",
    )
    job = create_ingestion_job(
        db,
        jurisdiction_id=jurisdiction_id,
        source_url=source_url,
        source_snapshot_id=snapshot.id,
        job_type=f"overlay_{layer_type}",
    )
    layer = DatasetLayer(
        jurisdiction_id=jurisdiction_id,
        source_snapshot_id=snapshot.id,
        name=layer_name,
        layer_type=layer_type,
        source_url=source_url,
        publisher=publisher,
        acquired_at=_now(),
        source_schema_version="geojson-feature-collection",
        last_refreshed=_now(),
        published_at=None,
    )
    db.add(layer)
    db.flush()

    summary = IngestionSummary(issues=[])
    try:
        for index, feature in enumerate(features):
            properties = feature.get("properties") or {}
            geometry = feature.get("geometry") or {}
            dataset_feature = DatasetFeature(
                dataset_layer_id=layer.id,
                source_record_id=str(feature.get("id") or _pick(properties, ("id", "ID", "OBJECTID", "_id")) or index),
                geom=WKTElement(geojson_to_wkt(geometry), srid=4326),
                attributes_json=properties,
            )
            db.add(dataset_feature)
            summary.processed += 1

        layer.published_at = _now()
        publish_snapshot(db, snapshot, validation_summary=summary.as_json())
        _finalize_job(job, summary)
    except Exception as exc:
        summary.failed += 1
        summary.issues.append({"reason": "exception", "detail": str(exc)})
        _finalize_job(job, summary, error=str(exc))
        raise

    db.commit()
    return snapshot, job


def ingest_development_applications(
    db: Session,
    *,
    jurisdiction_id: uuid.UUID,
    json_path: Path,
    version_label: str,
    source_url: str,
    publisher: str | None = None,
    parcel_snapshot_id: uuid.UUID | None = None,
) -> tuple[SourceSnapshot, IngestionJob]:
    from pyproj import Transformer

    transformer = Transformer.from_crs("EPSG:26917", "EPSG:4326", always_xy=True)

    records: list[dict[str, Any]] = json.loads(json_path.read_text())
    snapshot = create_snapshot(
        db,
        jurisdiction_id=jurisdiction_id,
        snapshot_type="development_applications",
        version_label=version_label,
        source_url=source_url,
        publisher=publisher,
        file_hash=_sha256_file(json_path),
        schema_version="toronto-open-data-json",
    )
    job = create_ingestion_job(
        db,
        jurisdiction_id=jurisdiction_id,
        source_url=source_url,
        source_snapshot_id=snapshot.id,
        job_type="development_applications",
    )

    summary = IngestionSummary(issues=[])
    seen_app_numbers: set[str] = set()
    try:
        for index, record in enumerate(records):
            app_number = record.get("APPLICATION#")
            if not app_number:
                summary.failed += 1
                summary.issues.append({"row": index, "reason": "missing_app_number"})
                continue
            if app_number in seen_app_numbers:
                summary.failed += 1
                summary.issues.append({"row": index, "reason": "duplicate_app_number", "app_number": app_number})
                continue
            seen_app_numbers.add(app_number)

            parts = [
                record.get("STREET_NUM") or "",
                record.get("STREET_NAME") or "",
                record.get("STREET_TYPE") or "",
                record.get("STREET_DIRECTION") or "",
            ]
            address = " ".join(p.strip() for p in parts if p.strip()) or None

            point_geom = None
            x_raw = _coerce_float(record.get("X"))
            y_raw = _coerce_float(record.get("Y"))
            if x_raw is not None and y_raw is not None:
                lon, lat = transformer.transform(x_raw, y_raw)
                point_geom = WKTElement(f"POINT ({lon} {lat})", srid=4326)

            proposed_units = None
            proposed_storeys = None
            description = record.get("DESCRIPTION") or ""
            storey_match = re.search(r"(\d+)[- ]?storey", description, re.IGNORECASE)
            if storey_match:
                proposed_storeys = int(storey_match.group(1))
            unit_match = re.search(r"(\d[\d,]*)\s*(?:residential\s+)?(?:units?|dwelling)", description, re.IGNORECASE)
            if unit_match:
                proposed_units = int(unit_match.group(1).replace(",", ""))

            ward_number = record.get("WARD_NUMBER") or ""
            ward_name = record.get("WARD_NAME") or ""
            ward = f"Ward {ward_number} - {ward_name}".strip(" -") if ward_number or ward_name else None

            parcel_id = None
            if point_geom is not None and parcel_snapshot_id is not None:
                matched = db.execute(
                    select(Parcel).where(
                        Parcel.jurisdiction_id == jurisdiction_id,
                        Parcel.source_snapshot_id == parcel_snapshot_id,
                        func.ST_Contains(Parcel.geom, point_geom),
                    )
                ).scalars().first()
                if matched:
                    parcel_id = matched.id

            metadata = {
                k: v
                for k, v in record.items()
                if k not in {
                    "APPLICATION#", "STREET_NUM", "STREET_NAME", "STREET_TYPE",
                    "STREET_DIRECTION", "X", "Y", "STATUS", "APPLICATION_TYPE",
                    "WARD_NUMBER", "WARD_NAME", "DESCRIPTION",
                }
            }

            dev_app = DevelopmentApplication(
                jurisdiction_id=jurisdiction_id,
                app_number=app_number,
                source_system="toronto_open_data",
                source_url=record.get("APPLICATION_URL"),
                address=address,
                parcel_id=parcel_id,
                geom=point_geom,
                app_type=record.get("APPLICATION_TYPE") or "unknown",
                status=record.get("STATUS") or "unknown",
                ward=ward,
                proposed_units=proposed_units,
                proposed_height_m=float(proposed_storeys * 3) if proposed_storeys else None,
                publisher=publisher,
                acquired_at=_now(),
                source_schema_version="toronto-open-data-json",
                metadata_json=metadata,
            )
            db.add(dev_app)
            summary.processed += 1

        publish_snapshot(db, snapshot, validation_summary=summary.as_json())
        _finalize_job(job, summary)
    except Exception as exc:
        summary.failed += 1
        summary.issues.append({"reason": "exception", "detail": str(exc)})
        _finalize_job(job, summary, error=str(exc))
        raise

    db.commit()
    return snapshot, job
