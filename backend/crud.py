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


DEFAULT_MAX_DRIFT_PCT = 0.10


def cap_change(current_val: float, new_val: float, max_pct: float = DEFAULT_MAX_DRIFT_PCT) -> float:
    """
    Limits the adjustment of any baseline parameter to at most max_pct (default 10%)
    of its current baseline value to prevent sudden poisoning shifts.
    """
    if current_val <= 0:
        return new_val
    max_delta = current_val * max_pct
    delta = new_val - current_val
    if abs(delta) > max_delta:
        return current_val + (max_delta if delta > 0 else -max_delta)
    return new_val


def update_behavior_profile(
    db: Session,
    profile: BehaviorProfile,
    avg_dwell_time: float,
    avg_flight_time: float,
    typing_speed: float,
    mouse_velocity: float,
):
    # Cap changes to prevent malicious parameter drift (Max 10% change per step)
    capped_dwell = cap_change(profile.avg_dwell_time, avg_dwell_time)
    capped_flight = cap_change(profile.avg_flight_time, avg_flight_time)
    capped_speed = cap_change(profile.typing_speed, typing_speed)
    capped_velocity = cap_change(profile.mouse_velocity, mouse_velocity)

    profile.avg_dwell_time = (
        profile.avg_dwell_time * profile.sample_count + capped_dwell
    ) / (profile.sample_count + 1)

    profile.avg_flight_time = (
        profile.avg_flight_time * profile.sample_count + capped_flight
    ) / (profile.sample_count + 1)

    profile.typing_speed = (
        profile.typing_speed * profile.sample_count + capped_speed
    ) / (profile.sample_count + 1)

    profile.mouse_velocity = (
        profile.mouse_velocity * profile.sample_count + capped_velocity
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
    avg_mouse_velocity: float,
):
    log = TrustLog(
        session_id=session_id,
        trust_score=trust_score,
        decision_score=decision_score,
        avg_dwell=avg_dwell,
        avg_flight=avg_flight,
        typing_speed=typing_speed,
        avg_mouse_velocity=avg_mouse_velocity
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return log


def get_student_feature_history(db: Session, student_id: int):
    """
    Fetch all historical genuine trust log features for a given student
    to build the covariance matrix for the Mahalanobis distance similarity model.
    """
    return (
        db.query(TrustLog)
        .join(ExamSession, TrustLog.session_id == ExamSession.id)
        .filter(ExamSession.student_id == student_id)
        .filter(TrustLog.trust_score >= 50.0)  # Filter out bot/anomaly samples to prevent poisoning
        .all()
    )


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
