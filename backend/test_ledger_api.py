import requests

API_URL = "http://127.0.0.1:8000"

def run_tests():
    print("============================================================")
    print("TrustGuard AI Secure Ledger API Test")
    print("============================================================")

    # 1. No Header (PIN)
    try:
        r = requests.get(f"{API_URL}/session/history")
        print(f"[TEST 1] No Header request: Code {r.status_code} (Expected: 403) - {'PASSED' if r.status_code == 403 else 'FAILED'}")
    except Exception as e:
        print(f"[TEST 1] Failed with error: {e}")

    # 2. Incorrect PIN
    try:
        headers = {"X-Admin-PIN": "9999"}
        r = requests.get(f"{API_URL}/session/history", headers=headers)
        print(f"[TEST 2] Wrong PIN request: Code {r.status_code} (Expected: 403) - {'PASSED' if r.status_code == 403 else 'FAILED'}")
    except Exception as e:
        print(f"[TEST 2] Failed with error: {e}")

    # 3. Correct PIN (1234)
    try:
        headers = {"X-Admin-PIN": "1234"}
        r = requests.get(f"{API_URL}/session/history", headers=headers)
        print(f"[TEST 3] Correct PIN request: Code {r.status_code} (Expected: 200) - {'PASSED' if r.status_code == 200 else 'FAILED'}")
        if r.status_code == 200:
            data = r.json()
            print(f"         Fetched {len(data)} trust log records from SQLite.")
            if len(data) > 0:
                print(f"         Sample Record: Student ID = {data[0]['student_id']}, Trust Score = {data[0]['trust_score']}%")
    except Exception as e:
        print(f"[TEST 3] Failed with error: {e}")

    print("============================================================")

if __name__ == "__main__":
    run_tests()
