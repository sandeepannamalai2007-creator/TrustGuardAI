import sys
import os

# Add the ml folder to Python path
sys.path.append(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "ml"
    )
)

from predictor import predict_trust_score


def calculate_trust_score(
    features,
    similarity_score=100
):
    """
    Calculate the final trust score by combining:
    1. AI model prediction
    2. Behaviour profile similarity
    """

    # Biometric Anti-Spoofing / Bot Detection:
    # Check for timing variance. Real human typing has natural micro-timing fluctuations.
    # Script bots type with near-perfect timing precision (zero variance).
    # If the user has typed at least 5 characters and standard deviation is < 2ms,
    # it is highly likely an automated typing script.
    keystroke_count = features.get("keystroke_count", 0)
    if keystroke_count >= 5:
        std_dwell = features.get("std_dwell_time_ms", 0.0)
        std_flight = features.get("std_flight_time_ms", 0.0)
        
        if std_dwell < 2.0 or std_flight < 2.0:
            print(f"[SECURITY ALERT] Synthetic bot detected! std_dwell={std_dwell:.2f}ms, std_flight={std_flight:.2f}ms")
            return 0.0

    ai_score = predict_trust_score(features)

    final_score = (
        ai_score * 0.7 +
        similarity_score * 0.3
    )

    return round(final_score, 2)


def update_security_state(session: dict, trust_score: float) -> str:
    """
    Enforces security state transitions with hysteresis:
    NORMAL -> SUSPICIOUS -> HIGH_RISK -> LOCKED

    - 3 consecutive low trust scores (< 50) trigger escalation.
    - 2 consecutive high trust scores (>= 50) trigger de-escalation.
    - Bot detections (trust score == 0.0) trigger immediate LOCK.
    - LOCKED state requires manual override/reset and cannot recover.
    """
    current_state = session.get("security_state", "NORMAL")
    if current_state == "LOCKED":
        return "LOCKED"

    low_trust_count = session.get("low_trust_count", 0)
    high_trust_count = session.get("high_trust_count", 0)

    # Bot detection triggers immediate LOCK
    if trust_score == 0.0:
        session["security_state"] = "LOCKED"
        session["low_trust_count"] = 0
        session["high_trust_count"] = 0
        return "LOCKED"

    if trust_score < 50.0:
        low_trust_count += 1
        high_trust_count = 0
        
        if low_trust_count >= 3:
            if current_state == "NORMAL":
                current_state = "SUSPICIOUS"
            elif current_state == "SUSPICIOUS":
                current_state = "HIGH_RISK"
            elif current_state == "HIGH_RISK":
                current_state = "LOCKED"
            low_trust_count = 0
    else:
        high_trust_count += 1
        low_trust_count = 0
        
        if high_trust_count >= 2:
            if current_state == "HIGH_RISK":
                current_state = "SUSPICIOUS"
            elif current_state == "SUSPICIOUS":
                current_state = "NORMAL"
            high_trust_count = 0

    session["security_state"] = current_state
    session["low_trust_count"] = low_trust_count
    session["high_trust_count"] = high_trust_count
    return current_state