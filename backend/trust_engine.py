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