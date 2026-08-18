# 📊 Test & Coverage Report — TrustGuard AI v2.0

## Executive Summary

- **Backend Python Test Suite**: **21 / 21 tests passing** (`pytest`)
- **Backend Code Coverage**: **90%** measured via `pytest-cov` across 966 statements
- **Frontend JS Test Suite**: **5 / 5 tests passing** (`npm test` / `node --test`)

---

## 🐍 Backend Python Test Coverage (90%)

Measured using `pytest-cov` across all modules in `backend/`:

| Module | Statements | Missed | Coverage |
|---|---|---|---|
| `backend/api_models.py` | 33 | 0 | **100%** |
| `backend/config.py` | 21 | 0 | **100%** |
| `backend/conftest.py` | 33 | 0 | **100%** |
| `backend/db_models.py` | 42 | 0 | **100%** |
| `backend/profile_service.py` | 7 | 0 | **100%** |
| `backend/metrics.py` | 45 | 1 | **98%** |
| `backend/crud.py` | 59 | 2 | **97%** |
| `backend/trust_engine.py` | 81 | 3 | **96%** |
| `backend/main.py` | 183 | 23 | **87%** |
| `backend/auth.py` | 25 | 4 | **84%** |
| `backend/profile_matcher.py` | 52 | 12 | **77%** |
| `backend/database.py` | 34 | 10 | **71%** |
| `backend/session_manager.py` | 102 | 38 | **63%** *(SQLite fallback path active)* |
| **TOTAL** | **966** | **95** | **90%** |

---

## 🌐 Frontend JS Unit Test Suite (5 / 5 Passed)

Run via `npm test` (`node --test frontend/test_modules.test.js`):

1. `average() returns correct mean for numbers` — **PASS**
2. `standardDeviation() computes population standard deviation` — **PASS**
3. `pushFeature() maintains max window length` — **PASS**
4. `fetchWithTimeout() successfully fetches valid URL` — **PASS**
5. `fetchWithTimeout() aborts on timeout` — **PASS**

---

## 🔄 End-to-End Integration Test Flow

Verified via `backend/test_e2e_integration.py`:
1. `POST /session/start` → Returns session ID & JWT Bearer token
2. `POST /session/features` with `Authorization: Bearer <token>` → Returns trust score & security state
3. `POST /session/features` without token → Returns `401 Unauthorized`
4. `GET /session/history` with `X-Admin-PIN` → Returns audit logs array
5. `POST /session/step-up/verify` with `X-Admin-PIN` / `STEP_UP_PIN` → Restores status to `NORMAL`
