import json
import urllib.request
import urllib.error
import pytest

API_URL = "http://127.0.0.1:8000"

def test_api_session_flow():
    # 1. Start Session
    start_url = f"{API_URL}/session/start"
    start_data = json.dumps({
        "user_id": "TestStudent",
        "demo_mode": True
    }).encode("utf-8")
    
    headers = {"Content-Type": "application/json"}
    
    req = urllib.request.Request(start_url, data=start_data, headers=headers, method="POST")
    with urllib.request.urlopen(req) as response:
        assert response.status == 200
        res_body = response.read().decode("utf-8")
        data = json.loads(res_body)
        assert "session_id" in data
        session_id = data["session_id"]

    # 2. Send features (typing data)
    feature_url = f"{API_URL}/session/features"
    feature_data = json.dumps({
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
    }).encode("utf-8")

    req_feat = urllib.request.Request(feature_url, data=feature_data, headers=headers, method="POST")
    with urllib.request.urlopen(req_feat) as response:
        assert response.status == 200
        res_body = response.read().decode("utf-8")
        data = json.loads(res_body)
        assert data["trust_score"] > 0
        assert data["status"] == "success"

    # 3. Send features (No typing data - testing default 100% bypass)
    feature_data_no_type = json.dumps({
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
    }).encode("utf-8")

    req_feat_no = urllib.request.Request(feature_url, data=feature_data_no_type, headers=headers, method="POST")
    with urllib.request.urlopen(req_feat_no) as response:
        assert response.status == 200
        res_body = response.read().decode("utf-8")
        data = json.loads(res_body)
        assert data["trust_score"] == 100.0

    # 4. Send features (Script Bot spoofing timing variance check)
    feature_data_bot = json.dumps({
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
    }).encode("utf-8")

    req_feat_bot = urllib.request.Request(feature_url, data=feature_data_bot, headers=headers, method="POST")
    with urllib.request.urlopen(req_feat_bot) as response:
        assert response.status == 200
        res_body = response.read().decode("utf-8")
        data = json.loads(res_body)
        assert data["trust_score"] == 0.0
