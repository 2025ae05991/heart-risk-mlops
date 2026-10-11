import numpy as np
import pandas as pd
import pytest

from heartml.data import CODES, EXPECTED_RAW_SHA256, clean_frame, sha256
from heartml.settings import FEATURES, RAW_PATH


def test_dataset_identity_and_contract(frame):
    assert sha256(RAW_PATH) == EXPECTED_RAW_SHA256
    assert len(frame) == 303
    assert list(frame.columns) == FEATURES + ["target"]
    assert frame["target"].value_counts().to_dict() == {0: 164, 1: 139}
    assert frame.isna().sum().sum() == 6
    assert frame["ca"].isna().sum() == 4
    assert frame["thal"].isna().sum() == 2


def test_original_categorical_codes(frame):
    for name, codes in CODES.items():
        assert set(frame[name].dropna()).issubset(codes)
    assert set(frame["thal"].dropna()) == {3.0, 6.0, 7.0}


def test_cleaning_maps_target_retains_missing_and_removes_duplicates(frame):
    raw = frame.iloc[:3].drop(columns="target").copy()
    raw["num"] = [0, 2, 4]
    raw.loc[0, "ca"] = np.nan
    raw = pd.concat([raw, raw.iloc[[0]]], ignore_index=True)
    cleaned = clean_frame(raw)
    assert len(cleaned) == 3
    assert cleaned["target"].tolist() == [0, 1, 1]
    assert cleaned.loc[0, "ca"] != cleaned.loc[0, "ca"]


@pytest.mark.parametrize("column,value", [("num", 8), ("cp", 0), ("thal", 2), ("age", -4)])
def test_invalid_raw_data_is_rejected(frame, column, value):
    raw = frame.iloc[:3].drop(columns="target").copy()
    raw["num"] = 0
    raw.loc[0, column] = value
    with pytest.raises(ValueError):
        clean_frame(raw)
