import json

from app.services.geospatial_ingestion import (
    _compose_address_text,
    _iter_geojson_features,
    _normalize_decision,
    _parse_geometry_value,
    _pick_zone_code,
)


def test_pick_zone_code_prefers_full_toronto_zone_string():
    properties = {
        "ZN_ZONE": "CR",
        "ZN_STRING": "CR 3.0 (c2.0; r2.5) SS2 (x345)",
    }

    assert _pick_zone_code(properties) == "CR 3.0 (c2.0; r2.5) SS2 (x345)"


def test_normalize_decision_maps_toronto_status_variants():
    assert _normalize_decision("Approved") == "approved"
    assert _normalize_decision("Conditionally Approved") == "conditionally approved"
    assert _normalize_decision("Under Review") == "pending"
    assert _normalize_decision("Appealed to OLT") == "appealed"
    assert _normalize_decision("Withdrawn by applicant") == "withdrawn"


def test_compose_address_text_uses_full_address_then_split_fields():
    assert _compose_address_text({"ADDRESS_FULL": "258 John St"}) == "258 John St"
    assert _compose_address_text({"ADDRESS_NUMBER": "258", "LINEAR_NAME_FULL": "John St"}) == "258 John St"
    assert _compose_address_text({"STREET_NUM": "123", "STREET_NAME": "Main", "STREET_TYPE": "St"}) == "123 Main St"


def test_parse_geometry_value_accepts_wkt_and_geojson_text():
    assert _parse_geometry_value("POINT (-79.4 43.7)") == "POINT (-79.4 43.7)"
    assert _parse_geometry_value('{"type":"Point","coordinates":[-79.4,43.7]}') == "POINT (-79.4 43.7)"


def test_iter_geojson_features_yields_each_feature(tmp_path):
    geojson_path = tmp_path / "sample.geojson"
    geojson_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"PIN": "1"},
                        "geometry": {"type": "Point", "coordinates": [0, 0]},
                    },
                    {
                        "type": "Feature",
                        "properties": {"PIN": "2"},
                        "geometry": {"type": "Point", "coordinates": [1, 1]},
                    },
                ],
            }
        )
    )

    features = list(_iter_geojson_features(geojson_path))

    assert [feature["properties"]["PIN"] for feature in features] == ["1", "2"]
