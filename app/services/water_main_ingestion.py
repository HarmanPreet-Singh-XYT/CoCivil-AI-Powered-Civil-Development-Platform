"""Water system ingestion service.

Handles all five Toronto Water asset layers from local GeoJSON files:

    Layer               File                                    Type
    ─────────────────── ─────────────────────────────────────── ──────────────────────
    Distribution mains  Watermain Distribution 4326.geojson     water_main_distribution
    Transmission mains  Toronto Watermain 4326.geojson          water_main_transmission
    Hydrants            Water Hydrants Toronto.geojson           water_hydrant
    Valves              Water Valve 4326.geojson                 water_valve
    Fittings            Water Fitting 4326.geojson               water_fitting
    Parks fountains     Parks Drinking Water Sources.geojson     parks_drinking_water

Field names are taken directly from the real Toronto Open Data exports.
All functions follow the same (SourceSnapshot, IngestionJob) return pattern
as the rest of app/services/geospatial_ingestion.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Material normalisation
# Toronto Water uses its own codes — map to civil_standards.py keys
# ---------------------------------------------------------------------------

MATERIAL_ALIASES: dict[str, str] = {
    # Ductile Iron
    "DI": "DI", "DIP": "DI", "DUCTILE IRON": "DI", "DUCTILEIRON": "DI",
    # Cast Iron (legacy — 1877 King St W main is likely this)
    "CI": "CI", "CIP": "CI", "CAST IRON": "CI", "CASTIRON": "CI",
    "GI": "CI", "GALV": "CI",
    # PVC
    "PVC": "PVC", "POLYVINYL": "PVC",
    # HDPE
    "HDPE": "HDPE", "PE": "HDPE", "POLYETHYLENE": "HDPE",
    # Concrete Pressure Pipe / Reinforced Concrete
    "CPP": "RCP", "RCP": "RCP", "CONCRETE": "RCP", "RC": "RCP",
    "PCCP": "RCP",   # Prestressed Concrete Cylinder Pipe
    # Steel
    "STE": "STEEL", "STEEL": "STEEL", "ST": "STEEL",
    # Asbestos Cement (legacy — still in network)
    "AC": "AC", "ACP": "AC", "ASBESTOS": "AC", "ASBESTOS CEMENT": "AC",
    # Corrugated Steel
    "CSP": "CSP",
    # Copper (small services)
    "COP": "COPPER", "COPPER": "COPPER",
}

VALID_STATUSES = {"ACTIVE", "ABANDONED", "PROPOSED", "INACTIVE", "UNKNOWN"}


def _normalise_material(raw: str | None) -> str:
    if not raw:
        return "UNKNOWN"
    return MATERIAL_ALIASES.get(str(raw).strip().upper(), "UNKNOWN")


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def _get(props: dict, *keys: str, default=None) -> Any:
    """Try multiple key variants (original / UPPER / lower)."""
    for key in keys:
        for variant in (key, key.upper(), key.lower()):
            val = props.get(variant)
            if val is not None and str(val) not in ("", "None", "null"):
                return val
    return default


def _safe_int(val) -> int | None:
    try:
        return int(float(val)) if val is not None else None
    except (ValueError, TypeError):
        return None


def _safe_float(val) -> float | None:
    try:
        return round(float(val), 4) if val is not None else None
    except (ValueError, TypeError):
        return None


def _safe_year(val) -> int | None:
    """Parse year from int, float, or ISO date string like '1877-01-01T00:04:00'."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        year = int(val)
        return year if 1800 <= year <= 2100 else None
    if isinstance(val, str) and len(val) >= 4:
        try:
            year = int(val[:4])
            return year if 1800 <= year <= 2100 else None
        except ValueError:
            pass
    return None


# ---------------------------------------------------------------------------
# Property extractors — one per layer type, using real Toronto field names
# ---------------------------------------------------------------------------

