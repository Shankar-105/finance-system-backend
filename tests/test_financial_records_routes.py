from decimal import Decimal

from httpx import AsyncClient

from app.config import get_settings


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_create_record_admin_success(client: AsyncClient, user_factory):
    admin = await user_factory(role="admin")
    token = admin["tokens"]["access_token"]

    resp = await client.post(
        "/api/v1/financial-records",
        headers=_auth(token),
        json={
            "amount": "1000.00",
            "record_type": "income",
            "category": "salary",
            "entry_date": "2026-04-01",
            "notes": "monthly income",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert Decimal(data["amount"]) == Decimal("1000.00")


async def test_create_record_analyst_forbidden(client: AsyncClient, user_factory):
    analyst = await user_factory(role="analyst")
    token = analyst["tokens"]["access_token"]

    resp = await client.post(
        "/api/v1/financial-records",
        headers=_auth(token),
        json={
            "amount": "1000.00",
            "record_type": "income",
            "category": "salary",
            "entry_date": "2026-04-01",
            "notes": "not allowed",
        },
    )
    assert resp.status_code == 403


async def test_list_records_analyst_allowed(client: AsyncClient, user_factory):
    admin = await user_factory(role="admin")
    analyst = await user_factory(role="analyst")

    create = await client.post(
        "/api/v1/financial-records",
        headers=_auth(admin["tokens"]["access_token"]),
        json={
            "amount": "50.00",
            "record_type": "expense",
            "category": "food",
            "entry_date": "2026-04-02",
            "notes": "lunch",
        },
    )
    assert create.status_code == 201

    list_resp = await client.get(
        "/api/v1/financial-records",
        headers=_auth(analyst["tokens"]["access_token"]),
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1


async def test_list_records_viewer_forbidden(client: AsyncClient, user_factory):
    viewer = await user_factory(role="viewer")
    list_resp = await client.get(
        "/api/v1/financial-records",
        headers=_auth(viewer["tokens"]["access_token"]),
    )
    assert list_resp.status_code == 403


async def test_list_records_pagination(client: AsyncClient, user_factory):
    admin = await user_factory(role="admin")
    token = admin["tokens"]["access_token"]

    for idx in range(3):
        resp = await client.post(
            "/api/v1/financial-records",
            headers=_auth(token),
            json={
                "amount": f"{100 + idx}.00",
                "record_type": "income",
                "category": "salary",
                "entry_date": "2026-04-03",
                "notes": f"row {idx}",
            },
        )
        assert resp.status_code == 201

    page = await client.get(
        "/api/v1/financial-records?offset=1&limit=2",
        headers=_auth(token),
    )
    assert page.status_code == 200
    data = page.json()
    assert data["offset"] == 1
    assert data["limit"] == 2
    assert len(data["items"]) == 2


async def test_filter_by_category(client: AsyncClient, user_factory):
    admin = await user_factory(role="admin")
    token = admin["tokens"]["access_token"]

    await client.post(
        "/api/v1/financial-records",
        headers=_auth(token),
        json={
            "amount": "200.00",
            "record_type": "expense",
            "category": "food",
            "entry_date": "2026-04-04",
            "notes": "food entry",
        },
    )
    await client.post(
        "/api/v1/financial-records",
        headers=_auth(token),
        json={
            "amount": "500.00",
            "record_type": "expense",
            "category": "transport",
            "entry_date": "2026-04-04",
            "notes": "transport entry",
        },
    )

    filtered = await client.get(
        "/api/v1/financial-records?category=food",
        headers=_auth(token),
    )
    assert filtered.status_code == 200
    items = filtered.json()["items"]
    assert all(item["category"] == "food" for item in items)


async def test_invalid_date_range_returns_400(client: AsyncClient, user_factory):
    admin = await user_factory(role="admin")
    token = admin["tokens"]["access_token"]

    resp = await client.get(
        "/api/v1/financial-records?start_date=2026-04-10&end_date=2026-04-01",
        headers=_auth(token),
    )
    assert resp.status_code == 400


async def test_update_record_admin_success(client: AsyncClient, user_factory):
    admin = await user_factory(role="admin")
    token = admin["tokens"]["access_token"]

    created = await client.post(
        "/api/v1/financial-records",
        headers=_auth(token),
        json={
            "amount": "300.00",
            "record_type": "expense",
            "category": "utilities",
            "entry_date": "2026-04-05",
            "notes": "bill",
        },
    )
    record_id = created.json()["id"]

    updated = await client.patch(
        f"/api/v1/financial-records/{record_id}",
        headers=_auth(token),
        json={"amount": "350.00", "notes": "updated bill"},
    )
    assert updated.status_code == 200
    assert Decimal(updated.json()["amount"]) == Decimal("350.00")


async def test_soft_delete_hides_record(client: AsyncClient, user_factory):
    admin = await user_factory(role="admin")
    token = admin["tokens"]["access_token"]

    created = await client.post(
        "/api/v1/financial-records",
        headers=_auth(token),
        json={
            "amount": "125.00",
            "record_type": "expense",
            "category": "misc",
            "entry_date": "2026-04-06",
            "notes": "to be deleted",
        },
    )
    record_id = created.json()["id"]

    deleted = await client.delete(f"/api/v1/financial-records/{record_id}", headers=_auth(token))
    assert deleted.status_code == 200

    get_deleted = await client.get(f"/api/v1/financial-records/{record_id}", headers=_auth(token))
    assert get_deleted.status_code == 404


async def test_recycle_bin_list_and_restore_flow(client: AsyncClient, user_factory):
    admin = await user_factory(role="admin")
    token = admin["tokens"]["access_token"]

    created = await client.post(
        "/api/v1/financial-records",
        headers=_auth(token),
        json={
            "amount": "210.00",
            "record_type": "expense",
            "category": "medical",
            "entry_date": "2026-04-07",
            "notes": "to recycle bin",
        },
    )
    assert created.status_code == 201
    record_id = created.json()["id"]

    deleted = await client.delete(f"/api/v1/financial-records/{record_id}", headers=_auth(token))
    assert deleted.status_code == 200

    in_bin = await client.get("/api/v1/financial-records/bin/records", headers=_auth(token))
    assert in_bin.status_code == 200
    assert in_bin.json()["total"] >= 1
    assert any(item["id"] == record_id for item in in_bin.json()["items"])

    restored = await client.post(
        f"/api/v1/financial-records/bin/records/{record_id}/restore",
        headers=_auth(token),
    )
    assert restored.status_code == 200
    assert restored.json()["id"] == record_id

    fetched = await client.get(f"/api/v1/financial-records/{record_id}", headers=_auth(token))
    assert fetched.status_code == 200


async def test_recycle_bin_requires_admin(client: AsyncClient, user_factory):
    admin = await user_factory(role="admin")
    analyst = await user_factory(role="analyst")

    created = await client.post(
        "/api/v1/financial-records",
        headers=_auth(admin["tokens"]["access_token"]),
        json={
            "amount": "99.00",
            "record_type": "expense",
            "category": "misc",
            "entry_date": "2026-04-07",
            "notes": "rbac test",
        },
    )
    record_id = created.json()["id"]
    await client.delete(
        f"/api/v1/financial-records/{record_id}",
        headers=_auth(admin["tokens"]["access_token"]),
    )

    list_resp = await client.get(
        "/api/v1/financial-records/bin/records",
        headers=_auth(analyst["tokens"]["access_token"]),
    )
    assert list_resp.status_code == 403

    restore_resp = await client.post(
        f"/api/v1/financial-records/bin/records/{record_id}/restore",
        headers=_auth(analyst["tokens"]["access_token"]),
    )
    assert restore_resp.status_code == 403


async def test_recycle_bin_auto_purges_after_retention(client: AsyncClient, user_factory, monkeypatch):
    monkeypatch.setenv("RECYCLE_BIN_RETENTION_DAYS", "0")
    get_settings.cache_clear()

    admin = await user_factory(role="admin")
    token = admin["tokens"]["access_token"]

    created = await client.post(
        "/api/v1/financial-records",
        headers=_auth(token),
        json={
            "amount": "77.00",
            "record_type": "expense",
            "category": "misc",
            "entry_date": "2026-04-07",
            "notes": "purge me",
        },
    )
    record_id = created.json()["id"]

    deleted = await client.delete(f"/api/v1/financial-records/{record_id}", headers=_auth(token))
    assert deleted.status_code == 200

    bin_resp = await client.get("/api/v1/financial-records/bin/records", headers=_auth(token))
    assert bin_resp.status_code == 200
    assert all(item["id"] != record_id for item in bin_resp.json()["items"])

    restore_resp = await client.post(
        f"/api/v1/financial-records/bin/records/{record_id}/restore",
        headers=_auth(token),
    )
    assert restore_resp.status_code == 404

    monkeypatch.delenv("RECYCLE_BIN_RETENTION_DAYS", raising=False)
    get_settings.cache_clear()
