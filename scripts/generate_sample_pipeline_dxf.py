"""Generate a sample water main DXF for testing the pipeline parser.

Produces sample_pipeline.dxf with:
- 10 pipe segments in a grid network
- 6 manholes at junctions
- 3 gate valves
- 2 fire hydrants
- Proper layers and block attributes
"""

import math
import sys
from pathlib import Path

try:
    import ezdxf
    from ezdxf.enums import TextEntityAlignment
except ImportError:
    print("Install ezdxf: pip install ezdxf")
    sys.exit(1)


def create_block_with_attrib(doc, block_name: str, attrib_defs: list[dict]):
    """Create a reusable block with attribute definitions."""
    if block_name in doc.blocks:
        return doc.blocks[block_name]
    blk = doc.blocks.new(block_name)
    blk.add_circle((0, 0), radius=0.3)
    for attdef in attrib_defs:
        blk.add_attdef(
            tag=attdef["tag"],
            insert=attdef.get("insert", (0.4, 0)),
            dxfattribs={"height": 0.4, "layer": block_name},
        )
    return blk


def add_block_insert(msp, block_name: str, position: tuple, attrib_values: dict, layer: str):
    """Insert a block reference with attribute values."""
    blkref = msp.add_blockref(block_name, position, dxfattribs={"layer": layer})
    blkref.add_auto_attribs(attrib_values)
    return blkref


def main():
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # ── Define layers ──
    layers = {
        "WATER-MAIN":    {"color": 5},   # blue
        "WATER-MH":      {"color": 3},   # green
        "WATER-VALVE":   {"color": 1},   # red
        "WATER-HYDRANT": {"color": 4},   # cyan
        "ANNOTATIONS":   {"color": 7},   # white
    }
    for name, props in layers.items():
        doc.layers.add(name, dxfattribs={"color": props["color"]})

    # ── Define blocks ──
    # Manhole block with attributes
    create_block_with_attrib(doc, "MANHOLE", [
        {"tag": "ID",     "insert": (0.4, 0.4)},
        {"tag": "DEPTH",  "insert": (0.4, 0.0)},
        {"tag": "RIM",    "insert": (0.4, -0.4)},
        {"tag": "INVERT", "insert": (0.4, -0.8)},
    ])

    # Valve block
    valve_blk = doc.blocks.new("GATE_VALVE")
    valve_blk.add_lwpolyline(
        [(-0.3, -0.3), (0.3, -0.3), (0.3, 0.3), (-0.3, 0.3)], close=True
    )
    valve_blk.add_line((0, -0.3), (0, 0.3))
    valve_blk.add_attdef("DIAMETER", insert=(0.4, 0), dxfattribs={"height": 0.3})

    # Hydrant block
    hydrant_blk = doc.blocks.new("FIRE_HYDRANT")
    hydrant_blk.add_circle((0, 0), radius=0.4)
    hydrant_blk.add_circle((0, 0), radius=0.2)

    # ── Network geometry ──
    # Grid layout: 3 columns × 3 rows of junctions, spacing 20m
    #
    #  MH1--P1--MH2--P2--MH3
    #   |         |         |
    #  P3        P4        P5
    #   |         |         |
    #  MH4--P6--MH5--P7--MH6
    #               |
    #              P8
    #               |
    #             DEAD-END

    mh_positions = {
        "MH-01": (0,   40),
        "MH-02": (20,  40),
        "MH-03": (40,  40),
        "MH-04": (0,   20),
        "MH-05": (20,  20),
        "MH-06": (40,  20),
    }

    pipes = [
        # Horizontal top row
        ("MH-01", "MH-02", 200),
        ("MH-02", "MH-03", 200),
        # Verticals
        ("MH-01", "MH-04", 200),
        ("MH-02", "MH-05", 150),
        ("MH-03", "MH-06", 150),
        # Horizontal bottom row
        ("MH-04", "MH-05", 200),
        ("MH-05", "MH-06", 200),
        # Dead-end lateral south from MH-05
        ("MH-05", "DEAD", 100),
    ]
    dead_pos = (20, 5)

    # ── Draw pipes as LINEs on WATER-MAIN ──
    all_positions = dict(mh_positions)
    all_positions["DEAD"] = dead_pos

    for (from_id, to_id, dia) in pipes:
        p1 = all_positions[from_id]
        p2 = all_positions[to_id]
        msp.add_line(p1, p2, dxfattribs={"layer": "WATER-MAIN"})
        # Add diameter label at midpoint
        mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        msp.add_text(
            f"DI {dia}mm",
            dxfattribs={"layer": "ANNOTATIONS", "height": 0.8, "insert": mid},
        )

    # ── Place manholes ──
    for mh_id, pos in mh_positions.items():
        add_block_insert(msp, "MANHOLE", pos, {
            "ID": mh_id,
            "DEPTH": "2.5",
            "RIM": "100.00",
            "INVERT": "97.50",
        }, "WATER-MH")

    # ── Place valves ──
    valve_positions = [
        ((10, 40), 200),
        ((30, 40), 200),
        ((20, 30), 150),
    ]
    for pos, dia in valve_positions:
        add_block_insert(msp, "GATE_VALVE", pos, {"DIAMETER": str(dia)}, "WATER-VALVE")

    # ── Place hydrants ──
    hydrant_positions = [(5, 40), (35, 20)]
    for pos in hydrant_positions:
        msp.add_blockref("FIRE_HYDRANT", pos, dxfattribs={"layer": "WATER-HYDRANT"})

    # ── Title block annotation ──
    msp.add_text(
        "SAMPLE WATER MAIN NETWORK",
        dxfattribs={"layer": "ANNOTATIONS", "height": 2.0, "insert": (20, -5)},
    )
    msp.add_text(
        "Materials: DI | Scale 1:500",
        dxfattribs={"layer": "ANNOTATIONS", "height": 1.0, "insert": (20, -8)},
    )

    # ── Save ──
    output = Path("sample_pipeline.dxf")
    doc.saveas(str(output))
    print(f"Saved: {output.resolve()}")
    print(f"  Pipes: {len(pipes)}")
    print(f"  Manholes: {len(mh_positions)}")
    print(f"  Valves: {len(valve_positions)}")
    print(f"  Hydrants: {len(hydrant_positions)}")


if __name__ == "__main__":
    main()
