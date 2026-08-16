import os
import logging

logger = logging.getLogger(__name__)
ADMIN_PIN = os.environ.get("TRUSTGUARD_ADMIN_PIN", "1234")

from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
from profile_service import update_student_profile
from profile_matcher import compare_with_profile

from database import get_db, Base, engine
import db_models
import crud

Base.metadata.create_all(bind=engine)

from api_models import (
    StartSessionRequest,
    StartSessionResponse,
    FeatureRequest,
    FeatureResponse,
    StudentCreate,
    StudentResponse
)

from session_manager import (
    create_session,
    get_session,
    add_features,
    set_exam_session_id,
    save_session
)

from trust_engine import calculate_trust_score, update_security_state

app = FastAPI(
    title="TrustGuard AI",
    version="2.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Scope CORS to trusted local origins and 'null' to support local file double-clicking
trusted_origins = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:8000",
    "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=trusted_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Admin-PIN"],
)


@app.get("/")
def home():
    return {
        "project": "TrustGuard AI",
        "status": "Running"
    }


@app.get("/health")
def health():
    return {
        "status": "Healthy"
    }


@app.post(
    "/session/start",
    response_model=StartSessionResponse
)
@limiter.limit("30/minute")
def start_session(
    request: Request,
    payload: StartSessionRequest,
    db: Session = Depends(get_db)
):

    # Check if the student already exists
    student = crud.get_student(db, payload.user_id)

    # Create the student if not found
    if student is None:
        student = crud.create_student(
            db=db,
            student_id=payload.user_id,
            name=payload.user_id,
            email=f"{payload.user_id}@trustguard.local"
        )

    # Create a TrustGuard session
    session = create_session(
        payload.user_id,
        payload.demo_mode
    )

    # Create the matching DB-backed exam session so that
    # trust logs for this session can be tied back to it
    exam_session = crud.create_exam_session(db, student.id)
    set_exam_session_id(session["session_id"], exam_session.id)

    return StartSessionResponse(
        session_id=session["session_id"],
        status=session["status"],
        message="Session started successfully"
    )


def _process_biometric_evaluation(db: Session, student, request: FeatureRequest):
    similarity_score = 100.0
    has_typing_data = request.avg_dwell_time_ms > 0
    explanations = []

    if student and has_typing_data:
        profile = crud.get_behavior_profile(db, student.id)
        if profile:
            similarity_score, explanations = compare_with_profile(
                db,
                profile,
                request.avg_dwell_time_ms,
                request.avg_flight_time_ms,
                request.typing_speed_cps,
                request.avg_mouse_velocity_px_s
            )
        else:
            explanations = ["Profile training in progress - establishing baseline."]

        logger.debug(f"Similarity Score: {similarity_score}")
        trust_score = calculate_trust_score(request.model_dump(), similarity_score)

        if trust_score >= 50:
            logger.info("Updating profile with trusted sample...")
            update_student_profile(
                db=db,
                student_id=student.id,
                avg_dwell_time=request.avg_dwell_time_ms,
                avg_flight_time=request.avg_flight_time_ms,
                typing_speed=request.typing_speed_cps,
                mouse_velocity=request.avg_mouse_velocity_px_s
            )
            logger.info("Profile updated.")
        else:
            logger.info(f"Skipping profile update: trust score {trust_score}% is below threshold.")
    else:
        trust_score = 100.0
        if not has_typing_data:
            explanations = ["Bypassed validation: No typing data collected during window."]

    return trust_score, similarity_score, explanations

def _log_security_audit(db: Session, session_id: str, trust_score: float, similarity_score: float, request: FeatureRequest):
    crud.create_trust_log(
        db=db,
        session_id=session_id,
        trust_score=trust_score,
        decision_score=similarity_score,
        avg_dwell=request.avg_dwell_time_ms,
        avg_flight=request.avg_flight_time_ms,
        typing_speed=request.typing_speed_cps,
        avg_mouse_velocity=request.avg_mouse_velocity_px_s
    )

@app.post(
    "/session/features",
    response_model=FeatureResponse
)
def receive_features(
    request: FeatureRequest,
    db: Session = Depends(get_db)
):
    logger.debug("receive_features() called")
    session = get_session(request.session_id)
    if not session:
        return FeatureResponse(status="error", message="Invalid Session ID", trust_score=0, security_state="LOCKED")

    current_state = session.get("security_state", "NORMAL")
    if current_state == "LOCKED":
        return FeatureResponse(status="locked", message="Workstation Locked: Continuous security policy violations detected.", trust_score=0.0, security_state="LOCKED")

    if not add_features(request.session_id, request.model_dump()):
        return FeatureResponse(status="error", message="Invalid Session ID", trust_score=0, security_state=current_state)

    session = get_session(request.session_id)
    student = crud.get_student(db, session["user_id"])
    
    trust_score, similarity_score, explanations = _process_biometric_evaluation(db, student, request)
    new_state = update_security_state(session, trust_score)
    save_session(request.session_id, session)

    _log_security_audit(db, session["exam_session_id"], trust_score, similarity_score, request)

    return FeatureResponse(
        status="locked" if new_state == "LOCKED" else "success",
        message="Workstation Locked: Continuous security violations detected." if new_state == "LOCKED" else "Features received successfully",
        trust_score=trust_score,
        security_state=new_state,
        explanations=explanations
    )


@app.post(
    "/student/register",
    response_model=StudentResponse
)
def register_student(
    request: StudentCreate,
    db: Session = Depends(get_db)
):
    student = crud.create_student(
        db,
        request.student_id,
        request.name,
        request.email
    )

    return StudentResponse(
        student_id=student.student_id,
        name=student.name,
        email=student.email,
        message="Student registered successfully"
    )


@app.get("/session/history")
@limiter.limit("5/minute")
def get_session_history(
    request: Request,
    x_admin_pin: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Secure endpoint returning database session trust logs.
    Requires header X-Admin-PIN = "1234".
    """
    if x_admin_pin != ADMIN_PIN:
        raise HTTPException(status_code=403, detail="Invalid Admin Security PIN")

    logs = crud.get_security_audit_logs(db, limit=50)
    
    result = []
    for log, student_id in logs:
        result.append({
            "timestamp": log.timestamp.isoformat() if log.timestamp else "",
            "student_id": student_id,
            "session_id": log.session_id,
            "trust_score": log.trust_score,
            "decision_score": log.decision_score,
            "avg_dwell": log.avg_dwell,
            "avg_flight": log.avg_flight,
            "typing_speed": log.typing_speed
        })
    return result