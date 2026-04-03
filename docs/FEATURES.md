# ✨ Features Overview

Comprehensive feature map for the Finance Data Processing and Access Control Backend.

> Built for secure finance operations, clean access control, and analytics-ready workflows.

---

## ⚙️ 1) Async-First Architecture

- All route handlers are async
- PostgreSQL access is fully async with SQLAlchemy AsyncSession and asyncpg
- Redis operations use redis asyncio client
- CPU-heavy tasks (password hashing and JWT operations) are offloaded with `asyncio.to_thread`

---

## 🔐 2) Secure JWT Authentication

- Access + refresh token pair issued on login
- Refresh token rotation on each refresh request
- Token revocation via `jti` blacklist
- Revocation state stored in database and mirrored in Redis for fast lookup

---

## 🛡️ 3) Role-Based Access Control (RBAC)

### Roles

- `viewer`
- `analyst`
- `admin`

### Access Behavior

- `viewer`: dashboard read access
- `analyst`: dashboard + records read access
- `admin`: user-management routes + full financial write access
- self-signup is viewer-only; privileged role assignment is admin-controlled
- first admin is provisioned through one-time bootstrap key flow

RBAC is enforced through backend dependency guards, not frontend trust.

---

## 💸 4) Financial Records Management

- Create, list, retrieve, update, and soft delete financial records
- Core fields: amount, type, category, date, notes, user id
- Filters: date range, category, record type
- Pagination with offset and limit
- Soft delete for auditability (no immediate hard loss)
- Recycle-bin endpoints for admin listing and restoring deleted records
- Automatic purge for expired recycle-bin records (default retention: 30 days)

---

## 📊 5) Dashboard Analytics APIs

- Summary totals for KPI cards:
  - total income
  - total expenses
  - net balance
- Category totals for composition analysis
- Recent activity feed for operational visibility
- Monthly trends endpoint for period analytics and forecasting workflows
- Date-range filtering across analytics endpoints
- Input validation for invalid date windows
- Centralized dashboard service for consistent metric computation
- Role-aware read access for viewer, analyst, and admin

---

## ⚡ 6) Redis Caching

- Dashboard aggregate endpoints are cached with TTL
- Cache invalidates on financial record mutations
- Cache invalidates on recycle-bin restore operations
- Graceful fallback to database computation if cache backend is unavailable

---

## 🚦 7) Rate Limiting

- Fixed-window limiter with Redis `INCR` + `EXPIRE`
- Applied to sensitive routes (register, login, refresh, logout, record mutations)
- Returns `429` with `Retry-After` on threshold exceed
- Returns controlled `503` when limiter backend is unavailable

---

## 🟢 8) Presence WebSocket

- Endpoint: `/ws/presence`
- Requires access token in query parameter
- Application-level heartbeat with `ping` and `heartbeat_ack`
- Online/offline presence tracked in Redis using TTL
- Admin endpoint can fetch online user IDs

---

## 🗃️ 9) Data Modeling And Persistence

- SQLAlchemy 2 model layer with explicit enums:
  - `UserRole`
  - `RecordType`
- Core entities:
  - `users`
  - `financial_records`
  - `refresh_tokens`
  - `token_blacklist`

### Schema Constraints

- positive amount check
- unique user email/username
- token uniqueness on `jti`
- indexed columns for common read paths

---

## 🔁 10) Migrations

- Alembic configured for async engine metadata
- Initial migration creates enums, tables, constraints, and indexes

---

## 🧪 11) Test Suite And CI

- 47 automated tests covering auth, RBAC, admin bootstrap, financial routes, recycle-bin retention, dashboard routes, presence service, and route surface
- Test isolation includes:
  - separate test database lifecycle
  - dependency-overridden async DB sessions
  - fakeredis-backed Redis isolation
- CI runs tests on every push and pull request with service containers

---

## 📚 12) Documentation Coverage

Dedicated guides are available for:

- Setup
- API usage
- testing strategy
- contribution workflow