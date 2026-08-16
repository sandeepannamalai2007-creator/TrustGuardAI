from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from profile_service import update_student_profile
from profile_matcher import compare_with_profile

from database import get_db
import crud

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
    set_exam_session_id
)

from trust_engine import calculate_trust_score

app = FastAPI(
    title="TrustGuard AI",
    version="2.0"
)

# Scope CORS to trusted local origins and 'null' to support local file double-clicking
trusted_origins = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "null"  # Matches browser Origin header when capture.html is opened directly as a file:// URI
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
def start_session(
    request: StartSessionRequest,
    db: Session = Depends(get_db)
):

    # Check if the student already exists
    student = crud.get_student(db, request.user_id)

    # Create the student if not found
    if student is None:
        student = crud.create_student(
            db=db,
            student_id=request.user_id,
            name=request.user_id,
            email=f"{request.user_id}@trustguard.local"
        )

    # Create a TrustGuard session
    session = create_session(
        request.user_id,
        request.demo_mode
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


@app.post(
    "/session/features",
    response_model=FeatureResponse
)
def receive_features(
    request: FeatureRequest,
    db: Session = Depends(get_db)
):
    print("receive_features() called")

    session = get_session(request.session_id)

    if session is None:
        return FeatureResponse(
            status="error",
            message="Invalid Session ID",
            trust_score=0
        )

    success = add_features(
        request.session_id,
        request.model_dump()
    )

    # Look up the student who actually owns this session,
    # instead of a hardcoded name
    student = crud.get_student(db, session["user_id"])

    print("Student:", student)

    similarity_score = 100.0
    has_typing_data = request.avg_dwell_time_ms > 0

    if student and has_typing_data:
        profile = crud.get_behavior_profile(db, student.id)

        if profile:
            similarity_score = compare_with_profile(
                profile,
                request.avg_dwell_time_ms,
                request.avg_flight_time_ms,
                request.typing_speed_cps,
                request.avg_mouse_velocity_px_s
            )

        print("Similarity Score:", similarity_score)

        # Calculate trust score first to determine if we should update profile
        trust_score = calculate_trust_score(
            request.model_dump(),
            similarity_score
        )

        # Protect user baseline: only update if active sample is highly trusted
        if trust_score >= 50:
            print("Updating profile with trusted sample...")
            update_student_profile(
                db=db,
                student_id=student.id,
                avg_dwell_time=request.avg_dwell_time_ms,
                avg_flight_time=request.avg_flight_time_ms,
                typing_speed=request.typing_speed_cps,
                mouse_velocity=request.avg_mouse_velocity_px_s
            )
            print("Profile updated.")
        else:
            print(f"Skipping profile update: trust score {trust_score}% is below threshold.")
    else:
        trust_score = 100.0

    # Use the DB-backed exam session created at /session/start,
    # instead of a hardcoded session_id=1 for every request
    crud.create_trust_log(
        db=db,
        session_id=session["exam_session_id"],
        trust_score=trust_score,
        decision_score=similarity_score,
        avg_dwell=request.avg_dwell_time_ms,
        avg_flight=request.avg_flight_time_ms,
        typing_speed=request.typing_speed_cps
    )

    if not success:
        return FeatureResponse(
            status="error",
            message="Invalid Session ID",
            trust_score=0
        )

    return FeatureResponse(
        status="success",
        message="Features received successfully",
        trust_score=trust_score
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
def get_session_history(
    x_admin_pin: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Secure endpoint returning database session trust logs.
    Requires header X-Admin-PIN = "1234".
    """
    if x_admin_pin != "1234":
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