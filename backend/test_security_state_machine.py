import pytest
from backend.trust_engine import update_security_state

def test_update_security_state_immediate_lock():
    session = {"security_state": "NORMAL", "low_trust_count": 0, "high_trust_count": 0}
    state = update_security_state(session, 0.0)
    assert state == "LOCKED"
    assert session["security_state"] == "LOCKED"

def test_update_security_state_escalation():
    session = {"security_state": "NORMAL", "low_trust_count": 0, "high_trust_count": 0}
    
    # 3 low scores -> SUSPICIOUS
    for _ in range(3):
        state = update_security_state(session, 49.0)
    assert state == "SUSPICIOUS"
    
    # 3 low scores -> HIGH_RISK
    for _ in range(3):
        state = update_security_state(session, 49.0)
    assert state == "HIGH_RISK"
    
    # 3 low scores -> LOCKED
    for _ in range(3):
        state = update_security_state(session, 49.0)
    assert state == "LOCKED"

def test_update_security_state_deescalation():
    session = {"security_state": "HIGH_RISK", "low_trust_count": 0, "high_trust_count": 0}
    
    # 2 high scores -> SUSPICIOUS
    for _ in range(2):
        state = update_security_state(session, 55.0)
    assert state == "SUSPICIOUS"
    
    # 2 high scores -> NORMAL
    for _ in range(2):
        state = update_security_state(session, 80.0)
    assert state == "NORMAL"

def test_update_security_state_locked_is_terminal():
    session = {"security_state": "LOCKED", "low_trust_count": 0, "high_trust_count": 0}
    state = update_security_state(session, 100.0)
    assert state == "LOCKED"
