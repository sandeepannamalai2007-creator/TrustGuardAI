# 📊 Machine Learning Evaluation Report — TrustGuard AI v2.0

## Executive Summary

This report provides a rigorous academic and engineering evaluation of TrustGuard AI's biometric machine learning pipeline. Evaluation is performed using a **Session-Disjoint Genuine Testing + Cross-Subject Impostor Evaluation** protocol across all 51 subjects in the CMU Keystroke Dynamics Benchmark Dataset (20,400 total test trials), alongside an independent **Adversarial Stress Test** for automated evasion bots.

---

## 1. 📁 Dataset & Feature Extraction

### Dataset Overview
- **Source**: CMU Keystroke Dynamics Benchmark Dataset (`DSL-StrongPasswordData.csv`)
- **Subjects**: 51 subjects ($s002 \dots s052$)
- **Sessions per Subject**: 50 sessions per subject, 8 repetitions per session ($400$ timing vectors per subject, $20,400$ total dataset rows).
- **Password String**: `.5600wstrv` (10 key presses, 9 key-unpress to key-press transitions).

### Feature Extraction Methodology
For each 10-key repetition vector:
1. **Mean Dwell Time ($\mu_{\text{dwell}}$)**: Average duration (ms) keys are held down ($\frac{1}{10} \sum H_k$).
2. **Standard Deviation of Dwell Time ($\sigma_{\text{dwell}}$)**: Variance in key hold durations.
3. **Mean Flight Time ($\mu_{\text{flight}}$)**: Average duration (ms) between key release and next key press ($\frac{1}{9} \sum UD_k$).
4. **Standard Deviation of Flight Time ($\sigma_{\text{flight}}$)**: Actual calculated variance in flight times from dataset ($UD$ columns).
5. **Typing Speed ($CPS$)**: Characters per second ($\frac{10}{\sum H_k + \sum UD_k}$).

---

## 2. 🔬 Evaluation Methodology

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      CMU Keystroke Dataset (51 Subjects)                 │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
             ┌───────────────────────┴────────────────────────┐
             ▼                                                ▼
┌──────────────────────────┐                      ┌──────────────────────────┐
│   Enrollment Profile     │                      │   Evaluation Testing     │
│   Sessions 1–25 (200)    │                      │   Sessions 26–50 (200)   │
└────────────┬─────────────┘                      └───────────┬──────────────┘
             │                                                │
             ▼                                                │
┌──────────────────────────┐                                  │
│ Mean μ & Covariance Σ    │                                  │
└────────────┬─────────────┘                                  │
             │                                                │
             └───────────────────────┬────────────────────────┘
                                     ▼
                    ┌─────────────────────────────────┐
                    │  Production Trust Engine Pipeline│
                    │  Isolation Forest + Mahalanobis │
                    │  + Shannon Entropy Check        │
                    └────────────────┬────────────────┘
                                     │
                   ┌─────────────────┴──────────────────┐
                   ▼                                    ▼
       ┌───────────────────────┐            ┌───────────────────────┐
       │ Session-Disjoint      │            │ Cross-Subject         │
       │ Genuine Testing       │            │ Impostor Testing      │
       │ (10,200 Trials)       │            │ (10,200 Trials)       │
       └───────────────────────┘            └───────────────────────┘
