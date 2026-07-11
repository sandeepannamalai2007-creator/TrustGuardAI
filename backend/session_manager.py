import uuid
from datetime import datetime

# Temporary in-memory storage
SESSIONS = {}


def create_session(user_id: str, demo_mode: bool):

    session_id = str(uuid.uuid4())

    session = {
        "session_id": session_id,
        "user_id": user_id,
        "status": "enrolling",
        "created_at": datetime.now(),
        "demo_mode": demo_mode,
        "trust_score": 100,
        "features": []
    }

    SESSIONS[session_id] = session

    return session


def get_session(session_id: str):
    return SESSIONS.get(session_id)