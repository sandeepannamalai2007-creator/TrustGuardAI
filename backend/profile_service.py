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
    trust_score: float | None = None,
    similarity_score: float | None = None,
    security_state: str = "NORMAL",
    high_trust_count: int = 0,
    is_enrollment_sample: bool = False
):

    """
    Updates the user's behavioral profile baseline or accumulates pre-profile enrollment buffer samples.
    - Enrollment Samples (is_enrollment_sample=True or profile is None): Collected in EnrollmentBuffer (N < 5)
    - Active Adaptation (profile exists): Enforces strict multi-factor poisoning shields & 10% max drift cap.
    """
    # Quality Control Check (Point 2): Reject invalid or bot-like timing samples during enrollment
    if avg_dwell_time <= 30.0 or avg_dwell_time > 500.0 or avg_flight_time <= 10.0 or avg_flight_time > 800.0:
        logger.info(f"[ENROLLMENT REJECT] Rejected low-quality/bot timing sample during enrollment (dwell={avg_dwell_time:.1f}ms, flight={avg_flight_time:.1f}ms)")
        return None

    profile = crud.get_behavior_profile(db, student_id)

    if profile is None or is_enrollment_sample:

        # Collect sample into temporary pre-profile enrollment buffer (Item 1)
        crud.add_enrollment_sample_to_buffer(
            db=db,
            student_id=student_id,
            avg_dwell_time=avg_dwell_time,
            avg_flight_time=avg_flight_time,
            typing_speed=typing_speed,
            mouse_velocity=mouse_velocity
        )
        samples = crud.get_enrollment_buffer_samples(db, student_id)
        cnt = len(samples)

        if cnt < 5:
            logger.info(f"[ENROLLMENT BUFFER] Collected sample {cnt}/5 for student {student_id}. No official profile created yet.")
            class TransientEnrollmentProgress:
                enrollment_status = "ENROLLING"
                enrollment_count = cnt
                sample_count = cnt
            return TransientEnrollmentProgress()

        # 5 valid samples collected in buffer! Calculate final mean baseline μ and create official profile
        mean_dwell = float(sum(s.avg_dwell_time for s in samples) / 5.0)
        mean_flight = float(sum(s.avg_flight_time for s in samples) / 5.0)
        mean_speed = float(sum(s.typing_speed for s in samples) / 5.0)
        mean_mouse = float(sum(s.mouse_velocity for s in samples) / 5.0)

        crud.clear_enrollment_buffer(db, student_id)
        logger.info(f"[BASELINE READY] 5 valid enrollment samples collected. Creating official BehaviorProfile for student {student_id}.")
        return crud.create_behavior_profile(
            db=db,
            student_id=student_id,
            avg_dwell_time=mean_dwell,
            avg_flight_time=mean_flight,
            typing_speed=mean_speed,
            mouse_velocity=mean_mouse
        )

    # Once profile exists (BASELINE_READY or AUTHENTICATING), validate multi-factor criteria for baseline update (Poisoning Shield)
    if trust_score is None or trust_score < MIN_TRUST_SCORE:
        score_val = trust_score if trust_score is not None else 0.0
        logger.info(f"[PROFILE SHIELD] Rejected profile update: Trust score {score_val:.1f}% < {MIN_TRUST_SCORE:.1f}%")
        return None

    if similarity_score is None or similarity_score < MIN_SIMILARITY_SCORE:
        sim_val = similarity_score if similarity_score is not None else 0.0
        logger.info(f"[PROFILE SHIELD] Rejected profile update: Similarity score {sim_val:.1f}% < {MIN_SIMILARITY_SCORE:.1f}%")
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