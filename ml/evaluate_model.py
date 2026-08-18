"""
ml/evaluate_model.py

TrustGuard AI v2.0 — Rigorous Multi-Subject Biometric & Adversarial Evaluation

Key Engineering Features:
1. Multi-Subject Evaluation across 51 subjects from CMU DSL Dataset (s002 to s052).
2. Subject-Disjoint Split: First 25 sessions (200 reps) per subject for profile enrollment;
   remaining 25 sessions (200 reps) for unseen genuine testing. Zero data leakage!
3. Impostor Cross-Testing: All other 50 subjects' typing samples evaluated against each subject's profile.
4. Comprehensive Metrics: FAR, FRR, EER (Equal Error Rate), ROC Curve, AUC, Precision, Recall, F1-Score, Confusion Matrix.
5. Adversarial Simulation / Stress Testing: Script Bot zero-variance & Erratic Attacker attacks evaluated separately from human biometrics.
"""

import os
import sys
import math
import logging
import numpy as np
import pandas as pd
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.trust_engine import calculate_trust_score


def load_and_preprocess_cmu_dataset():
    """
    Loads DSL-StrongPasswordData.csv and extracts 4D feature vectors grouped by subject.
    Returns:
        dict mapping subject_id -> numpy array (400, 4) of feature vectors
    """
    dataset_path = BASE_DIR / "data" / "DSL-StrongPasswordData.csv"
    if not dataset_path.exists():
        logger.error(f"Dataset not found at {dataset_path}")
        return None

    df = pd.read_csv(dataset_path)
    
    hold_cols = [c for c in df.columns if c.startswith("H.")]
    ud_cols = [c for c in df.columns if c.startswith("UD.")]
    
    df["avg_dwell_time_ms"] = df[hold_cols].mean(axis=1) * 1000.0
    df["std_dwell_time_ms"] = df[hold_cols].std(axis=1) * 1000.0
    df["avg_flight_time_ms"] = df[ud_cols].mean(axis=1) * 1000.0
    df["std_flight_time_ms"] = df[ud_cols].std(axis=1) * 1000.0
    
    total_time = df[hold_cols].sum(axis=1) + df[ud_cols].sum(axis=1)
    df["typing_speed_cps"] = 10.0 / total_time
    
    feature_cols = ["avg_dwell_time_ms", "std_dwell_time_ms", "avg_flight_time_ms", "typing_speed_cps"]
    
    subjects = df["subject"].unique()
    logger.info(f"Loaded CMU Keystroke Dataset: {len(df)} total rows across {len(subjects)} subjects.")
    
    subject_data = {}
    for sub in subjects:
        sub_df = df[df["subject"] == sub][feature_cols].copy()
        sub_df = sub_df.replace([np.inf, -np.inf], np.nan).dropna().clip(lower=0)
        subject_data[sub] = sub_df.values
        
    return subject_data


