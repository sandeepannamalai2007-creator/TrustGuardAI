import crud
import profile_service
from database import Base, SessionLocal, engine


def test_profile_lifecycle():
    # Guarantee schema is initialized in the test session SQLite
    Base.metadata.create_all(bind=engine)
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
            db.delete(profile)
            db.commit()

        # Clean existing enrollment buffer
        crud.clear_enrollment_buffer(db, student.id)

        # 2. Test enrollment buffer accumulation (Samples 1 to 4)
        for idx in range(1, 5):
            prog = profile_service.update_student_profile(
                db=db,
                student_id=student.id,
                avg_dwell_time=100.0,
                avg_flight_time=150.0,
                typing_speed=5.0,
                mouse_velocity=200.0
            )
            assert prog.enrollment_status == "ENROLLING"
            assert prog.sample_count == idx

        # Official profile not created yet
        assert crud.get_behavior_profile(db, student.id) is None

        # 3. 5th valid sample creates official BehaviorProfile with mean baseline
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
        assert profile.sample_count == 5
        assert profile.enrollment_status == "BASELINE_READY"


        
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
