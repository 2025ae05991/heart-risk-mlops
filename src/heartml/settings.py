"""Central paths and feature contracts, independent of the working directory."""

import os
from pathlib import Path

ROOT = Path(os.environ.get("HEARTML_ROOT", Path(__file__).resolve().parents[2]))
RAW_PATH = ROOT / "data/raw/processed.cleveland.data"
CLEAN_PATH = ROOT / "data/processed/heart_clean.csv"
REPORTS = ROOT / "reports"
MODEL_DIR = ROOT / "artifacts/model"
SEED = 42
TARGET = "target"
FEATURES = [
    "age",
    "sex",
    "cp",
    "trestbps",
    "chol",
    "fbs",
    "restecg",
    "thalach",
    "exang",
    "oldpeak",
    "slope",
    "ca",
    "thal",
]
NUMERIC = ["age", "trestbps", "chol", "thalach", "oldpeak"]
CATEGORICAL = ["sex", "cp", "fbs", "restecg", "exang", "slope", "ca", "thal"]
DERIVED = ["age_oldpeak", "exercise_oldpeak"]
EXPERIMENT = "HeartRisk-Cleveland"