def evaluate_biometric_performance():
    logger.info("=" * 75)
    logger.info("  TrustGuard AI v2.0 — Multi-Subject Biometric & Adversarial Evaluation")
    logger.info("=" * 75)

    subject_data = load_and_preprocess_cmu_dataset()
    if not subject_data:
        return

    subjects = list(subject_data.keys())
    num_subjects = len(subjects)

    all_genuine_scores = []
    all_impostor_scores = []

    logger.info(f"\nPerforming Subject-Disjoint Evaluation across {num_subjects} subjects...")
    logger.info("  - Enrollment : First 200 repetitions (Sessions 1-25)")
    logger.info("  - Genuine Test: Unseen 200 repetitions (Sessions 26-50)")
    logger.info("  - Impostor Test: Cross-subject samples from remaining 50 subjects")

    for i, sub in enumerate(subjects):
        data = subject_data[sub]
        if len(data) < 400:
            continue
        
        # 1. Subject-Disjoint Split (Enrollment vs Genuine Test)
        enroll_matrix = data[:200]
        genuine_test_matrix = data[200:400]
        
        # Compute baseline profile (mu and regularized cov_inv) for subject sub
        mu = np.mean(enroll_matrix, axis=0)
        cov = np.cov(enroll_matrix, rowvar=False) + np.eye(4) * 1e-4
        cov_inv = np.linalg.inv(cov)
        
        # 2. Vectorized Genuine Evaluation
        diff_gen = genuine_test_matrix - mu
        dm2_gen = np.sum((diff_gen @ cov_inv) * diff_gen, axis=1)
        dm_gen = np.sqrt(np.maximum(dm2_gen, 0.0))
        sim_gen = np.exp(-dm_gen / 2.0) * 100.0
        
        for idx in range(len(genuine_test_matrix)):
            row = genuine_test_matrix[idx]
            sample_dict = {
                "avg_dwell_time_ms": float(row[0]), "std_dwell_time_ms": float(row[1]),
                "avg_flight_time_ms": float(row[2]), "std_flight_time_ms": 15.0,
                "typing_speed_cps": float(row[3]), "avg_mouse_velocity_px_s": 150.0,
                "click_count": 5, "keystroke_count": 10, "session_duration_s": 5.0
            }
            score = calculate_trust_score(sample_dict, similarity_score=float(sim_gen[idx]))
            all_genuine_scores.append(score)

        # 3. Vectorized Impostor Evaluation (from remaining subjects)
        other_subjects = [s for s in subjects if s != sub]
        impostor_samples_list = []
        for other_sub in other_subjects:
            impostor_samples_list.append(subject_data[other_sub][200:204]) # 4 samples per other subject = 200
        impostor_matrix = np.vstack(impostor_samples_list)
        
        diff_imp = impostor_matrix - mu
        dm2_imp = np.sum((diff_imp @ cov_inv) * diff_imp, axis=1)
        dm_imp = np.sqrt(np.maximum(dm2_imp, 0.0))
        sim_imp = np.exp(-dm_imp / 2.0) * 100.0
        
        for idx in range(len(impostor_matrix)):
            row = impostor_matrix[idx]
            sample_dict = {
                "avg_dwell_time_ms": float(row[0]), "std_dwell_time_ms": float(row[1]),
                "avg_flight_time_ms": float(row[2]), "std_flight_time_ms": 15.0,
                "typing_speed_cps": float(row[3]), "avg_mouse_velocity_px_s": 150.0,
                "click_count": 5, "keystroke_count": 10, "session_duration_s": 5.0
            }
            score = calculate_trust_score(sample_dict, similarity_score=float(sim_imp[idx]))
            all_impostor_scores.append(score)

    all_genuine_scores = np.array(all_genuine_scores)
    all_impostor_scores = np.array(all_impostor_scores)

    num_genuine = len(all_genuine_scores)
    num_impostor = len(all_impostor_scores)

    logger.info(f"Evaluated {num_genuine} Genuine Test Samples and {num_impostor} Impostor Test Samples.")

    # 4. Sweep Decision Thresholds to Compute FAR, FRR, EER, ROC Curve, and AUC
    thresholds = np.linspace(0.0, 100.0, 201)
    far_list = []
    frr_list = []
    tpr_list = []
    fpr_list = []

    min_diff = 1.0
    eer_val = 0.0
    eer_threshold = 50.0

    for T in thresholds:
        far = np.mean(all_impostor_scores >= T)
        frr = np.mean(all_genuine_scores < T)
        tpr = 1.0 - frr
        fpr = far

        far_list.append(far)
        frr_list.append(frr)
        tpr_list.append(tpr)
        fpr_list.append(fpr)

        diff = abs(far - frr)
        if diff < min_diff:
            min_diff = diff
            eer_val = (far + frr) / 2.0
            eer_threshold = T

    # Calculate Area Under ROC Curve (AUC) using trapezoidal rule
    sorted_idx = np.argsort(fpr_list)
    sorted_fpr = np.array(fpr_list)[sorted_idx]
    sorted_tpr = np.array(tpr_list)[sorted_idx]
    if hasattr(np, "trapezoid"):
        auc_val = float(np.trapezoid(sorted_tpr, sorted_fpr))
    else:
        auc_val = float(np.sum(np.diff(sorted_fpr) * (sorted_tpr[1:] + sorted_tpr[:-1]) / 2.0))

    # 5. Compute Classification Metrics at Operating Threshold T = 50.0
    op_threshold = 50.0
    tp = np.sum(all_genuine_scores >= op_threshold)
    fn = np.sum(all_genuine_scores < op_threshold)
    tn = np.sum(all_impostor_scores < op_threshold)
    fp = np.sum(all_impostor_scores >= op_threshold)

    far_op = (fp / num_impostor) * 100.0
    frr_op = (fn / num_genuine) * 100.0

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    # 6. Adversarial Stress Testing (Script Bot & Erratic Attacker)
    logger.info("\n" + "=" * 75)
    logger.info("  ADVERSARIAL STRESS TESTING (Bot & Evasion Simulation)")
    logger.info("=" * 75)
    
    # Script Bot: Zero-variance automated timing spoofing
    bot_scores = []
    for _ in range(500):
        sample = {
            "avg_dwell_time_ms": 100.0, "std_dwell_time_ms": 0.0,
            "avg_flight_time_ms": 100.0, "std_flight_time_ms": 0.0,
            "typing_speed_cps": 5.0, "avg_mouse_velocity_px_s": 0.0,
            "click_count": 0, "keystroke_count": 10, "session_duration_s": 2.0
        }
        bot_scores.append(calculate_trust_score(sample, similarity_score=100.0))
    bot_scores = np.array(bot_scores)
    bot_accepted = np.sum(bot_scores >= op_threshold)
    bot_far = (bot_accepted / len(bot_scores)) * 100.0

    # Erratic Attacker
    np.random.seed(42)
    erratic_scores = []
    for _ in range(500):
        dwells = np.random.uniform(500, 1500, 10)
        flights = np.random.uniform(10, 50, 9)
        sample = {
            "avg_dwell_time_ms": float(np.mean(dwells)), "std_dwell_time_ms": float(np.std(dwells)),
            "avg_flight_time_ms": float(np.mean(flights)), "std_flight_time_ms": float(np.std(flights)),
            "typing_speed_cps": float(10.0 / (np.sum(dwells)/1000.0 + np.sum(flights)/1000.0)),
            "avg_mouse_velocity_px_s": 250.0, "click_count": 2, "keystroke_count": 10, "session_duration_s": 5.0
        }
        erratic_scores.append(calculate_trust_score(sample, similarity_score=100.0))
    erratic_scores = np.array(erratic_scores)
    erratic_accepted = np.sum(erratic_scores >= op_threshold)
    erratic_far = (erratic_accepted / len(erratic_scores)) * 100.0

    logger.info(f"Script Bot Evasion FAR         : {bot_far:.2f}% (Blocked: {100 - bot_far:.2f}%)")
    logger.info(f"Erratic Attacker Evasion FAR    : {erratic_far:.2f}% (Blocked: {100 - erratic_far:.2f}%)")

    # 7. Print Master Biometric Metric Report
    logger.info("\n" + "=" * 75)
    logger.info("  MASTER MULTI-SUBJECT BIOMETRIC PERFORMANCE REPORT")
    logger.info("=" * 75)
    logger.info(f"Subjects Evaluated           : {num_subjects}")
    logger.info(f"Total Test Evaluations       : {num_genuine + num_impostor} (Subject-Disjoint)")
    logger.info(f"  - Genuine Test Samples     : {num_genuine}")
    logger.info(f"  - Impostor Test Samples    : {num_impostor}")
    logger.info("-" * 75)
    logger.info(f"Equal Error Rate (EER)       : {eer_val * 100.0:.2f}% (at threshold T = {eer_threshold:.1f}%)")
    logger.info(f"Area Under ROC Curve (AUC)   : {auc_val:.4f}")
    logger.info("-" * 75)
    logger.info(f"At Default Operating Threshold T = {op_threshold:.1f}%:")
    logger.info(f"  - False Acceptance Rate (FAR): {far_op:.2f}% (Impostors accepted)")
    logger.info(f"  - False Rejection Rate (FRR): {frr_op:.2f}% (Genuines rejected)")
    logger.info(f"  - Precision                  : {precision:.4f}")
    logger.info(f"  - Recall                     : {recall:.4f}")
    logger.info(f"  - F1-Score                   : {f1_score:.4f}")
    logger.info("-" * 75)
    logger.info("CONFUSION MATRIX:")
    logger.info(f"  True Negatives (TN - Impostors Blocked) : {tn}")
    logger.info(f"  False Positives (FP - Impostors Allowed): {fp}")
    logger.info(f"  False Negatives (FN - Genuines Blocked) : {fn}")
    logger.info(f"  True Positives  (TP - Genuines Allowed) : {tp}")
    logger.info("=" * 75)

    return {
        "num_subjects": num_subjects,
        "num_genuine": num_genuine,
        "num_impostor": num_impostor,
        "eer_percent": round(eer_val * 100.0, 2),
        "eer_threshold": round(eer_threshold, 1),
        "auc": round(auc_val, 4),
        "far_operating": round(far_op, 2),
        "frr_operating": round(frr_op, 2),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1_score, 4),
        "confusion_matrix": {"TN": int(tn), "FP": int(fp), "FN": int(fn), "TP": int(tp)},
        "adversarial_bot_far": round(bot_far, 2),
        "adversarial_erratic_far": round(erratic_far, 2)
    }

if __name__ == "__main__":
    evaluate_biometric_performance()
