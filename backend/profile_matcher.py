"""Mahalanobis-distance biometric profile comparison engine."""
import math

import crud
import numpy as np
from db_models import BehaviorProfile
from sqlalchemy.orm import Session


def compare_with_profile(
    db: Session,
    profile: BehaviorProfile,
    avg_dwell_time: float = 0.0,
    avg_flight_time: float = 0.0,
    typing_speed: float = 0.0,
    mouse_velocity: float = 0.0,
    std_dwell_time: float = 0.0,
    std_flight_time: float = 0.0,
    pause_count: float = 0.0,
    features_dict: dict | None = None
):
    """
    🔴 Item 2: Compare current behaviour with stored profile using 7D Extended Telemetry Mahalanobis distance.
    1. avg_dwell_time
    2. std_dwell_time
    3. avg_flight_time
    4. std_flight_time
    5. typing_speed
    6. df_ratio (avg_dwell / (avg_flight + 1e-5))
    7. pause_count
    Returns tuple: (similarity_score from 0 to 100, list of parameter explanation strings).
    """
    if features_dict:
        avg_d = float(features_dict.get("avg_dwell_time_ms", avg_dwell_time))
        std_d = float(features_dict.get("std_dwell_time_ms", std_dwell_time))
        avg_f = float(features_dict.get("avg_flight_time_ms", avg_flight_time))
        std_f = float(features_dict.get("std_flight_time_ms", std_flight_time))
        spd = float(features_dict.get("typing_speed_cps", typing_speed))
        p_cnt = float(features_dict.get("pause_count", pause_count))
    else:
        avg_d = float(avg_dwell_time)
        std_d = float(std_dwell_time)
        avg_f = float(avg_flight_time)
        std_f = float(std_flight_time)
        spd = float(typing_speed)
        p_cnt = float(pause_count)

    df_ratio = avg_d / (avg_f + 1e-5)
    x_7d = np.array([avg_d, std_d, avg_f, std_f, spd, df_ratio, p_cnt])

    # Default 7D standard deviations for fallback variance matrix
    default_stds_7d = np.array([20.0, 5.0, 40.0, 10.0, 1.5, 0.5, 1.0])

    history = crud.get_student_feature_history(db, profile.student_id)

    if len(history) >= 5:
        history_vectors = []
        for log in history:
            ld_avg = log.avg_dwell
            ld_std = getattr(log, "std_dwell", 10.0) if getattr(log, "std_dwell", None) is not None else 10.0
            lf_avg = log.avg_flight
            lf_std = getattr(log, "std_flight", 20.0) if getattr(log, "std_flight", None) is not None else 20.0
            lspd = log.typing_speed
            ldf = ld_avg / (lf_avg + 1e-5)
            lpc = getattr(log, "pause_count", 0.0) if getattr(log, "pause_count", None) is not None else 0.0

            history_vectors.append([ld_avg, ld_std, lf_avg, lf_std, lspd, ldf, lpc])

        history_arr = np.array(history_vectors)
        mu_7d = np.mean(history_arr, axis=0)
        cov_7d = np.cov(history_arr, rowvar=False) + np.eye(7) * 1e-4
    else:
        # Fallback baseline mean from profile record
        prof_avg_d = profile.avg_dwell_time if profile.avg_dwell_time > 0 else 110.0
        prof_avg_f = profile.avg_flight_time if profile.avg_flight_time > 0 else 140.0
        prof_spd = profile.typing_speed if profile.typing_speed > 0 else 4.5
        prof_df = prof_avg_d / (prof_avg_f + 1e-5)

        mu_7d = np.array([prof_avg_d, 10.0, prof_avg_f, 20.0, prof_spd, prof_df, 0.0])
        cov_7d = np.diag(default_stds_7d ** 2)

    try:
        inv_cov = np.linalg.inv(cov_7d)
        diff = x_7d - mu_7d
        dm2 = diff.T @ inv_cov @ diff
        dm = np.sqrt(max(dm2, 0.0))
    except (np.linalg.LinAlgError, ValueError, TypeError):
        diff = x_7d - mu_7d
        dm = np.sqrt(np.sum((diff ** 2) / (default_stds_7d ** 2)))

    # Map 7D Mahalanobis distance to Similarity Score (0 to 100%)
    similarity_score = math.exp(-dm / 7.0) * 100.0

    explanations = []
    features_desc = [
        ("Dwell time", avg_d, mu_7d[0], default_stds_7d[0]),
        ("Dwell std", std_d, mu_7d[1], default_stds_7d[1]),
        ("Flight time", avg_f, mu_7d[2], default_stds_7d[2]),
        ("Flight std", std_f, mu_7d[3], default_stds_7d[3]),
        ("Typing speed", spd, mu_7d[4], default_stds_7d[4]),
        ("Dwell/Flight ratio", df_ratio, mu_7d[5], default_stds_7d[5]),
        ("Pause count", p_cnt, mu_7d[6], default_stds_7d[6])
    ]

    for name, current, expected, std in features_desc:
        delta = abs(current - expected)
        stds_off = delta / max(std, 1e-4)
        dev_pct = (delta / max(expected, 1e-4)) * 100.0
        explanations.append(f"{name} is {stds_off:.1f} SD off baseline (deviated {dev_pct:.1f}%)")

    return round(float(similarity_score), 2), explanations



def compute_adaptive_threshold(db: Session, profile: BehaviorProfile) -> float:
    """
    Computes a personalized adaptive security threshold (35.0% to 65.0%)
    based on multimodal profile stability across dwell, flight, speed, and mouse velocity variance.
    - Highly consistent multimodal behavior -> tighter threshold (~60%)
    - Variable behavior -> broader threshold (~40%)
    """
    if not profile or not profile.student_id:
        return 50.0

    history = crud.get_student_feature_history(db, profile.student_id)
    if len(history) < 5:
        return 50.0

    dwell_vals = [log.avg_dwell for log in history if log.avg_dwell > 0]
    flight_vals = [log.avg_flight for log in history if log.avg_flight > 0]
    speed_vals = [log.typing_speed for log in history if log.typing_speed > 0]
    mouse_vals = [log.avg_mouse_velocity for log in history if log.avg_mouse_velocity > 0]

    if len(dwell_vals) < 3 or len(flight_vals) < 3:
        return 50.0

    # Calculate normalized standard deviations per modality
    std_dwell = float(np.std(dwell_vals)) / 20.0
    std_flight = float(np.std(flight_vals)) / 40.0
    std_speed = (float(np.std(speed_vals)) / 1.5) if len(speed_vals) >= 3 else 0.5
    std_mouse = (float(np.std(mouse_vals)) / 50.0) if len(mouse_vals) >= 3 else 0.5

    # Combined multimodal instability penalty
    multimodal_instability = (std_dwell + std_flight + std_speed + std_mouse) / 4.0

    # Base threshold starts at 60.0, scales down up to 20 points based on multimodal variance
    adaptive_t = 60.0 - (15.0 * min(multimodal_instability, 1.5))
    return round(max(35.0, min(65.0, adaptive_t)), 1)