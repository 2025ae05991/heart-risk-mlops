"""Acquire the original UCI file and perform deterministic, non-learned cleaning."""

import hashlib
import io
import json
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from heartml.settings import CLEAN_PATH, FEATURES, RAW_PATH, ROOT, TARGET

SOURCE_URL = "https://archive.ics.uci.edu/static/public/45/heart+disease.zip"
EXPECTED_RAW_SHA256 = "a74b7efa387bc9d108d7d0115d831fe9b414b29ae7124f331b622b4efa0427c8"
CODES = {
    "sex": {0, 1},
    "cp": {1, 2, 3, 4},
    "fbs": {0, 1},
    "restecg": {0, 1, 2},
    "exang": {0, 1},
    "slope": {1, 2, 3},
    "ca": {0, 1, 2, 3},
    "thal": {3, 6, 7},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def acquire(force: bool = False, path: Path = RAW_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if force or not path.exists():
        request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "HeartML/1.0"})
        with urllib.request.urlopen(request, timeout=90) as response:
            archive = zipfile.ZipFile(io.BytesIO(response.read()))
        raw = archive.read("processed.cleveland.data")
        if hashlib.sha256(raw).hexdigest() != EXPECTED_RAW_SHA256:
            raise ValueError("UCI raw checksum changed; review the dataset before using it.")
        path.write_bytes(raw)
    if sha256(path) != EXPECTED_RAW_SHA256:
        raise ValueError("Raw file checksum mismatch; restore it or re-download with --force.")
    return path


def clean_frame(raw: pd.DataFrame) -> pd.DataFrame:
    expected = FEATURES + ["num"]
    if set(raw.columns) != set(expected):
        raise ValueError("Raw dataset must contain the 13 features and num target.")
    frame = raw.loc[:, expected].replace("?", float("nan")).copy()
    for column in expected:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    if frame["num"].isna().any() or not frame["num"].isin(range(5)).all():
        raise ValueError("Target must be a complete UCI diagnosis code from 0 through 4.")
    for column, codes in CODES.items():
        if not frame[column].dropna().isin(codes).all():
            raise ValueError(f"Invalid original Cleveland category in {column}.")
    if not frame["age"].dropna().between(18, 110).all():
        raise ValueError("Age outside the supported adult range.")
    if frame[FEATURES].isna().all(axis=1).any():
        raise ValueError("A patient row cannot have every feature missing.")
    frame[TARGET] = (frame.pop("num") > 0).astype(int)
    return frame.drop_duplicates().reset_index(drop=True)


def prepare(raw_path: Path = RAW_PATH, output_path: Path = CLEAN_PATH) -> pd.DataFrame:
    raw = pd.read_csv(raw_path, names=FEATURES + ["num"], na_values=["?"])
    frame = clean_frame(raw)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False, float_format="%.8g")
    summary = {
        "source_url": SOURCE_URL,
        "citation": "Janosi et al. (1989), UCI Heart Disease, DOI 10.24432/C52P4X",
        "license": "CC BY 4.0",
        "raw_sha256": sha256(raw_path),
        "clean_sha256": sha256(output_path),
        "raw_rows": len(raw),
        "clean_rows": len(frame),
        "duplicates_removed": len(raw) - len(frame),
        "raw_predictors": len(FEATURES),
        "engineered_predictors": 15,
        "target_mapping": "num=0 -> 0; num=1,2,3,4 -> 1",
        "class_counts": frame[TARGET].value_counts().sort_index().to_dict(),
        "missing_values": frame.isna().sum().to_dict(),
        "missing_policy": "Preserve nulls; fit imputers inside training/CV pipelines only.",
    }
    (ROOT / "data/processed/data_summary.json").write_text(json.dumps(summary, indent=2))
    return frame


def load_clean(path: Path = CLEAN_PATH) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if set(frame.columns) != set(FEATURES + [TARGET]):
        raise ValueError("Clean dataset has the wrong feature contract.")
    if not frame[TARGET].isin([0, 1]).all():
        raise ValueError("Clean target must be binary and complete.")
    return frame
