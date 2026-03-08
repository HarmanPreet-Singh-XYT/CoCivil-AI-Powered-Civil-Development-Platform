#!/usr/bin/env python3
"""
Generate a rich sample DXF file for a 6-storey mixed-use midrise building.

Includes:
- Separate layers for structural walls, partition walls, rooms, openings, annotations
- Ceiling height TEXT annotations per floor
- Door/window INSERT blocks with sill_height and head_height attributes
- Balcony polygons on dedicated layer
- Room HATCH fills with area/type labels
- Multiple floors with distinct layouts

Output: sample_building.dxf
"""

import ezdxf
from ezdxf import units
from ezdxf.enums import TextEntityAlignment
import math
import os

# ── Building dimensions ─────────────────────────────────────────────────────
BUILDING_W = 24.0   # metres along X
BUILDING_D = 16.0   # metres along Y
NUM_FLOORS = 6
GROUND_FLOOR_H = 4.5
TYPICAL_FLOOR_H = 3.3
WALL_THICK = 0.2
PARTITION_THICK = 0.15

# ── Layer definitions ────────────────────────────────────────────────────────
LAYERS = {
    # Structural / exterior walls
    "A-WALL-EXTR": {"color": 7, "description": "Exterior structural walls"},
    "A-WALL-STRC": {"color": 5, "description": "Interior structural / load-bearing walls"},
    "A-WALL-PART": {"color": 8, "description": "Interior partition walls"},
    # Rooms
    "A-ROOM-BDRY": {"color": 3, "description": "Room boundary polygons"},
    "A-ROOM-FILL": {"color": 62, "description": "Room hatch fills"},
    "A-ROOM-NAME": {"color": 2, "description": "Room name labels"},
    "A-ROOM-AREA": {"color": 2, "description": "Room area labels"},
    # Openings
    "A-DOOR":      {"color": 1, "description": "Door blocks"},
    "A-WINDOW":    {"color": 4, "description": "Window blocks"},
    # Balcony / exterior
    "A-BALCONY":   {"color": 6, "description": "Balcony outlines"},
    # Annotations
    "A-ANNO-CLG":  {"color": 9, "description": "Ceiling height annotations"},
    "A-ANNO-DIM":  {"color": 8, "description": "Dimensions"},
    "A-ANNO-FLOR": {"color": 7, "description": "Floor labels"},
    # Columns
    "S-COLS":      {"color": 5, "description": "Structural columns"},
}

# Floor offsets in DXF Y-space (each floor is laid out vertically offset)
FLOOR_SPACING_Y = BUILDING_D + 8.0  # gap between floor layouts in drawing


def create_door_block(doc):
    """Create a door block with attributes for width, swing, sill/head height."""
    blk = doc.blocks.new(name="DOOR-SINGLE")
    # Door leaf (arc swing)
    blk.add_arc(center=(0, 0), radius=0.9, start_angle=0, end_angle=90,
                dxfattribs={"layer": "A-DOOR"})
    # Door frame lines
    blk.add_line((0, 0), (0.9, 0), dxfattribs={"layer": "A-DOOR"})
    blk.add_line((0, 0), (0, 0.05), dxfattribs={"layer": "A-DOOR"})
    # Attributes
    blk.add_attdef("WIDTH_M", (0, -0.3), dxfattribs={"height": 0.15, "layer": "A-DOOR"})
    blk.add_attdef("HEAD_HEIGHT_M", (0, -0.5), dxfattribs={"height": 0.15, "layer": "A-DOOR"})
    blk.add_attdef("SWING", (0, -0.7), dxfattribs={"height": 0.15, "layer": "A-DOOR"})
    return blk


