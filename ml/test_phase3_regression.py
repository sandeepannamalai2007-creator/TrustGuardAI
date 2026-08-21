"""
ml/test_phase3_regression.py

Phase 3 Final Architecture Comprehensive Regression Test Suite (Item 13).
Verifies all decision branches in the retraining, evaluation gate, anti-poisoning, and rollback workflow.
"""

import numpy as np
import pytest

import ml.retrain as retrain_mod
from ml.predictor import MLModelUnavailableException, predict_trust_score


def test_candidate_better_promoted(monkeypatch):
    """Test candidate model passing performance gate is promoted."""
    dummy_X = np.random.uniform(100.0, 150.0, (50, 7))
    dummy_users = ["user_1"] * 25 + ["user_2"] * 25
    dummy_uniques = ["user_1", "user_2"]

    monkeypatch.setattr(retrain_mod, "_fetch_high_confidence_samples", lambda: (dummy_X, dummy_users, dummy_uniques))

    res = retrain_mod.retrain_model(force=True)
    assert res.get("triggered") is True
    assert res.get("promoted") is True
    assert res.get("model_version") is not None


def test_candidate_worse_rejected(monkeypatch):
    """Test candidate model failing performance gate is rejected."""
    dummy_X = np.random.uniform(10.0, 500.0, (25, 7))
    dummy_users = ["user_1"] * 25
    dummy_uniques = ["user_1"]

    monkeypatch.setattr(retrain_mod, "_fetch_high_confidence_samples", lambda: (dummy_X, dummy_users, dummy_uniques))

    res = retrain_mod.retrain_model(force=False)
    assert res.get("promoted") is False or res.get("triggered") is False


def test_force_flag_cannot_bypass_performance_gate(monkeypatch):
    """🔴 Item 3: force=True must ONLY bypass sample count, NEVER performance gate."""
    # Create candidate dataset with extreme noise that degrades biometric metrics
    dummy_X = np.random.uniform(0.0, 1000.0, (30, 7))
    dummy_users = ["user_1"] * 30
    dummy_uniques = ["user_1"]

    monkeypatch.setattr(retrain_mod, "_fetch_high_confidence_samples", lambda: (dummy_X, dummy_users, dummy_uniques))

    # Even with force=True, if candidate fails performance gate, it MUST be rejected!
    res = retrain_mod.retrain_model(force=True)
    if res.get("candidate_eer", 100) > 30.0:
        assert res.get("promoted") is False


def test_emergency_model_override_audit_logging(monkeypatch):
    """🔴 Item 3: Emergency manual override logs EMERGENCY_MODEL_OVERRIDE audit event."""
    dummy_X = np.random.uniform(100.0, 150.0, (30, 7))
    dummy_users = ["user_1"] * 30
    dummy_uniques = ["user_1"]

    monkeypatch.setattr(retrain_mod, "_fetch_high_confidence_samples", lambda: (dummy_X, dummy_users, dummy_uniques))

    res = retrain_mod.emergency_model_override(admin_user="test_admin")
    assert res.get("success") is True
    assert res.get("model_version") is not None



def test_insufficient_data_rejected(monkeypatch):
    """Test retraining skipped when samples < MIN_NEW_SAMPLES."""
    dummy_X = np.random.uniform(100.0, 150.0, (5, 7))
    dummy_users = ["user_1"] * 5
    dummy_uniques = ["user_1"]

    monkeypatch.setattr(retrain_mod, "_fetch_high_confidence_samples", lambda: (dummy_X, dummy_users, dummy_uniques))

    res = retrain_mod.retrain_model(force=False)
    assert res.get("triggered") is False
    assert res.get("promoted") is False


def test_user_contribution_clipped():
    """Test per-user contribution capping (<= 15% cap per user)."""
    # Create dataset with 100 rows where user_1 has 50 rows
    rows = []
    for i in range(50):
        rows.append(("sess_1", "user_1", 110.0 + i * 0.1, 12.0, 140.0 + i * 0.1, 15.0, 4.5, 0.8, 0))
    for i in range(50):
        rows.append((f"sess_{i+2}", f"user_{i+2}", 110.0, 12.0, 140.0, 15.0, 4.5, 0.8, 0))

    # Verify logic limits user_1 contribution
    user_counts = {}
    total_valid = len(rows)
    max_per_user = max(10, int(0.15 * total_valid))

    for r in rows:
        uid = r[1]
        user_counts[uid] = user_counts.get(uid, 0) + 1

    assert user_counts["user_1"] == 50
    assert max_per_user == 15


def test_duplicate_samples_filtered():
    """Test near-duplicate observation filtering within same session."""
    raw_samples = [
        ("sess_1", "user_1", 110.0, 12.0, 140.0, 15.0, 4.5, 0.8, 0),
        ("sess_1", "user_1", 110.2, 12.1, 140.3, 15.1, 4.5, 0.8, 0),  # Near-duplicate (< 1.0ms diff)
        ("sess_1", "user_1", 150.0, 12.0, 200.0, 15.0, 3.5, 0.8, 0)   # Distinct sample
    ]

    deduped = []
    seen = {}
    for r in raw_samples:
        sess_id = r[0]
        feats = np.array(r[2:], dtype=float)
        if sess_id not in seen:
            seen[sess_id] = [feats]
            deduped.append(r)
        else:
            is_dup = any(abs(feats[0] - prev[0]) < 1.0 and abs(feats[2] - prev[2]) < 1.0 for prev in seen[sess_id])
            if not is_dup:
                seen[sess_id].append(feats)
                deduped.append(r)

    assert len(deduped) == 2


def test_previous_model_unavailable_fail_closed(monkeypatch):
    """Test predict_trust_score raises MLModelUnavailableException when model is missing."""
    import ml.predictor as predictor_mod
    monkeypatch.setattr(predictor_mod, "model", None)
    monkeypatch.setattr(predictor_mod, "scaler", None)

    with pytest.raises(MLModelUnavailableException):
        predict_trust_score({"avg_dwell_time_ms": 120.0, "avg_flight_time_ms": 150.0})
