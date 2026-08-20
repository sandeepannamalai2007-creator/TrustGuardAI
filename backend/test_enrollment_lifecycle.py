"""
backend/test_enrollment_lifecycle.py

Automated test suite verifying the 5-window profile enrollment state machine:
NEW -> ENROLLING (N < 5) -> BASELINE_READY (N = 5) -> AUTHENTICATING (N > 5).
"""

import crud
import profile_service
from database import Base, SessionLocal, engine
from trust_engine import has_usable_biometric_signal


def test_enrollment_lifecycle_state_machine():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Setup student
        student = crud.get_student(db, "TestEnrollmentStudent")
        if student is None:
            student = crud.create_student(
                db,
                student_id="TestEnrollmentStudent",
                name="Enrollment Tester",
                email="enrollment@example.com"
            )

        # Clean existing profile
        profile = crud.get_behavior_profile(db, student.id)
        if profile is not None:
            db.delete(profile)
            db.commit()

        # 1. First observation (Sample 1/5): Profile initialized in ENROLLING state
        p1 = profile_service.update_student_profile(
            db=db,
            student_id=student.id,
            avg_dwell_time=100.0,
            avg_flight_time=150.0,
            typing_speed=5.0,
            mouse_velocity=200.0
        )
        assert p1.enrollment_status == "ENROLLING"
        assert p1.enrollment_count == 1
        assert p1.sample_count == 1

        # 2. Accumulate samples 2, 3, and 4: Remains ENROLLING
        for idx in range(2, 5):
            p = profile_service.update_student_profile(
                db=db,
                student_id=student.id,
                avg_dwell_time=102.0,
                avg_flight_time=148.0,
                typing_speed=5.1,
                mouse_velocity=205.0
            )
            assert p.enrollment_status == "ENROLLING"
            assert p.enrollment_count == idx

        # 3. 5th observation: Transitions to BASELINE_READY
        p5 = profile_service.update_student_profile(
            db=db,
            student_id=student.id,
            avg_dwell_time=100.0,
            avg_flight_time=150.0,
            typing_speed=5.0,
            mouse_velocity=200.0
        )
        assert p5.enrollment_status == "BASELINE_READY"
        assert p5.enrollment_count == 5

        # 4. 6th observation: Transitions to AUTHENTICATING
        p6 = profile_service.update_student_profile(
            db=db,
            student_id=student.id,
            avg_dwell_time=101.0,
            avg_flight_time=149.0,
            typing_speed=5.0,
            mouse_velocity=202.0,
            trust_score=85.0,
            similarity_score=80.0,
            security_state="NORMAL",
            high_trust_count=3
        )
        assert p6.enrollment_status == "AUTHENTICATING"
        assert p6.enrollment_count == 6

    finally:
        db.close()


def test_usable_biometric_signal_validation():
    # Valid biometric signal (5+ keys, non-zero dwell)
    valid_features = {"keystroke_count": 10, "avg_dwell_time_ms": 110.0}
    assert has_usable_biometric_signal(valid_features) is True

    # Invalid signal: < 5 keys
    few_keys = {"keystroke_count": 3, "avg_dwell_time_ms": 110.0}
    assert has_usable_biometric_signal(few_keys) is False

    # Invalid signal: 0 dwell time
    zero_dwell = {"keystroke_count": 10, "avg_dwell_time_ms": 0.0}
    assert has_usable_biometric_signal(zero_dwell) is False
