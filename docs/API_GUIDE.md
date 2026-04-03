# 📘 API Guide

Comprehensive endpoint reference for the Finance Data Processing and Access Control Backend.

> ⚡ Quick context: this service exposes 20 REST endpoints + 1 WebSocket endpoint under `/api/v1`.

---

## 🧭 At A Glance

| Type | Count |
|---|---|
| REST Endpoints | 20 |
| WebSocket Endpoints | 1 |
| API Prefix | `/api/v1` |

**Base URL (local):** `http://127.0.0.1:8000`

**Interactive docs:**

- Swagger: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

---

## ✅ Before You Start

1. Finish setup from [SETUP.md](SETUP.md)
2. Ensure PostgreSQL and Redis are running
3. Apply migrations using `alembic upgrade head`

---

## 🔐 Authentication Model

The system uses JWT access and refresh tokens.

- Access token: sent in Authorization header
- Refresh token: used in refresh endpoint
- Refresh rotation: old refresh token is revoked when a new pair is issued
- Revocation checks: Redis plus database blacklist

Authorization header format:

```http
Authorization: Bearer <access_token>
```

---

## 👥 Role Model

| Role | Allowed Actions |
|---|---|
| viewer | Read dashboard only |
| analyst | Read dashboard and financial records |
| admin | Full access to users and financial records |

---

## 🚨 Common Error Codes

| Status | Meaning |
|---|---|
| 400 | Invalid request data, e.g. `start_date > end_date` |
| 401 | Missing/invalid/expired/revoked token |
| 403 | Role does not have permission |
| 404 | Resource not found |
| 409 | Conflict, e.g. duplicate registration |
| 429 | Rate limit exceeded |
| 503 | Rate limiter backend unavailable |

---

## ❤️ Health Endpoint

### `GET /health`

- Auth: No
- Purpose: Service health check

Response:

```json
{
  "status": "ok"
}
```

---

## 👤 Users And Auth Endpoints

### `POST /api/v1/users/register`

- Auth: No
- Rate limited: Yes
- Purpose: Register a new user with viewer role

Request body:

```json
{
  "email": "user@example.com",
  "username": "normal_user",
  "password": "StrongPass123",
  "role": "viewer"
}
```

Security note:

- Self-registration is restricted to `viewer` role
- Sending `analyst` or `admin` in signup returns 403
- Privileged roles are assigned through admin-only management endpoint

Responses:

- 201 Created
- 409 Conflict when email or username already exists
- 403 Forbidden when role is analyst or admin

### `POST /api/v1/users/bootstrap-admin`

- Auth: No
- Rate limited: Yes
- Purpose: Securely create the very first admin user

Requirements:

- Environment variable `ADMIN_BOOTSTRAP_KEY` must be configured
- Header `X-Bootstrap-Key` must exactly match the configured key
- Endpoint is one-time: blocked once any admin already exists

Request body example:

```json
{
  "email": "founder-admin@example.com",
  "username": "founder_admin",
  "password": "StrongPass123",
  "role": "viewer"
}
```

Notes:

- Request role is ignored; created user is always `admin`

### `PATCH /api/v1/users/admin/users/{user_id}`

- Auth: Admin only
- Purpose: Update user role and/or active status

Request body example:

```json
{
  "role": "analyst",
  "is_active": true
}
```

### `POST /api/v1/users/admin/users`

- Auth: Admin only
- Purpose: Admin creates viewer or analyst account with initial credentials

Request body example:

```json
{
  "email": "analyst1@example.com",
  "username": "analyst1",
  "password": "StrongPass123",
  "role": "analyst"
}
```

Notes:

- This endpoint intentionally blocks direct `admin` creation
- Use role update flow for controlled admin promotion

### `POST /api/v1/users/login`

- Auth: No
- Rate limited: Yes
- Purpose: Exchange credentials for access and refresh tokens

Request body:

```json
{
  "email": "admin@example.com",
  "password": "StrongPass123"
}
```

Response:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

### `POST /api/v1/users/refresh`

- Auth: No
- Rate limited: Yes
- Purpose: Rotate refresh token and issue a new token pair

Request body:

```json
{
  "refresh_token": "..."
}
```

Responses:

- 200 OK with new token pair
- 401 Unauthorized for revoked, reused, or invalid refresh token

### `POST /api/v1/users/logout`

- Auth: Access token required
- Rate limited: Yes
- Purpose: Revoke current access token and optional refresh token

Request body:

```json
{
  "refresh_token": "..."
}
```

Response:

```json
{
  "message": "Logged out successfully"
}
```

### `GET /api/v1/users/me`

- Auth: Access token required
- Purpose: Fetch current authenticated user profile

### `GET /api/v1/users/admin/ping`

- Auth: Admin only
- Purpose: Verify admin-level authorization

Response:

```json
{
  "message": "Admin access granted"
}
```

### `GET /api/v1/users/admin/online-users`

- Auth: Admin only
- Purpose: List currently online users tracked by presence subsystem

Response:

```json
[1, 2, 10]
```

---

## 💰 Financial Records Endpoints

### `POST /api/v1/financial-records`

- Auth: Admin only
- Rate limited: Yes
- Purpose: Create a financial record

Request body:

```json
{
  "amount": "1200.50",
  "record_type": "income",
  "category": "salary",
  "entry_date": "2026-04-01",
  "notes": "monthly payout",
  "user_id": 1
}
```

Notes:

- `user_id` is optional
- If omitted, record is created for current admin user

