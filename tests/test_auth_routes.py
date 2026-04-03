from httpx import AsyncClient
import asyncio

from app.config import get_settings


async def test_health_endpoint(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_register_success(client: AsyncClient):
    payload = {
        "email": "register1@example.com",
        "username": "register_user_1",
        "password": "StrongPass123",
        "role": "viewer",
    }
    resp = await client.post("/api/v1/users/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == payload["email"]
    assert data["username"] == payload["username"]
    assert data["role"] == "viewer"


async def test_register_privileged_role_rejected(client: AsyncClient):
    payload = {
        "email": "register_admin_reject@example.com",
        "username": "register_admin_reject",
        "password": "StrongPass123",
        "role": "admin",
    }
    resp = await client.post("/api/v1/users/register", json=payload)
    assert resp.status_code == 403


async def test_register_duplicate_email_conflict(client: AsyncClient):
    payload = {
        "email": "dupe@example.com",
        "username": "dupe_user_1",
        "password": "StrongPass123",
        "role": "viewer",
    }
    first = await client.post("/api/v1/users/register", json=payload)
    assert first.status_code == 201

    second_payload = {
        "email": "dupe@example.com",
        "username": "dupe_user_2",
        "password": "StrongPass123",
        "role": "viewer",
    }
    second = await client.post("/api/v1/users/register", json=second_payload)
    assert second.status_code == 409


async def test_login_success_returns_tokens(client: AsyncClient, user_factory):
    user = await user_factory(role="admin")
    resp = await client.post(
        "/api/v1/users/login",
        json={"email": user["email"], "password": user["password"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert isinstance(data["refresh_token"], str)


async def test_login_invalid_credentials(client: AsyncClient, user_factory):
    user = await user_factory(role="admin")
    resp = await client.post(
        "/api/v1/users/login",
        json={"email": user["email"], "password": "WrongPass123"},
    )
    assert resp.status_code == 401


async def test_me_requires_token(client: AsyncClient):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


async def test_me_with_valid_token(client: AsyncClient, user_factory):
    user = await user_factory(role="analyst")
    token = user["tokens"]["access_token"]
    resp = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == user["email"]
    assert data["role"] == "analyst"


async def test_refresh_rotates_tokens(client: AsyncClient, user_factory):
    user = await user_factory(role="admin")
    old_refresh = user["tokens"]["refresh_token"]

    refresh_resp = await client.post("/api/v1/users/refresh", json={"refresh_token": old_refresh})
    assert refresh_resp.status_code == 200
    rotated = refresh_resp.json()
    assert rotated["refresh_token"] != old_refresh


async def test_refresh_reuse_old_token_fails(client: AsyncClient, user_factory):
    user = await user_factory(role="admin")
    old_refresh = user["tokens"]["refresh_token"]

    first = await client.post("/api/v1/users/refresh", json={"refresh_token": old_refresh})
    assert first.status_code == 200

    second = await client.post("/api/v1/users/refresh", json={"refresh_token": old_refresh})
    assert second.status_code == 401


async def test_logout_revokes_access_token(client: AsyncClient, user_factory):
    user = await user_factory(role="admin")
    access = user["tokens"]["access_token"]
    refresh = user["tokens"]["refresh_token"]

    logout_resp = await client.post(
        "/api/v1/users/logout",
        headers={"Authorization": f"Bearer {access}"},
        json={"refresh_token": refresh},
    )
    assert logout_resp.status_code == 200

    me_resp = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access}"})
    assert me_resp.status_code == 401


async def test_bootstrap_admin_requires_key_when_disabled(client: AsyncClient):
    get_settings.cache_clear()

    payload = {
        "email": "bootstrap-disabled@example.com",
        "username": "bootstrap_disabled",
        "password": "StrongPass123",
        "role": "admin",
    }
    resp = await client.post("/api/v1/users/bootstrap-admin", json=payload)
    assert resp.status_code == 403


async def test_bootstrap_admin_works_once_with_valid_key(client: AsyncClient, monkeypatch):
    monkeypatch.setenv("ADMIN_BOOTSTRAP_KEY", "test-bootstrap-key")
    get_settings.cache_clear()

    payload = {
        "email": "bootstrap-admin@example.com",
        "username": "bootstrap_admin",
        "password": "StrongPass123",
        "role": "viewer",
    }

    first = await client.post(
        "/api/v1/users/bootstrap-admin",
        headers={"X-Bootstrap-Key": "test-bootstrap-key"},
        json=payload,
    )
    assert first.status_code == 201
    assert first.json()["role"] == "admin"

    second_payload = {
        "email": "bootstrap-admin-2@example.com",
        "username": "bootstrap_admin_2",
        "password": "StrongPass123",
        "role": "viewer",
    }
    second = await client.post(
        "/api/v1/users/bootstrap-admin",
        headers={"X-Bootstrap-Key": "test-bootstrap-key"},
        json=second_payload,
    )
    assert second.status_code == 403

    monkeypatch.delenv("ADMIN_BOOTSTRAP_KEY", raising=False)
    get_settings.cache_clear()


async def test_refresh_concurrent_requests_do_not_return_500(client: AsyncClient, user_factory):
    user = await user_factory(role="admin")
    old_refresh = user["tokens"]["refresh_token"]

    async def do_refresh():
        return await client.post("/api/v1/users/refresh", json={"refresh_token": old_refresh})

    first, second = await asyncio.gather(do_refresh(), do_refresh())
    statuses = {first.status_code, second.status_code}

    assert 500 not in statuses
    assert statuses.issubset({200, 401})
