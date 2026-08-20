"""Mahalanobis-distance biometric profile comparison engine."""
import math

import crud
import numpy as np
from db_models import BehaviorProfile
from sqlalchemy.orm import Session


def compare_with_profile(
    db: Session,
    profile: BehaviorProfile,
    avg_dwell_time: float,
    avg_flight_time: float,
    typing_speed: float,
    mouse_velocity: float,
):
    """
    Compare current behaviour with the stored behaviour profile using Mahalanobis distance.
    Returns a tuple: (similarity_score from 0 to 100, list of parameter explanation strings).
    """
    
    # 1. Fetch user's historical genuine samples
    history = crud.get_student_feature_history(db, profile.student_id)
    
    # Pack current sample vector
    x = np.array([avg_dwell_time, avg_flight_time, typing_speed, mouse_velocity])
    
    # Baseline mean vector from profile database averages
    mu = np.array([
        profile.avg_dwell_time,
        profile.avg_flight_time,
        profile.typing_speed,
        profile.mouse_velocity
    ])
    
    # Default standard deviations (DS-StrongPassword baseline estimates for fallback)
    default_stds = np.array([20.0, 40.0, 2.0, 80.0])
    
    # 2. Compute covariance matrix
    # We require at least 5 genuine historical samples to construct a reliable covariance matrix
    if len(history) >= 5:
        history_vectors = []
        for log in history:
            # Handle possible null velocity logs from earlier versions gracefully
            v = log.avg_mouse_velocity if log.avg_mouse_velocity is not None else profile.mouse_velocity
            history_vectors.append([
                log.avg_dwell,
                log.avg_flight,
                log.typing_speed,
                v
            ])
            
        history_arr = np.array(history_vectors)
        cov = np.cov(history_arr, rowvar=False)
        
        # Add a tiny shrinkage regularization (diagonal loading) to avoid singularity
        cov += np.eye(4) * 1e-4
    else:
        # Fallback: diagonal covariance using default parameter variances
        cov = np.diag(default_stds ** 2)
        
    try:
        inv_cov = np.linalg.inv(cov)
        diff = x - mu
        dm2 = diff.T @ inv_cov @ diff
        dm = np.sqrt(max(dm2, 0.0))
    except (np.linalg.LinAlgError, ValueError, TypeError):

        # Ultimate fallback: Normalized Euclidean Distance (assuming independent default variances)
        diff = x - mu
        var = default_stds ** 2
        dm = np.sqrt(np.sum((diff ** 2) / var))

    # 3. Map Mahalanobis distance to Similarity Score (0 to 100%)
    # Distance mapping works perfectly with: Similarity = exp(-D_M / 2.0) * 100.0
    similarity_score = math.exp(-dm / 2.0) * 100.0
    
    # 4. Generate per-feature deviation logs for UI transparency
    # Deviation percentage is calculated relative to default standard deviation for clarity
    explanations = []
    
    features = [
        ("Dwell time", avg_dwell_time, profile.avg_dwell_time, default_stds[0]),
        ("Flight time", avg_flight_time, profile.avg_flight_time, default_stds[1]),
        ("Typing speed", typing_speed, profile.typing_speed, default_stds[2]),
        ("Mouse velocity", mouse_velocity, profile.mouse_velocity, default_stds[3])
    ]
    
    for name, current, expected, std in features:
        if expected == 0:
            explanations.append(f"{name} profile not initialized.")
            continue
            
        delta = abs(current - expected)
        dev_pct = (delta / expected) * 100.0
        # Calculate how many standard deviations off the feature is
        stds_off = delta / std
        
        explanations.append(
            f"{name} is {stds_off:.1f} SD off baseline (deviated {dev_pct:.1f}%)"
        )
        
    return round(similarity_score, 2), explanations


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