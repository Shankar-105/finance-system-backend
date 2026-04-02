import asyncio
from collections.abc import AsyncGenerator, Callable
from uuid import uuid4

import asyncpg
import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.db import get_db, get_redis
from app.main import app
from app.models import Base, User, UserRole
from app.services import presence_service

settings = get_settings()
TEST_DB_NAME = f"{settings.database_name}_test".lower()
TEST_DB_URL = (
    f"postgresql+asyncpg://{settings.database_user}:{settings.database_password}"
    f"@{settings.database_host}:{settings.database_port}/{TEST_DB_NAME}"
)

_test_engine = None
TestingSessionLocal: async_sessionmaker[AsyncSession] | None = None


async def _create_test_database_if_missing() -> None:
    conn = await asyncpg.connect(
        user=settings.database_user,
        password=settings.database_password,
        host=settings.database_host,
        port=settings.database_port,
        database="postgres",
    )
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB_NAME)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    finally:
        await conn.close()


async def _drop_test_database() -> None:
    conn = await asyncpg.connect(
        user=settings.database_user,
        password=settings.database_password,
        host=settings.database_host,
        port=settings.database_port,
        database="postgres",
    )
    try:
        await conn.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = $1 AND pid <> pg_backend_pid()
            """,
            TEST_DB_NAME,
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"')
    finally:
        await conn.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_environment() -> AsyncGenerator[None, None]:
    global _test_engine, TestingSessionLocal

    await _create_test_database_if_missing()

    _test_engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    TestingSessionLocal = async_sessionmaker(
        bind=_test_engine,
        class_=AsyncSession,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        assert TestingSessionLocal is not None
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Presence websocket service opens its own session factory.
    presence_service.SessionLocal = TestingSessionLocal

    yield

    app.dependency_overrides.clear()
    if _test_engine is not None:
        await _test_engine.dispose()

    await _drop_test_database()


@pytest_asyncio.fixture(scope="function")
async def clean_state() -> AsyncGenerator[None, None]:
    assert TestingSessionLocal is not None

    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)

    async def override_get_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = override_get_redis

    import app.main as app_main

    app_main.redis_client = fake_redis

    async with TestingSessionLocal() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE token_blacklist, refresh_tokens, financial_records, users RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()

    await fake_redis.flushall()
    yield
    await fake_redis.flushall()
    await fake_redis.aclose()


@pytest_asyncio.fixture(scope="function")
async def client(clean_state) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def user_factory(client: AsyncClient) -> Callable:
    async def _create_user(role: str = "admin", password: str = "StrongPass123") -> dict:
        unique = uuid4().hex[:10]
        register_payload = {
            "email": f"{unique}@example.com",
            "username": f"user_{unique}",
            "password": password,
            "role": "viewer",
        }
        register_resp = await client.post("/api/v1/users/register", json=register_payload)
        assert register_resp.status_code == 201

        if role != "viewer":
            assert TestingSessionLocal is not None
            async with TestingSessionLocal() as session:
                user = await session.get(User, register_resp.json()["id"])
                assert user is not None
                user.role = UserRole(role)
                await session.commit()

        login_resp = await client.post(
            "/api/v1/users/login",
            json={"email": register_payload["email"], "password": password},
        )
        assert login_resp.status_code == 200

        return {
            "user": register_resp.json(),
            "tokens": login_resp.json(),
            "password": password,
            "email": register_payload["email"],
            "username": register_payload["username"],
        }

    return _create_user
