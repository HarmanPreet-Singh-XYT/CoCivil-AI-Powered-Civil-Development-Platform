"""Tests for the deterministic compliance engine."""

import pytest

from app.data.toronto_zoning import VALID_BYLAW_SECTIONS
from app.services.compliance_engine import (
    ComplianceResult,
    ComplianceRule,
    check_compliance,
    render_compliance_matrix_markdown,
)
from app.services.zoning_parser import parse_zone_string, get_zone_standards
from app.services.zoning_service import ZoningAnalysis


def _make_zoning(zone_string: str = "CR 3.0", parking_area: str = "PA3") -> ZoningAnalysis:
    """Helper to create a ZoningAnalysis for testing."""
    from app.data.toronto_zoning import BICYCLE_PARKING, PARKING_STANDARDS, AMENITY_SPACE

    components = parse_zone_string(zone_string)
    standards = get_zone_standards(components)
    return ZoningAnalysis(
        parcel_id="test-parcel",
        address="123 Test St",
        zone_string=zone_string,
        components=components,
        standards=standards,
        parking_policy_area=parking_area,
        parking_standards=dict(PARKING_STANDARDS[parking_area]),
        bicycle_parking=dict(BICYCLE_PARKING),
        amenity_space=dict(AMENITY_SPACE),
    )


def _make_massing(
    height_m: float = 25.0,
    storeys: int = 8,
    fsi: float = 2.5,
    lot_coverage_pct: float = 0.45,
    gfa: float = 5000.0,
    gla: float = 4100.0,
) -> dict:
    return {
        "typology": "midrise",
        "lot_area_m2": 2000.0,
        "buildable_floorplate_m2": 900.0,
        "storeys": storeys,
        "height_m": height_m,
        "estimated_gfa_m2": gfa,
        "estimated_gla_m2": gla,
        "estimated_fsi": fsi,
        "lot_coverage_pct": lot_coverage_pct,
        "assumptions_used": {
            "policy_geometry_defaults": {
                "stepback_m": 3.0,
            }
        },
    }


def _make_layout(total_units: int = 60, parking: float = 30.0, amenity: float = 120.0) -> dict:
    return {
        "total_units": total_units,
        "parking_required": parking,
        "amenity_required_m2": amenity,
        "allocations": [
            {"name": "studio", "count": 9, "typical_area_m2": 40.0, "allocated_area_m2": 360.0, "is_accessible": False},
            {"name": "one_bed", "count": 24, "typical_area_m2": 52.0, "allocated_area_m2": 1248.0, "is_accessible": False},
            {"name": "two_bed", "count": 21, "typical_area_m2": 74.0, "allocated_area_m2": 1554.0, "is_accessible": False},
            {"name": "three_bed", "count": 6, "typical_area_m2": 96.0, "allocated_area_m2": 576.0, "is_accessible": False},
        ],
    }


