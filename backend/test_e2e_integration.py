from fastapi.testclient import TestClient

from backend.main import app, settings

client = TestClient(app)

def test_e2e_full_session_flow():
    """
    End-to-End Integration Test:
    1. Start an admin session (/session/start) & get JWT Bearer token
    2. Post biometric features (/session/features) with Bearer token header
    3. Verify unauthenticated call to /session/features is rejected with 401
    4. Fetch security audit history (/session/history) with Admin JWT + Admin PIN header
    5. Trigger step-up verification (/session/step-up/verify) with JWT + PIN
    """
    # Step 1: Start Session with Admin PIN to obtain Admin-scoped JWT
    start_resp = client.post("/session/start", json={
        "user_id": "IntegrationStudent",
        "demo_mode": True,
        "admin_pin": settings.ADMIN_PIN
    })
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    session_id = start_data["session_id"]
    access_token = start_data["access_token"]
    assert session_id is not None
    assert access_token is not None

    # Step 2: Post Features with Bearer Token
    feature_payload = {
        "session_id": session_id,
        "avg_dwell_time_ms": 110.5,
        "std_dwell_time_ms": 12.3,
        "avg_flight_time_ms": 140.2,
        "std_flight_time_ms": 15.1,
        "typing_speed_cps": 4.5,
        "avg_mouse_velocity_px_s": 250.0,
        "click_count": 5,
        "keystroke_count": 25,
        "session_duration_s": 10.0
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    # Post features 5 times to complete 5-sample enrollment phase
    for _ in range(5):
        feat_resp = client.post("/session/features", json=feature_payload, headers=headers)
        assert feat_resp.status_code == 200

    feat_data = feat_resp.json()
    assert feat_data["status"] in ("success", "warning")
    assert "trust_score" in feat_data
    assert "security_state" in feat_data



    # Step 3: Verify Unauthenticated Request Rejection (401)
    unauth_resp = client.post("/session/features", json=feature_payload)
    assert unauth_resp.status_code == 401

    # Step 4: Verify Admin Audit Ledger (GET /session/history with Admin JWT + Admin PIN)
    admin_headers = {
        "X-Admin-PIN": settings.ADMIN_PIN,
        "Authorization": f"Bearer {access_token}"
    }
    history_resp = client.get("/session/history", headers=admin_headers)
    assert history_resp.status_code == 200
    logs = history_resp.json()
    assert isinstance(logs, list)
    assert len(logs) > 0

    # Step 5: Verify Step-Up Re-Authentication (/session/step-up/verify with JWT + PIN)
    stepup_resp = client.post(
        "/session/step-up/verify",
        json={"session_id": session_id, "pin": settings.STEP_UP_PIN},
        headers=headers
    )
    assert stepup_resp.status_code == 200
    assert stepup_resp.json()["security_state"] == "NORMAL"
