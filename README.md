# 🛡️ TrustGuard AI: Zero-Trust Continuous Biometrics Console

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95.0+-009688.svg)](https://fastapi.tiangolo.com/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.2.0+-orange.svg)](https://scikit-learn.org/)
[![Coverage 90%](https://img.shields.io/badge/coverage-90%25-brightgreen.svg)](docs/COVERAGE_REPORT.md)
[![CI Pipeline](https://github.com/sandeepannamalai2007-creator/TrustGuardAI/actions/workflows/ci.yml/badge.svg)](https://github.com/sandeepannamalai2007-creator/TrustGuardAI/actions)


TrustGuard AI is a continuous biometric identity authentication console. Instead of authenticating a user just once at login (e.g., via password or MFA), TrustGuard AI continuously verifies that the person sitting at the keyboard is the legitimate user by analyzing their typing dynamics and mouse movement kinematics in real-time.

---

## 📐 Architecture & System Flow

The diagram below outlines how user telemetry travels from the frontend workstation to the FastAPI backend, where a hybrid ML model computes identity scores, flags threats, enforces state escalation, and logs results:

```mermaid
graph TD
    A["User Workstation (capture.html)"] -->|"Keyboard Dynamics & Mouse Kinematics"| B["JavaScript Capture Engine"]
    B -->|"POST /session/features (Bearer JWT)"| C["FastAPI Main Server (main.py)"]
    C -->|"Extract Features"| D["Trust Engine Evaluation"]
    D -->|"1. scikit-learn Isolation Forest"| E["Anomalies / Bot Detection"]
    D -->|"2. Mahalanobis Profile Kernel"| F["Keystroke Biometric Verification"]
    D -->|"3. Shannon Entropy Check"| G["Anti-Spoofing Bot Verification"]
    E --> H["Combined Identity Trust Score"]
    F --> H
    G --> H
    H -->|"Security State Hysteresis"| I["State Machine (NORMAL/SUSPICIOUS/HIGH_RISK/LOCKED)"]
    I -->|"Step-Up Challenge if Suspicious"| J["Step-Up PIN Modal"]
    H -->|"Write Audit Logs"| K["SQLite DB / Redis Session Store"]
    H -->|"Prometheus Exporter"| L["/metrics Telemetry Endpoint"]
    
    style A fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#fff
    style C fill:#0c4a6e,stroke:#38bdf8,stroke-width:2px,color:#fff
    style H fill:#581c87,stroke:#c084fc,stroke-width:2px,color:#fff
    style K fill:#14532d,stroke:#4ade80,stroke-width:2px,color:#fff
```

---

## ✨ Enterprise Security Features

- 🕵️ **Continuous Identity Verification**: Evaluates keystroke timing features (Dwell Times, Flight Times) and mouse movement speeds every 5 seconds.
- 🔑 **Cryptographic JWT Session Tokens**: Issuance of PyJWT signed tokens on session initialization with Bearer header verification on `/session/features`.
- 📊 **Prometheus Telemetry Endpoint**: Real-time metrics exporter at `/metrics` tracking http request rates, status codes, and moving average trust score metrics.
- 🛡️ **Step-Up Re-Authentication Challenge**: Triggers a dynamic glassmorphic PIN modal overlay (`#stepUpModal`) when security state escalates to `SUSPICIOUS` or `HIGH_RISK`.
- 📈 **SecOps Dashboard & Real-Time Trend Graph**: Live telemetry trend analysis on canvas (`#secopsChart`), active threat risk badges, and admin emergency force lock/unlock controls.
- 📥 **CSV Audit Ledger Export**: 1-click administrative export of compliance audit logs formatted as CSV via `GET /session/export/csv`.
- 🧠 **Adaptive Per-User Biometric Thresholds**: Personalized adaptive security bounds (35% to 65%) based on individual historical typing variance ($\max(35.0, 55.0 - 0.5 \cdot \sigma_{\text{dwell}})$).
- 🧹 **Automated Data Retention & Pruning**: Automated session cleanup routines purging expired SQLite session records.
- 🎨 **Unified Light & Dark Theme Support**: Full high-contrast Light & Cyber Dark themes with localStorage persistence and accessible canvas scaling.

---

## 📊 Model Performance & Biometric Evaluation

TrustGuard AI evaluates machine learning performance using a **Session-Disjoint Genuine Testing + Cross-Subject Impostor Evaluation** protocol across all 51 subjects in the CMU Keystroke Dynamics Benchmark Dataset (20,400 total test trials), strictly separated from automated evasion bot stress testing:

### 1. 🔬 Scientific Model Comparison Table
| Version | Feature Vector | EER (%) | FAR (@ T=85%) | FRR (@ T=85%) | ROC-AUC |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Baseline** | Dwell, Flight, Speed Averages | 26.63% | 26.63% | 26.63% | 0.8049 |
| **V2 (+ Rhythm)** | + Dwell/Flight Ratio & Pause Frequency | 25.05% | 25.05% | 25.05% | 0.8158 |
| **Selected Final** | **4D Keystroke + Mahalanobis Profile Matcher** | **`23.33%`** | **`23.33%`** | **`23.33%`** | **`0.8394`** |

### 2. 🧬 Session-Disjoint Genuine Testing + Cross-Subject Impostor Evaluation
```
Evaluation Metrics (CMU Keystroke Dynamics Benchmark)
──────────────────────────────────────────────────────────────────────────
Subjects Evaluated           : 51
Genuine Test Samples         : 10,200 (Sessions 26-50, Unseen)
Impostor Test Samples        : 10,200 (Cross-Subject)

Equal Error Rate (EER)       : 23.33% (at Operating Threshold T = 85.0%)
ROC Area Under Curve (AUC)   : 0.8394
──────────────────────────────────────────────────────────────────────────
```

### 3. 🛡️ Adversarial Stress Testing (Bot Evasion & Poisoning Defense)
```
Adversarial & Poisoning Defense
──────────────────────────────────────────────────────────────────────────
Script Bot Evasion FAR       : 0.00% (100.00% Blocked via Entropy IDS)
Erratic Attacker Evasion FAR  : 0.00% (100.00% Blocked via Anomaly Check)
Profile Poisoning Resistance : 100.00% (Shielded via Multi-Factor Criteria & 10% Drift Cap)
──────────────────────────────────────────────────────────────────────────
```

> Detailed methodologies, mathematical derivations, and limitation analyses are documented in [`docs/ML_EVALUATION.md`](docs/ML_EVALUATION.md). Generated evaluation plots are stored in [`ml/evaluation_results/`](ml/evaluation_results/).




---

## 📂 Project Structure

```
TrustGuardAI/
├── .github/workflows/
│   └── ci.yml             # GitHub Actions CI/CD Pipeline (Ruff + Pytest)
├── backend/
│   ├── main.py            # FastAPI Application & Security Endpoints
│   ├── config.py          # Centralized Pydantic Settings & Config
│   ├── auth.py            # PyJWT Token Issuance & Bearer Dependencies
│   ├── metrics.py         # Prometheus Telemetry Collector
│   ├── database.py        # SQLite Database connection setup
│   ├── db_models.py       # SQLAlchemy Database Schemas
│   ├── crud.py            # Database CRUD helper queries
│   ├── session_manager.py # Session Manager with Redis & SQLite Stores
│   ├── trust_engine.py    # Hybrid biometric decision maker & state machine
│   └── profile_matcher.py # Mahalanobis distance & adaptive threshold engine
├── ml/
│   ├── train_model.py     # Model training script
│   ├── evaluate_model.py  # Model evaluation and FAR/FRR test suite
│   ├── preprocess.py      # Feature engineering helper
│   ├── model.pkl          # Serialized scikit-learn Isolation Forest model
│   └── scaler.pkl         # Serialized StandardScaler model parameters
├── frontend/
│   ├── capture.html       # Cybersecurity Console UI & SecOps Dashboard
│   ├── style.css          # Glassmorphic cyber themes & Light/Dark styling
│   └── script.js          # Telemetry collection, SecOps chart & Step-Up JS
└── trustguard.db          # SQLite Database File
```

---

## 🚀 Getting Started

### 1. Setup virtual environment & dependencies
```bash
# Clone repository
git clone https://github.com/sandeepannamalai2007-creator/TrustGuardAI.git
cd TrustGuardAI

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate   # Windows
source venv/bin/activate # Linux/macOS

# Install requirements
pip install -r requirements.txt
```

### 2. Run FastAPI Backend
```bash
python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
```

### 3. Run Automated Tests
```bash
python -m pytest --verbose
```

### 4. Docker Deployment (Recommended for Production)
```bash
# Copy and configure your secrets
cp .env.example .env  # set TRUSTGUARD_JWT_SECRET, TRUSTGUARD_ADMIN_PIN, TRUSTGUARD_STEP_UP_PIN

# Start backend + Redis in one command
docker compose up
```

---

## 🗄️ Production Deployment Notes

> [!IMPORTANT]
> **SQLite is used for zero-configuration local development only.**
> Under concurrent load (multiple simultaneous exam sessions), SQLite's single-writer lock will become a bottleneck.
> For production, migrate to **PostgreSQL** by setting the `DATABASE_URL` environment variable:
> ```
> DATABASE_URL=postgresql://user:password@host:5432/trustguard
> ```
> No code changes are required — SQLAlchemy handles the dialect automatically.

### Required Environment Variables (Production)

| Variable | Purpose | Default (Insecure) |
|---|---|---|
| `TRUSTGUARD_JWT_SECRET` | JWT signing key | `super-secret-...-change-in-production` |
| `TRUSTGUARD_ADMIN_PIN` | Admin ledger & override PIN | `1234` |
| `TRUSTGUARD_STEP_UP_PIN` | User step-up re-auth PIN | `9999` |
| `DATABASE_URL` | PostgreSQL connection string | *(empty — falls back to SQLite)* |
| `REDIS_HOST` | Redis hostname | `localhost` |

TrustGuard AI logs a **CRITICAL** warning on startup if any of these remain at their insecure defaults.

---

## 🤖 ML Model Retraining

The Isolation Forest model ships pre-trained on the CMU Keystroke Dynamics dataset.
As users interact with TrustGuard AI, trusted session data accumulates in the `trust_logs` table.

**To retrain the model on accumulated data:**
```bash
# CLI (requires ≥ 50 trusted samples, or use --force)
python ml/retrain.py
python ml/retrain.py --force   # bypass sample threshold

# API (hot-reloads model without server restart)
curl -X POST http://127.0.0.1:8000/admin/retrain \
  -H "X-Admin-PIN: your_admin_pin"
```

The retraining log is saved to `ml/saved_model/retrain_log.json`.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
