"""
ml/retrain.py

Scheduled / on-demand model retraining script.
Loads trusted TrustLog records from the database, extracts feature vectors,
and retrains the Isolation Forest if enough new samples have accumulated
since the last training run.

Can be called directly:
    python ml/retrain.py

Or triggered via the /admin/retrain API endpoint.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np

# ---------------------------------------------------------------------------
# Allow importing from parent directories when run as a script
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sklearn.ensemble import IsolationForest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_PATH = BASE_DIR / "saved_model" / "trust_model.pkl"
RETRAIN_LOG_PATH = BASE_DIR / "saved_model" / "retrain_log.json"
MIN_NEW_SAMPLES = 50  # Minimum trusted samples required to trigger retraining


def _load_retrain_log() -> dict:
    """Load the persisted retraining log, or return defaults."""
    if RETRAIN_LOG_PATH.exists():
        with open(RETRAIN_LOG_PATH) as f:
            return json.load(f)
    return {"last_retrain_utc": None, "samples_trained_on": 0, "retrain_count": 0}


def _save_retrain_log(log: dict) -> None:
    RETRAIN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RETRAIN_LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)


def _fetch_trusted_samples() -> np.ndarray:
    """
    Query the SQLite TrustLog table for accepted biometric samples
    (trust_score >= 60) and return them as a numpy feature matrix.
    """
    import sqlite3
    db_path = BACKEND_DIR / "trustguard.db"
    if not db_path.exists():
        logger.warning("[RETRAIN] trustguard.db not found — cannot fetch samples.")
        return np.empty((0, 3))

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT avg_dwell, avg_flight, typing_speed
        FROM trust_logs
        WHERE trust_score >= 60
          AND avg_dwell > 0
          AND avg_flight > 0
          AND typing_speed > 0
    """)
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return np.empty((0, 3))
    return np.array(rows, dtype=float)


def retrain_model(force: bool = False) -> dict:
    """
    Check whether enough new trusted samples have accumulated and, if so,
    retrain the Isolation Forest model and hot-swap the saved artifact.

    Args:
        force: If True, retrain regardless of sample count threshold.

    Returns:
        dict with keys: triggered (bool), message (str), samples_used (int)
    """
    log = _load_retrain_log()
    X = _fetch_trusted_samples()
    n_samples = len(X)

    if n_samples < MIN_NEW_SAMPLES and not force:
        msg = (
            f"[RETRAIN] Skipped — only {n_samples} trusted samples available "
            f"(minimum required: {MIN_NEW_SAMPLES})."
        )
        logger.info(msg)
        return {"triggered": False, "message": msg, "samples_used": n_samples}

    logger.info(f"[RETRAIN] Starting retraining on {n_samples} trusted samples...")

    # Clip outliers before training
    X = np.clip(X, 0, None)
    X = X[~np.any(np.isnan(X) | np.isinf(X), axis=1)]

    model = IsolationForest(
        n_estimators=300,
        contamination=0.10,
        random_state=42
    )
    model.fit(X)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    # Update log
    log["last_retrain_utc"] = datetime.now(timezone.utc).isoformat()
    log["samples_trained_on"] = n_samples
    log["retrain_count"] = log.get("retrain_count", 0) + 1
    _save_retrain_log(log)

    msg = (
        f"[RETRAIN] Successfully retrained on {n_samples} trusted samples. "
        f"Total retrains: {log['retrain_count']}."
    )
    logger.info(msg)
    return {"triggered": True, "message": msg, "samples_used": n_samples}


if __name__ == "__main__":
    result = retrain_model(force="--force" in sys.argv)
    print(result["message"])
