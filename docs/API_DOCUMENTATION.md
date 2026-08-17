# 📚 API Documentation

This document describes the REST API endpoints provided by the TrustGuard AI backend.

Interactive OpenAPI/Swagger documentation is available at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## `POST /session/start`
Starts a new continuous authentication session.

**Request Schema:**
None (empty body).

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
