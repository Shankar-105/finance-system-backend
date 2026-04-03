# Basic App Flow 🧭

This is the practical workflow guide for this backend.

If you already checked `FEATURES.md` and `API_GUIDE.md`, this file is the missing piece: it explains how a real user journey moves from login to daily usage, and how the flow changes for viewer, analyst, and admin.

---

## Why This File Exists

- `FEATURES.md` tells you what exists.
- `API_GUIDE.md` tells you how to call each endpoint.
- This file tells you the real usage flow from start to finish.

---

## 1. First-Time System Bootstrap Flow

Before normal usage starts, first admin setup should happen once.

1. Configure `ADMIN_BOOTSTRAP_KEY` in `.env`.
2. Call `POST /api/v1/users/bootstrap-admin` with header `X-Bootstrap-Key`.
3. First admin account gets created.
4. This endpoint is blocked after an admin already exists.

Why this matters:

- Public users cannot self-register as admin.
- Privileged setup is controlled and one-time.

---

## 2. Normal User Registration Flow

For public signup:

1. User calls `POST /api/v1/users/register`.
2. Backend allows only `viewer` role in self-registration.
3. If user sends `analyst` or `admin`, backend returns `403`.
4. User logs in via `POST /api/v1/users/login` and receives:
- `access_token`
- `refresh_token`

---

## 3. Session Flow (All Roles)

After login, the common token lifecycle is:

1. Use access token in `Authorization: Bearer <token>`.
2. Access protected endpoints based on role.
3. When access token expires, call `POST /api/v1/users/refresh`.
4. Logout via `POST /api/v1/users/logout` to revoke active token usage.

Security behavior:

- Refresh tokens are rotated.
- Revocation checks are enforced.
- Invalid or revoked access fails with `401`.

---

## 4. Role-by-Role Workflow

## Viewer Flow

Viewer is read-only for dashboard analytics.

Typical steps:

1. Register as viewer.
2. Login.
3. Open dashboard:
- `GET /api/v1/dashboard/summary`
- `GET /api/v1/dashboard/categories`
- `GET /api/v1/dashboard/recent-activity`
- `GET /api/v1/dashboard/monthly-trends`
4. Viewer cannot access records CRUD or admin endpoints.

---

## Analyst Flow

Analyst accounts are created by admin.

Typical steps:

1. Admin creates analyst account using `POST /api/v1/users/admin/users`.
2. Analyst logs in with provided credentials.
3. Analyst can use all viewer dashboard reads.
4. Analyst can read financial records:
- `GET /api/v1/financial-records`
- `GET /api/v1/financial-records/{record_id}`
5. Analyst cannot create/update/delete records.

---

## Admin Flow

Admin handles operational and governance actions.

Typical steps:

1. Login as admin.
2. Create analyst/viewer accounts (`POST /api/v1/users/admin/users`).
3. Promote/demote roles and activate/deactivate users (`PATCH /api/v1/users/admin/users/{user_id}`).
4. Create and manage financial records:
- `POST /api/v1/financial-records`
- `PATCH /api/v1/financial-records/{record_id}`
- `DELETE /api/v1/financial-records/{record_id}`
5. Manage recycle bin:
- `GET /api/v1/financial-records/bin/records`
- `POST /api/v1/financial-records/bin/records/{record_id}/restore`
6. Monitor presence:
- `GET /api/v1/users/admin/online-users`

---

## 5. Financial Record Lifecycle (Real Path)

1. Admin creates income/expense entries.
2. Analyst/admin use filters and pagination while reading records.
3. Dashboard endpoints aggregate active (non-deleted) records.
4. When admin deletes a record, it goes to recycle bin.
5. Admin can restore record within retention window.
6. Expired deleted records are auto-purged based on retention config.

---

## 6. Dashboard Usage Pattern

Recommended usage sequence for frontend or API consumers:

1. Load `summary` for top cards.
2. Load `monthly-trends` for chart.
3. Load `categories` for distribution.
4. Load `recent-activity` for latest entries.

Behavior note:

- Aggregate dashboard endpoints use Redis caching.
- Cache invalidates on record changes and restores.

---

## 7. WebSocket Presence Flow

Presence endpoint: `WS /ws/presence?token=<access_token>`

Flow:

1. User connects with access token.
2. Backend validates token and user activity status.
3. User is marked online in Redis with TTL.
4. Heartbeat loop keeps status active.
5. On disconnect, user is marked offline.

---

## 8. Rate-Limit Behavior in Real Usage

Sensitive endpoints are protected with fixed-window limiting.

Limiter identity strategy:

- Anonymous traffic: IP-based limiting.
- Authenticated traffic (valid bearer token): user-based limiting.

This helps reduce spam on public endpoints and abuse on authenticated flows.

---

## 9. Quick End-to-End Example

A practical full journey:

1. Bootstrap first admin (one-time).
2. Admin logs in.
3. Admin creates analyst account.
4. Analyst logs in and reviews records + dashboard.
5. Admin creates/updates/deletes a few records.
6. Admin reviews recycle bin and restores one record.
7. All roles continue using dashboard with role-appropriate permissions.

---