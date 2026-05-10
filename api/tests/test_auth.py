import pytest


@pytest.mark.asyncio
async def test_register(client):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "new@example.com",
        "password": "securepass123",
        "display_name": "New User",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate(client):
    await client.post("/api/v1/auth/register", json={
        "email": "dup@example.com", "password": "pass123",
    })
    resp = await client.post("/api/v1/auth/register", json={
        "email": "dup@example.com", "password": "pass456",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login(client):
    await client.post("/api/v1/auth/register", json={
        "email": "login@example.com", "password": "mypassword",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "login@example.com", "password": "mypassword",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/register", json={
        "email": "wrong@example.com", "password": "correct",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "wrong@example.com", "password": "incorrect",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client):
    reg = await client.post("/api/v1/auth/register", json={
        "email": "me@example.com", "password": "pass123", "display_name": "Me",
    })
    token = reg.json()["access_token"]
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"
    assert resp.json()["display_name"] == "Me"
