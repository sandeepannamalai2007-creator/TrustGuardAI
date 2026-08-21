"""
ml/test_poisoning.py

Adversarial Training-Data Poisoning Resilience Simulation (Item 12).
Evaluates TrustGuard AI's resilience against 0%, 5%, 10%, 20%, and 30% adversarial sample injection.
"""

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


def _evaluate_dataset_performance(X_clean_gen, X_clean_imp, X_train):
    scaler = StandardScaler()
    scaled_train = scaler.fit_transform(X_train)
    clf = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    clf.fit(scaled_train)

    raw_train = clf.decision_function(scaled_train)
    p_min, p_max = float(np.percentile(raw_train, 5)), float(np.percentile(raw_train, 95))
    scale = max(p_max - p_min, 1e-4)

    raw_gen = clf.decision_function(scaler.transform(X_clean_gen))
    raw_imp = clf.decision_function(scaler.transform(X_clean_imp))

    gen_scores = np.clip(((raw_gen - p_min) / scale) * 100.0, 0.0, 100.0)
    imp_scores = np.clip(((raw_imp - p_min) / scale) * 100.0, 0.0, 100.0)

    far = np.mean(imp_scores >= 50.0)
    frr = np.mean(gen_scores < 50.0)
    eer = (far + frr) / 2.0
    return round(float(eer * 100.0), 2)


def test_poisoning_resilience_simulation():
    np.random.seed(42)
    # Generate clean genuine baseline (500 samples)
    n_clean = 500
    clean_gen = np.random.normal(loc=[110.0, 12.0, 140.0, 15.0, 4.5, 0.8, 0.0], scale=[10.0, 2.0, 15.0, 3.0, 0.5, 0.1, 0.0], size=(n_clean, 7))
    clean_imp = np.random.normal(loc=[180.0, 30.0, 220.0, 35.0, 2.5, 0.4, 2.0], scale=[20.0, 5.0, 25.0, 5.0, 0.8, 0.2, 1.0], size=(500, 7))

    clean_eer = _evaluate_dataset_performance(clean_gen, clean_imp, clean_gen)

    poison_levels = [0.05, 0.10, 0.20, 0.30]
    results = {}

    for lvl in poison_levels:
        n_poison = int(n_clean * lvl)
        # Poison samples: attacker trying to confuse boundaries
        poison_samples = np.random.uniform(low=[50.0, 0.0, 300.0, 0.0, 10.0, 2.0, 5.0], high=[250.0, 50.0, 50.0, 50.0, 1.0, 0.1, 0.0], size=(n_poison, 7))
        poisoned_train = np.vstack([clean_gen, poison_samples])

        poisoned_eer = _evaluate_dataset_performance(clean_gen, clean_imp, poisoned_train)
        results[f"{int(lvl*100)}% Poisoning"] = poisoned_eer

        # Verify performance degradation threshold
        if lvl <= 0.10:
            assert abs(poisoned_eer - clean_eer) <= 25.0, f"Excessive degradation at {lvl*100}% poisoning"

    assert len(results) == 4

