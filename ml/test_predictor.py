import pytest

from ml.predictor import MLModelUnavailableException, predict_trust_score, reload_model


def test_predict_trust_score_returns_valid_range():
    reload_model()
    features = {
        "avg_dwell_time_ms": 120.0,
        "avg_flight_time_ms": 150.0,
        "typing_speed_cps": 4.5,
        "pause_count": 0
    }
    try:
        score = predict_trust_score(features)
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100
    except MLModelUnavailableException:
        # If model binary is not loaded, fail-closed exception is expected
        pytest.skip("Model binary not loaded; MLModelUnavailableException correctly enforced.")


def test_predict_trust_score_extreme_values():
    reload_model()
    features = {
        "avg_dwell_time_ms": 0.0,
        "avg_flight_time_ms": 0.0,
        "typing_speed_cps": 0.0,
        "pause_count": 0
    }
    try:
        score = predict_trust_score(features)
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100
    except MLModelUnavailableException:
        pytest.skip("Model binary not loaded; MLModelUnavailableException correctly enforced.")


def test_ml_model_unavailable_exception_handling(monkeypatch):
    import ml.predictor as predictor_mod
    monkeypatch.setattr(predictor_mod, "model", None)
    monkeypatch.setattr(predictor_mod, "scaler", None)

    features = {"avg_dwell_time_ms": 120.0, "avg_flight_time_ms": 150.0}
    with pytest.raises(MLModelUnavailableException):
        predict_trust_score(features)