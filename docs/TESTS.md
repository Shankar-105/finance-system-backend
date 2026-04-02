# Testing Guide 🧪

Clean, repeatable backend testing with async pytest + isolated test DB + fakeredis.

---

## ✅ Current Status

- 47 tests passing
- Coverage includes:
	- auth + token lifecycle
	- RBAC and admin governance
	- financial CRUD + recycle bin retention/restore
	- dashboard endpoints
	- websocket presence service

---

## 🐳 Run Tests (Recommended)

From project root:

```bash
docker compose up -d --build
docker compose exec api pytest -q
```

Verbose mode:

```bash
docker compose exec api pytest -v
```

Single file:

```bash
docker compose exec api pytest tests/test_financial_records_routes.py -v
```

Keyword filter:

```bash
docker compose exec api pytest -k "dashboard" -v
```

---

## 💻 Optional Local Mode

If you are running without Docker:

```bash
.venv\Scripts\python.exe -m pytest -q
```

---

## 🧱 Isolation Model

The suite is safe by default:

- Creates a dedicated `<DATABASE_NAME>_test` database
- Rebuilds schema for clean sessions
- Uses dependency overrides for test DB sessions
- Uses fakeredis per test function
- Truncates tables between tests

No test writes to your normal development data.

---

## 📁 Test Layout

- `tests/test_auth_routes.py`
- `tests/test_rbac_users_routes.py`
- `tests/test_financial_records_routes.py`
- `tests/test_dashboard_routes.py`
- `tests/test_presence_websocket.py`
- `tests/test_route_surface.py`

---

## ⚠️ Quick Troubleshooting

### Tests fail before running

- Ensure containers are up: `docker compose ps`
- Check API logs: `docker compose logs -f api`

### DB-related errors

- Recreate stack: `docker compose down -v` then `docker compose up -d --build`

### Redis-related errors

- Verify redis container is healthy in `docker compose ps`

---

## 🔁 CI

GitHub Actions runs the same pytest suite on push and pull request.

Workflow: `.github/workflows/ci.yml`