def _extract_watermain_props(props: dict) -> dict[str, Any]:
    """
    Real fields (both distribution and transmission files):
      Watermain Asset Identification, Watermain Type (0=dist, 1=trans),
      Watermain Diameter, Watermain Material, Watermain Install Date,
      Watermain Construction Year, Watermain Measured Length,
      Watermain Location Description
    """
    raw_type = _get(props, "Watermain Type")
    watermain_subtype = "transmission" if str(raw_type) == "1" else "distribution"

    raw_material = _get(props, "Watermain Material", "MATERIAL", "PIPE_MAT")
    raw_install = _get(props, "Watermain Install Date", "INSTALL_YR")
    raw_year = _get(props, "Watermain Construction Year", "INSTALL_YR")

    return {
        "source_id":            str(_get(props, "_id", "OBJECTID", "FID") or ""),
        "asset_id":             str(_get(props, "Watermain Asset Identification", "WATMAIN_ID") or ""),
        "watermain_subtype":    watermain_subtype,
        "material":             _normalise_material(raw_material),
        "material_raw":         str(raw_material or ""),
        "diameter_mm":          _safe_int(_get(props, "Watermain Diameter", "DIAMETER", "DIA_MM")),
        "install_year":         _safe_year(raw_install) or _safe_year(raw_year),
        "length_m":             _safe_float(_get(props, "Watermain Measured Length", "Shape_Length", "LENGTH_M")),
        "location_description": str(_get(props, "Watermain Location Description") or ""),
        "pressure_zone":        str(_get(props, "PRESSURE_ZONE", "PRES_ZONE") or ""),
        "status":               "ACTIVE",
    }


def _extract_hydrant_props(props: dict) -> dict[str, Any]:
    """
    Real fields:
      Asset Identification, Hydrant Install Date,
      Hydrant Owned By, Hydrant Managed By
    """
    return {
        "source_id":   str(_get(props, "_id", "OBJECTID") or ""),
        "asset_id":    str(_get(props, "Asset Identification", "ASSET_ID") or ""),
        "install_year": _safe_year(_get(props, "Hydrant Install Date", "INSTALL_DATE")),
        "owned_by":    str(_get(props, "Hydrant Owned By", "OWNED_BY") or "City"),
        "managed_by":  str(_get(props, "Hydrant Managed By", "MANAGED_BY") or ""),
        "status":      "ACTIVE",
    }


def _extract_valve_props(props: dict) -> dict[str, Any]:
    """
    Real fields:
      Asset ID, Water Valve Diameter, Water Valve Purpose, Water Valve Type
    """
    return {
        "source_id":   str(_get(props, "_id", "OBJECTID") or ""),
        "asset_id":    str(_get(props, "Asset ID", "ASSET_ID") or ""),
        "diameter_mm": _safe_int(_get(props, "Water Valve Diameter", "DIAMETER")),
        "purpose":     str(_get(props, "Water Valve Purpose", "PURPOSE") or ""),
        "valve_type":  str(_get(props, "Water Valve Type", "VALVE_TYPE") or ""),
        "status":      "ACTIVE",
    }


def _extract_fitting_props(props: dict) -> dict[str, Any]:
    """
    Real fields:
      Asset ID, Water Fitting Type
    """
    return {
        "source_id":    str(_get(props, "_id", "OBJECTID") or ""),
        "asset_id":     str(_get(props, "Asset ID", "ASSET_ID") or ""),
        "fitting_type": str(_get(props, "Water Fitting Type", "FITTING_TYPE") or ""),
        "status":       "ACTIVE",
    }


def _extract_drinking_source_props(props: dict) -> dict[str, Any]:
    """
    Real fields:
      _id, id, asset_id, location, alternative_name, type,
      location_details, url, address, PostedDate, AssetName,
      Reason, Comments, Status  ("1"=open, "0"=closed/seasonal)
    """
    raw_status = _get(props, "Status", "STATUS")
    status = "ACTIVE" if str(raw_status) == "1" else "INACTIVE"
    return {
        "source_id":        str(_get(props, "_id", "id") or ""),
        "asset_id":         str(_get(props, "asset_id") or ""),
        "location":         str(_get(props, "location") or ""),
        "asset_name":       str(_get(props, "AssetName", "alternative_name") or ""),
        "fountain_type":    str(_get(props, "type") or ""),
        "location_details": str(_get(props, "location_details") or ""),
        "address":          str(_get(props, "address") or ""),
        "url":              str(_get(props, "url") or ""),
        "reason":           str(_get(props, "Reason") or ""),
        "comments":         str(_get(props, "Comments") or ""),
        "status":           status,
    }


