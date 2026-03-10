"""Generate a DXF file from real Toronto water main data.

Queries the water_mains dataset layer from the database (seeded from
Toronto Open Data) and exports it as a properly layered DXF with:
- Real pipe geometries (LineString / MultiLineString features)
- Real material codes (DI, PVC, HDPE, CSP, etc.)
- Real diameters from the source dataset
- Real installation years where available
- Colour-coded layers by pipe material
- Attribute blocks with pipe metadata

Prerequisites:
    python scripts/railway_seed_full.py   # must have water mains seeded first

Usage:
    python scripts/generate_water_main_dxf.py --output water_mains_toronto.dxf
    python scripts/generate_water_main_dxf.py --bbox-west -79.38 --bbox-east -79.36 \
        --bbox-south 43.64 --bbox-north 43.66 --output downtown_water_mains.dxf
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

try:
    import ezdxf
    from ezdxf.enums import TextEntityAlignment
except ImportError:
    print("Install ezdxf:  pip install ezdxf")
    sys.exit(1)

try:
    from shapely.geometry import shape, mapping
    from shapely.ops import transform
    import pyproj
except ImportError:
    print("Install shapely and pyproj:  pip install shapely pyproj")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Layer definitions — colour-coded by pipe material
# DXF colour index: 1=red, 2=yellow, 3=green, 4=cyan, 5=blue, 6=magenta, 7=white
# ---------------------------------------------------------------------------

MATERIAL_LAYERS = {
    "DI":     {"layer": "WATER-MAIN-DI",    "color": 5,  "label": "Ductile Iron"},
    "PVC":    {"layer": "WATER-MAIN-PVC",   "color": 3,  "label": "PVC"},
    "HDPE":   {"layer": "WATER-MAIN-HDPE",  "color": 4,  "label": "HDPE"},
    "CSP":    {"layer": "WATER-MAIN-CSP",   "color": 6,  "label": "Corrugated Steel"},
    "RCP":    {"layer": "WATER-MAIN-RCP",   "color": 2,  "label": "Reinforced Concrete"},
    "AC":     {"layer": "WATER-MAIN-AC",    "color": 1,  "label": "Asbestos Cement (legacy)"},
    "STEEL":  {"layer": "WATER-MAIN-STEEL", "color": 7,  "label": "Steel"},
    "UNKNOWN":{"layer": "WATER-MAIN-OTHER", "color": 8,  "label": "Unknown / Other"},
}

ANNOTATION_LAYER = "WATER-ANNO"
VALVE_LAYER = "WATER-VALVE"
HYDRANT_LAYER = "WATER-HYDRANT"


# ---------------------------------------------------------------------------
# Material normaliser
# Toronto Open Data uses various field names and abbreviations
# ---------------------------------------------------------------------------

MATERIAL_ALIASES: dict[str, str] = {
    # Ductile Iron
    "DI": "DI", "DUCTILE IRON": "DI", "DUCTILEIRON": "DI",
    # PVC
    "PVC": "PVC", "POLYVINYL": "PVC",
    # HDPE
    "HDPE": "HDPE", "POLYETHYLENE": "HDPE", "PE": "HDPE",
    # Asbestos Cement (legacy, still in network)
    "AC": "AC", "ASBESTOS": "AC", "ASBESTOS CEMENT": "AC",
    # Steel
    "STEEL": "STEEL", "ST": "STEEL",
    # Concrete
    "RCP": "RCP", "CONCRETE": "RCP", "RC": "RCP",
    # Corrugated Steel
    "CSP": "CSP",
}


def normalise_material(raw: str | None) -> str:
    if not raw:
        return "UNKNOWN"
    key = str(raw).strip().upper()
    return MATERIAL_ALIASES.get(key, "UNKNOWN")


# ---------------------------------------------------------------------------
# Coordinate projection
# Toronto Open Data water mains are in WGS84 (EPSG:4326).
# We project to MTM Zone 17 (EPSG:2019) — Ontario standard for Toronto —
# so that DXF coordinates are in metres, suitable for engineering use.
# ---------------------------------------------------------------------------

def make_projector():
    """Return a function that projects (lon, lat) → (easting, northing) in metres."""
    wgs84 = pyproj.CRS("EPSG:4326")
    mtm17 = pyproj.CRS("EPSG:2019")   # NAD83 / MTM zone 17 (Toronto)
    project = pyproj.Transformer.from_crs(wgs84, mtm17, always_xy=True).transform
    return project


def project_coords(coords: list, projector) -> list:
    """Recursively project a coordinate list."""
    if not coords:
        return coords
    if isinstance(coords[0], (int, float)):
        # Single coordinate pair [lon, lat] or [lon, lat, z]
        x, y = projector(coords[0], coords[1])
        return [x, y]
    return [project_coords(c, projector) for c in coords]


# ---------------------------------------------------------------------------
# Database query
# ---------------------------------------------------------------------------

def fetch_water_main_features(
    db,
    jurisdiction_id,
    *,
    bbox: tuple[float, float, float, float] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch water main features from the DatasetFeature table.

    Returns a list of dicts with keys: geometry_json, properties
    """
    from sqlalchemy import select, func, and_
    from app.models.dataset import DatasetFeature, DatasetLayer
    from app.models.ingestion import SourceSnapshot

    # Find the active water mains layer
    layer_query = (
        select(DatasetLayer)
        .join(SourceSnapshot, SourceSnapshot.id == DatasetLayer.source_snapshot_id)
        .where(DatasetLayer.jurisdiction_id == jurisdiction_id)
        .where(DatasetLayer.layer_type == "water_main")
        .where(SourceSnapshot.is_active.is_(True))
        .order_by(SourceSnapshot.created_at.desc())
        .limit(1)
    )
    layer = db.execute(layer_query).scalar_one_or_none()

    if layer is None:
        raise RuntimeError(
            "No active water_main layer found. "
            "Run: python scripts/railway_seed_full.py --seed-only"
        )

    print(f"  Using layer: {layer.layer_name} (id={layer.id})")

    # Build feature query
    feature_query = (
        select(DatasetFeature)
        .where(DatasetFeature.dataset_layer_id == layer.id)
    )

    # Spatial bbox filter using PostGIS ST_Intersects
    if bbox is not None:
        west, south, east, north = bbox
        bbox_wkt = f"POLYGON(({west} {south},{east} {south},{east} {north},{west} {north},{west} {south}))"
        feature_query = feature_query.where(
            func.ST_Intersects(
                DatasetFeature.geom,
                func.ST_GeomFromText(bbox_wkt, 4326),
            )
        )

    if limit:
        feature_query = feature_query.limit(limit)

    rows = db.execute(feature_query).scalars().all()
    print(f"  Fetched {len(rows):,} water main features")
    return rows


