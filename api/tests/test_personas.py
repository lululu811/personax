import pytest


@pytest.mark.asyncio
async def test_list_personas(client):
    resp = await client.get("/api/v1/personas")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "name" in data[0]
    assert "display_name" in data[0]


@pytest.mark.asyncio
async def test_list_tools(client):
    resp = await client.get("/api/v1/tools")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
