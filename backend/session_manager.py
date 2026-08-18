import uuid
import json
import os
import sqlite3
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Default Session TTL (1 hour)
TTL_SECONDS = 3600

# Try connecting to Redis
REDIS_CONNECTED = False
redis_client = None

try:
    import redis
    redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    # Test connection
    redis_client.ping()
    REDIS_CONNECTED = True
    logger.info("[SUCCESS] Session Manager: Connected to Redis on localhost:6379")
except Exception as e:
    logger.warning(f"[WARNING] Session Manager: Redis unavailable ({e}). Falling back to local SQLite session store.")

# SQLite Fallback Setup
DB_PATH = os.path.join(os.path.dirname(__file__), "sessions.db")

def init_sqlite_store():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            session_data TEXT,
            expires_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

if not REDIS_CONNECTED:
    init_sqlite_store()


def create_session(user_id: str, demo_mode: bool):
    session_id = str(uuid.uuid4())
    session = {
        "session_id": session_id,
        "user_id": user_id,
        "status": "enrolling",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "demo_mode": demo_mode,
        "trust_score": 100,
        "features": [],
        "security_state": "NORMAL",
        "low_trust_count": 0,
        "high_trust_count": 0
    }
    
    save_session(session_id, session)
    return session


def get_session(session_id: str):
    if REDIS_CONNECTED:
        try:
            data = redis_client.get(session_id)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.debug(f"Redis fallback: {e}") # Fail open to SQLite lookup if Redis goes down mid-run
            
    # SQLite Lookup
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT session_data, expires_at FROM sessions WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        data_str, expires_str = row
        expires_at = datetime.fromisoformat(expires_str)
        # Handle both naive and timezone-aware datetimes safely
        now_dt = datetime.now(timezone.utc) if expires_at.tzinfo is not None else datetime.now()
        if now_dt < expires_at:
            return json.loads(data_str)
        else:
            # Clean up expired session
            delete_session(session_id)
    return None


def save_session(session_id: str, session: dict):
    if REDIS_CONNECTED:
        try:
            redis_client.setex(session_id, TTL_SECONDS, json.dumps(session))
            return
        except Exception as e:
            logger.debug(f"Redis fallback: {e}")

    # SQLite Save
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=TTL_SECONDS)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO sessions (session_id, session_data, expires_at)
        VALUES (?, ?, ?)
    """, (session_id, json.dumps(session), expires_at.isoformat()))
    conn.commit()
    conn.close()


def delete_session(session_id: str):
    if REDIS_CONNECTED:
        try:
            redis_client.delete(session_id)
            return
        except Exception as e:
            logger.debug(f"Redis fallback: {e}")
            
    # SQLite Delete
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()


def prune_expired_sessions():
    """
    Data Retention & Cleanup: Purges expired session state records from storage.
    """
    if REDIS_CONNECTED:
        return # Redis handles TTL automatically
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE expires_at < ?", (datetime.now(timezone.utc).isoformat(),))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    if deleted_count > 0:
        logger.info(f"[RETENTION] Pruned {deleted_count} expired session store records.")


def set_exam_session_id(session_id: str, exam_session_id: int):
    session = get_session(session_id)
    if session is not None:
        session["exam_session_id"] = exam_session_id
        save_session(session_id, session)


def add_features(session_id: str, features):
    session = get_session(session_id)
    if session is None:
        return False
    session["features"].append(features)
    save_session(session_id, session)
    return True