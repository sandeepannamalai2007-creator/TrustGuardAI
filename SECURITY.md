# 🔒 TrustGuard AI: Security Policy & Limitations

This document outlines the security boundaries, limitations, and testing parameters of the TrustGuard AI continuous authentication console. This project is a proof-of-concept and technical demonstrator designed for deployment evaluations and academic/placement presentations.

---

## 🔑 1. Security Audit PIN Gate
* **Implementation**: Access to the database-backed security logs on the dashboard is protected by an admin PIN check (configured via TRUSTGUARD_ADMIN_PIN environment variable).
* **Limitation**: The PIN authentication is a mock administrative gateway verified on the backend via a simple request header (`X-Admin-PIN`). It is designed to demonstrate data-access visual control in mock dashboards, rather than a production-ready cryptographic role-based access control (RBAC) system.
* **Production Recommendation**: Real systems should authenticate users via standards like OAuth2 / OpenID Connect and secure logs behind cryptographically signed JSON Web Tokens (JWT) with fine-grained scopes.

---

## 🌐 2. CORS (Cross-Origin Resource Sharing) Boundaries
* **Implementation**: The backend CORS middleware (`backend/main.py`) restricts allowed incoming origins to:
  - `http://localhost` / `http://127.0.0.1` (Local development)
  - `http://localhost:8000` / `http://127.0.0.1:8000` (Backend API routes)
  - `"null"` (Required to allow local browser page loads via double-clicking `file:///.../capture.html` directly from the file explorer).
* **Limitation**: Allowing the `"null"` origin is necessary for local recruitment previews but opens the server to cross-origin requests from any local browser context.
* **Production Recommendation**: Remove `"null"` and scope origins strictly to the exact HTTPS domain from which the web app is served.

---

## 📊 3. Biometric Benchmarks (FAR/FRR)
* **Implementation**: Evaluation scripts demonstrate a False Rejection Rate (FRR) of **`2.09%`** and a False Acceptance Rate (FAR) of **`0.00%`** for bot attacks.
* **Limitation**: These metrics are evaluated against static historical benchmarks (including the DSL-StrongPassword dataset) and synthetic bot timing logs. Actual field numbers may vary depending on ambient user typing patterns, keyboard physical models, and network latency anomalies.

---

## 🛡️ 4. Profile Poisoning Safeguards
* **Implementation**: The profile updates mechanism is defended by two key rules:
  1. **Trust-Gated Updates**: Keystroke baseline profiles in the database are only updated if the active request's `trust_score` is greater than or equal to $50\%$. If a bot or intruder starts typing, their anomalous timing data is blocked from being written to the user's profile.
  2. **Step-Clipped Parameter Drift**: Adjustments to the baseline means (dwell, flight, speeds, velocities) are capped to a maximum change delta of **$10\%$ per update** using `cap_change` in `backend/crud.py`.
* **Security Context**: This ensures that even if an attacker manages to type close to the user's style, they cannot rapidly slide the baseline to corrupt or hijack the profile over time.

---

## 💾 5. Session Token Store
* **Implementation**: Session tokens (`session_id`) are generated in FastAPI and managed via a hybrid `SessionManager`. The manager connects to a Redis instance on localhost (offering shared state and TTL eviction across multiple server workers). If Redis is unreachable, the system automatically falls back to an isolated SQLite store (`backend/sessions.db`) to preserve persistence across backend restarts.
* **Security Context**: Fixes worker state splitting and session deletion on server restarts.

---

## ⚡ 6. Performance Latency Benchmarks
* **ML Inference Latency (predict_trust_score)**:
  - **Average**: `42.08 ms`
  - **95th Percentile (p95)**: `48.33 ms`
* **Features Telemetry Endpoint Roundtrip** (`/session/features` over 100 trials):
  - **Average**: `133.52 ms`
  - **95th Percentile (p95)**: `142.51 ms`
* **Performance Impact**: Sub-150ms verification round-trip guarantees transparent continuous identity confirmation during active sessions.
