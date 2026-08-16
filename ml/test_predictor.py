from ml.predictor import predict_trust_score


def test_predict_trust_score_returns_valid_range():
    features = {
        "avg_dwell_time_ms": 120.0,
        "avg_flight_time_ms": 150.0,
        "typing_speed_cps": 4.5
    }
    score = predict_trust_score(features)
    assert isinstance(score, (int, float))
    assert 0 <= score <= 100


def test_predict_trust_score_extreme_values():
    features = {
        "avg_dwell_time_ms": 0.0,
        "avg_flight_time_ms": 0.0,
        "typing_speed_cps": 0.0
    }
    score = predict_trust_score(features)
    assert isinstance(score, (int, float))
    assert 0 <= score <= 100