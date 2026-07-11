from fastapi import FastAPI

from models import (
    StartSessionRequest,
    StartSessionResponse
)

from session_manager import (
    create_session
)

app = FastAPI(
    title="TrustGuard AI",
    version="1.0"
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
def start_session(request: StartSessionRequest):

    session = create_session(
        request.user_id,
        request.demo_mode
    )

    return StartSessionResponse(
        session_id=session["session_id"],
        status=session["status"],
        message="Session started successfully"
    )