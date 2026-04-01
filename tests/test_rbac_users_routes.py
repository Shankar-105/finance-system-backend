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


async def test_dashboard_summary_allows_viewer(client: AsyncClient, user_factory):
    user = await user_factory(role="viewer")
    token = user["tokens"]["access_token"]

    resp = await client.get("/api/v1/dashboard/summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
