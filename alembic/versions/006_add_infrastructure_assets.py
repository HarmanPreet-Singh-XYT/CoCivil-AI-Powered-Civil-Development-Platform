"""Add infrastructure asset tables and project.asset_type column.

Revision ID: 006
Revises: 005
Create Date: 2026-03-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add asset_type column to projects
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("projects")}
    if "asset_type" not in columns:
        op.add_column(
            "projects",
            sa.Column("asset_type", sa.String(50), nullable=False, server_default="building"),
        )

    # Create pipeline_assets table
    op.create_table(
        "pipeline_assets",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("jurisdiction_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("jurisdictions.id"), nullable=False, index=True),
        sa.Column("source_snapshot_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("source_snapshots.id"), nullable=True, index=True),
        sa.Column("asset_id", sa.String, nullable=False, index=True),
        sa.Column("pipe_type", sa.String(50), nullable=False),
        sa.Column("material", sa.String(50), nullable=True),
        sa.Column("diameter_mm", sa.Float, nullable=True),
        sa.Column("install_year", sa.Integer, nullable=True),
        sa.Column("depth_m", sa.Float, nullable=True),
        sa.Column("slope_pct", sa.Float, nullable=True),
        # geom column added via PostGIS function below
        sa.Column("attributes_json", sa.dialects.postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Add PostGIS geometry column
    op.execute("SELECT AddGeometryColumn('pipeline_assets', 'geom', 4326, 'LINESTRING', 2)")

    # Create bridge_assets table
    op.create_table(
        "bridge_assets",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("jurisdiction_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("jurisdictions.id"), nullable=False, index=True),
        sa.Column("source_snapshot_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("source_snapshots.id"), nullable=True, index=True),
        sa.Column("asset_id", sa.String, nullable=False, index=True),
        sa.Column("bridge_type", sa.String(50), nullable=False),
        sa.Column("structure_type", sa.String(50), nullable=True),
        sa.Column("span_m", sa.Float, nullable=True),
        sa.Column("deck_width_m", sa.Float, nullable=True),
        sa.Column("clearance_m", sa.Float, nullable=True),
        sa.Column("year_built", sa.Integer, nullable=True),
        sa.Column("condition_rating", sa.String(50), nullable=True),
        sa.Column("road_name", sa.String, nullable=True),
        sa.Column("crossing_name", sa.String, nullable=True),
        sa.Column("attributes_json", sa.dialects.postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Add PostGIS geometry columns properly for bridge_assets
    op.execute("SELECT AddGeometryColumn('bridge_assets', 'geom', 4326, 'POINT', 2)")
    op.execute("SELECT AddGeometryColumn('bridge_assets', 'geom_line', 4326, 'LINESTRING', 2)")


def downgrade() -> None:
    op.drop_table("bridge_assets")
    op.drop_table("pipeline_assets")
    op.drop_column("projects", "asset_type")
