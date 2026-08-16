import requests
import time

API_URL = "http://127.0.0.1:8000"

def wait_for_server():
    t0 = time.time()
    while time.time() - t0 < 15:
        try:
            r = requests.get(f"{API_URL}/health")
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def test_secure_ledger_api():
    assert wait_for_server(), "FastAPI backend server did not start in time."

    # 1. No Header (PIN)
    r = requests.get(f"{API_URL}/session/history")
    assert r.status_code == 403

    # 2. Incorrect PIN
    headers = {"X-Admin-PIN": "9999"}
    r = requests.get(f"{API_URL}/session/history", headers=headers)
    assert r.status_code == 403

    # 3. Correct PIN (1234)
    headers = {"X-Admin-PIN": "1234"}
    r = requests.get(f"{API_URL}/session/history", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
