from decimal import Decimal
from redis.exceptions import RedisError

from httpx import AsyncClient


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_summary_empty_values(client: AsyncClient, user_factory):
    viewer = await user_factory(role="viewer")
    token = viewer["tokens"]["access_token"]

    resp = await client.get("/api/v1/dashboard/summary", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["total_income"]) == Decimal("0")
    assert Decimal(data["total_expenses"]) == Decimal("0")


async def test_summary_with_data(client: AsyncClient, user_factory):
    admin = await user_factory(role="admin")
    token = admin["tokens"]["access_token"]

    await client.post(
        "/api/v1/financial-records",
        headers=_auth(token),
        json={
            "amount": "1000.00",
            "record_type": "income",
            "category": "salary",
            "entry_date": "2026-04-01",
            "notes": "inc",
        },
    )
    await client.post(
        "/api/v1/financial-records",
        headers=_auth(token),
        json={
            "amount": "250.00",
            "record_type": "expense",
            "category": "food",
            "entry_date": "2026-04-01",
            "notes": "exp",
        },
    )

    resp = await client.get("/api/v1/dashboard/summary", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["total_income"]) == Decimal("1000.00")
    assert Decimal(data["total_expenses"]) == Decimal("250.00")
    assert Decimal(data["net_balance"]) == Decimal("750.00")


async def test_category_totals(client: AsyncClient, user_factory):
    admin = await user_factory(role="admin")
    token = admin["tokens"]["access_token"]

    await client.post(
        "/api/v1/financial-records",
        headers=_auth(token),
        json={
            "amount": "300.00",
            "record_type": "expense",
            "category": "food",
            "entry_date": "2026-04-03",
            "notes": "a",
        },
    )
    await client.post(
        "/api/v1/financial-records",
        headers=_auth(token),
        json={
            "amount": "200.00",
            "record_type": "expense",
            "category": "food",
            "entry_date": "2026-04-03",
            "notes": "b",
        },
    )

    resp = await client.get("/api/v1/dashboard/categories", headers=_auth(token))
    assert resp.status_code == 200
    items = resp.json()
    food = [item for item in items if item["category"] == "food"]
    assert len(food) == 1
    assert Decimal(food[0]["total"]) == Decimal("500.00")


async def test_recent_activity_limit(client: AsyncClient, user_factory):
    admin = await user_factory(role="admin")
    token = admin["tokens"]["access_token"]

    for idx in range(5):
        await client.post(
            "/api/v1/financial-records",
            headers=_auth(token),
            json={
                "amount": f"{idx + 1}.00",
                "record_type": "expense",
                "category": "misc",
                "entry_date": "2026-04-04",
                "notes": f"row {idx}",
            },
        )

    resp = await client.get("/api/v1/dashboard/recent-activity?limit=3", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 3


async def test_monthly_trends(client: AsyncClient, user_factory):
    admin = await user_factory(role="admin")
    token = admin["tokens"]["access_token"]

    await client.post(
        "/api/v1/financial-records",
        headers=_auth(token),
        json={
            "amount": "400.00",
            "record_type": "income",
            "category": "salary",
            "entry_date": "2026-03-01",
            "notes": "m1",
        },
    )
    await client.post(
        "/api/v1/financial-records",
        headers=_auth(token),
        json={
            "amount": "100.00",
            "record_type": "expense",
            "category": "food",
            "entry_date": "2026-03-15",
            "notes": "m1e",
        },
    )

    resp = await client.get("/api/v1/dashboard/monthly-trends", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["month"].startswith("2026-")


async def test_dashboard_invalid_date_range_returns_400(client: AsyncClient, user_factory):
    admin = await user_factory(role="admin")
    token = admin["tokens"]["access_token"]

    resp = await client.get(
        "/api/v1/dashboard/summary?start_date=2026-04-20&end_date=2026-04-01",
        headers=_auth(token),
    )
    assert resp.status_code == 400


async def test_dashboard_summary_falls_back_when_redis_unavailable(client: AsyncClient, user_factory, monkeypatch):
    import app.main as app_main

    viewer = await user_factory(role="viewer")
    token = viewer["tokens"]["access_token"]

    async def failing_get(*_args, **_kwargs):
        raise RedisError("simulated redis read failure")

    async def failing_set(*_args, **_kwargs):
        raise RedisError("simulated redis write failure")

    monkeypatch.setattr(app_main.redis_client, "get", failing_get)
    monkeypatch.setattr(app_main.redis_client, "set", failing_set)

    resp = await client.get("/api/v1/dashboard/summary", headers=_auth(token))
    assert resp.status_code == 200