class TestCheckCompliance:
    """Test the deterministic compliance check."""

    def test_compliant_proposal(self):
        """A proposal within all limits should be fully compliant."""
        zoning = _make_zoning("CR 3.0")
        massing = _make_massing(height_m=25.0, storeys=8, fsi=2.5, lot_coverage_pct=0.45)
        layout = _make_layout(total_units=60)

        result = check_compliance(zoning, massing, layout)

        assert isinstance(result, ComplianceResult)
        # FSI 2.5 <= 3.0 should comply
        fsi_rule = next(r for r in result.rules if "FSI" in r.parameter)
        assert fsi_rule.compliant is True
        assert fsi_rule.variance_required is False

    def test_height_variance_needed(self):
        """Exceeding max height should flag a variance."""
        zoning = _make_zoning("R")  # R zone: max 10m
        massing = _make_massing(height_m=15.0, storeys=5, fsi=0.5)
        layout = _make_layout(total_units=10)

        result = check_compliance(zoning, massing, layout)

        height_rule = next(r for r in result.rules if "Height" in r.parameter and "Angular" not in r.parameter)
        assert height_rule.compliant is False
        assert height_rule.variance_required is True
        assert height_rule.variance_pct is not None
        assert height_rule.variance_pct > 0

    def test_fsi_variance(self):
        """Exceeding max FSI should flag a variance."""
        zoning = _make_zoning("R")  # R zone: max FSI 0.6
        massing = _make_massing(fsi=1.2)
        layout = _make_layout(total_units=10)

        result = check_compliance(zoning, massing, layout)

        fsi_rule = next(r for r in result.rules if "FSI" in r.parameter)
        assert fsi_rule.compliant is False
        assert fsi_rule.variance_pct == pytest.approx(100.0, abs=0.1)  # 100% over

    def test_lot_coverage_check(self):
        """Lot coverage is checked correctly, handling fraction vs percentage."""
        zoning = _make_zoning("R")  # R zone: max 35%
        massing = _make_massing(lot_coverage_pct=0.40)  # 40% as fraction
        layout = _make_layout(total_units=10)

        result = check_compliance(zoning, massing, layout)

        coverage_rule = next(r for r in result.rules if "Lot Coverage" in r.parameter)
        # 40% > 35% -> not compliant
        assert coverage_rule.compliant is False

    def test_every_rule_has_bylaw_section(self):
        """Every compliance rule must cite a by-law section."""
        zoning = _make_zoning("CR 3.0")
        massing = _make_massing()
        layout = _make_layout()

        result = check_compliance(zoning, massing, layout)

        for rule in result.rules:
            assert rule.bylaw_section != "", f"Rule '{rule.parameter}' missing bylaw_section"

    def test_variance_pct_correct(self):
        """Verify variance percentage calculation."""
        zoning = _make_zoning("R")  # max height 10m
        massing = _make_massing(height_m=12.0)  # 20% over
        layout = _make_layout(total_units=10)

        result = check_compliance(zoning, massing, layout)

        height_rule = next(r for r in result.rules if "Height" in r.parameter and "Angular" not in r.parameter)
        assert height_rule.variance_pct == pytest.approx(20.0, abs=0.1)

    def test_minor_variance_applicable(self):
        """Small variances should qualify for minor variance."""
        # CR zone: 0m front setback, 100% lot coverage, no landscaping required
        zoning = _make_zoning("CR 3.0")
        # Slightly over FSI (3.15 vs 3.0 = 5% over), everything else compliant
        massing = _make_massing(height_m=25.0, storeys=8, fsi=3.15, lot_coverage_pct=0.45)
        # 60 units * 4.0m² amenity = 240m² required; provide 250m²
        layout = _make_layout(total_units=60, amenity=250.0)

        result = check_compliance(zoning, massing, layout)

        # All variances should be minor (<20%)
        for v in result.variances_needed:
            assert v.variance_pct is None or v.variance_pct < 20.0, (
                f"Variance for '{v.parameter}' is {v.variance_pct}% — expected <20%"
            )
        assert result.minor_variance_applicable is True

    def test_major_variance_not_minor(self):
        """Large variances should not qualify for minor variance."""
        zoning = _make_zoning("R")  # max height 10m, max FSI 0.6
        massing = _make_massing(height_m=25.0, storeys=8, fsi=3.0)  # 150% over height, 400% over FSI
        layout = _make_layout(total_units=60)

        result = check_compliance(zoning, massing, layout)

        assert result.minor_variance_applicable is False

    def test_no_standards_returns_warning(self):
        """If zoning has no standards, return a warning instead of crashing."""
        zoning = ZoningAnalysis(
            parcel_id="test",
            address="test",
            zone_string=None,
            components=None,
            standards=None,
            parking_policy_area="PA3",
        )
        result = check_compliance(zoning, {}, {})
        assert len(result.warnings) > 0
        assert result.rules == []

    def test_angular_plane_check_for_tall_buildings(self):
        """Buildings over 80m should trigger angular plane check."""
        zoning = _make_zoning("CR 10.0")
        massing = _make_massing(height_m=95.0, storeys=30, fsi=8.0)
        layout = _make_layout(total_units=300)

        result = check_compliance(zoning, massing, layout)

        angular_rule = next((r for r in result.rules if "Angular" in r.parameter), None)
        assert angular_rule is not None
        assert angular_rule.variance_required is True

    def test_parking_by_policy_area(self):
        """Parking requirements should vary by policy area."""
        zoning_pa1 = _make_zoning("CR 3.0", parking_area="PA1")
        zoning_pa4 = _make_zoning("CR 3.0", parking_area="PA4")
        massing = _make_massing()
        layout = _make_layout(total_units=60)

        result_pa1 = check_compliance(zoning_pa1, massing, layout)
        result_pa4 = check_compliance(zoning_pa4, massing, layout)

        parking_pa1 = next(r for r in result_pa1.rules if "Parking" in r.parameter and "Bicycle" not in r.parameter)
        parking_pa4 = next(r for r in result_pa4.rules if "Parking" in r.parameter and "Bicycle" not in r.parameter)

        # PA1 requires 0 parking, PA4 requires 0.7 per unit
        assert parking_pa1.permitted_value == 0.0
        assert parking_pa4.permitted_value == pytest.approx(42.0, abs=0.1)  # 60 * 0.7


class TestRenderComplianceMatrix:
    """Test the markdown rendering of the compliance matrix."""

    def test_renders_markdown_table(self):
        zoning = _make_zoning("CR 3.0")
        massing = _make_massing()
        layout = _make_layout()

        result = check_compliance(zoning, massing, layout)
        markdown = render_compliance_matrix_markdown(result)

        assert "| Provision |" in markdown
        assert "COMPLIES" in markdown or "VARIANCE REQUIRED" in markdown
        assert "**Summary**" in markdown

    def test_empty_result_renders(self):
        result = ComplianceResult()
        markdown = render_compliance_matrix_markdown(result)
        assert "0/0 provisions comply" in markdown
