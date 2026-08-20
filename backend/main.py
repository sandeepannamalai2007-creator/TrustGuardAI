import logging
import os
import sys

import crud
from api_models import (
    AdminLoginRequest,
    FeatureRequest,
    FeatureResponse,
    OverrideLockRequest,
    OverrideUnlockRequest,
    StartSessionRequest,
    StartSessionResponse,
    StepUpVerifyRequest,
    StudentCreate,
    StudentResponse,
)
from auth import create_access_token, verify_admin_token, verify_session_token
from config import settings
from database import Base, engine, get_db
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from metrics import MetricsMiddleware, metrics_collector
from profile_matcher import compare_with_profile, compute_adaptive_threshold
from profile_service import update_student_profile
from session_manager import (
    add_features,
    create_session,
    get_session,
    prune_expired_sessions,
    save_session,
    set_exam_session_id,
)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from trust_engine import (
    calculate_trust_score,
    has_usable_biometric_signal,
    is_step_up_required,
    update_security_state,
)

if os.path.join(os.path.dirname(__file__), '..') not in sys.path:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from ml.predictor import reload_model as reload_ml_model
from ml.retrain import retrain_model

logger = logging.getLogger(__name__)
ADMIN_PIN = settings.ADMIN_PIN

Base.metadata.create_all(bind=engine)

limiter = Limiter(key_func=get_remote_address)

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ADMIN_PIN == "1234":
        logger.critical("[SECURITY WARNING] TRUSTGUARD_ADMIN_PIN is using default '1234'. Set this env var before production deployment.")
    if "change-in-production" in settings.JWT_SECRET_KEY:
        logger.critical("[SECURITY WARNING] TRUSTGUARD_JWT_SECRET is using default key. Set this env var before production deployment.")
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(MetricsMiddleware)

if settings.ENABLE_HTTPS_REDIRECT:
    app.add_middleware(HTTPSRedirectMiddleware)

# Scope CORS to trusted origins from settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Admin-PIN", "Authorization"],
)




from fastapi.staticfiles import StaticFiles

frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")



@app.get("/health")
def health():
    prune_expired_sessions()
    return {
        "status": "Healthy"
    }



@app.get("/metrics")
def get_metrics():
    """
    Prometheus telemetry endpoint for scraping application performance and trust score metrics.
    """
    return Response(content=metrics_collector.generate_prometheus_output(), media_type="text/plain; version=0.0.4")


@app.post(
    "/session/start",
    response_model=StartSessionResponse
)
@limiter.limit(settings.RATE_LIMIT_START)
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

    # Generate JWT access token with role
    role = "admin" if (payload.admin_pin and payload.admin_pin == ADMIN_PIN) else "user"
    access_token = create_access_token(data={"sub": payload.user_id, "session_id": session["session_id"], "role": role})

    return StartSessionResponse(
        session_id=session["session_id"],
        status=session["status"],
        message="Session started successfully",
        access_token=access_token,
        token_type="bearer"
    )


@app.post("/admin/login")
def admin_login(payload: AdminLoginRequest):
    """
    Admin authentication endpoint. Issues an admin-scoped JWT access token.
    """
    if payload.admin_pin != ADMIN_PIN:
        raise HTTPException(status_code=403, detail="Invalid Admin Security PIN")
    
    access_token = create_access_token(data={"sub": "admin", "session_id": "admin_session", "role": "admin"})
    return {"access_token": access_token, "token_type": "bearer", "role": "admin"}



