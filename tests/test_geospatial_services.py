import uuid

import pytest
from sqlalchemy.dialects import postgresql

from app.schemas.geospatial import ParcelSearchParams
from app.services.geospatial import (
    AddressCandidate,
    ZoningAssignmentCandidate,
    build_parcel_search_statement,
    choose_canonical_address,
    choose_primary_zoning_assignment,
    normalize_address_text,
)


def test_normalize_address_text_collapses_whitespace():
    assert normalize_address_text(" 123   Main   St ") == "123 Main St"


def test_choose_canonical_address_prefers_highest_confidence_then_method():
    candidate = choose_canonical_address(
        [
            AddressCandidate(address_text="123 Main Street", match_method="spatial_contains", match_confidence=0.9),
            AddressCandidate(address_text="123 Main St", match_method="source_key", match_confidence=1.0),
        ]
    )

    assert candidate is not None
    assert candidate.address_text == "123 Main St"
    assert candidate.match_method == "source_key"


def test_choose_primary_zoning_assignment_prefers_max_overlap():
    dataset_feature_id = uuid.uuid4()
    candidate = choose_primary_zoning_assignment(
        [
            ZoningAssignmentCandidate(
                dataset_feature_id=uuid.uuid4(),
                zone_code="CR",
                assignment_method="max_overlap",
                overlap_area_m2=150.0,
            ),
            ZoningAssignmentCandidate(
                dataset_feature_id=dataset_feature_id,
                zone_code="RA",
                assignment_method="max_overlap",
                overlap_area_m2=250.0,
            ),
        ]
    )

    assert candidate is not None
    assert candidate.dataset_feature_id == dataset_feature_id
    assert candidate.zone_code == "RA"


def test_choose_primary_zoning_assignment_returns_none_on_material_tie():
    candidate = choose_primary_zoning_assignment(
        [
            ZoningAssignmentCandidate(
                dataset_feature_id=uuid.uuid4(),
                zone_code="CR",
                assignment_method="max_overlap",
                overlap_area_m2=100.0,
            ),
            ZoningAssignmentCandidate(
                dataset_feature_id=uuid.uuid4(),
                zone_code="RA",
                assignment_method="max_overlap",
                overlap_area_m2=100.0,
            ),
        ]
    )

    assert candidate is None


def test_parcel_search_params_validate_bbox_and_expose_bounds():
    params = ParcelSearchParams(bbox="-79.5,43.6,-79.3,43.8")

    assert params.bbox_bounds == (-79.5, 43.6, -79.3, 43.8)


def test_parcel_search_params_reject_invalid_bbox():
    params = ParcelSearchParams(bbox="bad,bounds")

    with pytest.raises(ValueError):
        _ = params.bbox_bounds


def test_build_parcel_search_statement_includes_new_filters():
    params = ParcelSearchParams(
        address="Main",
        zoning_code="CR",
        min_lot_area=250,
        max_lot_area=500,
        min_frontage=12,
        bbox="-79.5,43.6,-79.3,43.8",
        page=2,
        page_size=10,
    )

    statement = build_parcel_search_statement(params)
    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "parcels.address ILIKE" in compiled
    assert "parcels.zone_code =" in compiled
    assert "parcels.lot_area_m2 >=" in compiled
    assert "parcels.lot_area_m2 <=" in compiled
    assert "parcels.lot_frontage_m >=" in compiled
    assert "ST_MakeEnvelope" in compiled
    assert "OFFSET" in compiled
    assert "LIMIT" in compiled
