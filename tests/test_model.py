import joblib
import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression

from heartml.features import FeatureBuilder, build_pipeline
from heartml.settings import FEATURES
from heartml.train import split_data


def test_split_is_disjoint_stratified_and_reproducible(frame):
    train, test = split_data(frame)
    assert len(train) == 242 and len(test) == 61
    assert set(train).isdisjoint(test)
    assert set(train) | set(test) == set(range(len(frame)))
    assert np.array_equal(test, split_data(frame)[1])
    assert abs(frame.iloc[train].target.mean() - frame.iloc[test].target.mean()) < 0.03


def test_feature_engineering_is_label_free_and_does_not_mutate(frame):
    X = frame[FEATURES].copy()
    original = X.copy(deep=True)
    transformed = FeatureBuilder().fit_transform(X)
    assert len(transformed.columns) == 15
    assert np.allclose(transformed.age_oldpeak, X.age * X.oldpeak)
    assert X.equals(original)
    with pytest.raises(ValueError):
        FeatureBuilder().fit_transform(frame)


def test_imputer_is_fit_on_training_values_only(frame):
    training = frame.iloc[:20][FEATURES].copy()
    training["age"] = np.arange(20) + 30.0
    training.loc[training.index[0], "age"] = np.nan
    pipeline = build_pipeline(LogisticRegression(max_iter=2000)).fit(
        training,
        frame.iloc[:20].target,
    )
    fitted_median = pipeline["preprocess"].named_transformers_["numeric"]["impute"].statistics_[0]
    assert fitted_median == training.age.median()
    heldout = training.iloc[[0]].copy()
    heldout["age"] = 109.0
    pipeline.predict_proba(heldout)
    assert (
        pipeline["preprocess"].named_transformers_["numeric"]["impute"].statistics_[0]
        == fitted_median
    )


def test_serialized_pipeline_preserves_probabilities_and_missing_handling(frame, tmp_path):
    train, test = split_data(frame)
    pipeline = build_pipeline(LogisticRegression(max_iter=2000, random_state=42)).fit(
        frame.iloc[train][FEATURES],
        frame.iloc[train].target,
    )
    X = frame.iloc[test][FEATURES].copy()
    X.loc[X.index[0], ["ca", "thal"]] = np.nan
    before = pipeline.predict_proba(X)
    path = tmp_path / "pipeline.joblib"
    joblib.dump(pipeline, path)
    after = joblib.load(path).predict_proba(X)
    assert np.allclose(before, after)
    assert np.isfinite(after).all()
    assert np.allclose(after.sum(axis=1), 1)
