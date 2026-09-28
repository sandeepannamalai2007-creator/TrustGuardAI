import logging

import pandas as pd

logger = logging.getLogger(__name__)

PASSWORD_LENGTH = 10


def load_dataset(path):
    """Load the CMU Keystroke Dynamics dataset."""
    df = pd.read_csv(path)
    logger.info("Dataset loaded: %s rows, %s columns", df.shape[0], df.shape[1])
    return df


def engineer_features(df):
    """Convert raw keystroke timings into the 7D TrustGuard feature vector."""
    hold_cols = [c for c in df.columns if c.startswith("H.")]
    ud_cols = [c for c in df.columns if c.startswith("UD.")]
    if not hold_cols or not ud_cols:
        raise ValueError("Dataset must contain H.* hold-time and UD.* flight-time columns")

    processed = pd.DataFrame(index=df.index)
    processed["avg_dwell_time_ms"] = df[hold_cols].mean(axis=1) * 1000.0
    processed["std_dwell_time_ms"] = df[hold_cols].std(axis=1).fillna(0.0) * 1000.0
    processed["avg_flight_time_ms"] = df[ud_cols].mean(axis=1) * 1000.0
    processed["std_flight_time_ms"] = df[ud_cols].std(axis=1).fillna(0.0) * 1000.0

    total_time = df[hold_cols].sum(axis=1) + df[ud_cols].sum(axis=1)
    processed["typing_speed_cps"] = PASSWORD_LENGTH / total_time.replace(0, pd.NA)
    processed["dwell_flight_ratio"] = processed["avg_dwell_time_ms"] / (
        processed["avg_flight_time_ms"] + 1e-5
    )
    processed["pause_frequency"] = (df[ud_cols] * 1000.0 > 200.0).sum(axis=1).astype(float)
    return processed


if __name__ == "__main__":
    import os

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    dataset_path = os.path.join(BASE_DIR, "data", "DSL-StrongPasswordData.csv")
    dataset = load_dataset(dataset_path)
    processed = engineer_features(dataset)
    logger.info("Processed features:\n%s", processed.head())
    logger.info("Statistics:\n%s", processed.describe())
