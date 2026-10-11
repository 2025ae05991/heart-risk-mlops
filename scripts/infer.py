"""Offline inference using exactly the same packaged pipeline as the API."""

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd

from heartml.api import Patient
from heartml.settings import FEATURES, MODEL_DIR

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("examples/patient.json"))
    args = parser.parse_args()
    sample = Patient.model_validate(json.loads(args.input.read_text())).model_dump()
    probability = float(
        joblib.load(MODEL_DIR / "model.joblib").predict_proba(
            pd.DataFrame([sample], columns=FEATURES).astype(float)
        )[0, 1]
    )
    print(
        json.dumps(
            {"prediction": int(probability >= 0.5), "probability_disease": probability}, indent=2
        )
    )
