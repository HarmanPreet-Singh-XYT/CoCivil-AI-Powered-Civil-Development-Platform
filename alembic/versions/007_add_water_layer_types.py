"""Add water system layer types to dataset_layers check constraint.

Revision ID: 007
Revises: 006
Create Date: 2026-03-10
"""
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None

NEW_LAYER_TYPES = [
    "zoning",
    "height_overlay",
    "setback_overlay",
    "transit",
    "heritage",
    "floodplain",
    "environmental",
    "road",
    "amenity",
    "demographic",
    "building_mass",
    "other",
    # Water system layers
    "water_main_distribution",
    "water_main_transmission",
    "water_hydrant",
    "water_valve",
    "water_fitting",
    "parks_drinking_water",
]


def upgrade() -> None:
    # Drop the old constraint and recreate with expanded type list
    op.drop_constraint(
        "chk_dataset_layers_layer_type",
        "dataset_layers",
        type_="check",
    )
    types_sql = ", ".join(f"'{t}'::text" for t in NEW_LAYER_TYPES)
    op.create_check_constraint(
        "chk_dataset_layers_layer_type",
        "dataset_layers",
        f"layer_type = ANY (ARRAY[{types_sql}])",
    )


def downgrade() -> None:
    op.drop_constraint(
        "chk_dataset_layers_layer_type",
        "dataset_layers",
        type_="check",
    )
    original_types = [
        "zoning", "height_overlay", "setback_overlay", "transit",
        "heritage", "floodplain", "environmental", "road", "amenity",
        "demographic", "building_mass", "other",
    ]
    types_sql = ", ".join(f"'{t}'::text" for t in original_types)
    op.create_check_constraint(
        "chk_dataset_layers_layer_type",
        "dataset_layers",
        f"layer_type = ANY (ARRAY[{types_sql}])",
    )