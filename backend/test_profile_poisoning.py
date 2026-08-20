import crud
import pytest
from database import SessionLocal
from profile_service import update_student_profile


def test_profile_poisoning_resistance():
    """
    Security Experiment (Requirement 12):
    Tests profile baseline adaptation against deliberate poisoning attacks.
    An attacker attempts to gradually shift a legitimate user's profile from 100ms dwell to 350ms dwell.
    Verifies that multi-factor criteria (High Trust + High Similarity + Stable State + Observation Window)
    and 10% max drift protection successfully shield the profile baseline.
    """
    db = SessionLocal()
    try:
        # 1. Create Student and Baseline Profile
        student = crud.create_student(
            db=db,
            student_id="PoisoningTestUser",
            name="Poisoning Test Student",
            email="poison_test@trustguard.ai"
        )
        profile = crud.get_behavior_profile(db, student.id)
        if profile:
            db.delete(profile)
            db.commit()

        # Initialize Profile with 100.0ms dwell time baseline
        updated_init = update_student_profile(
            db=db,
            student_id=student.id,
            avg_dwell_time=100.0,
            avg_flight_time=150.0,
            typing_speed=4.5,
            mouse_velocity=200.0
        )
        assert updated_init is not None

        init_profile = crud.get_behavior_profile(db, student.id)
        assert init_profile.avg_dwell_time == pytest.approx(100.0, abs=1e-2)

        # 2. Simulate Attacker attempting to inject poisoned samples (350.0ms dwell time)
        # Attempt 1: Low similarity score (20%) + Low Trust (30%) -> SHIELDED
        rejected_1 = update_student_profile(
            db=db,
            student_id=student.id,
            avg_dwell_time=350.0,
            avg_flight_time=450.0,
            typing_speed=1.5,
            mouse_velocity=50.0,
            trust_score=30.0,
            similarity_score=20.0,
            security_state="SUSPICIOUS",
            high_trust_count=0
        )
        assert rejected_1 is None

        # Attempt 2: Attacker in SUSPICIOUS state -> SHIELDED
        rejected_2 = update_student_profile(
            db=db,
            student_id=student.id,
            avg_dwell_time=350.0,
            avg_flight_time=450.0,
            typing_speed=1.5,
            mouse_velocity=50.0,
            trust_score=75.0,
            similarity_score=65.0,
            security_state="SUSPICIOUS",
            high_trust_count=1
        )
        assert rejected_2 is None

        # Attempt 3: Single observation without 3 consecutive trusted windows -> SHIELDED
        rejected_3 = update_student_profile(
            db=db,
            student_id=student.id,
            avg_dwell_time=350.0,
            avg_flight_time=450.0,
            typing_speed=1.5,
            mouse_velocity=50.0,
            trust_score=75.0,
            similarity_score=65.0,
            security_state="NORMAL",
            high_trust_count=1
        )
        assert rejected_3 is None


        # 3. Verify Baseline Profile parameter remains un-poisoned (anchored at 100.0ms)
        final_profile = crud.get_behavior_profile(db, student.id)
        assert final_profile.avg_dwell_time == pytest.approx(100.0, abs=1e-2)

    finally:
        db.close()