# ---------------------------------------------------------------------------
# DXF generation
# ---------------------------------------------------------------------------

def _get_prop(props: dict, *keys: str, default=None):
    """Try multiple property key names (Toronto Open Data field names vary by vintage)."""
    for key in keys:
        val = props.get(key) or props.get(key.upper()) or props.get(key.lower())
        if val is not None:
            return val
    return default


def build_pipe_label(props: dict, diameter_mm: int | None, material: str) -> str:
    """Build a short annotation label for a pipe segment."""
    mat_label = MATERIAL_LAYERS.get(material, {}).get("label", material)
    parts = []
    if diameter_mm:
        parts.append(f"Ø{diameter_mm}mm")
    parts.append(mat_label)
    install_year = _get_prop(props, "INSTALL_YR", "INSTAL_YR", "YEAR_INST", "install_year")
    if install_year:
        parts.append(f"({install_year})")
    return " | ".join(parts)


def generate_dxf(
    features,
    output_path: Path,
    projector,
    *,
    annotate: bool = True,
    annotation_min_length_m: float = 50.0,
) -> dict[str, int]:
    """
    Generate a DXF from water main features.

    Returns a summary dict of counts per material.
    """
    doc = ezdxf.new("R2013")
    doc.header["$INSUNITS"] = 6   # metres
    msp = doc.modelspace()

    # Create layers
    for mat_info in MATERIAL_LAYERS.values():
        doc.layers.add(mat_info["layer"], color=mat_info["color"])
    doc.layers.add(ANNOTATION_LAYER, color=9)

    counts: dict[str, int] = {}
    skipped = 0
    annotated = 0

    for feature in features:
        # Get geometry — DatasetFeature stores it as GeoJSON dict or WKB
        geom_data = feature.geom_json if hasattr(feature, "geom_json") else None
        if geom_data is None:
            # Try to get geometry as GeoJSON via __geo_interface__ or similar
            try:
                from geoalchemy2.shape import to_shape
                geom_shape = to_shape(feature.geom)
                geom_data = mapping(geom_shape)
            except Exception:
                skipped += 1
                continue

        props = feature.properties or {}
        if isinstance(props, str):
            import json
            props = json.loads(props)

        # Normalise material
        raw_material = _get_prop(
            props,
            "MATERIAL", "PIPE_MAT", "PIPE_MATERIAL", "MAT_CODE", "material",
        )
        material = normalise_material(raw_material)
        layer_name = MATERIAL_LAYERS[material]["layer"]

        # Get diameter
        raw_dia = _get_prop(props, "DIAMETER", "DIA_MM", "PIPE_DIA", "diameter_mm")
        try:
            diameter_mm = int(float(raw_dia)) if raw_dia else None
        except (ValueError, TypeError):
            diameter_mm = None

        # Extract line segments from geometry
        geom_type = geom_data.get("type", "")
        raw_coords = geom_data.get("coordinates", [])

        if geom_type == "LineString":
            coord_sets = [raw_coords]
        elif geom_type == "MultiLineString":
            coord_sets = raw_coords
        else:
            skipped += 1
            continue

        for coord_list in coord_sets:
            if len(coord_list) < 2:
                continue

            # Project coordinates to MTM Zone 17 (metres)
            projected = [projector(c[0], c[1]) for c in coord_list]

            # Draw polyline
            msp.add_lwpolyline(
                projected,
                close=False,
                dxfattribs={"layer": layer_name},
            )
            counts[material] = counts.get(material, 0) + 1

            # Add annotation label at midpoint for longer segments
            if annotate:
                total_len = sum(
                    ((projected[i+1][0] - projected[i][0])**2 +
                     (projected[i+1][1] - projected[i][1])**2) ** 0.5
                    for i in range(len(projected) - 1)
                )
                if total_len >= annotation_min_length_m:
                    mid_idx = len(projected) // 2
                    mid = projected[mid_idx]
                    label = build_pipe_label(props, diameter_mm, material)
                    msp.add_text(
                        label,
                        height=2.0,
                        dxfattribs={"layer": ANNOTATION_LAYER},
                    ).set_placement(mid, align=TextEntityAlignment.MIDDLE_CENTER)
                    annotated += 1

    # Title block
    msp.add_text(
        "TORONTO WATER MAIN NETWORK — CITY OF TORONTO OPEN DATA",
        height=5.0,
        dxfattribs={"layer": ANNOTATION_LAYER},
    ).set_placement((0, -20), align=TextEntityAlignment.MIDDLE_LEFT)

    msp.add_text(
        "Source: Toronto Open Data | Projection: NAD83 / MTM Zone 17 (EPSG:2019)",
        height=2.5,
        dxfattribs={"layer": ANNOTATION_LAYER},
    ).set_placement((0, -26), align=TextEntityAlignment.MIDDLE_LEFT)

    # Legend
    legend_y = -35
    msp.add_text("LEGEND — PIPE MATERIAL", height=3.0, dxfattribs={"layer": ANNOTATION_LAYER}).set_placement(
        (0, legend_y), align=TextEntityAlignment.MIDDLE_LEFT
    )
    for i, (mat_code, mat_info) in enumerate(MATERIAL_LAYERS.items()):
        count = counts.get(mat_code, 0)
        if count == 0:
            continue
        msp.add_text(
            f"{mat_info['label']} ({mat_code}): {count:,} segments",
            height=2.0,
            dxfattribs={"layer": mat_info["layer"]},
        ).set_placement((0, legend_y - 5 - i * 4), align=TextEntityAlignment.MIDDLE_LEFT)

    doc.saveas(str(output_path))
    print(f"\n  Saved DXF: {output_path.resolve()}")
    print(f"  Pipe segments drawn: {sum(counts.values()):,}")
    print(f"  Annotations added: {annotated:,}")
    print(f"  Features skipped (no geometry): {skipped:,}")
    print(f"  Breakdown by material: {counts}")
    return counts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Export Toronto water mains from database to DXF")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("toronto_water_mains.dxf"),
        help="Output DXF file path (default: toronto_water_mains.dxf)",
    )
    parser.add_argument("--bbox-west",  type=float, default=None, help="Bounding box west longitude")
    parser.add_argument("--bbox-east",  type=float, default=None, help="Bounding box east longitude")
    parser.add_argument("--bbox-south", type=float, default=None, help="Bounding box south latitude")
    parser.add_argument("--bbox-north", type=float, default=None, help="Bounding box north latitude")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of features (useful for testing output before full export)",
    )
    parser.add_argument(
        "--no-annotations",
        action="store_true",
        help="Skip pipe label annotations (faster, smaller file)",
    )
    parser.add_argument(
        "--annotation-min-length",
        type=float,
        default=50.0,
        help="Only annotate segments longer than this many metres (default: 50)",
    )
    args = parser.parse_args()

    bbox = None
    if any(v is not None for v in [args.bbox_west, args.bbox_east, args.bbox_south, args.bbox_north]):
        if not all(v is not None for v in [args.bbox_west, args.bbox_east, args.bbox_south, args.bbox_north]):
            parser.error("All four --bbox-* arguments are required when using a bbox filter")
        bbox = (args.bbox_west, args.bbox_south, args.bbox_east, args.bbox_north)
        print(f"Bounding box: W={bbox[0]} S={bbox[1]} E={bbox[2]} N={bbox[3]}")
    else:
        print("No bbox specified — exporting full Toronto water main network")

    from app.database import get_sync_db
    from app.services.geospatial import get_toronto_jurisdiction_id

    db = get_sync_db()
    try:
        jurisdiction_id = get_toronto_jurisdiction_id(db)
        print(f"Jurisdiction ID: {jurisdiction_id}")

        print("Fetching water main features from database...")
        features = fetch_water_main_features(
            db,
            jurisdiction_id,
            bbox=bbox,
            limit=args.limit,
        )

        if not features:
            print("No water main features found. Have you run the seed?")
            print("  python scripts/railway_seed_full.py --seed-only")
            sys.exit(1)

        print("Setting up coordinate projection (WGS84 → MTM Zone 17)...")
        projector = make_projector()

        print(f"Generating DXF: {args.output}")
        generate_dxf(
            features,
            args.output,
            projector,
            annotate=not args.no_annotations,
            annotation_min_length_m=args.annotation_min_length,
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()