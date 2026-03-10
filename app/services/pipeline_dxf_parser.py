"""Pipeline DXF parsing for civil engineering pipe network files.

Extracts pipes, manholes, valves, hydrants, and fittings from DXF files
using standard civil engineering layer conventions.
All coordinates output in metres, centred at origin.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PipeSegment:
    start: tuple[float, float]
    end: tuple[float, float]
    diameter_mm: float = 150.0
    material: str = "PVC"
    pipe_type: str = "water_main"
    depth_m: float = 1.5


@dataclass
class ManholeNode:
    position: tuple[float, float]
    id: str = ""
    depth_m: float = 2.0
    rim_elevation: float | None = None
    invert_elevation: float | None = None


@dataclass
class ValveNode:
    position: tuple[float, float]
    type: str = "gate"
    diameter_mm: float = 150.0


@dataclass
class HydrantNode:
    position: tuple[float, float]


@dataclass
class FittingNode:
    position: tuple[float, float]
    type: str = "elbow"  # elbow, tee, reducer


# ── Layer classification ────────────────────────────────────────────────────

def _strip_xref_prefix(layer_name: str) -> str:
    if "$0$" in layer_name:
        return layer_name.split("$0$", 1)[-1]
    return layer_name


def _is_pipe_layer(layer_name: str) -> bool:
    lower = _strip_xref_prefix(layer_name).lower()
    return any(kw in lower for kw in (
        "pipe", "water", "sewer", "storm", "main", "force", "trunk", "lateral",
    ))


def _is_manhole_layer(layer_name: str) -> bool:
    lower = _strip_xref_prefix(layer_name).lower()
    return any(kw in lower for kw in (
        "manhole", "mh", "structure", "catch-basin", "cb",
    ))


def _is_valve_layer(layer_name: str) -> bool:
    lower = _strip_xref_prefix(layer_name).lower()
    return any(kw in lower for kw in ("valve", "vlv", "gate", "butterfly"))


def _is_hydrant_layer(layer_name: str) -> bool:
    lower = _strip_xref_prefix(layer_name).lower()
    return any(kw in lower for kw in ("hydrant", "hyd", "fire"))


def _is_fitting_layer(layer_name: str) -> bool:
    lower = _strip_xref_prefix(layer_name).lower()
    return any(kw in lower for kw in ("fitting", "elbow", "tee", "reducer", "bend"))


def _classify_pipe_type(layer_name: str) -> str:
    lower = _strip_xref_prefix(layer_name).lower()
    if any(kw in lower for kw in ("sanitary", "san", "sewer")):
        if "storm" not in lower:
            return "sanitary_sewer"
    if any(kw in lower for kw in ("storm", "stm", "drain")):
        return "storm_sewer"
    return "water_main"


def _get_block_attribs(entity) -> dict[str, str]:
    attribs = {}
    try:
        for att in entity.attribs:
            tag = att.dxf.tag.upper() if hasattr(att.dxf, "tag") else ""
            val = att.dxf.text if hasattr(att.dxf, "text") else ""
            if tag and val:
                attribs[tag] = val
    except Exception:
        logger.debug("Failed to read block attributes from entity on layer %s", getattr(entity.dxf, "layer", "?"))
    return attribs


def _get_polyline_points(entity) -> list[tuple[float, float]]:
    try:
        if hasattr(entity, "get_points"):
            return [(p[0], p[1]) for p in entity.get_points(format="xy")]
        if hasattr(entity, "vertices"):
            return [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
    except Exception:
        logger.debug("Failed to extract polyline points from entity on layer %s", getattr(entity.dxf, "layer", "?"))
    return []


def _parse_float(val: str, default: float) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _segment_length(start: tuple[float, float], end: tuple[float, float]) -> float:
    return math.hypot(end[0] - start[0], end[1] - start[1])


# ── Main parser ─────────────────────────────────────────────────────────────

def parse_pipeline_dxf(file_bytes: bytes) -> dict:
    """Parse a pipeline DXF file into structured pipe network data.

    Returns:
        {
            "type": "pipeline_network",
            "pipes": [...],
            "manholes": [...],
            "valves": [...],
            "hydrants": [...],
            "fittings": [...],
            "units": "metres",
            "bounds": {"min": [x, y], "max": [x, y]},
            "summary": {"total_length_m": float, "pipe_count": int, ...}
        }
    """
    import io

    import ezdxf

    stream = io.BytesIO(file_bytes)
    doc = ezdxf.read(stream)

    msp = doc.modelspace()

    pipes: list[PipeSegment] = []
    manholes: list[ManholeNode] = []
    valves: list[ValveNode] = []
    hydrants: list[HydrantNode] = []
    fittings: list[FittingNode] = []

    for entity in msp:
        layer = entity.dxf.layer if hasattr(entity.dxf, "layer") else ""
        dxftype = entity.dxftype()

        # ── Pipes: LINE on pipe layers ──
        if dxftype == "LINE" and _is_pipe_layer(layer):
            start = entity.dxf.start
            end = entity.dxf.end
            pipe_type = _classify_pipe_type(layer)
            pipes.append(PipeSegment(
                start=(start.x, start.y),
                end=(end.x, end.y),
                pipe_type=pipe_type,
            ))

        # ── Pipes: LWPOLYLINE / POLYLINE on pipe layers ──
        elif dxftype in ("LWPOLYLINE", "POLYLINE") and _is_pipe_layer(layer):
            pts = _get_polyline_points(entity)
            pipe_type = _classify_pipe_type(layer)
            for i in range(len(pts) - 1):
                pipes.append(PipeSegment(
                    start=pts[i],
                    end=pts[i + 1],
                    pipe_type=pipe_type,
                ))

        # ── Manholes: CIRCLE on manhole layers ──
        elif dxftype == "CIRCLE" and _is_manhole_layer(layer):
            center = entity.dxf.center
            manholes.append(ManholeNode(
                position=(center.x, center.y),
            ))

        # ── Manholes / Valves / Hydrants / Fittings: INSERT on relevant layers ──
        elif dxftype == "INSERT":
            insert = entity.dxf.insert
            attribs = _get_block_attribs(entity)
            pos = (insert.x, insert.y)

            if _is_manhole_layer(layer):
                mh = ManholeNode(position=pos)
                mh.id = attribs.get("ID", attribs.get("MH_ID", attribs.get("NUMBER", "")))
                mh.depth_m = _parse_float(attribs.get("DEPTH", attribs.get("DEPTH_M", "")), 2.0)
                mh.rim_elevation = _parse_float(attribs.get("RIM", attribs.get("RIM_ELEV", "")), None)
                mh.invert_elevation = _parse_float(attribs.get("INVERT", attribs.get("INV_ELEV", "")), None)
                manholes.append(mh)

            elif _is_valve_layer(layer):
                v = ValveNode(position=pos)
                block_name = (entity.dxf.name if hasattr(entity.dxf, "name") else "").lower()
                if "butterfly" in block_name:
                    v.type = "butterfly"
                elif "ball" in block_name:
                    v.type = "ball"
                elif "check" in block_name:
                    v.type = "check"
                else:
                    v.type = "gate"
                v.diameter_mm = _parse_float(attribs.get("DIAMETER", attribs.get("SIZE", "")), 150.0)
                valves.append(v)

            elif _is_hydrant_layer(layer):
                hydrants.append(HydrantNode(position=pos))

            elif _is_fitting_layer(layer):
                block_name = (entity.dxf.name if hasattr(entity.dxf, "name") else "").lower()
                if "tee" in block_name:
                    fit_type = "tee"
                elif "reducer" in block_name or "reduce" in block_name:
                    fit_type = "reducer"
                else:
                    fit_type = "elbow"
                fittings.append(FittingNode(position=pos, type=fit_type))

        # ── Manholes: LWPOLYLINE/POLYLINE (closed) on manhole layers — treat centroid as manhole ──
        elif dxftype in ("LWPOLYLINE", "POLYLINE") and _is_manhole_layer(layer):
            pts = _get_polyline_points(entity)
            if len(pts) >= 3:
                cx = sum(p[0] for p in pts) / len(pts)
                cy = sum(p[1] for p in pts) / len(pts)
                manholes.append(ManholeNode(position=(cx, cy)))

    # ── Extract pipe attributes from INSERT blocks on pipe layers ──
    # Some DXFs put diameter/material as block attributes alongside pipe geometry
    for entity in msp:
        layer = entity.dxf.layer if hasattr(entity.dxf, "layer") else ""
        if entity.dxftype() == "INSERT" and _is_pipe_layer(layer):
            attribs = _get_block_attribs(entity)
            diameter = _parse_float(attribs.get("DIAMETER", attribs.get("SIZE", attribs.get("DIA", ""))), None)
            material = attribs.get("MATERIAL", attribs.get("MAT", attribs.get("PIPE_MAT", "")))
            depth = _parse_float(attribs.get("DEPTH", attribs.get("DEPTH_M", "")), None)

            if diameter or material or depth:
                insert = entity.dxf.insert
                # Apply attributes to nearest pipe
                best_pipe = None
                best_dist = float("inf")
                for p in pipes:
                    mid_x = (p.start[0] + p.end[0]) / 2
                    mid_y = (p.start[1] + p.end[1]) / 2
                    d = math.hypot(insert.x - mid_x, insert.y - mid_y)
                    if d < best_dist:
                        best_dist = d
                        best_pipe = p
                if best_pipe and best_dist < 10.0:
                    if diameter:
                        best_pipe.diameter_mm = diameter
                    if material:
                        best_pipe.material = material.upper()
                    if depth:
                        best_pipe.depth_m = depth

    # ── Centre coordinates ──
    all_x: list[float] = []
    all_y: list[float] = []
    for p in pipes:
        all_x.extend([p.start[0], p.end[0]])
        all_y.extend([p.start[1], p.end[1]])
    for m in manholes:
        all_x.append(m.position[0])
        all_y.append(m.position[1])
    for v in valves:
        all_x.append(v.position[0])
        all_y.append(v.position[1])
    for h in hydrants:
        all_x.append(h.position[0])
        all_y.append(h.position[1])
    for f in fittings:
        all_x.append(f.position[0])
        all_y.append(f.position[1])

    if all_x:
        cx = (min(all_x) + max(all_x)) / 2
        cy = (min(all_y) + max(all_y)) / 2
    else:
        cx, cy = 0.0, 0.0

    for p in pipes:
        p.start = (p.start[0] - cx, p.start[1] - cy)
        p.end = (p.end[0] - cx, p.end[1] - cy)
    for m in manholes:
        m.position = (m.position[0] - cx, m.position[1] - cy)
    for v in valves:
        v.position = (v.position[0] - cx, v.position[1] - cy)
    for h in hydrants:
        h.position = (h.position[0] - cx, h.position[1] - cy)
    for f in fittings:
        f.position = (f.position[0] - cx, f.position[1] - cy)

    bounds = {
        "min": [min(all_x) - cx, min(all_y) - cy] if all_x else [0, 0],
        "max": [max(all_x) - cx, max(all_y) - cy] if all_x else [0, 0],
    }

    # ── Summary ──
    total_length = sum(_segment_length(p.start, p.end) for p in pipes)

    return {
        "type": "pipeline_network",
        "pipes": [
            {
                "start": list(p.start),
                "end": list(p.end),
                "diameter_mm": p.diameter_mm,
                "material": p.material,
                "pipe_type": p.pipe_type,
                "depth_m": p.depth_m,
            }
            for p in pipes
        ],
        "manholes": [
            {
                "position": list(m.position),
                "id": m.id,
                "depth_m": m.depth_m,
                **({"rim_elevation": m.rim_elevation} if m.rim_elevation is not None else {}),
                **({"invert_elevation": m.invert_elevation} if m.invert_elevation is not None else {}),
            }
            for m in manholes
        ],
        "valves": [
            {
                "position": list(v.position),
                "type": v.type,
                "diameter_mm": v.diameter_mm,
            }
            for v in valves
        ],
        "hydrants": [
            {"position": list(h.position)}
            for h in hydrants
        ],
        "fittings": [
            {"position": list(f.position), "type": f.type}
            for f in fittings
        ],
        "units": "metres",
        "bounds": bounds,
        "summary": {
            "total_length_m": round(total_length, 2),
            "pipe_count": len(pipes),
            "manhole_count": len(manholes),
            "valve_count": len(valves),
            "hydrant_count": len(hydrants),
            "fitting_count": len(fittings),
        },
    }
