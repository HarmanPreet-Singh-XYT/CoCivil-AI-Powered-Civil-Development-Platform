import uuid

from app.services.governance import build_manifest_hash, evaluate_export_controls


def test_build_manifest_hash_is_stable_for_item_order():
    jurisdiction_id = uuid.uuid4()
    items_a = [
        {"source_snapshot_id": uuid.uuid4(), "snapshot_role": "policy", "is_required": True},
        {"source_snapshot_id": uuid.uuid4(), "snapshot_role": "parcel", "is_required": True},
    ]
    items_b = list(reversed(items_a))

    assert build_manifest_hash(jurisdiction_id, items_a) == build_manifest_hash(jurisdiction_id, items_b)


def test_export_controls_block_unknown_license():
    decision = evaluate_export_controls(
        [
            {
                "source": "market_comparable",
                "license_status": "unknown",
                "internal_storage_allowed": True,
                "export_allowed": True,
            }
        ]
    )

    assert decision.decision == "block"
    assert decision.blocked_reason == "unknown_license_status"


def test_export_controls_redact_aggregate_only_sources():
    decision = evaluate_export_controls(
        [
            {
                "source": "application_document",
                "license_status": "restricted",
                "internal_storage_allowed": True,
                "export_allowed": False,
                "derived_export_allowed": True,
                "aggregation_required": True,
            }
        ]
    )

    assert decision.decision == "redact"
    assert decision.governance_status == "redacted"


def test_export_controls_allow_open_sources():
    decision = evaluate_export_controls(
        [
            {
                "source": "dataset_layer",
                "license_status": "open",
                "internal_storage_allowed": True,
                "export_allowed": True,
                "derived_export_allowed": True,
                "aggregation_required": False,
            }
        ]
    )

    assert decision.decision == "allow"
    assert decision.governance_status == "approved"
