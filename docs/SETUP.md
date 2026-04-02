# Setup Guide 🐳

This project is designed to run fast with Docker Compose. Use this path unless you intentionally want manual local service setup.

---

## ✅ Prerequisite

- Docker Desktop installed and running

Verify:

```bash
docker --version
docker compose version
```

---

## 🚦 Quick Setup (Recommended)

1. Clone and enter project.

```bash
git clone <your-repo-url>
cd finance-system-backend
```

2. Create env file.

```bash
cp .env.example .env
```

3. Start full stack.

```bash
docker compose up -d --build
```

4. Open API docs.

- Swagger: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Health: http://127.0.0.1:8000/health

That is enough to run the backend.

---

## 🔐 Important Environment Keys

Edit these in `.env` when needed:

- `SECRET_KEY`
- `ADMIN_BOOTSTRAP_KEY`
- `RECYCLE_BIN_RETENTION_DAYS`

Most database and redis values can stay at defaults for Docker Compose.

---

## 🧩 Useful Docker Commands

Start:

```bash
docker compose up -d
```

Logs:

```bash
docker compose logs -f api
```

Stop:

```bash
docker compose down
```

Stop + remove volumes (clears DB data):

```bash
docker compose down -v
```

---

## 🛠 Optional Local-Only Mode

Use this only if you do not want Docker for runtime:

1. Install Python 3.14, PostgreSQL, and Redis.
2. Activate venv and install `requirements.txt`.
3. Run migrations: `alembic upgrade head`.
4. Start API: `uvicorn app.main:app --reload`.

---

## 🧯 Troubleshooting

### Docker command fails

- Ensure Docker Desktop is running.
- Re-run with: `docker compose up -d --build`.

### API not reachable

- Check container logs: `docker compose logs -f api`.
- Check health endpoint: http://127.0.0.1:8000/health

### DB/Redis connection errors

- Confirm services are running: `docker compose ps`.
- Confirm `.env` values were not changed incorrectly.