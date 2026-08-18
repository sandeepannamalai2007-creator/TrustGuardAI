import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
from fastapi.testclient import TestClient
from main import app
from auth import create_access_token, decode_access_token

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
