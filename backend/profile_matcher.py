from db_models import BehaviorProfile


def compare_with_profile(
    profile: BehaviorProfile,
    avg_dwell_time: float,
    avg_flight_time: float,
    typing_speed: float,
    mouse_velocity: float,
):
    """
    Compare current behaviour with the stored behaviour profile.
    Returns a tuple: (similarity_score from 0 to 100, list of parameter explanation strings).
    """

    import math

    explanations = []

    def similarity_and_explain(current, expected, name):
        if expected == 0:
            return 100.0, f"{name} profile not initialized."

        difference = abs(current - expected)
        dev_pct = (difference / expected) * 100.0
        val = math.exp(- (difference / expected)) * 100.0
        
        explanation = f"{name} deviated {dev_pct:.1f}% from baseline (Score: {val:.1f}%)"
        return val, explanation

    dwell_score, dwell_explain = similarity_and_explain(
        avg_dwell_time,
        profile.avg_dwell_time,
        "Dwell time"
    )
    explanations.append(dwell_explain)

    flight_score, flight_explain = similarity_and_explain(
        avg_flight_time,
        profile.avg_flight_time,
        "Flight time"
    )
    explanations.append(flight_explain)

    typing_score, typing_explain = similarity_and_explain(
        typing_speed,
        profile.typing_speed,
        "Typing speed"
    )
    explanations.append(typing_explain)

    mouse_score, mouse_explain = similarity_and_explain(
        mouse_velocity,
        profile.mouse_velocity,
        "Mouse velocity"
    )
    explanations.append(mouse_explain)

    overall = (
        dwell_score +
        flight_score +
        typing_score +
        mouse_score
    ) / 4

    return round(overall, 2), explanations