# ---------------------------------------------------------------------------
# Geometry validation
# ---------------------------------------------------------------------------

def _valid_line(geom: dict | None) -> bool:
    if not geom:
        return False
    t = geom.get("type", "")
    c = geom.get("coordinates", [])
    if t == "LineString":
        return len(c) >= 2
    if t == "MultiLineString":
        return any(len(line) >= 2 for line in c)
    return False


def _valid_point(geom: dict | None) -> bool:
    if not geom:
        return False
    t = geom.get("type", "")
    c = geom.get("coordinates", [])
    if t == "Point":
        return len(c) >= 2
    if t == "MultiPoint":
        return len(c) >= 1 and len(c[0]) >= 2
    return False


# ---------------------------------------------------------------------------
# GeoJSON → EWKT  (no shapely needed in ingestion path)
# ---------------------------------------------------------------------------

def _geojson_to_ewkt(geom: dict) -> str:
    t = geom["type"]
    c = geom["coordinates"]

    if t == "LineString":
        interior = "(" + ",".join(f"{p[0]} {p[1]}" for p in c) + ")"
        return f"LINESTRING{interior}"

    if t == "MultiLineString":
        parts = ["(" + ",".join(f"{p[0]} {p[1]}" for p in line) + ")" for line in c]
        return "MULTILINESTRING(" + ",".join(parts) + ")"

    if t == "Point":
        return f"POINT({c[0]} {c[1]})"

    if t == "MultiPoint":
        # Flatten to POINT using first coordinate — keeps downstream simple
        pt = c[0]
        return f"POINT({pt[0]} {pt[1]})"

    raise ValueError(f"Unsupported geometry type: {t}")


# ---------------------------------------------------------------------------
# Streaming feature iterator
# ---------------------------------------------------------------------------

def _stream_features(path: Path) -> Iterator[dict]:
    try:
        import ijson
        with open(path, "rb") as f:
            yield from ijson.items(f, "features.item")
    except ImportError:
        import json
        with open(path) as f:
            data = json.load(f)
        yield from data.get("features", [])


# ---------------------------------------------------------------------------
# Core ingestion engine — shared by all layer types
# ---------------------------------------------------------------------------

