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


def test_trusted_proxies_header_filtering():
    from unittest.mock import MagicMock

    from config import settings
    from main import get_identifier_and_ip

    # 1. Untrusted socket IP -> ignores X-Forwarded-For
    req_untrusted = MagicMock()
    req_untrusted.client.host = "203.0.113.50"
    req_untrusted.headers = {"X-Forwarded-For": "1.2.3.4"}
    req_untrusted.query_params = {}

    settings.TRUSTED_PROXIES = ["127.0.0.1"]
    key = get_identifier_and_ip(req_untrusted)
    assert key.startswith("203.0.113.50:")

    # 2. Trusted socket IP -> honors X-Forwarded-For
    req_trusted = MagicMock()
    req_trusted.client.host = "127.0.0.1"
    req_trusted.headers = {"X-Forwarded-For": "198.51.100.22"}
    req_trusted.query_params = {}

    key_t = get_identifier_and_ip(req_trusted)
    assert key_t.startswith("198.51.100.22:")


