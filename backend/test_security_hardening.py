import pytest
from audit_service import record_audit_event, verify_audit_log_chain
from auth import create_access_token
from database import Base, engine
from fastapi.testclient import TestClient
from main import app
from retention import enforce_data_retention_policy

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield


def test_jwt_invalid_token_rejected():
    response = client.get("/session/history", headers={"Authorization": "Bearer invalid_jwt_token_format"})
    assert response.status_code == 401


from datetime import timedelta


def test_jwt_expired_token_rejected():
    expired_token = create_access_token(data={"sub": "admin", "role": "admin"}, expires_delta=timedelta(seconds=-100))
    response = client.get("/session/history", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401


def test_admin_endpoint_without_admin_role_rejected():
    user_token = create_access_token(data={"sub": "user_123", "role": "user"})
    response = client.get("/session/history", headers={"Authorization": f"Bearer {user_token}", "X-Admin-PIN": "1234"})
    assert response.status_code == 403


def test_admin_endpoint_without_jwt_rejected():
    response = client.get("/session/history", headers={"X-Admin-PIN": "1234"})
    assert response.status_code == 401


def test_step_up_jwt_session_mismatch_rejected():
    session_res = client.post("/session/start", json={"user_id": "student_001", "demo_mode": True})
    token = session_res.json()["access_token"]

    # Step-up request with mismatching session ID
    res = client.post(
        "/session/step-up/verify",
        headers={"Authorization": f"Bearer {token}"},
        json={"session_id": "mismatched_session_uuid", "pin": "9999"}
    )
    assert res.status_code == 403
    assert "Session ID" in res.json()["detail"]


def test_step_up_without_jwt_rejected():
    res = client.post("/session/step-up/verify", json={"session_id": "some_session", "pin": "9999"})
    assert res.status_code == 401


def test_wrong_admin_pin_rejected():
    res = client.post(
        "/admin/login",
        json={"admin_pin": "wrong_pin_value"}
    )
    assert res.status_code == 403


def test_oversized_payload_rejected():
    large_payload = "a" * (1024 * 1024 + 100)  # > 1MB
    res = client.post(
        "/session/start",
        headers={"Content-Length": str(len(large_payload))},
        content=large_payload
    )
    assert res.status_code == 413
    assert res.json()["error"] == "PayloadTooLarge"


def test_sql_injection_safety():
    # Attempt SQL injection payload in user_id
    sql_payload = "user_1' OR '1'='1"
    res = client.post("/session/start", json={"user_id": sql_payload, "demo_mode": True})
    assert res.status_code == 200
    assert res.json()["session_id"] is not None


def test_audit_log_hash_chain_integrity(db_session):
    # Record multiple audit events
    record_audit_event(db_session, actor="admin", action="admin_login", target="system", result="SUCCESS")
    record_audit_event(db_session, actor="admin", action="model_retrain", target="v001", result="SUCCESS")
    record_audit_event(db_session, actor="admin", action="session_lock", target="sess_123", result="SUCCESS")

    report = verify_audit_log_chain(db_session)
    assert report["valid"] is True
    assert report["status"] == "VERIFIED_INTACT"
    assert report["total_records"] >= 3


def test_data_retention_policy_cleanup(db_session):
    result = enforce_data_retention_policy(db_session)
    assert result["status"] == "success"
    assert "deleted_enrollment_buffers" in result
    assert "deleted_trust_logs" in result