def _ingest_layer(
    db: Session,
    *,
    jurisdiction_id: uuid.UUID,
    geojson_path: Path,
    version_label: str,
    source_url: str,
    publisher: str,
    layer_name: str,
    layer_type: str,
    snapshot_type: str,
    prop_extractor,
    geom_validator,
    batch_size: int = 1000,
    feature_iterator: Iterator[dict] | None = None,
    skip_inactive: bool = False,
) -> tuple[Any, Any]:
    from app.models.dataset import DatasetFeature, DatasetLayer
    from app.models.ingestion import IngestionJob, SourceSnapshot

    now = datetime.now(timezone.utc)

    # SourceSnapshot fields: jurisdiction_id, snapshot_type, version_label, is_active, created_at
    # Note: no source_url or publisher on SourceSnapshot — those belong on IngestionJob / DatasetLayer
    snapshot = SourceSnapshot(
        id=uuid.uuid4(),
        jurisdiction_id=jurisdiction_id,
        snapshot_type=snapshot_type,
        version_label=version_label,
        is_active=True,
        created_at=now,
    )
    db.add(snapshot)
    db.flush()

    layer = DatasetLayer(
        id=uuid.uuid4(),
        jurisdiction_id=jurisdiction_id,
        source_snapshot_id=snapshot.id,
        name=layer_name,
        layer_type=layer_type,
        source_url=source_url,
        publisher=publisher,
        acquired_at=now,
        internal_storage_allowed=True,
        redistribution_allowed=False,
        export_allowed=False,
        derived_export_allowed=True,
        aggregation_required=False,
        redistribution_policy="Refer users to the official source URL for the full dataset.",
        license_status="open",
        retention_policy="retain_until_reseeded",
        lineage_json={"seed_managed": True, "layer_type": layer_type},
        source_metadata_json={"source_url": source_url, "publisher": publisher},
    )
    db.add(layer)
    db.flush()

    # IngestionJob fields include source_url (maps to where data came from)
    job = IngestionJob(
        id=uuid.uuid4(),
        jurisdiction_id=jurisdiction_id,
        source_snapshot_id=snapshot.id,
        source_url=source_url,
        job_type=f"{layer_type}_ingest",
        status="running",
        records_processed=0,
        records_failed=0,
        started_at=now,
    )
    db.add(job)
    db.commit()

    iterator = feature_iterator or _stream_features(geojson_path)
    batch: list[DatasetFeature] = []
    processed = failed = skipped = 0

    def _flush():
        if batch:
            db.bulk_save_objects(batch)
            db.flush()
            batch.clear()

    try:
        for raw in iterator:
            geom = raw.get("geometry")
            props = raw.get("properties") or {}

            if not geom_validator(geom):
                failed += 1
                continue

            clean = prop_extractor(props)

            if skip_inactive and clean.get("status") == "INACTIVE":
                skipped += 1
                continue

            batch.append(DatasetFeature(
                id=uuid.uuid4(),
                dataset_layer_id=layer.id,
                geom=f"SRID=4326;{_geojson_to_ewkt(geom)}",
                attributes_json=clean,
                source_record_id=clean.get("source_id") or None,
            ))
            processed += 1

            if len(batch) >= batch_size:
                _flush()
                print(f"\r    {processed:,} {layer_type} features ingested...", end="", flush=True)

        _flush()
        print(f"\r    {processed:,} {layer_type} features ingested.     ")
        if skipped:
            print(f"    {skipped:,} inactive features skipped")
        if failed:
            print(f"    {failed:,} features skipped (no valid geometry)")

        job.status = "completed"
        job.records_processed = processed
        job.records_failed = failed
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as exc:
        db.rollback()
        job.status = "failed"
        job.records_processed = processed
        job.records_failed = failed + 1
        job.error_message = str(exc)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise

    return snapshot, job


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ingest_distribution_watermains(
    db: Session, *, jurisdiction_id, geojson_path, version_label,
    source_url, publisher, batch_size=1000, feature_iterator=None,
):
    """Ingest Watermain Distribution 4326.geojson."""
    return _ingest_layer(
        db, jurisdiction_id=jurisdiction_id, geojson_path=geojson_path,
        version_label=version_label, source_url=source_url, publisher=publisher,
        layer_name="Toronto Distribution Water Mains",
        layer_type="water_main_distribution", snapshot_type="water_main_distribution",
        prop_extractor=_extract_watermain_props, geom_validator=_valid_line,
        batch_size=batch_size, feature_iterator=feature_iterator,
    )


def ingest_transmission_watermains(
    db: Session, *, jurisdiction_id, geojson_path, version_label,
    source_url, publisher, batch_size=1000, feature_iterator=None,
):
    """Ingest Toronto Watermain 4326.geojson (transmission/trunk mains)."""
    return _ingest_layer(
        db, jurisdiction_id=jurisdiction_id, geojson_path=geojson_path,
        version_label=version_label, source_url=source_url, publisher=publisher,
        layer_name="Toronto Transmission Water Mains",
        layer_type="water_main_transmission", snapshot_type="water_main_transmission",
        prop_extractor=_extract_watermain_props, geom_validator=_valid_line,
        batch_size=batch_size, feature_iterator=feature_iterator,
    )


def ingest_water_hydrants(
    db: Session, *, jurisdiction_id, geojson_path, version_label,
    source_url, publisher, batch_size=1000, feature_iterator=None,
):
    """Ingest Water Hydrants Toronto.geojson."""
    return _ingest_layer(
        db, jurisdiction_id=jurisdiction_id, geojson_path=geojson_path,
        version_label=version_label, source_url=source_url, publisher=publisher,
        layer_name="Toronto Water Hydrants",
        layer_type="water_hydrant", snapshot_type="water_hydrant",
        prop_extractor=_extract_hydrant_props, geom_validator=_valid_point,
        batch_size=batch_size, feature_iterator=feature_iterator,
    )