def _process_biometric_evaluation(db: Session, student, request: FeatureRequest):
    similarity_score = 100.0
    features_dict = request.model_dump()
    has_signal = has_usable_biometric_signal(features_dict)
    explanations = []

    if not has_signal:
        return 0.0, 0.0, ["INSUFFICIENT_SIGNAL: Insufficient biometric timing captured during window."]

    if student:
        profile = crud.get_behavior_profile(db, student.id)
        if profile and profile.enrollment_status in ("BASELINE_READY", "AUTHENTICATING"):
            similarity_score, explanations = compare_with_profile(
                db,
                profile,
                request.avg_dwell_time_ms,
                request.avg_flight_time_ms,
                request.typing_speed_cps,
                request.avg_mouse_velocity_px_s
            )
        else:
            explanations = ["Profile enrollment in progress — establishing behavioral baseline."]

        logger.debug(f"Similarity Score: {similarity_score}")
        trust_score = calculate_trust_score(features_dict, similarity_score)
    else:
        trust_score = calculate_trust_score(features_dict, 100.0)

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
    db: Session = Depends(get_db),
    token_payload: dict = Depends(verify_session_token)
):

    logger.debug("receive_features() called")
    
    # 1. Enforce JWT session_id = request session_id
    if request.session_id != token_payload.get("session_id"):
        raise HTTPException(
            status_code=403,
            detail="Session ID in JWT token does not match requested session ID"
        )

    session = get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Invalid Session ID")

    # 2. Enforce JWT sub (user_id) = session user_id
    if session.get("user_id") != token_payload.get("sub"):
        raise HTTPException(
            status_code=403,
            detail="User ID in JWT token does not match session user ID"
        )

    current_state = session.get("security_state", "NORMAL")
    if current_state == "LOCKED":
        return FeatureResponse(
            status="locked",
            message="Workstation Locked: Continuous security policy violations detected.",
            trust_score=0.0,
            security_state="LOCKED"
        )

    if not add_features(request.session_id, request.model_dump()):
        raise HTTPException(status_code=404, detail="Invalid Session ID")

    session = get_session(request.session_id)

    if not has_usable_biometric_signal(request.model_dump()):
        last_score = session.get("last_trust_score", 50.0)
        return FeatureResponse(
            status="insufficient_data",
            message="INSUFFICIENT_SIGNAL: No usable biometric timing collected during window. Security state preserved.",
            trust_score=last_score,
            security_state=current_state,
            explanations=["Insufficient biometric data captured during window."]
        )



    session["last_trust_score"] = session.get("last_trust_score", 50.0)
    student = crud.get_student(db, session["user_id"])
    profile = crud.get_behavior_profile(db, student.id) if student else None

    # Handle NEW / ENROLLING profile lifecycle phase
    if student and (profile is None or profile.enrollment_status == "ENROLLING"):
        updated_profile = update_student_profile(
            db=db,
            student_id=student.id,
            avg_dwell_time=request.avg_dwell_time_ms,
            avg_flight_time=request.avg_flight_time_ms,
            typing_speed=request.typing_speed_cps,
            mouse_velocity=request.avg_mouse_velocity_px_s,
            is_enrollment_sample=True
        )

        cnt = updated_profile.enrollment_count if updated_profile else 1
        status_str = updated_profile.enrollment_status if updated_profile else "ENROLLING"
        if status_str == "ENROLLING":
            save_session(request.session_id, session)
            return FeatureResponse(
                status="enrolling",
                message=f"Enrollment in progress (Sample {cnt}/5). Establishing behavioral baseline.",
                trust_score=100.0,
                security_state="NORMAL",
                explanations=[f"Enrollment phase active: {cnt}/5 trusted observation windows collected."]
            )

    adaptive_t = compute_adaptive_threshold(db, profile) if profile else 50.0

    trust_score, similarity_score, explanations = _process_biometric_evaluation(db, student, request)
    session["last_trust_score"] = trust_score
    metrics_collector.record_trust_score(trust_score)
    new_state = update_security_state(session, trust_score, adaptive_threshold=adaptive_t)

    # Attempt baseline adaptation (enforces high trust, high similarity, normal state, and observation count)
    if student:
        update_student_profile(
            db=db,
            student_id=student.id,
            avg_dwell_time=request.avg_dwell_time_ms,
            avg_flight_time=request.avg_flight_time_ms,
            typing_speed=request.typing_speed_cps,
            mouse_velocity=request.avg_mouse_velocity_px_s,
            trust_score=trust_score,
            similarity_score=similarity_score,
            security_state=new_state,
            high_trust_count=session.get("high_trust_count", 0)
        )

    step_up = is_step_up_required(session)
    save_session(request.session_id, session)

    _log_security_audit(db, session["exam_session_id"], trust_score, similarity_score, request)



    return FeatureResponse(
        status="locked" if new_state == "LOCKED" else ("warning" if step_up else "success"),
        message="Workstation Locked: Continuous security violations detected." if new_state == "LOCKED" else ("Step-Up Authentication Required." if step_up else "Features received successfully"),
        trust_score=trust_score,
        security_state=new_state,
        step_up_required=step_up,
        adaptive_threshold=adaptive_t,
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
@limiter.limit(settings.RATE_LIMIT_HISTORY)
def get_session_history(
    request: Request,
    x_admin_pin: str = Header(None),
    db: Session = Depends(get_db),
    admin_token: dict = Depends(verify_admin_token)
):
    """
    Secure endpoint returning database session trust logs.
    Requires Bearer JWT with admin role AND header X-Admin-PIN.
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



@app.post("/session/step-up/verify")
def verify_step_up(
    payload: StepUpVerifyRequest,
    token_payload: dict = Depends(verify_session_token)
):
    """
    Priority C: Step-Up Re-Authentication Endpoint.
    Requires valid JWT token matching the session_id and user_id, plus user PIN challenge.
    """
    # 1. Enforce JWT session_id = request session_id
    if payload.session_id != token_payload.get("session_id"):
        raise HTTPException(status_code=403, detail="Session ID in JWT token does not match requested session ID")

    session = get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Invalid Session ID")

    # 2. Enforce JWT sub (user_id) = session user_id
    if session.get("user_id") != token_payload.get("sub"):
        raise HTTPException(status_code=403, detail="User ID in JWT token does not match session user ID")

    # 3. Validate PIN against configured STEP_UP_PIN or ADMIN_PIN
    if payload.pin not in (settings.STEP_UP_PIN, ADMIN_PIN):
        raise HTTPException(status_code=401, detail="Invalid Step-Up Verification PIN")

    session["security_state"] = "NORMAL"
    session["low_trust_count"] = 0
    session["high_trust_count"] = 0
    session["step_up_completed"] = True
    save_session(payload.session_id, session)

    logger.info(f"[SECURITY] Step-Up Re-Authentication succeeded for session {payload.session_id}")
    return {"status": "success", "message": "Step-Up verification successful. Workstation status restored to NORMAL.", "security_state": "NORMAL"}


@app.post("/session/override/lock")
def override_lock(
    payload: OverrideLockRequest,
    admin_token: dict = Depends(verify_admin_token)
):
    """
    Priority C: Administrative Force Lock Intervention.
    Requires Admin JWT token and Admin PIN.
    """
    if payload.admin_pin != ADMIN_PIN:
        raise HTTPException(status_code=403, detail="Invalid Admin PIN")

    session = get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Invalid Session ID")

    session["security_state"] = "LOCKED"
    save_session(payload.session_id, session)
    logger.warning(f"[ADMIN OVERRIDE] Session {payload.session_id} forcibly LOCKED by administrator.")
    return {"status": "locked", "message": "Workstation forcibly locked by administrator.", "security_state": "LOCKED"}


@app.post("/session/override/unlock")
def override_unlock(
    payload: OverrideUnlockRequest,
    admin_token: dict = Depends(verify_admin_token)
):
    """
    Priority C: Administrative Emergency Unlock Override.
    Requires Admin JWT token and Admin PIN.
    """
    if payload.admin_pin != ADMIN_PIN:
        raise HTTPException(status_code=403, detail="Invalid Admin PIN")

    session = get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Invalid Session ID")

    session["security_state"] = "NORMAL"
    session["low_trust_count"] = 0
    session["high_trust_count"] = 0
    session["step_up_completed"] = True
    save_session(payload.session_id, session)
    logger.info(f"[ADMIN OVERRIDE] Session {payload.session_id} unlocked by administrator.")
    return {"status": "success", "message": "Workstation lock cleared by administrator.", "security_state": "NORMAL"}


@app.get("/session/export/csv")
def export_csv_report(
    x_admin_pin: str = Header(None),
    db: Session = Depends(get_db),
    admin_token: dict = Depends(verify_admin_token)
):
    """
    Priority C: Export Security Audit Logs as CSV Report.
    Requires Admin JWT token and Admin PIN.
    """
    if x_admin_pin != ADMIN_PIN:
        raise HTTPException(status_code=403, detail="Invalid Admin Security PIN")

    logs = crud.get_security_audit_logs(db, limit=200)
    
    csv_lines = ["Timestamp,Student_ID,Session_ID,Trust_Score,Decision_Score,Avg_Dwell_ms,Avg_Flight_ms,Typing_Speed_cps"]
    for log, student_id in logs:
        ts = log.timestamp.isoformat() if log.timestamp else ""
        csv_lines.append(f"{ts},{student_id},{log.session_id},{log.trust_score:.1f},{log.decision_score:.3f},{log.avg_dwell:.2f},{log.avg_flight:.2f},{log.typing_speed:.2f}")

    content = "\n".join(csv_lines)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="trustguard_audit_report.csv"'}
    )


@app.post("/admin/retrain")
def trigger_model_retrain(
    x_admin_pin: str = Header(None, alias="X-Admin-PIN"),
    force: bool = False,
    admin_token: dict = Depends(verify_admin_token)
):
    """
    Admin endpoint to trigger on-demand Isolation Forest model retraining.
    Requires Admin JWT token and Admin PIN.
    """
    if x_admin_pin != ADMIN_PIN:
        raise HTTPException(status_code=403, detail="Invalid Admin PIN")

    result = retrain_model(force=force)
    if result["triggered"]:
        reload_ml_model()
        logger.info("[ADMIN] Model retrained and hot-reloaded.")

    return {
        "triggered": result["triggered"],
        "message": result["message"],
        "samples_used": result["samples_used"]
    }


from fastapi.responses import FileResponse


@app.get("/")
def serve_root():
    capture_path = os.path.join(frontend_dir, "capture.html")
    if os.path.exists(capture_path):
        return FileResponse(capture_path)
    return {"project": settings.PROJECT_NAME, "version": settings.VERSION, "status": "Running"}

# Serve Frontend Web Application (capture.html, style.css, script.js, modules/*.js)
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

