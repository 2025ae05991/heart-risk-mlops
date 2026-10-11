"""Fail CI if the model package is incomplete or its holdout quality is below the demo gate."""

import json

import joblib

from heartml.data import sha256
from heartml.settings import MODEL_DIR

if __name__ == "__main__":
    metadata = json.loads((MODEL_DIR / "metadata.json").read_text())
    assert sha256(MODEL_DIR / "model.joblib") == metadata["model_sha256"]
    model = joblib.load(MODEL_DIR / "model.joblib")
    assert list(model.named_steps) == ["features", "preprocess", "classifier"]
    assert metadata["test_metrics"]["roc_auc"] >= 0.75, "Holdout ROC-AUC gate failed"
    assert metadata["test_metrics"]["accuracy"] >= 0.70, "Holdout accuracy gate failed"
    print("Model checksum, pipeline contract, and educational quality gates passed.")
