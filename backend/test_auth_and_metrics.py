import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth import create_access_token, decode_access_token
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_jwt_token_creation_and_decoding():
    token = create_access_token({"sub": "Student_01", "session_id": "test-uuid"})
    assert isinstance(token, str)
    payload = decode_access_token(token)
    assert payload["sub"] == "Student_01"
    assert payload["session_id"] == "test-uuid"

def test_session_start_returns_jwt():
    response = client.post("/session/start", json={"user_id": "Student_JWT_Test", "demo_mode": True})
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["access_token"] is not None

def test_prometheus_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "trustguard_http_requests_total" in response.text


def test_liveness_and_readiness_probes():
    res_live = client.get("/live")
    assert res_live.status_code == 200
    assert res_live.json()["status"] == "alive"

    res_ready = client.get("/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "ready"


def test_security_headers_presence():
    res = client.get("/live")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert "strict-origin" in res.headers.get("Referrer-Policy")
    assert "default-src" in res.headers.get("Content-Security-Policy")


def test_validate_production_config_rejection():
    import pytest
    from config import Settings, validate_production_config

    insecure_settings = Settings(
        ENV="production",
        JWT_SECRET_KEY="super-secret-trustguard-key-change-in-production",
        ADMIN_PIN="1234",
        STEP_UP_PIN="9999",
        DATABASE_URL="",
        ALLOWED_ORIGINS=["null"],
        ENABLE_HTTPS_REDIRECT=False
    )

    with pytest.raises(RuntimeError) as exc_info:
        validate_production_config(insecure_settings)

    assert "PRODUCTION SECURITY CONFIGURATION FAILURE" in str(exc_info.value)

