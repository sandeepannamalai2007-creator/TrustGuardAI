from database import SessionLocal
import crud
import profile_service

def test_profile_lifecycle():
    db = SessionLocal()
    try:
        # 1. Setup mock student
        student = crud.get_student(db, "TestBiometricStudent")
        if student is None:
            student = crud.create_student(
                db,
                student_id="TestBiometricStudent",
                name="Biometrics Tester",
                email="tester@example.com"
            )
        
        # Clean existing behavior profile if present
        profile = crud.get_behavior_profile(db, student.id)
        if profile is not None:
            # Delete profile directly to clean state
            db.delete(profile)
            db.commit()

        # 2. Test create profile
        profile = profile_service.update_student_profile(
            db=db,
            student_id=student.id,
            avg_dwell_time=100.0,
            avg_flight_time=150.0,
            typing_speed=5.0,
            mouse_velocity=200.0
        )
        assert profile.student_id == student.id
        assert profile.avg_dwell_time == 100.0
        assert profile.avg_flight_time == 150.0
        assert profile.typing_speed == 5.0
        assert profile.mouse_velocity == 200.0
        assert profile.sample_count == 1

        # 3. Test capped drift updating
        # We send a huge jump (300.0 ms dwell). Capping limits it to 10% (100.0 + 10.0 = 110.0 ms).
        # When combined with the first sample (100.0), the mean becomes: (100.0 * 1 + 110.0) / 2 = 105.0 ms
        updated_profile = profile_service.update_student_profile(
            db=db,
            student_id=student.id,
            avg_dwell_time=300.0,
            avg_flight_time=150.0,
            typing_speed=5.0,
            mouse_velocity=200.0
        )
        assert updated_profile.sample_count == 2
        assert updated_profile.avg_dwell_time == 105.0 # (100 + 110) / 2
        
    finally:
        db.close()


def test_cap_change_bounds():
    # Test cap_change directly
    # Original 100.0, target 300.0 (greater than 10% of 100.0)
    capped = crud.cap_change(100.0, 300.0, max_pct=0.10)
    assert capped == 110.0

    # Original 100.0, target 50.0 (lesser than 10% of 100.0)
    capped_low = crud.cap_change(100.0, 50.0, max_pct=0.10)
    assert capped_low == 90.0

    # Original 100.0, target 105.0 (within 10% delta)
    capped_ok = crud.cap_change(100.0, 105.0, max_pct=0.10)
    assert capped_ok == 105.0