```

### Enrollment Methodology
- For each subject $S_i$, the first 25 sessions (200 repetitions) form the **Enrollment Set**.
- Computes baseline mean vector $\boldsymbol{\mu}_i \in \mathbb{R}^4$ and regularized inverse covariance matrix $\boldsymbol{\Sigma}_i^{-1}$ over features $[\mu_{\text{dwell}}, \sigma_{\text{dwell}}, \mu_{\text{flight}}, CPS]$.

### Genuine Testing Methodology (Session-Disjoint)
- The remaining 25 sessions (200 repetitions) of the **SAME** subject $S_i$ form the **Genuine Test Set**.
- Ensures zero session leakage between profile enrollment and genuine evaluation.

### Impostor Testing Methodology (Cross-Subject)
- For subject $S_i$, 4 repetitions from each of the other 50 subjects $S_j \neq S_i$ ($200$ total cross-subject impostor trials) are evaluated against $S_i$'s profile.

---

## 3. 📈 Production Pipeline Alignment

The evaluation script `ml/evaluate_model.py` executes the exact production scoring pipeline:
1. **Isolation Forest ML Anomaly Score**: `predictor.predict_trust_score(sample)`
2. **Mahalanobis Similarity Score**: $S_{\text{sim}} = 100 \cdot \exp(-\frac{D_M}{2})$ where $D_M = \sqrt{(\mathbf{x} - \boldsymbol{\mu})^T \boldsymbol{\Sigma}^{-1} (\mathbf{x} - \boldsymbol{\mu})}$.
3. **Shannon Entropy Check**: Penalizes zero-variance bot vectors ($\sigma_{\text{dwell}} = 0$, $\sigma_{\text{flight}} = 0$).
4. **Combined Hybrid Trust Score**:
   $$T = \max\left(0, \min\left(100, 0.45 \cdot \text{Score}_{\text{ML}} + 0.45 \cdot S_{\text{sim}} - \text{Penalty}_{\text{entropy}}\right)\right)$$

---

## 4. 📊 Empirical Evaluation Results

### Master Biometric Metrics Table
| Metric | Measured Value | Definition / Interpretation |
|---|---|---|
| **Subjects Evaluated** | **`51`** | Total distinct human subjects in benchmark |
| **Genuine Test Samples** | **`10,200`** | Unseen sessions 26–50 (Session-disjoint) |
| **Impostor Test Samples** | **`10,200`** | Cross-subject unauthorized access attempts |
| **Equal Error Rate (EER)** | **`40.08%`** | Operating point where $FAR(T) = FRR(T)$ at $T = 60.5\%$ |
| **ROC Area Under Curve (AUC)** | **`0.6330`** | Discrimination capability across all operating thresholds |
| **False Acceptance Rate (FAR)** | **`72.81%`** | Cross-subject human impostors allowed at default $T = 50.0\%$ |
| **False Rejection Rate (FRR)** | **`17.32%`** | Genuine users flagged at default $T = 50.0\%$ |
| **Precision** | **`0.5317`** | Ratio of true genuine acceptances over total acceptances |
| **Recall** | **`0.8268`** | Ratio of true genuine acceptances over total genuine samples |
| **F1-Score** | **`0.6472`** | Harmonic mean of Precision and Recall |

### Confusion Matrix (Operating Threshold $T = 50.0\%$)
| | Predicted Impostor (0) | Predicted Genuine (1) |
|---|---|---|
| **Actual Impostor (0)** | **TN = 2,773** | **FP = 7,427** |
| **Actual Genuine (1)** | **FN = 1,767** | **TP = 8,433** |

---

## 5. 🛡️ Adversarial Stress Testing (Bot & Evasion Simulation)

Evaluates system resilience against automated timing spoofing and erratic anomaly injection:

| Attack Vector | Sample Count | FAR (Allowed) | Defense Rate (Blocked) | Status |
|---|---|---|---|---|
| **Zero-Variance Script Bot** (`std_dwell=0.0ms`, `std_flight=0.0ms`) | 500 | **0.00%** | **100.00%** | ✅ **Passed (Entropy IDS)** |
| **Erratic Random Attacker** | 500 | **0.00%** | **100.00%** | ✅ **Passed (Anomaly Check)** |

> [!NOTE]
> Bot testing evaluates Intrusion Detection System (IDS) signature and entropy penalties, which operate independently of human biometric timing similarities.

---

## 6. 🖼️ Generated Evaluation Plots

High-resolution plots are stored in [`ml/evaluation_results/`](../ml/evaluation_results/):
- **`roc_curve.png`**: ROC Curve plot ($TPR$ vs $FPR$) labeled with $AUC = 0.6330$.
- **`confusion_matrix.png`**: Heatmap of True Negatives, False Positives, False Negatives, and True Positives.
- **`score_distribution.png`**: Overlaid probability density histogram of Genuine vs Impostor scores.
- **`eer_curve.png`**: FAR and FRR curves vs Decision Threshold showing exact EER intersection ($40.08\%$ at $T=60.5\%$).

---

## 7. 💡 Limitations & Engineering Tradeoffs

1. **Short Password Text Strings**:
   - Biometric evaluations on short 10-character password strings exhibit cross-subject timing overlap, resulting in an EER of **40.08%**.
2. **Production Compensation**:
   - In production, TrustGuard AI compensates by integrating **mouse movement kinematics**, **adaptive user thresholds**, and **multi-window hysteresis state escalation** (`NORMAL` $\to$ `SUSPICIOUS` $\to$ `HIGH_RISK` $\to$ `LOCKED`), ensuring single short typing bursts do not cause immediate false locks.
