# Features

Comprehensive feature overview for the Finance Data Processing and Access Control Backend.

## 1. Async-First Architecture

- All route handlers use async functions.
- PostgreSQL access is fully async with SQLAlchemy AsyncSession and asyncpg.
- Redis operations use redis asyncio client.
- CPU-bound operations (password hashing and JWT operations) are offloaded with asyncio.to_thread.

## 2. Secure JWT Authentication

- Access and refresh token pair issued on login.
- Refresh token rotation on each refresh request.
- Token revocation supported with jti blacklist.
- Revocation state persisted in database and mirrored in Redis for fast lookup.

## 3. Role-Based Access Control

Roles:

- viewer
- analyst
- admin

Behavior:

- viewer: dashboard read access.
- analyst: dashboard plus records read access.
- admin: users admin routes and full financial records write access.
- self-signup is viewer-only; analyst/admin assignment is admin-controlled.
- first admin is created through one-time bootstrap key flow.

RBAC is enforced via dependency guards, not frontend trust.

## 4. Financial Records Management

- Create, list, retrieve, update, soft delete financial records.
- Fields include amount, type, category, date, notes, user id.
- Supports filtering by date range, category, and record type.
- Supports pagination using offset and limit.
- Soft delete keeps auditability without hard data loss.
- Recycle bin endpoints allow admin listing and restoring deleted records.
- Automatic purge removes records from recycle bin after retention window (default 30 days).

## 5. Dashboard Analytics APIs

- Summary totals: total income, total expenses, net balance.
- Category totals.
- Recent activity feed.
- Monthly trends grouped by month.
- Date-range filters available across analytics endpoints.

## 6. Redis Caching

- Dashboard aggregate endpoints are cached with TTL.
- Cache invalidation occurs on financial record mutations.
- Graceful fallback to DB computation if cache backend is unavailable.

## 7. Rate Limiting

- Fixed-window limiter implemented with Redis INCR and EXPIRE.
- Applied to sensitive routes (register, login, refresh, logout, and record mutations).
- Returns 429 with Retry-After when threshold is exceeded.
- Returns controlled 503 when limiter backend is unavailable.

## 8. Presence WebSocket

- Endpoint: /ws/presence
- Requires access token in query parameter.
- Application-level heartbeat support with ping and heartbeat_ack events.
- Online/offline presence tracked in Redis with TTL.
- Admin endpoint exposes current online user ids.

## 9. Data Modeling and Persistence

- SQLAlchemy 2 model layer with explicit enums:
- UserRole enum
- RecordType enum
- Core entities:
- users
- financial_records
- refresh_tokens
- token_blacklist

Schema constraints include:

- Positive amount check
- Unique user email/username
- Token uniqueness on jti
- Indexed columns for common read patterns

## 10. Migrations

- Alembic configured for async engine metadata.
- Initial migration creates enums, tables, constraints, and indexes.

## 11. Test Suite and CI

- 47 automated tests covering auth, RBAC, admin account provisioning, financial routes, recycle-bin retention behavior, dashboard routes, presence service, and route surface.
- Test isolation includes:
- Separate test database lifecycle
- Dependency-overridden async DB sessions
- fakeredis-backed Redis isolation
- CI workflow runs tests on every push and pull request with service containers.

## 12. Documentation Quality

- Dedicated docs provided for setup, API usage, testing, contribution workflow, and feature architecture.
- Suitable for internship evaluation and recruiter review.