def create_window_block(doc):
    """Create a window block with attributes for width, sill height, head height."""
    blk = doc.blocks.new(name="WINDOW-STD")
    # Window symbol (two parallel lines)
    blk.add_line((0, -0.05), (1.2, -0.05), dxfattribs={"layer": "A-WINDOW"})
    blk.add_line((0, 0.05), (1.2, 0.05), dxfattribs={"layer": "A-WINDOW"})
    # Glass line
    blk.add_line((0, 0), (1.2, 0), dxfattribs={"layer": "A-WINDOW", "color": 4})
    # Attributes
    blk.add_attdef("WIDTH_M", (0, -0.3), dxfattribs={"height": 0.15, "layer": "A-WINDOW"})
    blk.add_attdef("SILL_HEIGHT_M", (0, -0.5), dxfattribs={"height": 0.15, "layer": "A-WINDOW"})
    blk.add_attdef("HEAD_HEIGHT_M", (0, -0.7), dxfattribs={"height": 0.15, "layer": "A-WINDOW"})
    return blk


def create_storefront_block(doc):
    """Large storefront window for ground floor retail."""
    blk = doc.blocks.new(name="WINDOW-STOREFRONT")
    blk.add_line((0, -0.08), (3.0, -0.08), dxfattribs={"layer": "A-WINDOW"})
    blk.add_line((0, 0.08), (3.0, 0.08), dxfattribs={"layer": "A-WINDOW"})
    blk.add_line((0, 0), (3.0, 0), dxfattribs={"layer": "A-WINDOW", "color": 4})
    # Mullion
    blk.add_line((1.5, -0.08), (1.5, 0.08), dxfattribs={"layer": "A-WINDOW"})
    blk.add_attdef("WIDTH_M", (0, -0.3), dxfattribs={"height": 0.15, "layer": "A-WINDOW"})
    blk.add_attdef("SILL_HEIGHT_M", (0, -0.5), dxfattribs={"height": 0.15, "layer": "A-WINDOW"})
    blk.add_attdef("HEAD_HEIGHT_M", (0, -0.7), dxfattribs={"height": 0.15, "layer": "A-WINDOW"})
    return blk


