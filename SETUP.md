# Setup Guide

This guide helps you run the Finance Data Processing and Access Control Backend locally with minimal friction.

## Prerequisites

- Python 3.14
- PostgreSQL 16 or Docker
- Redis 7 or Docker
- Git

## 1. Clone and Enter Project

```bash
git clone <your-repo-url>
cd finance-system-backend
```

## 2. Configure Environment

Create .env from sample:

```bash
cp .env.example .env
```

Review and update values in .env as needed:

- DATABASE_HOST
- DATABASE_PORT
- DATABASE_NAME
- DATABASE_USER
- DATABASE_PASSWORD
- REDIS_HOST
- REDIS_PORT
- SECRET_KEY
- ADMIN_BOOTSTRAP_KEY
- RECYCLE_BIN_RETENTION_DAYS

## 3. Install Dependencies

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux or macOS:

```bash
source .venv/bin/activate
```

Then install packages:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Start Infrastructure

### Option A: Docker (recommended)

```bash
docker compose up -d postgres redis
```

### Option B: Local services

Ensure PostgreSQL and Redis are running and match .env connection values.

## 5. Run Migrations

```bash
alembic upgrade head
```

## 6. Run API

```bash
uvicorn app.main:app --reload
```

App URLs:

- Health: http://127.0.0.1:8000/health
- Swagger: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## 7. WebSocket Presence Quick Check

After obtaining an access token, connect to:

```text
ws://127.0.0.1:8000/ws/presence?token=<access_token>
```

## Troubleshooting

### Alembic enum already exists

If migration previously failed mid-run and enum types were created, rerun:

```bash
alembic upgrade head
```

The migration is idempotent for enum creation.

### Redis not reachable

Sensitive routes can return 503 when the limiter backend is unavailable. Start Redis and retry.

### Docker engine unavailable

If docker compose commands fail on Windows, ensure Docker Desktop is open and running.

## Optional: Run Full Stack in Docker

```bash
docker compose up -d
```

This starts postgres, redis, and api containers together.