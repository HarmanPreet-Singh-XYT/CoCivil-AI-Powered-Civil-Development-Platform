import uuid
from datetime import date, datetime, timezone

import pytest

from app.dependencies import get_db_session
from app.main import app
from app.services.policy_stack import PolicyStackRecord, build_policy_stack_response


def test_build_policy_stack_response_orders_by_precedence_and_deduplicates_snapshots():
    parcel_id = uuid.uuid4()
    shared_snapshot_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    lower_precedence = PolicyStackRecord(
        clause_id=uuid.uuid4(),
        policy_version_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_title="Base Zoning",
        doc_type="zoning_bylaw",
        override_level=4,
        section_ref="40.10.40.10",
        page_ref="12",
        raw_text="Base height is 30 metres.",
        normalized_type="max_height",
        normalized_json={"value": 30, "unit": "m"},
        applicability_json={},
        confidence=0.98,
        effective_date=date(2026, 1, 1),
        source_url="https://example.com/base",
        snapshot_id=shared_snapshot_id,
        snapshot_type="policy",
        snapshot_label="policy-v1",
        snapshot_published_at=now,
    )
    higher_precedence = PolicyStackRecord(
        clause_id=uuid.uuid4(),
        policy_version_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_title="Site Specific Exception",
        doc_type="site_specific",
        override_level=1,
        section_ref="SSA-1",
        page_ref="2",
        raw_text="Site-specific height is 36 metres.",
        normalized_type="max_height",
        normalized_json={"value": 36, "unit": "m"},
        applicability_json={"lot": "specific"},
        confidence=0.99,
        effective_date=date(2026, 2, 1),
        source_url="https://example.com/site-specific",
        snapshot_id=shared_snapshot_id,
        snapshot_type="policy",
        snapshot_label="policy-v1",
        snapshot_published_at=now,
    )

    response = build_policy_stack_response(parcel_id, [lower_precedence, higher_precedence])

    assert response.parcel_id == parcel_id
    assert [entry.override_level for entry in response.applicable_policies] == [1, 4]
    assert response.applicable_policies[0].document_title == "Site Specific Exception"
    assert len(response.citations) == 2
    assert len(response.snapshots) == 1
    assert response.snapshots[0].version_label == "policy-v1"


@pytest.mark.anyio
async def test_parcel_policy_stack_returns_404_when_parcel_missing(client):
    class MissingParcelSession:
        async def get(self, model, key):
            return None

    async def override_db():
        yield MissingParcelSession()

    app.dependency_overrides[get_db_session] = override_db
    try:
        response = await client.get(f"/api/v1/parcels/{uuid.uuid4()}/policy-stack")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Parcel not found"
