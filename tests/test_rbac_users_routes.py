from httpx import AsyncClient


async def test_admin_ping_allows_admin(client: AsyncClient, user_factory):
    user = await user_factory(role="admin")
    token = user["tokens"]["access_token"]

    resp = await client.get("/api/v1/users/admin/ping", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


async def test_admin_ping_blocks_analyst(client: AsyncClient, user_factory):
    user = await user_factory(role="analyst")
    token = user["tokens"]["access_token"]

    resp = await client.get("/api/v1/users/admin/ping", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


async def test_admin_ping_blocks_viewer(client: AsyncClient, user_factory):
    user = await user_factory(role="viewer")
    token = user["tokens"]["access_token"]

    resp = await client.get("/api/v1/users/admin/ping", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


async def test_online_users_requires_admin(client: AsyncClient, user_factory):
    user = await user_factory(role="analyst")
    token = user["tokens"]["access_token"]

    resp = await client.get("/api/v1/users/admin/online-users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


async def test_online_users_admin_empty_initially(client: AsyncClient, user_factory):
    user = await user_factory(role="admin")
    token = user["tokens"]["access_token"]

    resp = await client.get("/api/v1/users/admin/online-users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_admin_can_promote_user_role(client: AsyncClient, user_factory):
    admin = await user_factory(role="admin")
    viewer = await user_factory(role="viewer")

    resp = await client.patch(
        f"/api/v1/users/admin/users/{viewer['user']['id']}",
        headers={"Authorization": f"Bearer {admin['tokens']['access_token']}"},
        json={"role": "analyst"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "analyst"


async def test_non_admin_cannot_update_user_role(client: AsyncClient, user_factory):
    analyst = await user_factory(role="analyst")
    viewer = await user_factory(role="viewer")

    resp = await client.patch(
        f"/api/v1/users/admin/users/{viewer['user']['id']}",
        headers={"Authorization": f"Bearer {analyst['tokens']['access_token']}"},
        json={"role": "admin"},
    )
    assert resp.status_code == 403


async def test_admin_can_create_analyst_account(client: AsyncClient, user_factory):
    admin = await user_factory(role="admin")

    resp = await client.post(
        "/api/v1/users/admin/users",
        headers={"Authorization": f"Bearer {admin['tokens']['access_token']}"},
        json={
            "email": "analyst-created-by-admin@example.com",
            "username": "analyst_created",
            "password": "StrongPass123",
            "role": "analyst",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "analyst"


async def test_non_admin_cannot_create_analyst_account(client: AsyncClient, user_factory):
    analyst = await user_factory(role="analyst")

    resp = await client.post(
        "/api/v1/users/admin/users",
        headers={"Authorization": f"Bearer {analyst['tokens']['access_token']}"},
        json={
            "email": "illegal-analyst-create@example.com",
            "username": "illegal_analyst_create",
            "password": "StrongPass123",
            "role": "analyst",
        },
    )
    assert resp.status_code == 403


async def test_admin_create_user_blocks_direct_admin_role(client: AsyncClient, user_factory):
    admin = await user_factory(role="admin")

    resp = await client.post(
        "/api/v1/users/admin/users",
        headers={"Authorization": f"Bearer {admin['tokens']['access_token']}"},
        json={
            "email": "direct-admin-create@example.com",
            "username": "direct_admin_create",
            "password": "StrongPass123",
            "role": "admin",
        },
    )
    assert resp.status_code == 400


async def test_dashboard_summary_allows_viewer(client: AsyncClient, user_factory):
    user = await user_factory(role="viewer")
    token = user["tokens"]["access_token"]

    resp = await client.get("/api/v1/dashboard/summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


async def test_admin_update_user_route_is_rate_limited(client: AsyncClient, user_factory):
    admin = await user_factory(role="admin")
    viewer = await user_factory(role="viewer")

    statuses: list[int] = []
    for _ in range(25):
        resp = await client.patch(
            f"/api/v1/users/admin/users/{viewer['user']['id']}",
            headers={"Authorization": f"Bearer {admin['tokens']['access_token']}"},
            json={"is_active": True},
        )
        statuses.append(resp.status_code)

    assert 429 in statuses
