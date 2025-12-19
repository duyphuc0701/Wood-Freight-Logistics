import pytest

pytestmark = pytest.mark.asyncio(loop_scope="module")


async def test_health_check(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "ok"
