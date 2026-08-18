# 📚 API Documentation

This document describes the REST API endpoints provided by the TrustGuard AI backend.

Interactive OpenAPI/Swagger documentation is available at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## `POST /session/start`
Starts a new continuous authentication session.

**Request Schema:**
```json
{
  "user_id": "string",
  "demo_mode": true
}
```

**Response Schema:**
```json
{
  "session_id": "string (UUID)",
  "status": "active"
}
```

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/session/start
```

## `POST /session/features`
Submits behavioral biometric telemetry for evaluation.

**Rate Limits:** 1 request per second per session (recommended).

**Headers:**
- `Authorization: Bearer <token>`: Required. The JWT token received from `POST /session/start`.

**Request Schema:**
```json
{
  "session_id": "string",
  "dwell_times": [100.5, 120.3],
  "flight_times": [150.2, 110.1],
  "mouse_velocities": [0.5, 1.2]
}
```

**Response Schema:**
```json
{
  "session_id": "string",
  "trust_score": 85.5,
  "is_human": true,
  "action": "allow"
}
```

## `GET /session/history`
Retrieves the audit log of all session evaluation histories.

**Headers:**
- `X-Admin-PIN`: Required string header containing the admin PIN for authorization.

**Rate Limits:** 10 requests per minute.

**Response Schema:**
```json
[
  {
    "id": 1,
    "session_id": "string",
    "timestamp": "2026-08-17T11:30:12",
    "trust_score": 85.5,
    "is_human": true
  }
]
```

## `GET /health`
Returns the health status of the API.

**Response Schema:**
```json
{
  "status": "healthy"
}
```

---

## `POST /session/step-up/verify`
Validates user Security PIN during step-up re-authentication challenge. Resets trust state to NORMAL on success.

**Request Schema:**
```json
{
  "session_id": "string (UUID)",
  "pin": "string"
}
```

**Response Schema:**
```json
{
  "status": "success",
  "message": "Step-Up verification successful.",
  "security_state": "NORMAL"
}
```

**Error Codes:**
- `401 Unauthorized` — Invalid PIN.
- `404 Not Found` — Invalid Session.

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/session/step-up/verify \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<uuid>", "pin": "<your-pin>"}'
```

## `POST /session/override/lock`
Admin force-lock — immediately sets session security state to LOCKED regardless of trust score.

**Request Schema:**
```json
{
  "session_id": "string",
  "admin_pin": "string"
}
```

**Response Schema:**
```json
{
  "status": "locked",
  "message": "Session forcibly locked."
}
```

**Error Codes:**
- `403 Forbidden` — Invalid PIN.
- `404 Not Found` — Invalid Session.

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/session/override/lock \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<uuid>", "admin_pin": "<admin-pin>"}'
```

## `POST /session/override/unlock`
Admin emergency unlock — resets session security state to NORMAL.

**Request Schema:**
```json
{
  "session_id": "string",
  "admin_pin": "string"
}
```

**Response Schema:**
```json
{
  "status": "unlocked",
  "message": "Session unlocked by admin."
}
```

**Error Codes:**
- `403 Forbidden` — Invalid PIN.
- `404 Not Found` — Invalid Session.

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/session/override/unlock \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<uuid>", "admin_pin": "<admin-pin>"}'
```

## `GET /session/export/csv`
Exports all TrustLog audit records as a downloadable CSV compliance report.

**Headers:**
- `X-Admin-PIN`: Required. The admin PIN for authorization.

**Response:** CSV file download (`Content-Type: text/csv`).

**Error Codes:**
- `403 Forbidden` — Invalid PIN.

**Example:**
```bash
curl -X GET http://127.0.0.1:8000/session/export/csv \
  -H "X-Admin-PIN: <admin-pin>" \
  --output trustlog_export.csv
```

## `POST /admin/retrain`
Triggers on-demand Isolation Forest model retraining on accumulated trusted session data. Hot-reloads the model in-process without a server restart.

Requires at least **50 trusted samples** (`trust_score >= 60`). Pass `?force=true` to override the sample threshold.

**Headers:**
- `X-Admin-PIN`: Required. The admin PIN for authorization.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `force` | bool | `false` | If `true`, bypasses the minimum sample threshold. |

**Response Schema:**
```json
{
  "triggered": true,
  "message": "Retrained on N samples.",
  "samples_used": 124
}
```

**Error Codes:**
- `403 Forbidden` — Invalid PIN.

**Example:**
```bash
curl -X POST "http://127.0.0.1:8000/admin/retrain?force=true" \
  -H "X-Admin-PIN: <admin-pin>"
```
