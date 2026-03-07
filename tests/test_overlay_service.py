import uuid
from datetime import date, datetime, timezone

import pytest

from app.dependencies import get_db_session
from app.main import app
from app.services.overlay_service import (
    OverlayRecord,
    ParcelMetricRecord,
    build_overlay_response,
)


def test_build_overlay_response_deduplicates_snapshots_and_sorts_metrics():
    parcel_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    overlays = [
        OverlayRecord(
            feature_id=uuid.uuid4(),
            layer_id=uuid.uuid4(),
            layer_name="Ravine Protection",
            layer_type="environmental",
            relationship_type="intersects",
            source_record_id="ravine-1",
            source_url="https://example.com/ravine",
            effective_date=date(2026, 1, 15),
            attributes_json={"constraint": "ravine"},
            snapshot_id=snapshot_id,
            snapshot_type="overlay",
            snapshot_label="overlay-v1",
            snapshot_published_at=now,
        ),
        OverlayRecord(
            feature_id=uuid.uuid4(),
            layer_id=uuid.uuid4(),
            layer_name="Heritage Register",
            layer_type="heritage",
            relationship_type="contains",
            source_record_id="heritage-1",
            source_url="https://example.com/heritage",
            effective_date=date(2026, 1, 10),
            attributes_json={"status": "listed"},
            snapshot_id=snapshot_id,
            snapshot_type="overlay",
            snapshot_label="overlay-v1",
            snapshot_published_at=now,
        ),
    ]
    metrics = [
        ParcelMetricRecord(metric_type="overlay_feature_count", metric_value=2.0, unit="count"),
        ParcelMetricRecord(metric_type="heritage_flag", metric_value=1.0, unit="boolean"),
    ]

    response = build_overlay_response(parcel_id, overlays, metrics)

    assert response.parcel_id == parcel_id
    assert [entry.layer_type for entry in response.overlays] == ["environmental", "heritage"]
    assert [metric.metric_type for metric in response.parcel_metrics] == ["heritage_flag", "overlay_feature_count"]
    assert len(response.snapshots) == 1
    assert response.snapshots[0].version_label == "overlay-v1"


@pytest.mark.anyio
async def test_parcel_overlays_returns_404_when_parcel_missing(client):
    class MissingParcelSession:
        async def get(self, model, key):
            return None

    async def override_db():
        yield MissingParcelSession()

    app.dependency_overrides[get_db_session] = override_db
    try:
        response = await client.get(f"/api/v1/parcels/{uuid.uuid4()}/overlays")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Parcel not found"