def add_wall(msp, start, end, layer, thickness=WALL_THICK):
    """Add a wall as a LWPOLYLINE rectangle."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.sqrt(dx * dx + dy * dy)
    if length < 0.01:
        return
    # Normal perpendicular to wall direction
    nx = -dy / length * thickness / 2
    ny = dx / length * thickness / 2
    pts = [
        (start[0] + nx, start[1] + ny),
        (end[0] + nx, end[1] + ny),
        (end[0] - nx, end[1] - ny),
        (start[0] - nx, start[1] - ny),
    ]
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": layer})


def add_room(msp, polygon, name, room_type, area_m2, floor_y_offset=0):
    """Add room boundary polygon, label, and area annotation."""
    offset_poly = [(p[0], p[1] + floor_y_offset) for p in polygon]
    # Room boundary
    msp.add_lwpolyline(offset_poly, close=True, dxfattribs={"layer": "A-ROOM-BDRY"})
    # Centroid for labels
    cx = sum(p[0] for p in offset_poly) / len(offset_poly)
    cy = sum(p[1] for p in offset_poly) / len(offset_poly)
    # Room name
    msp.add_text(
        f"{name} ({room_type})",
        height=0.25,
        dxfattribs={"layer": "A-ROOM-NAME"}
    ).set_placement((cx, cy), align=TextEntityAlignment.MIDDLE_CENTER)
    # Area
    msp.add_text(
        f"{area_m2:.1f} m²",
        height=0.18,
        dxfattribs={"layer": "A-ROOM-AREA"}
    ).set_placement((cx, cy - 0.4), align=TextEntityAlignment.MIDDLE_CENTER)


def add_column(msp, cx, cy, size=0.4):
    """Add a structural column (square)."""
    hs = size / 2
    pts = [(cx - hs, cy - hs), (cx + hs, cy - hs), (cx + hs, cy + hs), (cx - hs, cy + hs)]
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "S-COLS"})


def draw_ground_floor(msp, doc, y_off):
    """Floor 1: Retail ground floor with storefront windows."""
    W, D = BUILDING_W, BUILDING_D

    # ── Exterior walls ───────────────────────────────────────────────
    add_wall(msp, (0, y_off), (W, y_off), "A-WALL-EXTR")               # south
    add_wall(msp, (W, y_off), (W, y_off + D), "A-WALL-EXTR")           # east
    add_wall(msp, (W, y_off + D), (0, y_off + D), "A-WALL-EXTR")       # north
    add_wall(msp, (0, y_off + D), (0, y_off), "A-WALL-EXTR")           # west

    # ── Structural walls (core) ──────────────────────────────────────
    core_x = 10.0
    add_wall(msp, (core_x, y_off), (core_x, y_off + D), "A-WALL-STRC")
    add_wall(msp, (core_x, y_off + 6), (core_x + 4, y_off + 6), "A-WALL-STRC")
    add_wall(msp, (core_x, y_off + 10), (core_x + 4, y_off + 10), "A-WALL-STRC")
    add_wall(msp, (core_x + 4, y_off), (core_x + 4, y_off + D), "A-WALL-STRC")

    # ── Partition walls ──────────────────────────────────────────────
    add_wall(msp, (core_x + 4, y_off + 8), (W, y_off + 8), "A-WALL-PART", PARTITION_THICK)

    # ── Columns ──────────────────────────────────────────────────────
    for cx_pos in [4.0, 8.0, 16.0, 20.0]:
        for cy_pos in [4.0, 12.0]:
            add_column(msp, cx_pos, y_off + cy_pos)

    # ── Rooms ────────────────────────────────────────────────────────
    # Retail space (west)
    add_room(msp, [(0, 0), (core_x, 0), (core_x, D), (0, D)],
             "Retail A", "retail", core_x * D, y_off)
    # Retail space (east-south)
    add_room(msp, [(core_x + 4, 0), (W, 0), (W, 8), (core_x + 4, 8)],
             "Retail B", "retail", (W - core_x - 4) * 8, y_off)
    # Lobby
    add_room(msp, [(core_x, 0), (core_x + 4, 0), (core_x + 4, 6), (core_x, 6)],
             "Lobby", "lobby", 4 * 6, y_off)
    # Elevator/stair core
    add_room(msp, [(core_x, 6), (core_x + 4, 6), (core_x + 4, 10), (core_x, 10)],
             "Core", "elevator", 4 * 4, y_off)
    # Service/utility (east-north)
    add_room(msp, [(core_x + 4, 8), (W, 8), (W, D), (core_x + 4, D)],
             "Service", "utility", (W - core_x - 4) * (D - 8), y_off)
    # Mechanical
    add_room(msp, [(core_x, 10), (core_x + 4, 10), (core_x + 4, D), (core_x, D)],
             "Mechanical", "utility", 4 * (D - 10), y_off)

    # ── Storefront windows (south facade) ────────────────────────────
    for wx in [1.0, 5.0, 15.0, 19.0]:
        attribs = {"WIDTH_M": "3.0", "SILL_HEIGHT_M": "0.0", "HEAD_HEIGHT_M": "3.5"}
        insert = msp.add_blockref("WINDOW-STOREFRONT", (wx, y_off),
                                   dxfattribs={"layer": "A-WINDOW", "rotation": 0})
        insert.add_auto_attribs(attribs)

    # ── Standard windows (north facade) ──────────────────────────────
    for wx in [2.0, 6.0, 16.0, 20.0]:
        attribs = {"WIDTH_M": "1.2", "SILL_HEIGHT_M": "0.9", "HEAD_HEIGHT_M": "3.5"}
        insert = msp.add_blockref("WINDOW-STD", (wx, y_off + D),
                                   dxfattribs={"layer": "A-WINDOW", "rotation": 180})
        insert.add_auto_attribs(attribs)

    # ── Doors ────────────────────────────────────────────────────────
    # Main entrance
    attribs = {"WIDTH_M": "1.8", "HEAD_HEIGHT_M": "3.0", "SWING": "inward"}
    ins = msp.add_blockref("DOOR-SINGLE", (core_x + 1, y_off),
                            dxfattribs={"layer": "A-DOOR", "rotation": 0})
    ins.add_auto_attribs(attribs)
    # Service door
    attribs = {"WIDTH_M": "0.9", "HEAD_HEIGHT_M": "2.4", "SWING": "inward"}
    ins = msp.add_blockref("DOOR-SINGLE", (W - 1, y_off + D),
                            dxfattribs={"layer": "A-DOOR", "rotation": 180})
    ins.add_auto_attribs(attribs)

    # ── Ceiling height annotation ────────────────────────────────────
    msp.add_text(
        "CLG 4.2m", height=0.3,
        dxfattribs={"layer": "A-ANNO-CLG"}
    ).set_placement((W / 2, y_off + D + 1.0), align=TextEntityAlignment.MIDDLE_CENTER)

    # ── Floor label ──────────────────────────────────────────────────
    msp.add_text(
        "FLOOR 1 — GROUND / RETAIL", height=0.4,
        dxfattribs={"layer": "A-ANNO-FLOR"}
    ).set_placement((W / 2, y_off - 1.5), align=TextEntityAlignment.MIDDLE_CENTER)


def draw_typical_residential_floor(msp, doc, floor_num, y_off):
    """Floors 2-6: Residential with 2-bedroom and 1-bedroom units, balconies."""
    W, D = BUILDING_W, BUILDING_D

    # ── Exterior walls ───────────────────────────────────────────────
    add_wall(msp, (0, y_off), (W, y_off), "A-WALL-EXTR")
    add_wall(msp, (W, y_off), (W, y_off + D), "A-WALL-EXTR")
    add_wall(msp, (W, y_off + D), (0, y_off + D), "A-WALL-EXTR")
    add_wall(msp, (0, y_off + D), (0, y_off), "A-WALL-EXTR")

    # ── Core walls (structural) ──────────────────────────────────────
    core_x = 10.0
    add_wall(msp, (core_x, y_off), (core_x, y_off + D), "A-WALL-STRC")
    add_wall(msp, (core_x + 4, y_off), (core_x + 4, y_off + D), "A-WALL-STRC")
    # Core horizontal walls
    add_wall(msp, (core_x, y_off + 6), (core_x + 4, y_off + 6), "A-WALL-STRC")
    add_wall(msp, (core_x, y_off + 10), (core_x + 4, y_off + 10), "A-WALL-STRC")

    # ── Corridor ─────────────────────────────────────────────────────
    add_wall(msp, (0, y_off + 7), (core_x, y_off + 7), "A-WALL-PART", PARTITION_THICK)
    add_wall(msp, (0, y_off + 9), (core_x, y_off + 9), "A-WALL-PART", PARTITION_THICK)
    add_wall(msp, (core_x + 4, y_off + 7), (W, y_off + 7), "A-WALL-PART", PARTITION_THICK)
    add_wall(msp, (core_x + 4, y_off + 9), (W, y_off + 9), "A-WALL-PART", PARTITION_THICK)

    # ── Unit dividers (structural party walls) ───────────────────────
    add_wall(msp, (5, y_off), (5, y_off + 7), "A-WALL-STRC")
    add_wall(msp, (5, y_off + 9), (5, y_off + D), "A-WALL-STRC")
    add_wall(msp, (18, y_off), (18, y_off + 7), "A-WALL-STRC")
    add_wall(msp, (18, y_off + 9), (18, y_off + D), "A-WALL-STRC")

    # ── Interior partitions (within units) ───────────────────────────
    # Unit A (SW corner) — 2-bed
    add_wall(msp, (0, y_off + 4), (5, y_off + 4), "A-WALL-PART", PARTITION_THICK)
    add_wall(msp, (3, y_off), (3, y_off + 4), "A-WALL-PART", PARTITION_THICK)
    # Unit B (NW corner) — 1-bed
    add_wall(msp, (0, y_off + 12), (5, y_off + 12), "A-WALL-PART", PARTITION_THICK)
    add_wall(msp, (3, y_off + 9), (3, y_off + 12), "A-WALL-PART", PARTITION_THICK)
    # Unit C (SE corner) — 2-bed
    add_wall(msp, (14 + 4, y_off + 4), (W, y_off + 4), "A-WALL-PART", PARTITION_THICK)
    add_wall(msp, (21, y_off), (21, y_off + 4), "A-WALL-PART", PARTITION_THICK)
    # Unit D (NE corner) — 1-bed
    add_wall(msp, (18, y_off + 12), (W, y_off + 12), "A-WALL-PART", PARTITION_THICK)
    add_wall(msp, (21, y_off + 9), (21, y_off + 12), "A-WALL-PART", PARTITION_THICK)

    # ── Rooms ────────────────────────────────────────────────────────
    # CORRIDOR
    add_room(msp, [(0, 7), (core_x, 7), (core_x, 9), (0, 9)],
             "Corridor W", "hallway", core_x * 2, y_off)
    add_room(msp, [(core_x + 4, 7), (W, 7), (W, 9), (core_x + 4, 9)],
             "Corridor E", "hallway", (W - core_x - 4) * 2, y_off)

    # CORE
    add_room(msp, [(core_x, 0), (core_x + 4, 0), (core_x + 4, 6), (core_x, 6)],
             "Stair/Elev", "elevator", 4 * 6, y_off)
    add_room(msp, [(core_x, 6), (core_x + 4, 6), (core_x + 4, 10), (core_x, 10)],
             "Core", "elevator", 4 * 4, y_off)
    add_room(msp, [(core_x, 10), (core_x + 4, 10), (core_x + 4, D), (core_x, D)],
             "Stair N", "elevator", 4 * (D - 10), y_off)

    # UNIT A (SW) — 2 bedroom
    add_room(msp, [(0, 0), (3, 0), (3, 4), (0, 4)],
             "Bedroom 1", "bedroom", 3 * 4, y_off)
    add_room(msp, [(3, 0), (5, 0), (5, 4), (3, 4)],
             "Bathroom A", "bathroom", 2 * 4, y_off)
    add_room(msp, [(0, 4), (5, 4), (5, 7), (0, 7)],
             "Living/Kitchen A", "living", 5 * 3, y_off)

    # UNIT B (NW) — 1 bedroom
    add_room(msp, [(0, 9), (3, 9), (3, 12), (0, 12)],
             "Bathroom B", "bathroom", 3 * 3, y_off)
    add_room(msp, [(3, 9), (5, 9), (5, 12), (3, 12)],
             "Kitchen B", "kitchen", 2 * 3, y_off)
    add_room(msp, [(0, 12), (5, 12), (5, D), (0, D)],
             "Bedroom B", "bedroom", 5 * (D - 12), y_off)

    # UNIT C (SE) — 2 bedroom
    add_room(msp, [(18, 0), (21, 0), (21, 4), (18, 4)],
             "Bedroom 2", "bedroom", 3 * 4, y_off)
    add_room(msp, [(21, 0), (W, 0), (W, 4), (21, 4)],
             "Bathroom C", "bathroom", (W - 21) * 4, y_off)
    add_room(msp, [(18, 4), (W, 4), (W, 7), (18, 7)],
             "Living/Kitchen C", "living", (W - 18) * 3, y_off)

    # UNIT D (NE) — 1 bedroom
    add_room(msp, [(18, 9), (21, 9), (21, 12), (18, 12)],
             "Kitchen D", "kitchen", 3 * 3, y_off)
    add_room(msp, [(21, 9), (W, 9), (W, 12), (21, 12)],
             "Bathroom D", "bathroom", (W - 21) * 3, y_off)
    add_room(msp, [(18, 12), (W, 12), (W, D), (18, D)],
             "Bedroom D", "bedroom", (W - 18) * (D - 12), y_off)

    # Middle units (between party walls and core)
    add_room(msp, [(5, 0), (core_x, 0), (core_x, 7), (5, 7)],
             "Unit E Living", "living", (core_x - 5) * 7, y_off)
    add_room(msp, [(5, 9), (core_x, 9), (core_x, D), (5, D)],
             "Unit F Living", "living", (core_x - 5) * (D - 9), y_off)
    add_room(msp, [(core_x + 4, 0), (18, 0), (18, 7), (core_x + 4, 7)],
             "Unit G Living", "living", (18 - core_x - 4) * 7, y_off)
    add_room(msp, [(core_x + 4, 9), (18, 9), (18, D), (core_x + 4, D)],
             "Unit H Living", "living", (18 - core_x - 4) * (D - 9), y_off)

    # ── Windows ──────────────────────────────────────────────────────
    sill = "0.9"
    head = "2.7"
    # South facade
    for wx in [1.0, 3.5, 6.5, 15.0, 19.0, 22.0]:
        attribs = {"WIDTH_M": "1.2", "SILL_HEIGHT_M": sill, "HEAD_HEIGHT_M": head}
        ins = msp.add_blockref("WINDOW-STD", (wx, y_off),
                                dxfattribs={"layer": "A-WINDOW"})
        ins.add_auto_attribs(attribs)
    # North facade
    for wx in [1.0, 3.5, 6.5, 15.0, 19.0, 22.0]:
        attribs = {"WIDTH_M": "1.2", "SILL_HEIGHT_M": sill, "HEAD_HEIGHT_M": head}
        ins = msp.add_blockref("WINDOW-STD", (wx, y_off + D),
                                dxfattribs={"layer": "A-WINDOW", "rotation": 180})
        ins.add_auto_attribs(attribs)
    # East facade
    for wy_rel in [2.0, 5.5, 10.0, 13.5]:
        attribs = {"WIDTH_M": "1.2", "SILL_HEIGHT_M": sill, "HEAD_HEIGHT_M": head}
        ins = msp.add_blockref("WINDOW-STD", (W, y_off + wy_rel),
                                dxfattribs={"layer": "A-WINDOW", "rotation": 270})
        ins.add_auto_attribs(attribs)
    # West facade
    for wy_rel in [2.0, 5.5, 10.0, 13.5]:
        attribs = {"WIDTH_M": "1.2", "SILL_HEIGHT_M": sill, "HEAD_HEIGHT_M": head}
        ins = msp.add_blockref("WINDOW-STD", (0, y_off + wy_rel),
                                dxfattribs={"layer": "A-WINDOW", "rotation": 90})
        ins.add_auto_attribs(attribs)

    # ── Doors ────────────────────────────────────────────────────────
    unit_doors = [
        (1.0, 7, 0),     # Unit A from corridor
        (3.0, 9, 180),   # Unit B from corridor
        (7.0, 7, 0),     # Unit E
        (7.0, 9, 180),   # Unit F
        (16.0, 7, 0),    # Unit G
        (16.0, 9, 180),  # Unit H
        (20.0, 7, 0),    # Unit C
        (20.0, 9, 180),  # Unit D
    ]
    for dx, dy_rel, rot in unit_doors:
        attribs = {"WIDTH_M": "0.9", "HEAD_HEIGHT_M": "2.1", "SWING": "inward"}
        ins = msp.add_blockref("DOOR-SINGLE", (dx, y_off + dy_rel),
                                dxfattribs={"layer": "A-DOOR", "rotation": rot})
        ins.add_auto_attribs(attribs)

    # ── Balconies (south facade, alternating floors) ─────────────────
    if floor_num % 2 == 0:
        # Unit A balcony
        bal = [(0, -1.2), (4.5, -1.2), (4.5, 0), (0, 0)]
        offset_bal = [(p[0], p[1] + y_off) for p in bal]
        msp.add_lwpolyline(offset_bal, close=True, dxfattribs={"layer": "A-BALCONY"})
        add_room(msp, bal, "Balcony A", "balcony", 4.5 * 1.2, y_off)
        # Unit C balcony
        bal = [(18, -1.2), (W, -1.2), (W, 0), (18, 0)]
        offset_bal = [(p[0], p[1] + y_off) for p in bal]
        msp.add_lwpolyline(offset_bal, close=True, dxfattribs={"layer": "A-BALCONY"})
        add_room(msp, bal, "Balcony C", "balcony", (W - 18) * 1.2, y_off)

    # North facade balconies (odd floors)
    if floor_num % 2 == 1:
        bal = [(0, D), (5, D), (5, D + 1.2), (0, D + 1.2)]
        offset_bal = [(p[0], p[1] + y_off) for p in bal]
        msp.add_lwpolyline(offset_bal, close=True, dxfattribs={"layer": "A-BALCONY"})
        add_room(msp, bal, "Balcony B", "balcony", 5 * 1.2, y_off)
        bal = [(18, D), (W, D), (W, D + 1.2), (18, D + 1.2)]
        offset_bal = [(p[0], p[1] + y_off) for p in bal]
        msp.add_lwpolyline(offset_bal, close=True, dxfattribs={"layer": "A-BALCONY"})
        add_room(msp, bal, "Balcony D", "balcony", (W - 18) * 1.2, y_off)

    # ── Columns ──────────────────────────────────────────────────────
    for cx_pos in [4.0, 8.0, 16.0, 20.0]:
        for cy_pos in [4.0, 12.0]:
            add_column(msp, cx_pos, y_off + cy_pos)

    # ── Ceiling height ───────────────────────────────────────────────
    ceiling_h = "3.0" if floor_num <= 2 else "2.7"
    msp.add_text(
        f"CLG {ceiling_h}m", height=0.3,
        dxfattribs={"layer": "A-ANNO-CLG"}
    ).set_placement((W / 2, y_off + D + 1.5), align=TextEntityAlignment.MIDDLE_CENTER)

    # ── Floor label ──────────────────────────────────────────────────
    label = f"FLOOR {floor_num} — RESIDENTIAL"
    if floor_num == NUM_FLOORS:
        label = f"FLOOR {floor_num} — PENTHOUSE"
    msp.add_text(
        label, height=0.4,
        dxfattribs={"layer": "A-ANNO-FLOR"}
    ).set_placement((W / 2, y_off - 1.5), align=TextEntityAlignment.MIDDLE_CENTER)


def main():
    doc = ezdxf.new("R2013")
    doc.units = units.M
    msp = doc.modelspace()

    # Create layers
    for name, props in LAYERS.items():
        doc.layers.add(name, color=props["color"])

    # Create blocks
    create_door_block(doc)
    create_window_block(doc)
    create_storefront_block(doc)

    # Draw each floor
    y = 0.0
    # Ground floor
    draw_ground_floor(msp, doc, y)
    y += FLOOR_SPACING_Y

    # Floors 2-6
    for floor_num in range(2, NUM_FLOORS + 1):
        draw_typical_residential_floor(msp, doc, floor_num, y)
        y += FLOOR_SPACING_Y

    # Title block
    msp.add_text(
        "SAMPLE MIXED-USE MIDRISE — 6 STOREYS",
        height=0.6,
        dxfattribs={"layer": "A-ANNO-FLOR"}
    ).set_placement((BUILDING_W / 2, -4.0), align=TextEntityAlignment.MIDDLE_CENTER)
    msp.add_text(
        "24m x 16m footprint | Ground: retail | Floors 2-6: residential",
        height=0.3,
        dxfattribs={"layer": "A-ANNO-FLOR"}
    ).set_placement((BUILDING_W / 2, -5.0), align=TextEntityAlignment.MIDDLE_CENTER)

    # Save
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(os.path.dirname(out_dir), "sample_building.dxf")
    doc.saveas(out_path)
    print(f"Saved: {out_path}")
    print(f"  Floors: {NUM_FLOORS}")
    print(f"  Footprint: {BUILDING_W}m x {BUILDING_D}m")
    print(f"  Layers: {len(LAYERS)}")
    print(f"  Blocks: DOOR-SINGLE, WINDOW-STD, WINDOW-STOREFRONT")
    print(f"  Features: ceiling heights, sill/head heights, balconies, structural walls, columns")


if __name__ == "__main__":
    main()
