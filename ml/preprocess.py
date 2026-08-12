import pandas as pd
import numpy as np


PASSWORD_LENGTH = 10


def load_dataset(path):
    """
    Load CMU Keystroke Dynamics dataset.
    """
    df = pd.read_csv(path)

    print("=" * 50)
    print("Dataset Loaded Successfully")
    print("=" * 50)
    print("Rows    :", df.shape[0])
    print("Columns :", df.shape[1])

    return df


def engineer_features(df):
    """
    Convert raw keystroke timings into
    TrustGuard AI features.
    """

    # Hold Time Columns
    hold_cols = [c for c in df.columns if c.startswith("H.")]

    # Flight Time Columns
    ud_cols = [c for c in df.columns if c.startswith("UD.")]

    print("\nHold Columns :", len(hold_cols))
    print("Flight Columns :", len(ud_cols))

    processed = pd.DataFrame()

    # Average Hold Time
    processed["avg_dwell_time_ms"] = (
        df[hold_cols].mean(axis=1) * 1000
    )

    # Average Flight Time
    processed["avg_flight_time_ms"] = (
        df[ud_cols].mean(axis=1) * 1000
    )

    # Total typing time
    total_time = (
        df[hold_cols].sum(axis=1)
        +
        df[ud_cols].sum(axis=1)
    )

    # Characters per second
    processed["typing_speed_cps"] = (
        PASSWORD_LENGTH / total_time
    )

    return processed


if __name__ == "__main__":
    import os
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    dataset_path = os.path.join(BASE_DIR, "data", "DSL-StrongPasswordData.csv")
    dataset = load_dataset(dataset_path)

    processed = engineer_features(dataset)

    print("\nProcessed Features")

    print(processed.head())

    print("\nStatistics")

    print(processed.describe())