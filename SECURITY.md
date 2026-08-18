# 🔒 TrustGuard AI: Security Architecture & Vulnerability Policy

This document outlines the security architecture, authentication mechanisms, policy controls, and known security boundaries of the **TrustGuard AI v2.0** continuous authentication console.

---

## 🔑 1. Multi-Tier Authentication Architecture

TrustGuard AI enforces a strict separation between end-user biometric re-authentication and administrative override controls:

| Role / Feature | Credential | Environment Variable | Default (Dev) | Description |
|---|---|---|---|---|
| **Session Ingestion** | JWT Bearer Token | `TRUSTGUARD_JWT_SECRET` | `super-secret-...` | Issued on `/session/start`, required in `Authorization` header for `/session/features` |
| **Step-Up Challenge** | User Re-Auth PIN | `TRUSTGUARD_STEP_UP_PIN` | `9999` | Restores workstation status from `SUSPICIOUS`/`HIGH_RISK` back to `NORMAL` |
| **Admin Controls & Audit** | Admin Security PIN | `TRUSTGUARD_ADMIN_PIN` | `1234` | Unlocks raw database audit ledger, force lock/unlock, CSV compliance export, and ML retrain |

### Startup Security Warnings
On application startup, FastAPI evaluates environment variables and outputs a `CRITICAL` security audit log if production deployments rely on insecure defaults:
```
[SECURITY WARNING] TRUSTGUARD_ADMIN_PIN is using default '1234'. Set this env var before production deployment.
[SECURITY WARNING] TRUSTGUARD_JWT_SECRET is using default key. Set this env var before production deployment.
```

---

## 🛡️ 2. Security State Machine & Hysteresis

To prevent security state flapping on temporary noise or typing pauses, TrustGuard AI enforces state transitions through a 4-tier state machine with hysteresis:

$$\text{NORMAL} \xrightarrow{\text{3 consecutive scores } < 50} \text{SUSPICIOUS} \xrightarrow{\text{3 consecutive scores } < 50} \text{HIGH\_RISK} \xrightarrow{\text{3 consecutive scores } < 50} \text{LOCKED}$$

- **De-escalation**: Requires **2 consecutive scores $\ge 50$** to step down one risk level.
- **Immediate Lockout**: Synthetic bot signatures (standard deviation $< 2.0\text{ ms}$) or manual admin override trigger immediate transition to **`LOCKED`**.
- **Step-Up Invalidation**: Whenever the security state escalates to a higher risk level, `step_up_completed` is reset to `False`, forcing a fresh PIN verification challenge.

---

## 🔐 3. Profile Poisoning Safeguards

Keystroke baseline profiles in the database are defended by two complementary security rules:

1. **Trust-Gated Profile Updates**: Baseline profiles are updated **only** when `trust_score >= 50%`. Anomalous or intruder typing sequences are rejected from entering baseline calculations.
2. **Step-Clipped Parameter Drift**: Adjustments to baseline feature means (dwell time, flight time, typing speed, mouse velocity) are capped to a maximum change delta of **$\pm 10\%$ per update** via `cap_change()` in `backend/crud.py`.

---

## ⚡ 4. Rate Limiting & HTTPS Enforcement

- **Rate Limiting (`slowapi`)**:
  - `POST /session/start`: **30 requests / minute** per IP
  - `GET /session/history`: **5 requests / minute** per IP
- **HTTPS Enforcement**: `HTTPSRedirectMiddleware` is wired into `backend/main.py` and activated by setting `ENABLE_HTTPS_REDIRECT=True` in `config.py` or `.env`.

---

## 💾 5. Session Store Eviction & Fallback

Session state is managed via `SessionManager`:
- **Primary Store**: Redis on `localhost:6379` with automatic TTL eviction (1 hour / 3600s).
- **SQLite Fallback**: If Redis is unreachable, the system gracefully falls back to `backend/sessions.db` with timestamp-based expiry filtering.

---

## 📊 6. Biometric Benchmarks & Performance Latency

| Benchmark / Metric | Evaluated Value | Context |
|---|---|---|
| **False Acceptance Rate (FAR)** | **`0.00%`** | 0 synthetic bot attacks accepted |
| **False Rejection Rate (FRR)** | **`2.09%`** | Evaluated on 21,400 CMU keystroke samples |
| **ML Inference Latency** | **`42.08 ms`** | `predict_trust_score()` execution time |
| **Feature Telemetry Roundtrip** | **`133.52 ms`** | Complete HTTP `/session/features` roundtrip (p95: 142.51ms) |

---

## 📄 License & Intellectual Property

TrustGuard AI is licensed under the [MIT License](LICENSE) (Copyright © 2026 Sandeep Annamalai).
