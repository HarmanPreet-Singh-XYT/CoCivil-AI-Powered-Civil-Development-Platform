import pytest

from app.dependencies import get_db_session
from app.main import app


@pytest.mark.asyncio
async def test_search_parcels_rejects_invalid_bbox(client):
    class DummySession:
        async def execute(self, *_args, **_kwargs):  # pragma: no cover - should never be reached
            raise AssertionError("execute should not be called for invalid bbox")

    async def override_db():
        yield DummySession()

    app.dependency_overrides[get_db_session] = override_db
    try:
        response = await client.get("/api/v1/parcels/search", params={"bbox": "bad,bounds"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
