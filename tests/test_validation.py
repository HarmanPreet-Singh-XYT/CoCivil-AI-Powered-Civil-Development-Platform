from app.services.validation import (
    validate_finance_record,
    validate_policy_rule,
    validate_precedent_record,
    validate_source_metadata,
)


def test_validate_source_metadata_requires_publisher_and_known_license():
    summary = validate_source_metadata(
        {
            "source_url": "https://example.com/source.csv",
            "license_status": "unknown",
            "export_allowed": False,
            "derived_export_allowed": False,
        }
    )

    codes = {issue["code"] for issue in summary.issues}
    assert summary.ok is False
    assert {"missing_publisher", "unknown_license_status"} <= codes


def test_validate_policy_rule_routes_low_confidence_to_review():
    summary = validate_policy_rule(
        {
            "section_ref": "40.10.40.10",
            "confidence": 0.55,
            "normalized_json": {
                "rule_type": "max_height",
                "effective_date": "2026-01-01",
            },
        }
    )

    assert summary.ok is True
    assert summary.non_blocking_issue_count == 1
    assert summary.issues[0]["code"] == "low_confidence"


def test_validate_precedent_record_requires_location_linkage():
    summary = validate_precedent_record(
        {
            "app_number": "23 100000 STE 01 OZ",
            "status": "active",
            "license_status": "restricted",
        }
    )

    codes = {issue["code"] for issue in summary.issues}
    assert summary.ok is False
    assert "missing_location_linkage" in codes


def test_validate_finance_record_requires_unit_basis_and_geography():
    summary = validate_finance_record(
        {
            "effective_date": "2026-01-01",
            "source": "internal_open_data",
            "license_status": "open",
            "attributes_json": {},
        }
    )

    codes = {issue["code"] for issue in summary.issues}
    assert summary.ok is False
    assert {"missing_unit_basis", "missing_geography"} <= codes
