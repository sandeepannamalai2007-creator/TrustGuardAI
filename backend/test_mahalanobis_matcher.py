from unittest.mock import Mock, patch

from backend.profile_matcher import compare_with_profile


class MockProfile:
    def __init__(self):
        self.student_id = "test_student"
        self.avg_dwell_time = 100.0
        self.avg_flight_time = 120.0
        self.typing_speed = 5.0
        self.mouse_velocity = 200.0

class MockHistory:
    def __init__(self, dwell, flight, speed, vel):
        self.avg_dwell = dwell
        self.avg_flight = flight
        self.typing_speed = speed
        self.avg_mouse_velocity = vel

@patch("backend.profile_matcher.crud.get_student_feature_history")
def test_compare_with_profile_fallback(mock_get_history):
    # Test with < 5 history logs, which triggers fallback to default diagonal variance
    mock_get_history.return_value = []
    
    profile = MockProfile()
    db = Mock()
    
    score, explanations = compare_with_profile(
        db, profile, 
        avg_dwell_time=100.0, 
        avg_flight_time=120.0, 
        typing_speed=5.0, 
        mouse_velocity=0.0,
        std_dwell_time=10.0,
        std_flight_time=20.0,
        pause_count=0.0
    )


    
    # Distance is 0 -> score is 100.0
    assert score == 100.0

    assert len(explanations) == 7
    assert "Dwell time is 0.0 SD off baseline" in explanations[0]

@patch("backend.profile_matcher.crud.get_student_feature_history")
def test_compare_with_profile_mahalanobis(mock_get_history):
    # Test with 5+ history logs to compute covariance
    mock_get_history.return_value = [
        MockHistory(100.0, 120.0, 5.0, 200.0),
        MockHistory(102.0, 118.0, 5.1, 210.0),
        MockHistory(98.0, 122.0, 4.9, 190.0),
        MockHistory(105.0, 115.0, 5.2, 220.0),
        MockHistory(95.0, 125.0, 4.8, 180.0)
    ]

    profile = MockProfile()
    db = Mock()

    score, explanations = compare_with_profile(
        db, profile, 
        avg_dwell_time=110.0, # Slight deviation
        avg_flight_time=110.0, 
        typing_speed=4.5, 
        mouse_velocity=250.0
    )

    # Just asserting it calculates without error and score < 100
    assert score < 100.0
    assert score >= 0.0
    assert len(explanations) == 7

    # Check explanations have correct formatting
    assert any("SD off baseline" in exp for exp in explanations)

