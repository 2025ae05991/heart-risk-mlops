"""One serializable preprocessing pipeline for both fitting and serving."""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from heartml.settings import CATEGORICAL, DERIVED, FEATURES, NUMERIC


class FeatureBuilder(TransformerMixin, BaseEstimator):
    """Create two label-free interactions, without learning from the holdout set."""

    def fit(self, X, y=None):
        self._check(X)
        self.feature_names_in_ = np.asarray(FEATURES, dtype=object)
        return self

    def transform(self, X):
        self._check(X)
        result = X.loc[:, FEATURES].copy()
        result["age_oldpeak"] = result["age"] * result["oldpeak"]
        result["exercise_oldpeak"] = result["exang"] * result["oldpeak"]
        return result

    def get_feature_names_out(self, input_features=None):
        return np.asarray(FEATURES + DERIVED, dtype=object)

    @staticmethod
    def _check(X):
        if not isinstance(X, pd.DataFrame):
            raise TypeError("Pipeline input must be a pandas DataFrame with named columns.")
        if set(X.columns) != set(FEATURES):
            raise ValueError("Input must contain exactly the 13 original Cleveland features.")


def build_pipeline(estimator) -> Pipeline:
    numeric = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scale", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        [
            ("impute", SimpleImputer(strategy="most_frequent", keep_empty_features=True)),
            ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    preprocess = ColumnTransformer(
        [
            ("numeric", numeric, NUMERIC + DERIVED),
            ("categorical", categorical, CATEGORICAL),
        ]
    )
    return Pipeline(
        [
            ("features", FeatureBuilder()),
            ("preprocess", preprocess),
            ("classifier", estimator),
        ]
    )
