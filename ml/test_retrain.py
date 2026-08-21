"""
ml/test_retrain.py

Unit tests for the robust retraining pipeline with evaluation gate and model versioning.
"""

import numpy as np

from ml.retrain import _compute_dataset_hash, _get_next_version_dir, retrain_model


def test_compute_dataset_hash():
    X1 = np.array([[100.0, 10.0, 150.0], [110.0, 12.0, 140.0]])
    X2 = np.array([[100.0, 10.0, 150.0], [110.0, 12.0, 140.0]])
    X3 = np.array([[200.0, 20.0, 300.0], [210.0, 22.0, 340.0]])

    hash1 = _compute_dataset_hash(X1)
    hash2 = _compute_dataset_hash(X2)
    hash3 = _compute_dataset_hash(X3)

    assert hash1 == hash2
    assert hash1 != hash3


def test_get_next_version_dir():
    vdir = _get_next_version_dir()
    assert vdir.exists()
    assert vdir.is_dir()
    assert vdir.name.startswith("v")


def test_retrain_model_evaluation_gate():
    res = retrain_model(force=False)
    assert isinstance(res, dict)
    assert "triggered" in res