### `GET /api/v1/financial-records`

- Auth: Analyst or Admin
- Purpose: List records with pagination and filters

Query params:

- `offset` (default 0)
- `limit` (default 20, max 100)
- `start_date`
- `end_date`
- `category`
- `record_type` (`income` or `expense`)

Validation rule:

- `start_date` cannot be after `end_date`

Response shape:

```json
{
  "total": 3,
  "offset": 0,
  "limit": 20,
  "items": [
    {
      "id": 1,
      "amount": "1200.50",
      "record_type": "income",
      "category": "salary",
      "entry_date": "2026-04-01",
      "notes": "monthly payout",
      "user_id": 1,
      "created_at": "2026-04-01T00:00:00Z",
      "updated_at": "2026-04-01T00:00:00Z"
    }
  ]
}
```

### `GET /api/v1/financial-records/{record_id}`

- Auth: Analyst or Admin
- Purpose: Fetch one record by id

### `PATCH /api/v1/financial-records/{record_id}`

- Auth: Admin only
- Rate limited: Yes
- Purpose: Partially update a record

Example request body:

```json
{
  "amount": "1300.00",
  "notes": "updated"
}
```

### `DELETE /api/v1/financial-records/{record_id}`

- Auth: Admin only
- Rate limited: Yes
- Purpose: Soft delete a record

Behavior:

- Sets `is_deleted` true and `deleted_at` timestamp
- Deleted records are excluded from standard reads
- Deleted records are retained in recycle bin up to configured retention days (default 30)

### `GET /api/v1/financial-records/bin/records`

- Auth: Admin only
- Purpose: List soft-deleted records currently in recycle bin
- Query params: `offset`, `limit`

### `POST /api/v1/financial-records/bin/records/{record_id}/restore`

- Auth: Admin only
- Purpose: Restore a soft-deleted record from recycle bin

Retention policy:

- Records older than configured retention window are automatically purged
- Expired records are not restorable

---

## 📊 Dashboard Endpoints

All dashboard endpoints require any authenticated role: `viewer`, `analyst`, or `admin`.

### Dashboard Endpoint Matrix

| Endpoint | Main Use | Typical Widget |
|---|---|---|
| `GET /api/v1/dashboard/summary` | KPI snapshot | Income/Expense/Net cards |
| `GET /api/v1/dashboard/categories` | Spend or income composition | Category pie/bar |
| `GET /api/v1/dashboard/recent-activity` | Latest changes | Recent activity table |
| `GET /api/v1/dashboard/monthly-trends` | Time-series behavior | Multi-line trend chart |

### Role-Based Dashboard Consumption

| Role | What They Usually Need |
|---|---|
| viewer | Read-only KPIs and trends |
| analyst | KPI + category + trend analysis |
| admin | Same analytics plus operational actions elsewhere |

### `GET /api/v1/dashboard/summary`

- Purpose: total income, total expenses, net balance
- Query params: `start_date`, `end_date`

Response:

```json
{
  "total_income": "1000.00",
  "total_expenses": "250.00",
  "net_balance": "750.00"
}
```

### `GET /api/v1/dashboard/categories`

- Purpose: category-wise totals
- Query params: `start_date`, `end_date`

Response:

```json
[
  {
    "category": "salary",
    "total": "1000.00"
  },
  {
    "category": "food",
    "total": "250.00"
  }
]
```

### `GET /api/v1/dashboard/recent-activity`

- Purpose: recent financial records ordered by newest
- Query params: `limit` (default 10, max 50)

### `GET /api/v1/dashboard/monthly-trends`

- Purpose: monthly grouped income and expense trends
- Query params: `start_date`, `end_date`

Response:

```json
[
  {
    "month": "2026-04",
    "income": "1000.00",
    "expense": "250.00"
  }
]
```

### High-Value Query Patterns

Example: Monthly snapshot

```http
GET /api/v1/dashboard/summary?start_date=2026-04-01&end_date=2026-04-30
```

Example: Quarterly trend analysis

```http
GET /api/v1/dashboard/monthly-trends?start_date=2026-01-01&end_date=2026-03-31
```

Example: Focused recent feed

```http
GET /api/v1/dashboard/recent-activity?limit=20
```

### Recommended Next Dashboard APIs (Roadmap)

The current implementation already provides a strong 4-endpoint base. Typical production extensions are:

1. `/dashboard/period-comparison`
2. `/dashboard/top-expense-categories`
3. `/dashboard/cashflow`
4. `/dashboard/anomalies`

These are recommendations and are not part of the currently implemented route set.

---

## 🔌 WebSocket Presence API

### `WS /ws/presence?token=<access_token>`

- Auth: Access token in query parameter
- Purpose: Track online/offline state and heartbeat

Client message examples:

- `ping`
- `pong`
- `heartbeat`

Server message examples:

- `{ "type": "heartbeat_ack", "status": "ok" }`
- `{ "type": "ping" }`
- `{ "type": "echo", "message": "..." }`

Presence behavior:

- On connect, user marked online in Redis with TTL
- Server sends ping when idle for heartbeat interval
- On disconnect, user marked offline

---

## 🧪 Practical Testing Order For Evaluators

1. Bootstrap first admin user
2. Login and capture access and refresh token
3. Call `users/me`
4. Create analyst account via admin endpoint
5. Create income and expense records
6. Soft delete a record, inspect recycle bin, then restore
7. Call dashboard summary and categories
8. Refresh token and verify old refresh token is rejected on reuse
9. Logout and verify old access token no longer works
