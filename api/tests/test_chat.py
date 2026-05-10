import pytest


@pytest.mark.asyncio
async def test_chat_requires_auth(client):
    resp = await client.post("/api/v1/chat", json={"query": "帮我看看茅台"})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_chat_with_auth(client):
    reg = await client.post("/api/v1/auth/register", json={
        "email": "chat@example.com", "password": "pass123",
    })
    token = reg.json()["access_token"]

    resp = await client.post("/api/v1/chat", json={
        "query": "帮我看看KDJ指标",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "persona_analysis" in data
    assert "route" in data