def ingest_water_valves(
    db: Session, *, jurisdiction_id, geojson_path, version_label,
    source_url, publisher, batch_size=1000, feature_iterator=None,
):
    """Ingest Water Valve 4326.geojson."""
    return _ingest_layer(
        db, jurisdiction_id=jurisdiction_id, geojson_path=geojson_path,
        version_label=version_label, source_url=source_url, publisher=publisher,
        layer_name="Toronto Water Valves",
        layer_type="water_valve", snapshot_type="water_valve",
        prop_extractor=_extract_valve_props, geom_validator=_valid_point,
        batch_size=batch_size, feature_iterator=feature_iterator,
    )


def ingest_water_fittings(
    db: Session, *, jurisdiction_id, geojson_path, version_label,
    source_url, publisher, batch_size=1000, feature_iterator=None,
):
    """Ingest Water Fitting 4326.geojson."""
    return _ingest_layer(
        db, jurisdiction_id=jurisdiction_id, geojson_path=geojson_path,
        version_label=version_label, source_url=source_url, publisher=publisher,
        layer_name="Toronto Water Fittings",
        layer_type="water_fitting", snapshot_type="water_fitting",
        prop_extractor=_extract_fitting_props, geom_validator=_valid_point,
        batch_size=batch_size, feature_iterator=feature_iterator,
    )


def ingest_parks_drinking_water(
    db: Session, *, jurisdiction_id, geojson_path, version_label,
    source_url, publisher, batch_size=1000, feature_iterator=None,
    active_only=False,
):
    """
    Ingest Parks Drinking Water Sources.geojson.
    active_only=True skips fountains closed for the season (Status=0).
    """
    return _ingest_layer(
        db, jurisdiction_id=jurisdiction_id, geojson_path=geojson_path,
        version_label=version_label, source_url=source_url, publisher=publisher,
        layer_name="Toronto Parks Drinking Water Sources",
        layer_type="parks_drinking_water", snapshot_type="parks_drinking_water",
        prop_extractor=_extract_drinking_source_props, geom_validator=_valid_point,
        batch_size=batch_size, feature_iterator=feature_iterator,
        skip_inactive=active_only,
    )


# ---------------------------------------------------------------------------
# Convenience: seed all water layers in one call
# ---------------------------------------------------------------------------

WATER_LAYER_MANIFEST = [
    # (function, local_filename, source_url_suffix, description)
    (ingest_distribution_watermains,  "watermain-distribution-4326.geojson",  "water-mains",         "Distribution water mains"),
    (ingest_transmission_watermains,  "water-mains-4326.geojson",             "water-mains",         "Transmission water mains"),
    (ingest_water_hydrants,           "water-hydrants-4326.geojson",          "water-hydrants",      "Water hydrants"),
    (ingest_water_valves,             "water-valves-4326.geojson",            "water-valves",        "Water valves"),
    (ingest_water_fittings,           "water-fittings-4326.geojson",          "water-fittings",      "Water fittings"),
    (ingest_parks_drinking_water,     "parks-drinking-water-4326.geojson",    "parks-drinking-water","Parks drinking water sources"),
]


def seed_all_water_layers(
    db: Session,
    *,
    jurisdiction_id: uuid.UUID,
    data_dir: Path,
    version_label: str,
    publisher: str = "City of Toronto",
    source_base: str = "https://open.toronto.ca/dataset",
    batch_size: int = 1000,
) -> dict[str, dict]:
    """
    Seed all available water system layers from staged data_dir.
    Silently skips any file that doesn't exist yet.
    Returns a summary dict keyed by layer type.
    """
    results = {}
    for fn, filename, url_suffix, description in WATER_LAYER_MANIFEST:
        path = data_dir / filename
        if not path.exists():
            print(f"  SKIP {description} — {filename} not found in {data_dir}")
            continue
        print(f"\n  [{description}]")
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"    File: {filename} ({size_mb:.1f} MB)")
        snap, job = fn(
            db,
            jurisdiction_id=jurisdiction_id,
            geojson_path=path,
            version_label=version_label,
            source_url=f"{source_base}/{url_suffix}",
            publisher=publisher,
            batch_size=batch_size,
        )
        results[job.job_type] = {
            "snapshot_id": str(snap.id),
            "processed": job.records_processed,
            "failed": job.records_failed,
            "status": job.status,
        }
    return results