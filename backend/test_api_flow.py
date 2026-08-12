import json
import urllib.request
import urllib.error

def test_flow():
    print("=" * 60)
    print("TrustGuard AI API Flow Test")
    print("=" * 60)

    # 1. Start Session
    start_url = "http://127.0.0.1:8000/session/start"
    start_data = json.dumps({
        "user_id": "TestStudent",
        "demo_mode": True
    }).encode("utf-8")
    
    headers = {"Content-Type": "application/json"}
    
    req = urllib.request.Request(start_url, data=start_data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            data = json.loads(res_body)
            session_id = data["session_id"]
            print(f"[SUCCESS] Start Session: session_id={session_id}")
    except urllib.error.URLError as e:
        print(f"[ERROR] Failed to connect to server: {e}")
        return False

    # 2. Send features (typing data)
    feature_url = "http://127.0.0.1:8000/session/features"
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
    try:
        with urllib.request.urlopen(req_feat) as response:
            res_body = response.read().decode("utf-8")
            data = json.loads(res_body)
            print(f"[SUCCESS] Send Features: trust_score={data['trust_score']}% ({data['message']})")
    except urllib.error.URLError as e:
        print(f"[ERROR] Failed to send features: {e}")
        return False

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
    try:
        with urllib.request.urlopen(req_feat_no) as response:
            res_body = response.read().decode("utf-8")
            data = json.loads(res_body)
            print(f"[SUCCESS] Send Features (No Typing): trust_score={data['trust_score']}% (Bypass works: {data['trust_score'] == 100.0})")
    except urllib.error.URLError as e:
        print(f"[ERROR] Failed to send empty features: {e}")
        return False

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
    try:
        with urllib.request.urlopen(req_feat_bot) as response:
            res_body = response.read().decode("utf-8")
            data = json.loads(res_body)
            print(f"[SUCCESS] Send Features (Script Bot): trust_score={data['trust_score']}% (Bot Blocked works: {data['trust_score'] == 0.0})")
    except urllib.error.URLError as e:
        print(f"[ERROR] Failed to send bot features: {e}")
        return False

    print("=" * 60)
    print("API Flow Test Completed Successfully")
    print("=" * 60)
    return True

if __name__ == "__main__":
    test_flow()
