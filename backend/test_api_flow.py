
def test_api_session_flow(client):

    # 1. Start Session
    start_data = {
        "user_id": "TestStudent",
        "demo_mode": True
    }
    
    response = client.post("/session/start", json=start_data)
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "access_token" in data
    session_id = data["session_id"]
    access_token = data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Send features (typing data)
    feature_data = {
        "session_id": session_id,
        "avg_dwell_time_ms": 120.0,
        "std_dwell_time_ms": 30.0,
        "avg_flight_time_ms": 150.0,
        "std_flight_time_ms": 40.0,
        "typing_speed_cps": 4.5,
        "avg_mouse_velocity_px_s": 250.0,
        "click_count": 10,
        "keystroke_count": 12,
        "session_duration_s": 5.0
    }

    response = client.post("/session/features", json=feature_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["trust_score"] > 0
    assert data["status"] == "success"

    # 3. Send features (No typing data - testing default 100% bypass)
    feature_data_no_type = {
        "session_id": session_id,
        "avg_dwell_time_ms": 0.0,
        "std_dwell_time_ms": 0.0,
        "avg_flight_time_ms": 0.0,
        "std_flight_time_ms": 0.0,
        "typing_speed_cps": 0.0,
        "avg_mouse_velocity_px_s": 120.0,
        "click_count": 2,
        "keystroke_count": 0,
        "session_duration_s": 10.0
    }

    response = client.post("/session/features", json=feature_data_no_type, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["trust_score"] == 100.0

    # 4. Send features without Auth Header -> Expect 401 Unauthorized
    unauth_response = client.post("/session/features", json=feature_data_no_type)
    assert unauth_response.status_code == 401

    # 5. Send features (Script Bot spoofing timing variance check)
    feature_data_bot = {
        "session_id": session_id,
        "avg_dwell_time_ms": 100.0,
        "std_dwell_time_ms": 0.5,      # Extremely low variance (bot)
        "avg_flight_time_ms": 100.0,
        "std_flight_time_ms": 0.5,
        "typing_speed_cps": 5.0,
        "avg_mouse_velocity_px_s": 0.0,
        "click_count": 0,
        "keystroke_count": 10,
        "session_duration_s": 15.0
    }

    response = client.post("/session/features", json=feature_data_bot, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["trust_score"] <= 1e-6
    assert data["security_state"] == "LOCKED"
