import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from database import SessionLocal
from fastapi.testclient import TestClient
from main import app
from profile_matcher import compute_adaptive_threshold

client = TestClient(app)

def test_step_up_verification_flow():
    # 1. Start a session & get JWT token
    start_resp = client.post("/session/start", json={"user_id": "Student_StepUp_Test", "demo_mode": True})
    assert start_resp.status_code == 200
    session_id = start_resp.json()["session_id"]
    access_token = start_resp.json()["access_token"]

    # 2. Verify valid step-up PIN with Bearer token
    headers = {"Authorization": f"Bearer {access_token}"}
    step_resp = client.post(
        "/session/step-up/verify",
        json={"session_id": session_id, "pin": settings.STEP_UP_PIN},
        headers=headers
    )
    assert step_resp.status_code == 200
    assert step_resp.json()["status"] == "success"
    assert step_resp.json()["security_state"] == "NORMAL"

def test_admin_force_lock_and_unlock_override():
    # 1. Start an admin session
    start_resp = client.post("/session/start", json={
        "user_id": "Student_Override_Test",
        "demo_mode": True,
        "admin_pin": settings.ADMIN_PIN
    })
    session_id = start_resp.json()["session_id"]
    access_token = start_resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Admin Force Lock (with Admin Bearer token + Admin PIN)
    lock_resp = client.post(
        "/session/override/lock",
        json={"session_id": session_id, "admin_pin": settings.ADMIN_PIN},
        headers=headers
    )
    assert lock_resp.status_code == 200
    assert lock_resp.json()["security_state"] == "LOCKED"

    # 3. Admin Force Unlock (with Admin Bearer token + Admin PIN)
    unlock_resp = client.post(
        "/session/override/unlock",
        json={"session_id": session_id, "admin_pin": settings.ADMIN_PIN},
        headers=headers
    )
    assert unlock_resp.status_code == 200
    assert unlock_resp.json()["security_state"] == "NORMAL"

def test_csv_export_endpoint():
    # Obtain Admin Bearer Token
    start_resp = client.post("/session/start", json={
        "user_id": "CSVAdminTest",
        "demo_mode": True,
        "admin_pin": settings.ADMIN_PIN
    })
    access_token = start_resp.json()["access_token"]

    headers = {
        "X-Admin-PIN": settings.ADMIN_PIN,
        "Authorization": f"Bearer {access_token}"
    }
    resp = client.get("/session/export/csv", headers=headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "Timestamp,Student_ID,Session_ID,Trust_Score" in resp.text

def test_adaptive_threshold_calculation():
    db = SessionLocal()
    try:
        threshold = compute_adaptive_threshold(db, None)
        assert 30.0 <= threshold <= 65.0
    finally:
        db.close()
