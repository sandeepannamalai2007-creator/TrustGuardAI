import logging

import crud
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Strict criteria for profile baseline adaptation to prevent profile poisoning
MIN_TRUST_SCORE = 70.0
MIN_SIMILARITY_SCORE = 60.0
MIN_TRUSTED_OBSERVATIONS = 3


def update_student_profile(
    db: Session,
    student_id: int,
    avg_dwell_time: float,
    avg_flight_time: float,
    typing_speed: float,
    mouse_velocity: float,
    trust_score: float = 100.0,
    similarity_score: float = 100.0,
    security_state: str = "NORMAL",
    high_trust_count: int = 3
) -> bool:
    """
    Updates the user's behavioral profile baseline if and only if strict conditions are met:
    1. High Trust Score (trust_score >= 70.0)
    2. High Profile Similarity (similarity_score >= 60.0)
    3. Stable Security State (security_state == "NORMAL")
    4. Multiple Observations (high_trust_count >= 3 consecutive trusted windows)

    Maintains existing 10% max drift protection (cap_change) in crud.update_behavior_profile.
    """
    profile = crud.get_behavior_profile(db, student_id)

    if profile is None:
        # Initialize initial baseline profile
        logger.info(f"[PROFILE INIT] Establishing initial enrollment profile for student {student_id}")
        return crud.create_behavior_profile(
            db=db,
            student_id=student_id,
            avg_dwell_time=avg_dwell_time,
            avg_flight_time=avg_flight_time,
            typing_speed=typing_speed,
            mouse_velocity=mouse_velocity
        )

    # During ENROLLING phase (N < 5), accumulate baseline samples without enforcing poisoning checks
    if profile.enrollment_status == "ENROLLING":
        logger.info(f"[ENROLLMENT ACCUMULATE] Adding enrollment sample {profile.enrollment_count + 1}/5 for student {student_id}")
        return crud.update_behavior_profile(
            db=db,
            profile=profile,
            avg_dwell_time=avg_dwell_time,
            avg_flight_time=avg_flight_time,
            typing_speed=typing_speed,
            mouse_velocity=mouse_velocity
        )

    # Once BASELINE_READY or AUTHENTICATING, validate multi-factor criteria for baseline update (Poisoning Resistance)
    if trust_score < MIN_TRUST_SCORE:
        logger.info(f"[PROFILE SHIELD] Rejected profile update: Trust score {trust_score:.1f}% < {MIN_TRUST_SCORE:.1f}%")
        return None

    if similarity_score < MIN_SIMILARITY_SCORE:
        logger.info(f"[PROFILE SHIELD] Rejected profile update: Similarity score {similarity_score:.1f}% < {MIN_SIMILARITY_SCORE:.1f}%")
        return None

    if security_state != "NORMAL":
        logger.info(f"[PROFILE SHIELD] Rejected profile update: Security state '{security_state}' != 'NORMAL'")
        return None

    if high_trust_count < MIN_TRUSTED_OBSERVATIONS:
        logger.info(f"[PROFILE SHIELD] Rejected profile update: High trust observation count {high_trust_count} < {MIN_TRUSTED_OBSERVATIONS}")
        return None


    logger.info(f"[PROFILE UPDATE] Multi-factor criteria satisfied. Updating profile baseline for student {student_id}...")
    return crud.update_behavior_profile(
        db=db,
        profile=profile,
        avg_dwell_time=avg_dwell_time,
        avg_flight_time=avg_flight_time,
        typing_speed=typing_speed,
        mouse_velocity=mouse_velocity
    )