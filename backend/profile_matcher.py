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
    Returns a similarity score from 0 to 100.
    """

    import math

    def similarity(current, expected):

        if expected == 0:
            return 100.0

        difference = abs(current - expected)

        # Exponential decay: e^(-diff/expected) * 100
        # If difference is 0, similarity is 100%.
        # If difference equals expected (100% deviation), similarity is ~36.8%.
        # Prevents similarity from dropping to 0 immediately for natural typing variations.
        val = math.exp(- (difference / expected)) * 100.0

        return val

    dwell_score = similarity(
        avg_dwell_time,
        profile.avg_dwell_time
    )

    flight_score = similarity(
        avg_flight_time,
        profile.avg_flight_time
    )

    typing_score = similarity(
        typing_speed,
        profile.typing_speed
    )

    mouse_score = similarity(
        mouse_velocity,
        profile.mouse_velocity
    )

    overall = (
        dwell_score +
        flight_score +
        typing_score +
        mouse_score
    ) / 4

    return round(overall, 2)