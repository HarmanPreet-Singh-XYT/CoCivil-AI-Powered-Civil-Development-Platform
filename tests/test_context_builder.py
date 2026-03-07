"""Tests for the document context builder."""

from app.services.compliance_engine import check_compliance
from app.services.submission.context_builder import build_document_context
from app.services.zoning_parser import get_zone_standards, parse_zone_string
from app.services.zoning_service import ZoningAnalysis
from app.data.toronto_zoning import BICYCLE_PARKING, PARKING_STANDARDS, AMENITY_SPACE


def _make_zoning(zone_string: str = "CR 3.0") -> ZoningAnalysis:
    components = parse_zone_string(zone_string)
    standards = get_zone_standards(components)
    return ZoningAnalysis(
        parcel_id="test-parcel",
        address="123 Test St",
        zone_string=zone_string,
        components=components,
        standards=standards,
        parking_policy_area="PA3",
        parking_standards=dict(PARKING_STANDARDS["PA3"]),
        bicycle_parking=dict(BICYCLE_PARKING),
        amenity_space=dict(AMENITY_SPACE),
    )


def _make_massing() -> dict:
    return {
        "typology": "midrise",
        "lot_area_m2": 2000.0,
        "buildable_floorplate_m2": 900.0,
        "storeys": 8,
        "height_m": 25.0,
        "estimated_gfa_m2": 5000.0,
        "estimated_gla_m2": 4100.0,
        "estimated_fsi": 2.5,
        "lot_coverage_pct": 0.45,
        "assumptions_used": {"policy_geometry_defaults": {"stepback_m": 3.0}},
    }


def _make_layout() -> dict:
    return {
        "total_units": 60,
        "parking_required": 30.0,
        "amenity_required_m2": 120.0,
        "available_area_m2": 4100.0,
        "allocated_area_m2": 3738.0,
        "allocations": [
            {"name": "studio", "count": 9, "typical_area_m2": 40.0, "allocated_area_m2": 360.0, "is_accessible": False},
            {"name": "one_bed", "count": 24, "typical_area_m2": 52.0, "allocated_area_m2": 1248.0, "is_accessible": False},
        ],
    }


def _make_finance() -> dict:
    return {
        "tenure": "rental",
        "total_revenue": 5000000.0,
        "hard_cost": 24000000.0,
        "soft_cost": 5280000.0,
        "contingency_cost": 1756800.0,
        "total_cost": 31036800.0,
        "opex": 1400000.0,
        "noi": 3600000.0,
        "valuation": 80000000.0,
        "residual_land_value": 48963200.0,
        "assumptions_used": {
            "cost_assumptions": {"hard_cost_per_m2": 4800.0, "soft_cost_pct": 0.22},
            "valuation": {"cap_rate": 0.045},
            "financing": {"loan_to_cost_pct": 0.65, "interest_rate": 0.055},
        },
    }


class TestBuildDocumentContext:
    """Test that context builder fills all template placeholders."""

    def test_all_template_keys_present(self):
        """Every key used in templates should be present in context."""
        from app.services.submission.templates import DOCUMENT_TEMPLATES

        zoning = _make_zoning()
        massing = _make_massing()
        layout = _make_layout()
        finance = _make_finance()
        compliance = check_compliance(zoning, massing, layout)

        context = build_document_context(
            parcel_data={"address": "123 Test St", "zone_code": "CR 3.0",
                        "lot_area_m2": 2000.0, "lot_frontage_m": 30.0,
                        "lot_depth_m": 66.7, "current_use": "parking lot"},
            zoning=zoning,
            massing=massing,
            layout=layout,
            finance=finance,
            compliance=compliance,
            precedents=[],
            policy_stack=None,
            overlays=None,
            project_name="Test Project",
            organization_name="Test Org",
        )

        # Check that all template placeholders can be filled
        for doc_type, template in DOCUMENT_TEMPLATES.items():
            user_prompt = template["user_prompt_template"]
            # Use SafeDict-like approach to find placeholders
            import re
            placeholders = re.findall(r"\{(\w+)\}", user_prompt)
            for placeholder in placeholders:
                assert placeholder in context, (
                    f"Template '{doc_type}' requires '{placeholder}' but it's "
                    f"missing from context"
                )

    def test_missing_data_marked_not_available(self):
        """Missing data should be explicitly marked, never silently omitted."""
        context = build_document_context(
            parcel_data=None,
            zoning=None,
            massing=None,
            layout=None,
            finance=None,
            compliance=None,
            precedents=None,
            policy_stack=None,
            overlays=None,
        )

        not_available_marker = "[NOT AVAILABLE"
        # Key fields should have the marker
        assert not_available_marker in context["address"]
        assert not_available_marker in context["zoning_code"]

    def test_compliance_summary_is_deterministic(self):
        """Compliance summary should contain the deterministic matrix."""
        zoning = _make_zoning()
        massing = _make_massing()
        layout = _make_layout()
        compliance = check_compliance(zoning, massing, layout)

        context = build_document_context(
            parcel_data={"address": "123 Test St"},
            zoning=zoning,
            massing=massing,
            layout=layout,
            finance=None,
            compliance=compliance,
            precedents=None,
            policy_stack=None,
            overlays=None,
        )

        # Should contain the markdown table
        assert "| Provision |" in context["compliance_summary"]
        assert "By-law Section" in context["compliance_summary"]

    def test_financial_data_formatted(self):
        """Financial values should be formatted with dollar signs and commas."""
        finance = _make_finance()
        context = build_document_context(
            parcel_data=None,
            zoning=None,
            massing=None,
            layout=None,
            finance=finance,
            compliance=None,
            precedents=None,
            policy_stack=None,
            overlays=None,
        )

        assert "$" in context["financial_results"]

    def test_precedent_data_formatted(self):
        """Precedent data should be formatted correctly."""
        precedents = [
            {
                "address": "456 Nearby St",
                "app_number": "21-123456",
                "decision": "approved",
                "proposed_height_m": 25.0,
                "proposed_units": 50,
                "distance_m": 300.0,
                "score": 0.82,
            }
        ]
        context = build_document_context(
            parcel_data=None,
            zoning=None,
            massing=None,
            layout=None,
            finance=None,
            compliance=None,
            precedents=precedents,
            policy_stack=None,
            overlays=None,
        )

        assert "456 Nearby St" in context["precedent_results"]
        assert "21-123456" in context["precedent_results"]
