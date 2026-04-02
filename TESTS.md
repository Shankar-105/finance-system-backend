# Testing Guide

This project uses pytest with async fixtures, a dedicated PostgreSQL test database, and fakeredis for isolated Redis behavior.

## Current Test Status

- 47 tests passing.
- Coverage includes auth, RBAC, admin account provisioning, financial records, recycle-bin restore/retention purge, dashboard analytics, presence service, and route surface validation.

## Test Stack

- pytest
- pytest-asyncio
- httpx AsyncClient with ASGITransport
- fakeredis for Redis isolation
- asyncpg plus SQLAlchemy async for database integration tests

## Running Tests

From repository root:

```bash
python -m pytest -q
```

Verbose mode:

```bash
python -m pytest -v
```

Run a single file:

```bash
python -m pytest tests/test_financial_records_routes.py -v
```

Run tests by keyword:

```bash
python -m pytest -k "dashboard" -v
```

## How Isolation Works

In tests/conftest.py:

- A separate database named <DATABASE_NAME>_test is created automatically.
- Metadata is dropped and recreated once per test session.
- DB dependency is overridden to use a dedicated async session factory.
- Redis dependency is overridden with fakeredis per test.
- Tables are truncated before each test function for clean state.

This ensures test repeatability without touching local dev data.

## Test Organization

- tests/test_auth_routes.py
- tests/test_rbac_users_routes.py
- tests/test_financial_records_routes.py
- tests/test_dashboard_routes.py
- tests/test_presence_websocket.py
- tests/test_route_surface.py

## CI Integration

GitHub Actions runs the same pytest command on every push and pull request.

Workflow file:

- .github/workflows/ci.yml

CI bootstraps PostgreSQL and Redis service containers, installs dependencies, and executes tests.

## Common Test Troubleshooting

### Database connection errors

Check:

- DATABASE_HOST
- DATABASE_PORT
- DATABASE_USER
- DATABASE_PASSWORD

For local runs, ensure PostgreSQL is running and user has create database permissions.

### Redis errors

Application tests use fakeredis override, but local redis config still needs to be valid for non-overridden paths.

### Alembic mismatch in local environment

Apply migrations before starting manual API checks:

```bash
alembic upgrade head
```

## Adding New Tests

1. Add a test file under tests.
2. Reuse fixtures from tests/conftest.py.
3. Keep each test focused on one behavior.
4. Prefer explicit status and payload assertions.
5. Run full suite before pushing.
