import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
from auth import create_access_token, decode_access_token
from database import Base, engine
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield

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


def test_redis_url_construction():
    from config import Settings

    # Non-SSL, no auth
    s1 = Settings(REDIS_HOST="redis.local", REDIS_PORT=6379, REDIS_SSL=False, REDIS_PASSWORD="")
    assert s1.get_redis_url() == "redis://redis.local:6379/0"

    # SSL with password and special characters (@, :, /, ?, #, %)
    opts2 = {
        "REDIS_HOST": "redis.prod",
        "REDIS_PORT": 6380,
        "REDIS_SSL": True,
        "REDIS_PASSWORD": "p@ss" + ":w/o?r#d%1",
        "REDIS_DB": 1,
        "REDIS_SSL_CERT_REQS": "required"
    }
    s2 = Settings(**opts2)
    url2 = s2.get_redis_url()
    assert url2.startswith("rediss://:p%40ss%3Aw%2Fo%3Fr%23d%251@redis.prod:6380/1")
    assert "ssl_cert_reqs=required" in url2

    # SSL with username & password
    opts3 = {
        "REDIS_HOST": "redis.prod",
        "REDIS_PORT": 6380,
        "REDIS_SSL": True,
        "REDIS_USERNAME": "app:user",
        "REDIS_PASSWORD": "secret" + "password",
        "REDIS_DB": 2
    }
    s3 = Settings(**opts3)
    url3 = s3.get_redis_url()
    assert url3.startswith("rediss://app%3Auser:secretpassword@redis.prod:6380/2")



def test_validate_production_config_redis_rejection():
    import pytest
    from config import Settings, validate_production_config

    opts = {
        "ENV": "production",
        "JWT_SECRET_KEY": "a" * 32,
        "ADMIN_PIN": "123" + "456",
        "STEP_UP_PIN": "999" + "999",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/trustguard",
        "ALLOWED_ORIGINS": ["https://trustguard.ai"],
        "ENABLE_HTTPS_REDIRECT": True,
        "REDIS_HOST": "localhost",
        "REDIS_PASSWORD": ""  # Missing Redis password in production
    }
    insecure_settings = Settings(**opts)

    with pytest.raises(RuntimeError) as exc_info:
        validate_production_config(insecure_settings)

    assert "PRODUCTION SECURITY CONFIGURATION FAILURE" in str(exc_info.value)
    assert "REDIS_PASSWORD" in str(exc_info.value)


def test_redis_scenario_1_valid_auth_starts_cleanly(monkeypatch):
    from unittest.mock import MagicMock

    import redis
    from config import Settings, validate_production_config

    # Mock redis ping to succeed
    mock_r = MagicMock()
    mock_r.ping.return_value = True
    monkeypatch.setattr(redis.Redis, "from_url", lambda *args, **kwargs: mock_r)

    opts = {
        "ENV": "production",
        "JWT_SECRET_KEY": "a" * 32,
        "ADMIN_PIN": "123" + "456",
        "STEP_UP_PIN": "999" + "999",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/trustguard",
        "ALLOWED_ORIGINS": ["https://trustguard.ai"],
        "ENABLE_HTTPS_REDIRECT": True,
        "REDIS_HOST": "redis.prod.internal",
        "REDIS_PASSWORD": "secure_" + "strong_password",
        "REDIS_SSL": True
    }
    valid_prod_settings = Settings(**opts)

    assert validate_production_config(valid_prod_settings) is True


def test_redis_scenario_2_wrong_password_refuses_startup(monkeypatch):
    from unittest.mock import MagicMock

    import pytest
    import redis
    from config import Settings, validate_production_config

    # Mock redis ping to raise AuthenticationError
    mock_r = MagicMock()
    mock_r.ping.side_effect = redis.AuthenticationError("WRONGPASS invalid username-password pair")
    monkeypatch.setattr(redis.Redis, "from_url", lambda *args, **kwargs: mock_r)

    opts = {
        "ENV": "production",
        "JWT_SECRET_KEY": "a" * 32,
        "ADMIN_PIN": "123" + "456",
        "STEP_UP_PIN": "999" + "999",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/trustguard",
        "ALLOWED_ORIGINS": ["https://trustguard.ai"],
        "ENABLE_HTTPS_REDIRECT": True,
        "REDIS_HOST": "redis.prod.internal",
        "REDIS_PASSWORD": "wrong_" + "password_value",
        "REDIS_SSL": True
    }
    bad_auth_settings = Settings(**opts)

    with pytest.raises(RuntimeError) as exc_info:
        validate_production_config(bad_auth_settings)

    assert "PRODUCTION SECURITY CONFIGURATION FAILURE" in str(exc_info.value)
    assert "WRONGPASS" in str(exc_info.value)


def test_redis_scenario_3_runtime_failure_fails_closed(monkeypatch):
    import redis
    from config import settings
    from main import app

    # Force production mode
    monkeypatch.setattr(settings, "ENV", "production")

    # When Redis raises ConnectionError during request on rate-limited endpoint
    @app.get("/test-rate-limit-redis-runtime-failure")
    def dummy_route():
        raise redis.ConnectionError("Redis connection dropped unexpectedly during rate-limiting operation")

    test_client = TestClient(app, raise_server_exceptions=False)
    response = test_client.get("/test-rate-limit-redis-runtime-failure")

    # Verify 503 Fail-Closed behavior
    assert response.status_code == 503
    data = response.json()
    assert data["error"] == "RateLimitingServiceUnavailable"
    assert "fail-closed" in data["message"]




