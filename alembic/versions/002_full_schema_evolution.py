"""Consolidated schema evolution: governance, data spine, overlay runtime, thin-slice.

Merges the previously conflicting 002/003 migrations into a single linear step.

Revision ID: 002
Revises: 001
Create Date: 2026-03-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # NEW TABLES — governance backbone
    # =========================================================================

    op.create_table(
        "snapshot_manifests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("jurisdiction_id", UUID(as_uuid=True), sa.ForeignKey("jurisdictions.id"), nullable=False),
        sa.Column("manifest_hash", sa.Text(), nullable=False),
        sa.Column("parser_versions_json", JSON(), nullable=False, server_default="{}"),
        sa.Column("model_versions_json", JSON(), nullable=False, server_default="{}"),
        sa.Column("notes_json", JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("manifest_hash", name="uq_snapshot_manifests_manifest_hash"),
    )
    op.create_index("idx_snapshot_manifests_jurisdiction", "snapshot_manifests", ["jurisdiction_id"])
    op.create_index("idx_snapshot_manifests_hash", "snapshot_manifests", ["manifest_hash"])

    op.create_table(
        "snapshot_manifest_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("manifest_id", UUID(as_uuid=True), sa.ForeignKey("snapshot_manifests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_snapshot_id", UUID(as_uuid=True), sa.ForeignKey("source_snapshots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_role", sa.Text(), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("manifest_id", "source_snapshot_id", "snapshot_role", name="uq_manifest_snapshot_role"),
    )
    op.create_index("idx_snapshot_manifest_items_manifest", "snapshot_manifest_items", ["manifest_id"])
    op.create_index("idx_snapshot_manifest_items_snapshot", "snapshot_manifest_items", ["source_snapshot_id"])

    op.create_table(
        "parse_artifacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("source_family", sa.Text(), nullable=False),
        sa.Column("source_entity_type", sa.Text(), nullable=False),
        sa.Column("source_entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("artifact_type", sa.Text(), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("file_hash", sa.Text(), nullable=True),
        sa.Column("content_type", sa.Text(), nullable=True),
        sa.Column("producer_version", sa.Text(), nullable=True),
        sa.Column("validation_summary_json", JSON(), nullable=False, server_default="{}"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("parent_artifact_id", UUID(as_uuid=True), sa.ForeignKey("parse_artifacts.id"), nullable=True),
        sa.Column("ingestion_job_id", UUID(as_uuid=True), sa.ForeignKey("ingestion_jobs.id"), nullable=True),
        sa.Column("source_snapshot_id", UUID(as_uuid=True), sa.ForeignKey("source_snapshots.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_parse_artifacts_entity", "parse_artifacts", ["source_entity_type", "source_entity_id"])

    op.create_table(
        "review_queue_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("queue_type", sa.Text(), nullable=False),
        sa.Column("reason_code", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("artifact_id", UUID(as_uuid=True), sa.ForeignKey("parse_artifacts.id"), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("priority", sa.Text(), nullable=False, server_default="normal"),
        sa.Column("assigned_to", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_code", sa.Text(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("decision_json", JSON(), nullable=False, server_default="{}"),
    )
    op.create_index("idx_review_queue_type", "review_queue_items", ["queue_type"])
    op.create_index("idx_review_queue_entity", "review_queue_items", ["entity_type", "entity_id"])

    op.create_table(
        "refresh_schedules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("source_family", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("cadence", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner", sa.Text(), nullable=True),
        sa.Column("failure_policy", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_refresh_schedules_family", "refresh_schedules", ["source_family"])

    op.create_table(
        "policy_review_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("policy_clause_id", UUID(as_uuid=True), sa.ForeignKey("policy_clauses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("review_reason", sa.Text(), nullable=False),
        sa.Column("assigned_to", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolution_json", JSON(), nullable=False, server_default="{}"),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.execute(
        "ALTER TABLE policy_review_items ADD CONSTRAINT chk_policy_review_items_status "
        "CHECK (status IN ('pending', 'in_review', 'approved', 'rejected'))"
    )
    op.create_index("idx_policy_review_clause", "policy_review_items", ["policy_clause_id"])
    op.create_index("idx_policy_review_status", "policy_review_items", ["status"])

    # =========================================================================
    # NEW TABLE — analysis_snapshot_manifests (overlay runtime)
    # =========================================================================

    op.create_table(
        "analysis_snapshot_manifests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("scenario_run_id", UUID(as_uuid=True), sa.ForeignKey("scenario_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parcel_snapshot_id", UUID(as_uuid=True), sa.ForeignKey("source_snapshots.id"), nullable=True),
        sa.Column("policy_snapshot_id", UUID(as_uuid=True), sa.ForeignKey("source_snapshots.id"), nullable=True),
        sa.Column("overlay_snapshot_id", UUID(as_uuid=True), sa.ForeignKey("source_snapshots.id"), nullable=True),
        sa.Column("precedent_snapshot_id", UUID(as_uuid=True), sa.ForeignKey("source_snapshots.id"), nullable=True),
        sa.Column("market_snapshot_id", UUID(as_uuid=True), sa.ForeignKey("source_snapshots.id"), nullable=True),
        sa.Column("model_versions_json", JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("scenario_run_id", name="uq_analysis_snapshot_manifests_scenario"),
    )
    op.create_index("idx_analysis_snapshot_manifests_scenario", "analysis_snapshot_manifests", ["scenario_run_id"])

    # =========================================================================
    # NEW TABLES — data spine (track 1-2)
    # =========================================================================

    op.create_table(
        "parcel_addresses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("parcel_id", UUID(as_uuid=True), sa.ForeignKey("parcels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_snapshot_id", UUID(as_uuid=True), sa.ForeignKey("source_snapshots.id"), nullable=False),
        sa.Column("source_record_id", sa.Text(), nullable=True),
        sa.Column("address_text", sa.Text(), nullable=False),
        sa.Column("match_method", sa.Text(), nullable=False),
        sa.Column("match_confidence", sa.Float(), nullable=True),
        sa.Column("is_canonical", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("source_snapshot_id", "source_record_id", name="uq_parcel_addresses_snapshot_source_record"),
        sa.UniqueConstraint("parcel_id", "source_snapshot_id", "address_text", name="uq_parcel_addresses_parcel_snapshot_address"),
    )
    op.execute("ALTER TABLE parcel_addresses ADD COLUMN address_point_geom geometry(Point, 4326)")
    op.create_index("idx_parcel_addresses_parcel", "parcel_addresses", ["parcel_id"])
    op.create_index("idx_parcel_addresses_snapshot", "parcel_addresses", ["source_snapshot_id"])
    op.execute("CREATE INDEX idx_parcel_addresses_geom ON parcel_addresses USING GIST (address_point_geom)")
    op.execute(
        "ALTER TABLE parcel_addresses ADD CONSTRAINT chk_parcel_addresses_match_method "
        "CHECK (match_method IN ('source_key', 'spatial_contains', 'manual_review'))"
    )
    op.execute(
        "ALTER TABLE parcel_addresses ADD CONSTRAINT chk_parcel_addresses_match_confidence "
        "CHECK (match_confidence IS NULL OR (match_confidence >= 0.0 AND match_confidence <= 1.0))"
    )

    op.create_table(
        "parcel_zoning_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("parcel_id", UUID(as_uuid=True), sa.ForeignKey("parcels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dataset_feature_id", UUID(as_uuid=True), sa.ForeignKey("dataset_features.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_snapshot_id", UUID(as_uuid=True), sa.ForeignKey("source_snapshots.id"), nullable=False),
        sa.Column("zone_code", sa.Text(), nullable=False),
        sa.Column("overlap_area_m2", sa.Float(), nullable=True),
        sa.Column("assignment_method", sa.Text(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("parcel_id", "dataset_feature_id", "source_snapshot_id", name="uq_parcel_zoning_assignments_parcel_feature_snapshot"),
    )
    op.create_index("idx_parcel_zoning_assignments_parcel", "parcel_zoning_assignments", ["parcel_id"])
    op.create_index("idx_parcel_zoning_assignments_snapshot", "parcel_zoning_assignments", ["source_snapshot_id"])
    op.execute(
        "ALTER TABLE parcel_zoning_assignments ADD CONSTRAINT chk_parcel_zoning_assignments_method "
        "CHECK (assignment_method IN ('max_overlap', 'centroid_fallback', 'manual_review'))"
    )

    # =========================================================================
    # NEW TABLES — thin-slice runtime (track 5-6)
    # =========================================================================

    op.create_table(
        "building_permits",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("jurisdiction_id", UUID(as_uuid=True), sa.ForeignKey("jurisdictions.id"), nullable=False),
        sa.Column("development_application_id", UUID(as_uuid=True), sa.ForeignKey("development_applications.id"), nullable=True),
        sa.Column("parcel_id", UUID(as_uuid=True), sa.ForeignKey("parcels.id"), nullable=True),
        sa.Column("permit_number", sa.Text(), nullable=False),
        sa.Column("permit_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("source_system", sa.Text(), nullable=False, server_default="unknown"),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("application_date", sa.Date(), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("closed_date", sa.Date(), nullable=True),
        sa.Column("metadata_json", JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("jurisdiction_id", "permit_number", name="uq_building_permits_jurisdiction_number"),
    )
    op.execute("ALTER TABLE building_permits ADD COLUMN geom geometry(Point, 4326)")
    op.create_index("idx_building_permits_jurisdiction", "building_permits", ["jurisdiction_id"])
    op.create_index("idx_building_permits_application", "building_permits", ["development_application_id"])
    op.create_index("idx_building_permits_parcel", "building_permits", ["parcel_id"])
    op.create_index("idx_building_permits_number", "building_permits", ["permit_number"])
    op.execute("CREATE INDEX idx_building_permits_geom ON building_permits USING GIST (geom)")

    op.create_table(
        "precedent_matches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("precedent_search_id", UUID(as_uuid=True), sa.ForeignKey("precedent_searches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("development_application_id", UUID(as_uuid=True), sa.ForeignKey("development_applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("distance_m", sa.Float(), nullable=True),
        sa.Column("matched_permit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score_breakdown_json", JSON(), nullable=False, server_default="{}"),
        sa.Column("summary_json", JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("precedent_search_id", "development_application_id", name="uq_precedent_match_search_app"),
    )
    op.create_index("idx_precedent_matches_search", "precedent_matches", ["precedent_search_id"])
    op.create_index("idx_precedent_matches_application", "precedent_matches", ["development_application_id"])

    # =========================================================================
    # ALTER EXISTING TABLES — parcels
    # =========================================================================

    op.add_column("parcels", sa.Column("source_snapshot_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_parcels_source_snapshot_id", "parcels", "source_snapshots", ["source_snapshot_id"], ["id"])
    op.create_index("idx_parcels_source_snapshot", "parcels", ["source_snapshot_id"])
    op.drop_constraint("uq_parcels_jurisdiction_pin", "parcels", type_="unique")
    op.create_unique_constraint("uq_parcels_jurisdiction_pin_snapshot", "parcels", ["jurisdiction_id", "pin", "source_snapshot_id"])

    # =========================================================================
    # ALTER EXISTING TABLES — scenario_runs
    # =========================================================================

    op.add_column("scenario_runs", sa.Column("snapshot_manifest_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_scenario_runs_snapshot_manifest_id", "scenario_runs", "snapshot_manifests", ["snapshot_manifest_id"], ["id"])
    op.create_index("idx_scenario_runs_snapshot_manifest", "scenario_runs", ["snapshot_manifest_id"])

    # =========================================================================
    # ALTER EXISTING TABLES — source_snapshots
    # =========================================================================

    op.add_column("source_snapshots", sa.Column("extractor_version", sa.Text(), nullable=True))
    op.add_column("source_snapshots", sa.Column("extraction_confidence", sa.Float(), nullable=True))
    op.add_column("source_snapshots", sa.Column("validation_summary_json", JSON(), nullable=False, server_default="{}"))

    # =========================================================================
    # ALTER EXISTING TABLES — ingestion_jobs
    # =========================================================================

    op.add_column("ingestion_jobs", sa.Column("source_snapshot_id", UUID(as_uuid=True), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("source_type", sa.Text(), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("parser_version", sa.Text(), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("validation_summary_json", JSON(), nullable=False, server_default="{}"))
    op.create_foreign_key("fk_ingestion_jobs_source_snapshot_id", "ingestion_jobs", "source_snapshots", ["source_snapshot_id"], ["id"])
    op.create_index("idx_ingestion_jobs_source_snapshot", "ingestion_jobs", ["source_snapshot_id"])

    # =========================================================================
    # ALTER EXISTING TABLES — dataset_layers
    # =========================================================================

    op.add_column("dataset_layers", sa.Column("source_snapshot_id", UUID(as_uuid=True), nullable=True))
    op.add_column("dataset_layers", sa.Column("publisher", sa.Text(), nullable=True))
    op.add_column("dataset_layers", sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("dataset_layers", sa.Column("lineage_json", JSON(), nullable=False, server_default="{}"))
    op.add_column("dataset_layers", sa.Column("redistribution_policy", sa.Text(), nullable=True))
    op.add_column("dataset_layers", sa.Column("source_schema_version", sa.Text(), nullable=True))
    op.add_column("dataset_layers", sa.Column("internal_storage_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("dataset_layers", sa.Column("redistribution_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("dataset_layers", sa.Column("export_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("dataset_layers", sa.Column("derived_export_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("dataset_layers", sa.Column("aggregation_required", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("dataset_layers", sa.Column("retention_policy", sa.Text(), nullable=True))
    op.add_column("dataset_layers", sa.Column("license_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("dataset_layers", sa.Column("source_metadata_json", JSON(), nullable=False, server_default="{}"))
    op.create_foreign_key("fk_dataset_layers_source_snapshot_id", "dataset_layers", "source_snapshots", ["source_snapshot_id"], ["id"])
    op.create_index("idx_dataset_layers_source_snapshot", "dataset_layers", ["source_snapshot_id"])
    op.drop_constraint("uq_dataset_layers_jurisdiction_name", "dataset_layers", type_="unique")
    op.create_unique_constraint("uq_dataset_layers_jurisdiction_name_snapshot", "dataset_layers", ["jurisdiction_id", "name", "source_snapshot_id"])
    # Expand layer_type check constraint to include 'zoning'
    op.drop_constraint("chk_dataset_layers_layer_type", "dataset_layers", type_="check")
    op.execute(
        "ALTER TABLE dataset_layers ADD CONSTRAINT chk_dataset_layers_layer_type "
        "CHECK (layer_type IN ('zoning', 'height_overlay', 'setback_overlay', 'transit', 'heritage', "
        "'floodplain', 'environmental', 'road', 'amenity', 'demographic', 'building_mass', 'other'))"
    )

    # =========================================================================
    # ALTER EXISTING TABLES — policy_documents
    # =========================================================================

    op.add_column("policy_documents", sa.Column("publisher", sa.Text(), nullable=True))
    op.add_column("policy_documents", sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("policy_documents", sa.Column("lineage_json", JSON(), nullable=False, server_default="{}"))
    op.add_column("policy_documents", sa.Column("redistribution_policy", sa.Text(), nullable=True))
    op.add_column("policy_documents", sa.Column("source_schema_version", sa.Text(), nullable=True))
    op.add_column("policy_documents", sa.Column("license_status", sa.Text(), nullable=False, server_default="unknown"))
    op.add_column("policy_documents", sa.Column("internal_storage_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("policy_documents", sa.Column("redistribution_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("policy_documents", sa.Column("export_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("policy_documents", sa.Column("derived_export_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("policy_documents", sa.Column("aggregation_required", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("policy_documents", sa.Column("retention_policy", sa.Text(), nullable=True))
    op.add_column("policy_documents", sa.Column("license_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("policy_documents", sa.Column("source_metadata_json", JSON(), nullable=False, server_default="{}"))

    # =========================================================================
    # ALTER EXISTING TABLES — policy_versions
    # =========================================================================

    op.add_column("policy_versions", sa.Column("source_snapshot_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_policy_versions_source_snapshot_id", "policy_versions", "source_snapshots", ["source_snapshot_id"], ["id"])
    op.create_index("idx_policy_versions_source_snapshot", "policy_versions", ["source_snapshot_id"])

    # =========================================================================
    # ALTER EXISTING TABLES — market_comparables
    # =========================================================================

    op.add_column("market_comparables", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column("market_comparables", sa.Column("publisher", sa.Text(), nullable=True))
    op.add_column("market_comparables", sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("market_comparables", sa.Column("source_schema_version", sa.Text(), nullable=True))
    op.add_column("market_comparables", sa.Column("internal_storage_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("market_comparables", sa.Column("redistribution_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("market_comparables", sa.Column("export_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("market_comparables", sa.Column("derived_export_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("market_comparables", sa.Column("aggregation_required", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("market_comparables", sa.Column("retention_policy", sa.Text(), nullable=True))
    op.add_column("market_comparables", sa.Column("license_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("market_comparables", sa.Column("source_metadata_json", JSON(), nullable=False, server_default="{}"))
    op.add_column("market_comparables", sa.Column("lineage_json", JSON(), nullable=False, server_default="{}"))

    # =========================================================================
    # ALTER EXISTING TABLES — financial_runs
    # =========================================================================

    op.alter_column("financial_runs", "assumption_set_id", existing_type=UUID(as_uuid=True), nullable=True)
    op.alter_column("financial_runs", "output_json", existing_type=JSON(), nullable=True)

    # =========================================================================
    # ALTER EXISTING TABLES — entitlement_results
    # =========================================================================

    op.add_column("entitlement_results", sa.Column("snapshot_manifest_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_entitlement_results_snapshot_manifest_id", "entitlement_results", "snapshot_manifests", ["snapshot_manifest_id"], ["id"])
    op.create_index("idx_entitlement_results_snapshot_manifest", "entitlement_results", ["snapshot_manifest_id"])
    op.execute("ALTER TABLE entitlement_results DROP CONSTRAINT IF EXISTS chk_entitlement_compliance")
    op.execute(
        "ALTER TABLE entitlement_results ADD CONSTRAINT chk_entitlement_compliance "
        "CHECK (overall_compliance IN ('pending', 'compliant', 'minor_variance', 'major_variance', "
        "'non_compliant', 'pass', 'review', 'failed'))"
    )

    # =========================================================================
    # ALTER EXISTING TABLES — precedent_searches
    # =========================================================================

    op.add_column("precedent_searches", sa.Column("snapshot_manifest_id", UUID(as_uuid=True), nullable=True))
    op.add_column("precedent_searches", sa.Column("status", sa.Text(), nullable=False, server_default="pending"))
    op.add_column("precedent_searches", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column("precedent_searches", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("precedent_searches", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key("fk_precedent_searches_snapshot_manifest_id", "precedent_searches", "snapshot_manifests", ["snapshot_manifest_id"], ["id"])
    op.create_index("idx_precedent_searches_snapshot_manifest", "precedent_searches", ["snapshot_manifest_id"])
    op.execute(
        "ALTER TABLE precedent_searches ADD CONSTRAINT chk_precedent_searches_status "
        "CHECK (status IN ('pending', 'running', 'completed', 'failed'))"
    )

    # =========================================================================
    # ALTER EXISTING TABLES — development_applications
    # =========================================================================

    op.add_column("development_applications", sa.Column("source_system", sa.Text(), nullable=False, server_default="unknown"))
    op.add_column("development_applications", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column("development_applications", sa.Column("authority", sa.Text(), nullable=True))
    op.add_column("development_applications", sa.Column("stage", sa.Text(), nullable=True))
    op.add_column("development_applications", sa.Column("ward", sa.Text(), nullable=True))
    op.add_column("development_applications", sa.Column("submitted_at", sa.Date(), nullable=True))
    op.add_column("development_applications", sa.Column("document_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("development_applications", sa.Column("publisher", sa.Text(), nullable=True))
    op.add_column("development_applications", sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("development_applications", sa.Column("source_schema_version", sa.Text(), nullable=True))
    op.add_column("development_applications", sa.Column("license_status", sa.Text(), nullable=False, server_default="unknown"))
    op.add_column("development_applications", sa.Column("internal_storage_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("development_applications", sa.Column("redistribution_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("development_applications", sa.Column("export_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("development_applications", sa.Column("derived_export_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("development_applications", sa.Column("aggregation_required", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("development_applications", sa.Column("retention_policy", sa.Text(), nullable=True))
    op.add_column("development_applications", sa.Column("license_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("development_applications", sa.Column("lineage_json", JSON(), nullable=False, server_default="{}"))
    op.add_column("development_applications", sa.Column("source_metadata_json", JSON(), nullable=False, server_default="{}"))
    op.execute("ALTER TABLE development_applications DROP CONSTRAINT IF EXISTS chk_dev_apps_decision")
    op.execute(
        "ALTER TABLE development_applications ADD CONSTRAINT chk_dev_apps_decision "
        "CHECK (decision IN ('approved', 'conditionally approved', 'refused', 'withdrawn', 'pending', 'appealed'))"
    )

    # =========================================================================
    # ALTER EXISTING TABLES — application_documents
    # =========================================================================

    op.add_column("application_documents", sa.Column("document_title", sa.Text(), nullable=True))
    op.add_column("application_documents", sa.Column("document_url", sa.Text(), nullable=True))
    op.add_column("application_documents", sa.Column("download_status", sa.Text(), nullable=False, server_default="pending"))
    op.add_column("application_documents", sa.Column("publisher", sa.Text(), nullable=True))
    op.add_column("application_documents", sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("application_documents", sa.Column("source_schema_version", sa.Text(), nullable=True))
    op.add_column("application_documents", sa.Column("license_status", sa.Text(), nullable=False, server_default="unknown"))
    op.add_column("application_documents", sa.Column("internal_storage_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("application_documents", sa.Column("redistribution_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("application_documents", sa.Column("export_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("application_documents", sa.Column("derived_export_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("application_documents", sa.Column("aggregation_required", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("application_documents", sa.Column("retention_policy", sa.Text(), nullable=True))
    op.add_column("application_documents", sa.Column("license_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("application_documents", sa.Column("source_metadata_json", JSON(), nullable=False, server_default="{}"))
    op.add_column("application_documents", sa.Column("lineage_json", JSON(), nullable=False, server_default="{}"))
    op.add_column("application_documents", sa.Column("citation_json", JSON(), nullable=False, server_default="{}"))
    op.add_column("application_documents", sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("application_documents", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("application_documents", sa.Column("reviewed_by", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_application_documents_reviewed_by", "application_documents", "users", ["reviewed_by"], ["id"])

    # =========================================================================
    # ALTER EXISTING TABLES — rationale_extracts
    # =========================================================================

    op.add_column("rationale_extracts", sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("rationale_extracts", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("rationale_extracts", sa.Column("reviewed_by", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_rationale_extracts_reviewed_by", "rationale_extracts", "users", ["reviewed_by"], ["id"])

    # =========================================================================
    # ALTER EXISTING TABLES — export_jobs
    # =========================================================================

    op.add_column("export_jobs", sa.Column("governance_status", sa.Text(), nullable=False, server_default="pending"))
    op.add_column("export_jobs", sa.Column("blocked_reason", sa.Text(), nullable=True))
    op.add_column("export_jobs", sa.Column("applied_controls_json", JSON(), nullable=False, server_default="{}"))
    op.add_column("export_jobs", sa.Column("error_message", sa.Text(), nullable=True))

    # =========================================================================
    # ALTER EXISTING TABLES — massing_templates
    # =========================================================================

    op.execute("ALTER TABLE massing_templates DROP CONSTRAINT IF EXISTS chk_massing_templates_typology")
    op.execute(
        "ALTER TABLE massing_templates ADD CONSTRAINT chk_massing_templates_typology "
        "CHECK (typology IN ('tower', 'tower_on_podium', 'midrise', 'lowrise', 'townhouse', "
        "'mixed', 'mixed_use_midrise', 'custom'))"
    )


def downgrade() -> None:
    # massing_templates
    op.execute("ALTER TABLE massing_templates DROP CONSTRAINT IF EXISTS chk_massing_templates_typology")
    op.execute(
        "ALTER TABLE massing_templates ADD CONSTRAINT chk_massing_templates_typology "
        "CHECK (typology IN ('tower', 'midrise', 'lowrise', 'townhouse', 'mixed', 'custom'))"
    )

    # export_jobs
    for col in ("error_message", "applied_controls_json", "blocked_reason", "governance_status"):
        op.drop_column("export_jobs", col)

    # rationale_extracts
    op.drop_constraint("fk_rationale_extracts_reviewed_by", "rationale_extracts", type_="foreignkey")
    for col in ("reviewed_by", "reviewed_at", "needs_review"):
        op.drop_column("rationale_extracts", col)

    # application_documents
    op.drop_constraint("fk_application_documents_reviewed_by", "application_documents", type_="foreignkey")
    for col in (
        "reviewed_by", "reviewed_at", "needs_review", "citation_json", "lineage_json",
        "source_metadata_json", "license_expires_at", "retention_policy", "aggregation_required",
        "derived_export_allowed", "export_allowed", "redistribution_allowed", "internal_storage_allowed",
        "license_status", "source_schema_version", "acquired_at", "publisher", "download_status",
        "document_url", "document_title",
    ):
        op.drop_column("application_documents", col)

    # development_applications
    op.execute("ALTER TABLE development_applications DROP CONSTRAINT IF EXISTS chk_dev_apps_decision")
    for col in (
        "source_metadata_json", "lineage_json", "license_expires_at", "retention_policy",
        "aggregation_required", "derived_export_allowed", "export_allowed", "redistribution_allowed",
        "internal_storage_allowed", "license_status", "source_schema_version", "acquired_at",
        "publisher", "document_count", "submitted_at", "ward", "stage", "authority",
        "source_url", "source_system",
    ):
        op.drop_column("development_applications", col)

    # precedent_searches
    op.execute("ALTER TABLE precedent_searches DROP CONSTRAINT IF EXISTS chk_precedent_searches_status")
    op.drop_index("idx_precedent_searches_snapshot_manifest", table_name="precedent_searches")
    op.drop_constraint("fk_precedent_searches_snapshot_manifest_id", "precedent_searches", type_="foreignkey")
    for col in ("completed_at", "started_at", "error_message", "status", "snapshot_manifest_id"):
        op.drop_column("precedent_searches", col)

    # entitlement_results
    op.execute("ALTER TABLE entitlement_results DROP CONSTRAINT IF EXISTS chk_entitlement_compliance")
    op.drop_index("idx_entitlement_results_snapshot_manifest", table_name="entitlement_results")
    op.drop_constraint("fk_entitlement_results_snapshot_manifest_id", "entitlement_results", type_="foreignkey")
    op.drop_column("entitlement_results", "snapshot_manifest_id")

    # financial_runs
    op.alter_column("financial_runs", "output_json", existing_type=JSON(), nullable=False)
    op.alter_column("financial_runs", "assumption_set_id", existing_type=UUID(as_uuid=True), nullable=False)

    # market_comparables
    for col in (
        "lineage_json", "source_metadata_json", "license_expires_at", "retention_policy",
        "aggregation_required", "derived_export_allowed", "export_allowed", "redistribution_allowed",
        "internal_storage_allowed", "source_schema_version", "acquired_at", "publisher", "source_url",
    ):
        op.drop_column("market_comparables", col)

    # policy_versions
    op.drop_index("idx_policy_versions_source_snapshot", table_name="policy_versions")
    op.drop_constraint("fk_policy_versions_source_snapshot_id", "policy_versions", type_="foreignkey")
    op.drop_column("policy_versions", "source_snapshot_id")

    # policy_documents
    for col in (
        "source_metadata_json", "license_expires_at", "retention_policy", "aggregation_required",
        "derived_export_allowed", "export_allowed", "redistribution_allowed", "internal_storage_allowed",
        "license_status", "source_schema_version", "redistribution_policy", "lineage_json",
        "acquired_at", "publisher",
    ):
        op.drop_column("policy_documents", col)

    # dataset_layers
    op.drop_constraint("chk_dataset_layers_layer_type", "dataset_layers", type_="check")
    op.execute(
        "ALTER TABLE dataset_layers ADD CONSTRAINT chk_dataset_layers_layer_type "
        "CHECK (layer_type IN ('transit', 'heritage', 'floodplain', 'environmental', "
        "'road', 'amenity', 'demographic', 'building_mass', 'other'))"
    )
    op.drop_constraint("uq_dataset_layers_jurisdiction_name_snapshot", "dataset_layers", type_="unique")
    op.create_unique_constraint("uq_dataset_layers_jurisdiction_name", "dataset_layers", ["jurisdiction_id", "name"])
    op.drop_index("idx_dataset_layers_source_snapshot", table_name="dataset_layers")
    op.drop_constraint("fk_dataset_layers_source_snapshot_id", "dataset_layers", type_="foreignkey")
    for col in (
        "source_metadata_json", "license_expires_at", "retention_policy", "aggregation_required",
        "derived_export_allowed", "export_allowed", "redistribution_allowed", "internal_storage_allowed",
        "source_schema_version", "redistribution_policy", "lineage_json", "acquired_at",
        "publisher", "source_snapshot_id",
    ):
        op.drop_column("dataset_layers", col)

    # ingestion_jobs
    op.drop_index("idx_ingestion_jobs_source_snapshot", table_name="ingestion_jobs")
    op.drop_constraint("fk_ingestion_jobs_source_snapshot_id", "ingestion_jobs", type_="foreignkey")
    for col in ("validation_summary_json", "parser_version", "source_type", "source_snapshot_id"):
        op.drop_column("ingestion_jobs", col)

    # source_snapshots
    for col in ("validation_summary_json", "extraction_confidence", "extractor_version"):
        op.drop_column("source_snapshots", col)

    # scenario_runs
    op.drop_index("idx_scenario_runs_snapshot_manifest", table_name="scenario_runs")
    op.drop_constraint("fk_scenario_runs_snapshot_manifest_id", "scenario_runs", type_="foreignkey")
    op.drop_column("scenario_runs", "snapshot_manifest_id")

    # parcels
    op.drop_constraint("uq_parcels_jurisdiction_pin_snapshot", "parcels", type_="unique")
    op.create_unique_constraint("uq_parcels_jurisdiction_pin", "parcels", ["jurisdiction_id", "pin"])
    op.drop_index("idx_parcels_source_snapshot", table_name="parcels")
    op.drop_constraint("fk_parcels_source_snapshot_id", "parcels", type_="foreignkey")
    op.drop_column("parcels", "source_snapshot_id")

    # Drop new tables (reverse order)
    op.drop_index("idx_precedent_matches_application", table_name="precedent_matches")
    op.drop_index("idx_precedent_matches_search", table_name="precedent_matches")
    op.drop_table("precedent_matches")

    op.execute("DROP INDEX IF EXISTS idx_building_permits_geom")
    op.drop_index("idx_building_permits_number", table_name="building_permits")
    op.drop_index("idx_building_permits_parcel", table_name="building_permits")
    op.drop_index("idx_building_permits_application", table_name="building_permits")
    op.drop_index("idx_building_permits_jurisdiction", table_name="building_permits")
    op.drop_table("building_permits")

    op.drop_constraint("chk_parcel_zoning_assignments_method", "parcel_zoning_assignments", type_="check")
    op.drop_index("idx_parcel_zoning_assignments_snapshot", table_name="parcel_zoning_assignments")
    op.drop_index("idx_parcel_zoning_assignments_parcel", table_name="parcel_zoning_assignments")
    op.drop_table("parcel_zoning_assignments")

    op.drop_constraint("chk_parcel_addresses_match_confidence", "parcel_addresses", type_="check")
    op.drop_constraint("chk_parcel_addresses_match_method", "parcel_addresses", type_="check")
    op.execute("DROP INDEX IF EXISTS idx_parcel_addresses_geom")
    op.drop_index("idx_parcel_addresses_snapshot", table_name="parcel_addresses")
    op.drop_index("idx_parcel_addresses_parcel", table_name="parcel_addresses")
    op.drop_table("parcel_addresses")

    op.drop_index("idx_analysis_snapshot_manifests_scenario", table_name="analysis_snapshot_manifests")
    op.drop_table("analysis_snapshot_manifests")

    op.drop_index("idx_policy_review_status", table_name="policy_review_items")
    op.drop_index("idx_policy_review_clause", table_name="policy_review_items")
    op.drop_table("policy_review_items")

    op.drop_index("idx_refresh_schedules_family", table_name="refresh_schedules")
    op.drop_table("refresh_schedules")

    op.drop_index("idx_review_queue_entity", table_name="review_queue_items")
    op.drop_index("idx_review_queue_type", table_name="review_queue_items")
    op.drop_table("review_queue_items")

    op.drop_index("idx_parse_artifacts_entity", table_name="parse_artifacts")
    op.drop_table("parse_artifacts")

    op.drop_index("idx_snapshot_manifest_items_snapshot", table_name="snapshot_manifest_items")
    op.drop_index("idx_snapshot_manifest_items_manifest", table_name="snapshot_manifest_items")
    op.drop_table("snapshot_manifest_items")

    op.drop_index("idx_snapshot_manifests_hash", table_name="snapshot_manifests")
    op.drop_index("idx_snapshot_manifests_jurisdiction", table_name="snapshot_manifests")
    op.drop_table("snapshot_manifests")
