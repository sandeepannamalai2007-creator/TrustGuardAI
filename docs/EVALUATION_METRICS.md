# 📊 Biometric Evaluation & Adversarial Stress Test Report — TrustGuard AI v2.0

## Executive Summary

TrustGuard AI v2.0 enforces a **Subject-Disjoint Multi-Subject Evaluation Protocol** across all 51 subjects in the CMU Keystroke Dynamics Benchmark Dataset (20,400 total test trials), alongside an **Adversarial Stress Test** for automated evasion bots.

---

## 1. 🛡️ Adversarial Stress Testing (Bot & Evasion Simulation)

Evaluates system resilience against automated timing spoofing and erratic anomaly injection:

| Attack Vector | Sample Count | FAR (Allowed) | Defense Rate (Blocked) | Status |
|---|---|---|---|---|
| **Zero-Variance Script Bot** (`std_dwell=0.0ms`) | 500 | **0.00%** | **100.00%** | ✅ **Passed (IDS Bot Alert)** |
| **Erratic Random Attacker** | 500 | **0.00%** | **100.00%** | ✅ **Passed (Entropy Anomaly)** |

> [!NOTE]
> Synthetic bot tests evaluate Intrusion Detection System (IDS) bot signature and entropy penalties, **not** multi-subject human biometric uniqueness.

---

## 2. 🧬 Multi-Subject Biometric Performance Report

Evaluated using a **Subject-Disjoint Protocol** (Enrollment: Sessions 1–25; Unseen Genuine Test: Sessions 26–50; Impostor Test: 50 cross-subject accounts):

- **Subjects Evaluated**: 51 subjects ($s002 \dots s052$)
- **Total Test Evaluations**: **20,400** (10,200 Genuine, 10,200 Impostor)
- **Data Leakage Prevention**: Zero sample overlap between enrollment and evaluation sets.

### Key Biometric Metrics

| Metric | Measured Value | Description |
|---|---|---|
| **Equal Error Rate (EER)** | **`40.08%`** | Threshold where $FAR(T) = FRR(T)$ at $T = 60.5\%$ |
| **ROC Area Under Curve (AUC)** | **`0.6330`** | Overall discrimination capability across all thresholds |
| **False Rejection Rate (FRR)** | **`17.32%`** | Genuine users flagged at default threshold $T = 50.0\%$ |
| **False Acceptance Rate (FAR)** | **`72.81%`** | Cross-subject human impostors allowed at default $T = 50.0\%$ |
| **Precision** | **`0.5317`** | Ratio of true genuine acceptances over total acceptances |
| **Recall** | **`0.8268`** | Ratio of true genuine acceptances over total genuine samples |
| **F1-Score** | **`0.6472`** | Harmonic mean of Precision and Recall |

### Confusion Matrix (At Default Threshold $T = 50.0\%$)

$$\begin{bmatrix} \text{TN (Impostors Blocked): 2,773} & \text{FP (Impostors Allowed): 7,427} \\ \text{FN (Genuines Blocked): 1,767} & \text{TP (Genuines Allowed): 8,433} \end{bmatrix}$$

---

## 3. 🔍 Scientific Discussion & Interview Context

1. **Why is the Human Impostor FAR 72.81% while Bot FAR is 0.00%?**
   - Automated bots exhibit non-human timing variance ($\sigma = 0\text{ms}$), triggering entropy penalties.
   - Human impostors type with natural biological variance. On short 10-character password strings, keystroke timing alone exhibits overlap across subjects, yielding an Equal Error Rate of **40.08%**.
2. **How does TrustGuard AI compensate in production?**
   - TrustGuard AI combines keystroke dynamics with **mouse kinematics**, **adaptive thresholds**, and a **4-tier security state machine** to accumulate risk over multi-window sessions rather than relying on a single typing snapshot.
