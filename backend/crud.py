from sqlalchemy.orm import Session

from db_models import (
    Student,
    BehaviorProfile,
    ExamSession,
    TrustLog
)


def get_student(db: Session, student_id: str):
    return (
        db.query(Student)
        .filter(Student.student_id == student_id)
        .first()
    )


def create_student(
    db: Session,
    student_id: str,
    name: str,
    email: str
):
    existing = get_student(db, student_id)

    if existing:
        return existing

    student = Student(
        student_id=student_id,
        name=name,
        email=email
    )

    db.add(student)
    db.commit()
    db.refresh(student)

    return student


def get_behavior_profile(db: Session, student_id: int):
    return (
        db.query(BehaviorProfile)
        .filter(BehaviorProfile.student_id == student_id)
        .first()
    )


def create_behavior_profile(
    db: Session,
    student_id: int,
    avg_dwell_time: float,
    avg_flight_time: float,
    typing_speed: float,
    mouse_velocity: float,
):
    profile = BehaviorProfile(
        student_id=student_id,
        avg_dwell_time=avg_dwell_time,
        avg_flight_time=avg_flight_time,
        typing_speed=typing_speed,
        mouse_velocity=mouse_velocity,
        sample_count=1,
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return profile


def update_behavior_profile(
    db: Session,
    profile: BehaviorProfile,
    avg_dwell_time: float,
    avg_flight_time: float,
    typing_speed: float,
    mouse_velocity: float,
):
    profile.avg_dwell_time = (
        profile.avg_dwell_time * profile.sample_count + avg_dwell_time
    ) / (profile.sample_count + 1)

    profile.avg_flight_time = (
        profile.avg_flight_time * profile.sample_count + avg_flight_time
    ) / (profile.sample_count + 1)

    profile.typing_speed = (
        profile.typing_speed * profile.sample_count + typing_speed
    ) / (profile.sample_count + 1)

    profile.mouse_velocity = (
        profile.mouse_velocity * profile.sample_count + mouse_velocity
    ) / (profile.sample_count + 1)

    profile.sample_count += 1

    db.commit()
    db.refresh(profile)

    return profile


def create_exam_session(db: Session, student_id: int):
    session = ExamSession(student_id=student_id)

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


def create_trust_log(
    db: Session,
    session_id: int,
    trust_score: float,
    decision_score: float,
    avg_dwell: float,
    avg_flight: float,
    typing_speed: float,
):
    log = TrustLog(
        session_id=session_id,
        trust_score=trust_score,
        decision_score=decision_score,
        avg_dwell=avg_dwell,
        avg_flight=avg_flight,
        typing_speed=typing_speed
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return log


def get_security_audit_logs(db: Session, limit: int = 50):
    """
    Fetch historical session trust logs joined with student records
    for the secure admin audit ledger.
    """
    return (
        db.query(TrustLog, Student.student_id)
        .join(ExamSession, TrustLog.session_id == ExamSession.id)
        .join(Student, ExamSession.student_id == Student.id)
        .order_by(TrustLog.id.desc())
        .limit(limit)
        .all()
    )
