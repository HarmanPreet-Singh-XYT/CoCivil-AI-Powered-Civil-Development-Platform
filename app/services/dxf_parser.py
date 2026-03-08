"""DXF floor plan parsing using ezdxf.

Extracts walls, rooms, doors/windows, and floor groupings from DXF files.
All coordinates output in metres, centred at origin.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class WallSegment:
    start: tuple[float, float]
    end: tuple[float, float]
    thickness_m: float = 0.2
    type: str = "interior"  # "interior", "exterior", "structural"
    load_bearing: str = "unknown"  # "yes", "no", "unknown"


@dataclass
class Room:
    name: str
    type: str
    polygon: list[tuple[float, float]]
    area_m2: float


@dataclass
class Column:
    position: tuple[float, float]  # centre
    size_m: float = 0.4  # square column side length


@dataclass
class Opening:
    position: tuple[float, float]
    width_m: float
    type: str  # "door" or "window"
    sill_height_m: float | None = None
    head_height_m: float | None = None
    swing_direction: str | None = None  # "inward", "outward", "sliding"


@dataclass
class FloorPlan:
    floor_number: int
    floor_label: str
    ceiling_height_m: float | None = None
    walls: list[WallSegment] = field(default_factory=list)
    rooms: list[Room] = field(default_factory=list)
    openings: list[Opening] = field(default_factory=list)
    columns: list[Column] = field(default_factory=list)


def _polygon_area(pts: list[tuple[float, float]]) -> float:
    """Shoelace formula for polygon area."""
    n = len(pts)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += pts[i][0] * pts[j][1]
        area -= pts[j][0] * pts[i][1]
    return abs(area) / 2.0


def _classify_room(name: str) -> str:
    """Guess room type from label text."""
    lower = name.lower()
    for keyword, rtype in [
        ("bed", "bedroom"), ("bath", "bathroom"), ("wash", "bathroom"),
        ("wc", "bathroom"), ("toilet", "bathroom"), ("shower", "bathroom"),
        ("kitchen", "kitchen"), ("kit", "kitchen"),
        ("living", "living"), ("lounge", "living"), ("family", "living"),
        ("dining", "dining"), ("hall", "hallway"), ("corridor", "hallway"),
        ("foyer", "hallway"), ("entry", "hallway"), ("lobby", "hallway"),
        ("closet", "storage"), ("storage", "storage"), ("pantry", "storage"),
        ("laundry", "utility"), ("mechanical", "utility"), ("mech", "utility"),
        ("balcony", "balcony"), ("terrace", "balcony"), ("deck", "balcony"),
        ("garage", "garage"), ("parking", "garage"),
        ("office", "office"), ("study", "office"), ("den", "office"),
    ]:
        if keyword in lower:
            return rtype
    return "other"


def _detect_floor(layer_name: str) -> tuple[int, str]:
    """Extract floor number from layer name conventions."""
    import re
    lower = layer_name.lower()

    patterns = [
        (r"(?:floor|flr|level|lvl|storey)[_\s-]*(\d+)", None),
        (r"(?:f|l)(\d+)", None),
        (r"basement|bsmt", (-1, "Basement")),
        (r"ground|gf|gr", (0, "Ground")),
        (r"roof|rf", (99, "Roof")),
    ]

    for pattern, fixed in patterns:
        m = re.search(pattern, lower)
        if m:
            if fixed:
                return fixed
            num = int(m.group(1))
            return (num, f"Floor {num}")

    return (1, "Floor 1")


def _strip_xref_prefix(layer_name: str) -> str:
    """Strip xref prefixes like 'xref-Name$0$' from layer names."""
    if "$0$" in layer_name:
        return layer_name.split("$0$", 1)[-1]
    return layer_name


def _is_wall_layer(layer_name: str) -> bool:
    lower = _strip_xref_prefix(layer_name).lower()
    return any(kw in lower for kw in ("wall", "a-wall", "struc", "partition", "outline"))


def _wall_type_from_layer(layer_name: str) -> tuple[str, str]:
    """Return (wall_type, load_bearing) from layer name."""
    lower = _strip_xref_prefix(layer_name).lower()
    if any(kw in lower for kw in ("extr", "exterior", "outline")):
        return "exterior", "yes"
    if any(kw in lower for kw in ("strc", "struc", "structural", "party")):
        return "structural", "yes"
    if any(kw in lower for kw in ("part", "partition")):
        return "interior", "no"
    return "interior", "unknown"


def _is_room_layer(layer_name: str) -> bool:
    lower = _strip_xref_prefix(layer_name).lower()
    return any(kw in lower for kw in ("room", "area", "space", "hatch", "fill", "zone", "case", "footprint", "balcony", "balc", "deck", "terrace"))


def _is_balcony_layer(layer_name: str) -> bool:
    lower = _strip_xref_prefix(layer_name).lower()
    return any(kw in lower for kw in ("balcony", "balc", "deck", "terrace"))


def _is_column_layer(layer_name: str) -> bool:
    lower = _strip_xref_prefix(layer_name).lower()
    return any(kw in lower for kw in ("col", "s-col", "column", "pillar", "pier"))


def _is_ceiling_annotation(text: str) -> float | None:
    """Extract ceiling height from annotation text like 'CLG 4.2m'."""
    import re
    m = re.search(r"(?:clg|ceiling|ceil|c/h|ch)[:\s]*(\d+\.?\d*)\s*m?", text, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


def _get_block_attribs(entity) -> dict[str, str]:
    """Extract attribute values from an INSERT entity."""
    attribs = {}
    try:
        for att in entity.attribs:
            tag = att.dxf.tag.upper() if hasattr(att.dxf, "tag") else ""
            val = att.dxf.text if hasattr(att.dxf, "text") else ""
            if tag and val:
                attribs[tag] = val
    except Exception:
        pass
    return attribs


def _is_door_window(block_name: str) -> str | None:
    lower = block_name.lower()
    if any(kw in lower for kw in ("door", "dr", "entry")):
        return "door"
    if any(kw in lower for kw in ("window", "win", "glazing")):
        return "window"
    return None


def _get_polyline_points(entity) -> list[tuple[float, float]]:
    """Extract 2D points from a polyline entity."""
    try:
        if hasattr(entity, "get_points"):
            return [(p[0], p[1]) for p in entity.get_points(format="xy")]
        if hasattr(entity, "vertices"):
            return [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
    except Exception:
        pass
    return []


def _centre_coords(
    plans: list[FloorPlan],
) -> tuple[list[FloorPlan], dict]:
    """Shift all coordinates so the centroid is at origin. Return (plans, bounds)."""
    all_x: list[float] = []
    all_y: list[float] = []

    for fp in plans:
        for w in fp.walls:
            all_x.extend([w.start[0], w.end[0]])
            all_y.extend([w.start[1], w.end[1]])
        for r in fp.rooms:
            for px, py in r.polygon:
                all_x.append(px)
                all_y.append(py)
        for o in fp.openings:
            all_x.append(o.position[0])
            all_y.append(o.position[1])
        for c in fp.columns:
            all_x.append(c.position[0])
            all_y.append(c.position[1])

    if not all_x:
        return plans, {"min": [0, 0], "max": [0, 0]}

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2

    for fp in plans:
        for w in fp.walls:
            w.start = (w.start[0] - cx, w.start[1] - cy)
            w.end = (w.end[0] - cx, w.end[1] - cy)
        for r in fp.rooms:
            r.polygon = [(px - cx, py - cy) for px, py in r.polygon]
        for o in fp.openings:
            o.position = (o.position[0] - cx, o.position[1] - cy)
        for c in fp.columns:
            c.position = (c.position[0] - cx, c.position[1] - cy)

    bounds = {
        "min": [min_x - cx, min_y - cy],
        "max": [max_x - cx, max_y - cy],
    }
    return plans, bounds


def _nearest_room(rooms: list[Room], x: float, y: float) -> Room | None:
    """Find the room whose centroid is closest to (x, y)."""
    best = None
    best_dist = float("inf")
    for room in rooms:
        if not room.polygon:
            continue
        cx = sum(p[0] for p in room.polygon) / len(room.polygon)
        cy = sum(p[1] for p in room.polygon) / len(room.polygon)
        d = math.hypot(x - cx, y - cy)
        if d < best_dist:
            best_dist = d
            best = room
    return best


def detect_dxf_type(file_bytes: bytes) -> str:
    """Scan layer names to classify DXF as 'building' or 'pipeline'.

    Returns 'pipeline' if pipe/manhole/valve layers dominate, else 'building'.
    """
    import os
    import tempfile

    import ezdxf

    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        doc = ezdxf.readfile(tmp_path)
    finally:
        os.unlink(tmp_path)

    pipeline_kws = {"pipe", "water", "sewer", "storm", "main", "force", "trunk",
                    "lateral", "manhole", "mh", "valve", "vlv", "hydrant", "hyd"}
    building_kws = {"wall", "a-wall", "struc", "partition", "room", "door",
                    "window", "floor", "balcony", "column"}

    pipeline_hits = 0
    building_hits = 0
    for layer in doc.layers:
        lower = _strip_xref_prefix(layer.dxf.name).lower()
        for kw in pipeline_kws:
            if kw in lower:
                pipeline_hits += 1
                break
        for kw in building_kws:
            if kw in lower:
                building_hits += 1
                break

    return "pipeline" if pipeline_hits > building_hits else "building"


def parse_dxf(file_bytes: bytes) -> dict:
    """Parse a DXF file into structured floor plan data.

    Returns:
        {
            "floor_plans": [
                {
                    "floor_number": int,
                    "floor_label": str,
                    "walls": [{start, end, thickness_m, type}],
                    "rooms": [{name, type, polygon, area_m2}],
                    "openings": [{position, width_m, type}],
                }
            ],
            "units": "metres",
            "bounds": {"min": [x, y], "max": [x, y]},
        }
    """
    import tempfile

    import ezdxf

    # Write to temp file — ezdxf.readfile handles both ASCII and binary DXF
    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        doc = ezdxf.readfile(tmp_path)
    finally:
        import os
        os.unlink(tmp_path)

    msp = doc.modelspace()

    # ── Pass 1: Scan for FLOOR label annotations to build Y-band ranges ────
    import re as _re
    floor_bands: list[tuple[float, int, str]] = []  # (y_position, floor_num, label)
    for entity in msp:
        dxftype = entity.dxftype()
        if dxftype not in ("TEXT", "MTEXT"):
            continue
        layer = entity.dxf.layer if hasattr(entity.dxf, "layer") else ""
        stripped_layer = _strip_xref_prefix(layer).lower()
        if "flor" not in stripped_layer and "anno" not in stripped_layer:
            continue
        try:
            insert = entity.dxf.insert
            text = (entity.dxf.text if dxftype == "TEXT" else entity.text).strip()
            m = _re.search(r"FLOOR\s+(\d+)", text, _re.IGNORECASE)
            if m:
                floor_bands.append((insert.y, int(m.group(1)), text))
        except Exception:
            pass

    # Sort bands by Y ascending, compute midpoints for assignment
    floor_bands.sort(key=lambda b: b[0])

    def _y_to_floor(y: float) -> tuple[int, str]:
        """Map a Y coordinate to the nearest floor band."""
        if not floor_bands:
            return (1, "Floor 1")
        best_num, best_label = floor_bands[0][1], floor_bands[0][2]
        best_dist = float("inf")
        for band_y, fnum, flabel in floor_bands:
            d = abs(y - band_y)
            if d < best_dist:
                best_dist = d
                best_num = fnum
                best_label = flabel
        return (best_num, best_label)

    # ── Pass 2: Process all entities ─────────────────────────────────────
    floor_map: dict[int, FloorPlan] = {}
    labels: list[tuple[float, float, str, int]] = []  # x, y, text, floor_num

    def get_floor_from_layer(layer: str) -> FloorPlan:
        num, label = _detect_floor(layer)
        if num not in floor_map:
            floor_map[num] = FloorPlan(floor_number=num, floor_label=label)
        return floor_map[num]

    def get_floor_from_y(y: float) -> FloorPlan:
        num, label = _y_to_floor(y)
        if num not in floor_map:
            floor_map[num] = FloorPlan(floor_number=num, floor_label=label)
        return floor_map[num]

    for entity in msp:
        layer = entity.dxf.layer if hasattr(entity.dxf, "layer") else ""
        dxftype = entity.dxftype()

        # Determine floor: prefer layer-encoded floor, fallback to Y-position
        layer_floor_num, _ = _detect_floor(layer)
        has_floor_in_layer = layer_floor_num != 1 or any(
            kw in layer.lower() for kw in ("floor", "flr", "level", "lvl", "f1", "l1")
        )

        def _get_fp_for_y(y_coord: float) -> FloorPlan:
            if has_floor_in_layer or not floor_bands:
                return get_floor_from_layer(layer)
            return get_floor_from_y(y_coord)

        # Get a representative Y for this entity
        try:
            if dxftype == "LINE":
                rep_y = (entity.dxf.start.y + entity.dxf.end.y) / 2
            elif dxftype == "LWPOLYLINE":
                pts = _get_polyline_points(entity)
                rep_y = sum(p[1] for p in pts) / len(pts) if pts else 0
            elif dxftype == "INSERT":
                rep_y = entity.dxf.insert.y
            elif dxftype in ("TEXT", "MTEXT"):
                rep_y = entity.dxf.insert.y
            elif dxftype == "HATCH":
                rep_y = 0
                for path in entity.paths:
                    if hasattr(path, "vertices") and path.vertices:
                        rep_y = sum(v[1] for v in path.vertices) / len(path.vertices)
                        break
            else:
                rep_y = 0
        except Exception:
            rep_y = 0

        fp = _get_fp_for_y(rep_y)

        # Walls — LINE entities on wall layers
        if dxftype == "LINE" and _is_wall_layer(layer):
            start = entity.dxf.start
            end = entity.dxf.end
            wtype, lb = _wall_type_from_layer(layer)
            fp.walls.append(WallSegment(
                start=(start.x, start.y),
                end=(end.x, end.y),
                type=wtype,
                load_bearing=lb,
            ))

        # Walls — LWPOLYLINE on wall layers
        elif dxftype == "LWPOLYLINE" and _is_wall_layer(layer):
            pts = _get_polyline_points(entity)
            wtype, lb = _wall_type_from_layer(layer)
            for i in range(len(pts) - 1):
                fp.walls.append(WallSegment(
                    start=pts[i],
                    end=pts[i + 1],
                    type=wtype,
                    load_bearing=lb,
                ))
            if entity.closed and len(pts) > 2:
                fp.walls.append(WallSegment(
                    start=pts[-1],
                    end=pts[0],
                    type=wtype,
                    load_bearing=lb,
                ))

        # Columns — closed LWPOLYLINE on column layers
        elif dxftype == "LWPOLYLINE" and _is_column_layer(layer):
            pts = _get_polyline_points(entity)
            if len(pts) >= 3:
                cx = sum(p[0] for p in pts) / len(pts)
                cy = sum(p[1] for p in pts) / len(pts)
                # Estimate size from bounding box
                xs = [p[0] for p in pts]
                size = max(xs) - min(xs) if xs else 0.4
                fp.columns.append(Column(position=(cx, cy), size_m=round(size, 2)))

        # Rooms — closed LWPOLYLINE on room layers
        elif dxftype == "LWPOLYLINE" and _is_room_layer(layer):
            pts = _get_polyline_points(entity)
            if len(pts) >= 3:
                area = _polygon_area(pts)
                fp.rooms.append(Room(
                    name=layer,
                    type=_classify_room(layer),
                    polygon=pts,
                    area_m2=round(area, 2),
                ))

        # Rooms — HATCH entities (hatches are commonly used for room fills on any layer)
        elif dxftype == "HATCH":
            try:
                for path in entity.paths:
                    if hasattr(path, "vertices"):
                        pts = [(v[0], v[1]) for v in path.vertices]
                        if len(pts) >= 3:
                            area = _polygon_area(pts)
                            # Skip unrealistically large hatches (>500m2 likely borders/title blocks)
                            if area > 500:
                                continue
                            fp.rooms.append(Room(
                                name=layer,
                                type=_classify_room(layer),
                                polygon=pts,
                                area_m2=round(area, 2),
                            ))
            except Exception:
                pass

        # Text labels (room names, ceiling heights, floor labels)
        elif dxftype in ("TEXT", "MTEXT"):
            try:
                insert = entity.dxf.insert
                text = entity.dxf.text if dxftype == "TEXT" else entity.text
                if text and text.strip():
                    clean = text.strip()
                    # Check for ceiling height annotation
                    clg = _is_ceiling_annotation(clean)
                    if clg is not None:
                        fp.ceiling_height_m = clg
                    else:
                        labels.append((insert.x, insert.y, clean, fp.floor_number))
            except Exception:
                pass

        # Doors/windows — INSERT (block references)
        elif dxftype == "INSERT":
            block_name = entity.dxf.name if hasattr(entity.dxf, "name") else ""
            opening_type = _is_door_window(block_name)
            if opening_type:
                insert = entity.dxf.insert
                attribs = _get_block_attribs(entity)
                # Width: prefer attribute, fallback to block scale
                width_str = attribs.get("WIDTH_M", "")
                if width_str:
                    try:
                        width = float(width_str)
                    except ValueError:
                        sx = getattr(entity.dxf, "xscale", 1.0)
                        width = abs(sx) if abs(sx) > 0.1 else 0.9
                else:
                    sx = getattr(entity.dxf, "xscale", 1.0)
                    width = abs(sx) if abs(sx) > 0.1 else 0.9
                # Sill & head heights from attributes
                sill_h = None
                head_h = None
                swing = None
                if "SILL_HEIGHT_M" in attribs:
                    try:
                        sill_h = float(attribs["SILL_HEIGHT_M"])
                    except ValueError:
                        pass
                if "HEAD_HEIGHT_M" in attribs:
                    try:
                        head_h = float(attribs["HEAD_HEIGHT_M"])
                    except ValueError:
                        pass
                if "SWING" in attribs:
                    swing = attribs["SWING"].lower()
                fp.openings.append(Opening(
                    position=(insert.x, insert.y),
                    width_m=round(width, 2),
                    type=opening_type,
                    sill_height_m=sill_h,
                    head_height_m=head_h,
                    swing_direction=swing,
                ))

    # If no floors detected, create a default floor 1
    if not floor_map:
        floor_map[1] = FloorPlan(floor_number=1, floor_label="Floor 1")

    # Match text labels to nearest rooms
    # Strip DXF formatting codes (%%u = underline, %%o = overline, etc.)
    import re
    for x, y, text, floor_num in labels:
        clean_text = re.sub(r"%%[a-zA-Z]", "", text).strip()
        if not clean_text or floor_num not in floor_map:
            continue
        # Only match room-like labels (skip dimension text, notes, etc.)
        if _classify_room(clean_text) == "other" and not any(
            kw in clean_text.lower() for kw in ("room", "hall", "closet", "porch", "garage", "foyer", "entry")
        ):
            continue
        room = _nearest_room(floor_map[floor_num].rooms, x, y)
        if room:
            room.name = clean_text
            room.type = _classify_room(clean_text)

    # Post-process: remove oversized rooms (likely border/title-block hatches)
    # Cap at 500 m2 — any real room above this is a data error
    for fp in floor_map.values():
        fp.rooms = [r for r in fp.rooms if r.area_m2 <= 500]

    plans = sorted(floor_map.values(), key=lambda fp: fp.floor_number)
    plans, bounds = _centre_coords(plans)

    # Serialize to dict
    def _serialize_plan(fp: FloorPlan) -> dict:
        result = {
            "floor_number": fp.floor_number,
            "floor_label": fp.floor_label,
            "walls": [
                {
                    "start": list(w.start), "end": list(w.end),
                    "thickness_m": w.thickness_m, "type": w.type,
                    "load_bearing": w.load_bearing,
                }
                for w in fp.walls
            ],
            "rooms": [
                {"name": r.name, "type": r.type, "polygon": [list(p) for p in r.polygon], "area_m2": r.area_m2}
                for r in fp.rooms
            ],
            "openings": [
                {
                    "position": list(o.position), "width_m": o.width_m, "type": o.type,
                    **({"sill_height_m": o.sill_height_m} if o.sill_height_m is not None else {}),
                    **({"head_height_m": o.head_height_m} if o.head_height_m is not None else {}),
                    **({"swing_direction": o.swing_direction} if o.swing_direction else {}),
                }
                for o in fp.openings
            ],
        }
        if fp.ceiling_height_m is not None:
            result["ceiling_height_m"] = fp.ceiling_height_m
        if fp.columns:
            result["columns"] = [
                {"position": list(c.position), "size_m": c.size_m}
                for c in fp.columns
            ]
        return result

    return {
        "floor_plans": [_serialize_plan(fp) for fp in plans],
        "units": "metres",
        "bounds": bounds,
    }
