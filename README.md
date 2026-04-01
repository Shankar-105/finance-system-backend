# Finance Data Processing and Access Control Backend

Async-first FastAPI backend for finance record management, dashboard analytics, secure JWT auth, strict role-based access control, Redis-backed rate limiting and caching, plus CI-tested reliability.

## Why This Project Stands Out

- Fully async stack: FastAPI + SQLAlchemy async + asyncpg + Redis asyncio.
- Production-style auth: Access and refresh JWT with rotation and revocation.
- Real RBAC: Viewer, Analyst, Admin enforced at backend dependency level.
- Data processing focus: Aggregates, category totals, trends, and recent activity APIs.
- Realtime capability: Presence WebSocket with application-level heartbeat.
- Quality signal: 36 passing tests + GitHub Actions CI.

## Tech Stack

- Python 3.14
- FastAPI
- PostgreSQL 16
- SQLAlchemy 2.x (async)
- asyncpg
- Redis 7
- Alembic
- Pydantic v2
- Pytest + pytest-asyncio + fakeredis
- Docker Compose

## Project Docs

- Full feature map: [FEATURES.md](FEATURES.md)
- Complete endpoint reference: [API_GUIDE.md](API_GUIDE.md)
- Setup guide (Docker + local): [SETUP.md](SETUP.md)
- Testing guide: [TESTS.md](TESTS.md)
- Contribution workflow: [CONTRIBUTING.md](CONTRIBUTING.md)

## Quick Start

1. Copy environment file.

```bash
cp .env.example .env
```

2. Start infrastructure.

```bash
docker compose up -d postgres redis
```

3. Install dependencies and migrate.

```bash
python -m pip install -r requirements.txt
alembic upgrade head
```

4. Start API.

```bash
uvicorn app.main:app --reload
```

5. Open docs.

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Test and CI

- Run tests locally:

```bash
python -m pytest -q
```

- CI workflow file:

[.github/workflows/ci.yml](.github/workflows/ci.yml)

It runs PostgreSQL + Redis services, installs dependencies, validates DB connectivity, and executes the full test suite on every push and pull request.

## Assignment Mapping

This implementation directly covers the internship assignment requirements:

- User and role management: Implemented.
- Financial record CRUD + filtering: Implemented.
- Dashboard summary and trends: Implemented.
- Access control logic: Implemented.
- Validation and error handling: Implemented.
- Data persistence with PostgreSQL: Implemented.
- Optional enhancements (auth, rate limits, tests, docs, CI, WebSocket): Implemented.