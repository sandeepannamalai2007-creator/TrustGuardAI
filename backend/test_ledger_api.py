from backend.config import settings


def test_secure_ledger_api(client):
    # 1. No Authorization Header (JWT Missing) -> 401 Unauthorized
    r = client.get("/session/history")
    assert r.status_code == 401

    # Obtain Admin Bearer Token
    start_resp = client.post("/session/start", json={
        "user_id": "LedgerAdminTest",
        "demo_mode": True,
        "admin_pin": settings.ADMIN_PIN
    })
    assert start_resp.status_code == 200
    token = start_resp.json()["access_token"]

    # 2. Valid Admin JWT but Incorrect Admin PIN -> 403 Forbidden
    headers_bad_pin = {
        "Authorization": f"Bearer {token}",
        "X-Admin-PIN": "wrong_pin"
    }
    r = client.get("/session/history", headers=headers_bad_pin)
    assert r.status_code == 403

    # 3. Valid Admin JWT AND Correct Admin PIN -> 200 OK
    headers_valid = {
        "Authorization": f"Bearer {token}",
        "X-Admin-PIN": settings.ADMIN_PIN
    }
    r = client.get("/session/history", headers=headers_valid)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
