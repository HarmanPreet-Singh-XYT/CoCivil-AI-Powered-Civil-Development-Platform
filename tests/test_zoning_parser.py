"""Tests for Toronto By-law 569-2013 zone string parser."""

import pytest

from app.services.zoning_parser import ZoneComponents, get_zone_standards, parse_zone_string


class TestParseZoneString:
    """Test parsing various Toronto zone string formats."""

    def test_cr_full_with_split_density_and_exception(self):
        """CR 3.0 (c2.0; r2.5) SS2 (x345)"""
        result = parse_zone_string("CR 3.0 (c2.0; r2.5) SS2 (x345)")
        assert result.category == "CR"
        assert result.density == 3.0
        assert result.commercial_density == 2.0
        assert result.residential_density == 2.5
        assert result.height_suffix == "SS2"
        assert result.exception_number == 345

    def test_r_with_density_exception(self):
        """R (d0.6) (x123)"""
        result = parse_zone_string("R (d0.6) (x123)")
        assert result.category == "R"
        assert result.residential_density == 0.6
        assert result.exception_number == 123
        assert result.density is None

    def test_ra_simple_density(self):
        """RA 2.5"""
        result = parse_zone_string("RA 2.5")
        assert result.category == "RA"
        assert result.density == 2.5
        assert result.exception_number is None
        assert result.height_suffix is None

    def test_cl_with_exception(self):
        """CL 2.0 (x15)"""
        result = parse_zone_string("CL 2.0 (x15)")
        assert result.category == "CL"
        assert result.density == 2.0
        assert result.exception_number == 15

    def test_e_simple(self):
        """E 1.5"""
        result = parse_zone_string("E 1.5")
        assert result.category == "E"
        assert result.density == 1.5

    def test_r_bare(self):
        """R"""
        result = parse_zone_string("R")
        assert result.category == "R"
        assert result.density is None

    def test_rm_category(self):
        result = parse_zone_string("RM 1.0")
        assert result.category == "RM"
        assert result.density == 1.0

    def test_os_category(self):
        result = parse_zone_string("OS")
        assert result.category == "OS"

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            parse_zone_string("")

    def test_unknown_category_raises(self):
        with pytest.raises(ValueError, match="Unrecognized zone category"):
            parse_zone_string("XYZ 1.0")

    def test_case_insensitive(self):
        result = parse_zone_string("cr 3.0 (c2.0; r2.5) ss2 (x345)")
        assert result.category == "CR"
        assert result.height_suffix == "SS2"

    def test_raw_preserved(self):
        result = parse_zone_string("  CR 3.0  ")
        assert result.raw == "CR 3.0"


class TestGetZoneStandards:
    """Test looking up deterministic standards from parsed components."""

    def test_r_zone_base_standards(self):
        components = parse_zone_string("R")
        standards = get_zone_standards(components)
        assert standards.category == "R"
        assert standards.label == "Residential"
        assert standards.max_height_m == 10.0
        assert standards.max_storeys == 3
        assert standards.max_fsi == 0.6
        assert standards.min_front_setback_m == 6.0
        assert standards.min_rear_setback_m == 7.5
        assert standards.max_lot_coverage_pct == 35.0
        assert standards.bylaw_section == "10.20"

    def test_cr_zone_with_density_override(self):
        components = parse_zone_string("CR 3.0 (c2.0; r2.5)")
        standards = get_zone_standards(components)
        assert standards.category == "CR"
        assert standards.max_fsi == 3.0
        assert standards.commercial_fsi == 2.0
        assert standards.residential_fsi == 2.5
        assert standards.bylaw_section == "40.10"

    def test_ra_zone(self):
        components = parse_zone_string("RA 2.5")
        standards = get_zone_standards(components)
        assert standards.category == "RA"
        assert standards.max_fsi == 2.5  # overridden by density suffix
        assert standards.label == "Residential Apartment"

    def test_exception_number_preserved(self):
        components = parse_zone_string("R (x123)")
        standards = get_zone_standards(components)
        assert standards.exception_number == 123

    def test_site_specific_height_flag(self):
        components = parse_zone_string("CR 3.0 SS2")
        standards = get_zone_standards(components)
        assert standards.has_site_specific_height is True

    def test_unknown_category_returns_unknown(self):
        # Manually create components with unknown category
        components = ZoneComponents(raw="ZZ 1.0", category="ZZ")
        standards = get_zone_standards(components)
        assert standards.label == "Unknown (ZZ)"

    def test_permitted_uses_populated(self):
        components = parse_zone_string("R")
        standards = get_zone_standards(components)
        assert len(standards.permitted_uses) > 0
        assert "detached house" in standards.permitted_uses

    def test_all_known_categories_parse(self):
        """Every category in ZONE_STANDARDS should parse and return valid standards."""
        categories = ["R", "RM", "RA", "CR", "CL", "CG", "E", "EL", "I", "OS", "OR", "U"]
        for cat in categories:
            components = parse_zone_string(cat)
            standards = get_zone_standards(components)
            assert standards.category == cat
            assert standards.bylaw_section != ""
