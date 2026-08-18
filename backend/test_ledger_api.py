
API_URL = "http://127.0.0.1:8000"

def test_secure_ledger_api(client):
    # 1. No Header (PIN)
    r = client.get("/session/history")
    assert r.status_code == 403

    # 2. Incorrect PIN
    headers = {"X-Admin-PIN": "9999"}
    r = client.get("/session/history", headers=headers)
    assert r.status_code == 403

    # 3. Correct PIN (1234)
    headers = {"X-Admin-PIN": "1234"}
    r = client.get("/session/history", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
