"""Compare models using training-only CV, then evaluate one winner on held-out data."""

import argparse
import importlib.metadata
import json
import os
import platform
import subprocess

import joblib
import matplotlib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from mlflow.models import infer_signature
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import ConfusionMatrixDisplay, RocCurveDisplay
from sklearn.model_selection import ParameterGrid, StratifiedKFold, train_test_split

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from heartml.data import load_clean, sha256
from heartml.evaluation import compute_metrics
from heartml.features import build_pipeline
from heartml.settings import CLEAN_PATH, EXPERIMENT, FEATURES, MODEL_DIR, REPORTS, ROOT, SEED


def split_data(frame, seed=SEED):
    train_idx, test_idx = train_test_split(
        np.arange(len(frame)),
        test_size=0.2,
        stratify=frame["target"],
        random_state=seed,
    )
    return train_idx, test_idx


def candidates(quick=False):
    lr_grid = {"C": [0.1, 1.0, 10.0], "class_weight": [None, "balanced"]}
    rf_grid = {"max_depth": [4, 8, None], "min_samples_leaf": [1, 3]}
    if quick:
        lr_grid = {"C": [1.0], "class_weight": [None]}
        rf_grid = {"max_depth": [8], "min_samples_leaf": [3]}
    for params in ParameterGrid(lr_grid):
        yield (
            "logistic_regression",
            params,
            LogisticRegression(
                **params,
                solver="liblinear",
                max_iter=2000,
                random_state=SEED,
            ),
        )
    for params in ParameterGrid(rf_grid):
        yield (
            "random_forest",
            params,
            RandomForestClassifier(
                **params,
                n_estimators=150,
                class_weight="balanced",
                random_state=SEED,
                n_jobs=1,
            ),
        )


def configure_mlflow():
    uri = os.environ.get("MLFLOW_TRACKING_URI", f"sqlite:///{(ROOT / 'mlflow.db').as_posix()}")
    mlflow.set_tracking_uri(uri)
    if mlflow.get_experiment_by_name(EXPERIMENT) is None:
        mlflow.create_experiment(EXPERIMENT, artifact_location=(ROOT / "mlartifacts").as_uri())
    mlflow.set_experiment(EXPERIMENT)
    return uri


def train(quick=False) -> dict:
    frame = load_clean()
    train_idx, test_idx = split_data(frame)
    X = frame[FEATURES]
    y = frame["target"]
    X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
    X_test, y_test = X.iloc[test_idx], y.iloc[test_idx]
    for path in [REPORTS, MODEL_DIR, REPORTS / "figures", ROOT / "artifacts/logs"]:
        path.mkdir(parents=True, exist_ok=True)
    folds = 3 if quick else 5
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=SEED)
    tracking_uri = configure_mlflow()
    results = []
    best_score = -1.0
    best_pipeline = None
    with mlflow.start_run(run_name="comparison-quick" if quick else "comparison-full") as parent:
        parent_id = parent.info.run_id
        mlflow.log_params(
            {
                "seed": SEED,
                "cv_folds": folds,
                "test_fraction": 0.2,
                "train_rows": len(train_idx),
                "test_rows": len(test_idx),
                "raw_features": 13,
                "engineered_features": 15,
                "threshold": 0.5,
            }
        )
        mlflow.set_tags(
            {
                "dataset_sha256": sha256(CLEAN_PATH),
                "selection_metric": "mean training CV ROC-AUC",
                "holdout_policy": "evaluate only the selected model",
            }
        )
        for number, (name, params, estimator) in enumerate(candidates(quick), start=1):
            pipeline = build_pipeline(estimator)
            fold_metrics = []
            oof = np.zeros(len(X_train))
            with mlflow.start_run(run_name=f"{name}-{number:02d}", nested=True) as run:
                mlflow.log_params({"model_family": name, **estimator.get_params()})
                for fold, (fit_idx, val_idx) in enumerate(cv.split(X_train, y_train)):
                    fitted = clone(pipeline).fit(X_train.iloc[fit_idx], y_train.iloc[fit_idx])
                    probability = fitted.predict_proba(X_train.iloc[val_idx])[:, 1]
                    oof[val_idx] = probability
                    metrics = compute_metrics(y_train.iloc[val_idx], probability)
                    fold_metrics.append(metrics)
                    mlflow.log_metrics(
                        {f"fold_{key}": value for key, value in metrics.items()}, step=fold
                    )
                summary = {
                    f"cv_{key}_mean": float(np.mean([m[key] for m in fold_metrics]))
                    for key in fold_metrics[0]
                }
                summary.update(
                    {
                        f"cv_{key}_std": float(np.std([m[key] for m in fold_metrics], ddof=1))
                        for key in fold_metrics[0]
                    }
                )
                mlflow.log_metrics(summary)
                pipeline.fit(X_train, y_train)
                mlflow.sklearn.log_model(
                    pipeline,
                    "pipeline",
                    signature=infer_signature(X_train, pipeline.predict(X_train)),
                    pip_requirements=str(ROOT / "requirements-serve.txt"),
                )
                mlflow.log_dict({"folds": fold_metrics, "parameters": params}, "cv_details.json")
                fig, ax = plt.subplots(figsize=(6, 4.5), constrained_layout=True)
                RocCurveDisplay.from_predictions(y_train, oof, ax=ax, name=name)
                ax.set_title("Out-of-fold ROC on training partition")
                mlflow.log_figure(fig, "plots/cv_roc.png")
                plt.close(fig)
                for plot in sorted((REPORTS / "figures").glob("*.png")):
                    if plot.stem in {"histograms", "correlation", "balance_missing"}:
                        mlflow.log_artifact(str(plot), "eda")
                row = {
                    "model_family": name,
                    "parameters": json.dumps(params, sort_keys=True),
                    "run_id": run.info.run_id,
                    **summary,
                }
                results.append(row)
                if summary["cv_roc_auc_mean"] > best_score:
                    best_score = summary["cv_roc_auc_mean"]
                    best_pipeline = pipeline
                    best_row = row
            print(f"{number:02d} {name}: CV AUC={summary['cv_roc_auc_mean']:.4f}", flush=True)
        # The holdout has not influenced any candidate or hyperparameter choice.
        probabilities = best_pipeline.predict_proba(X_test)[:, 1]
        test_metrics = compute_metrics(y_test, probabilities)
        mlflow.log_metrics({f"test_{key}": value for key, value in test_metrics.items()})
        mlflow.log_param("selected_model", best_row["model_family"])
        model_path = MODEL_DIR / "model.joblib"
        joblib.dump(best_pipeline, model_path)
        model_hash = sha256(model_path)
        versions = {
            name: importlib.metadata.version(name)
            for name in ["numpy", "scipy", "pandas", "scikit-learn", "joblib", "mlflow"]
        }
        try:
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=ROOT,
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            commit = None
        metadata = {
            "model_family": best_row["model_family"],
            "parameters": json.loads(best_row["parameters"]),
            "model_version": model_hash[:12],
            "model_sha256": model_hash,
            "features": FEATURES,
            "engineered_features": ["age_oldpeak", "exercise_oldpeak"],
            "threshold": 0.5,
            "seed": SEED,
            "cv_folds": folds,
            "quick_mode": quick,
            "cv_roc_auc_mean": best_score,
            "test_metrics": test_metrics,
            "train_rows": len(train_idx),
            "test_rows": len(test_idx),
            "data_sha256": sha256(CLEAN_PATH),
            "mlflow_parent_run_id": parent_id,
            "selected_run_id": best_row["run_id"],
            "python_version": platform.python_version(),
            "package_versions": versions,
            "git_commit": commit,
            "intended_use": "Educational dataset classification; not a clinical risk score.",
        }
        (MODEL_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2))
        pd.DataFrame(results).to_csv(REPORTS / "model_comparison.csv", index=False)
        (REPORTS / "metrics.json").write_text(json.dumps(metadata, indent=2))
        (REPORTS / "split_indices.json").write_text(
            json.dumps(
                {
                    "train_indices": train_idx.tolist(),
                    "test_indices": test_idx.tolist(),
                },
                indent=2,
            )
        )
        pd.DataFrame(
            {
                "row_index": test_idx,
                "actual": y_test.to_numpy(),
                "probability_disease": probabilities,
                "prediction": (probabilities >= 0.5).astype(int),
            }
        ).to_csv(REPORTS / "holdout_predictions.csv", index=False)
        for filename, display in [
            ("roc_holdout.png", RocCurveDisplay),
            ("confusion_matrix.png", ConfusionMatrixDisplay),
        ]:
            fig, ax = plt.subplots(figsize=(6, 4.5), constrained_layout=True)
            if display is RocCurveDisplay:
                display.from_predictions(
                    y_test, probabilities, ax=ax, name=best_row["model_family"]
                )
                ax.plot([0, 1], [0, 1], "--", color="gray")
            else:
                display.from_predictions(
                    y_test,
                    probabilities >= 0.5,
                    ax=ax,
                    display_labels=["Absent", "Present"],
                    colorbar=False,
                )
            ax.set_title("Selected model on untouched holdout")
            fig.savefig(REPORTS / "figures" / filename, dpi=180)
            mlflow.log_figure(fig, f"plots/{filename}")
            plt.close(fig)
        mlflow.log_artifact(str(REPORTS / "model_comparison.csv"))
        mlflow.log_artifact(str(MODEL_DIR / "metadata.json"))
        mlflow.log_artifact(str(ROOT / "data/processed/data_summary.json"))
        mlflow.log_artifact(str(REPORTS / "holdout_predictions.csv"))
        mlflow.sklearn.log_model(
            best_pipeline,
            "selected_pipeline",
            signature=infer_signature(X_train, best_pipeline.predict(X_train)),
            pip_requirements=str(ROOT / "requirements-serve.txt"),
        )
    print(
        json.dumps(
            {
                "selected": metadata["model_family"],
                "test_metrics": test_metrics,
                "model_path": str(model_path),
                "mlflow_tracking_uri": tracking_uri,
            },
            indent=2,
        )
    )
    return metadata


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="CI smoke mode: 2 candidates, 3 folds")
    args = parser.parse_args()
    train(quick=args.quick)


if __name__ == "__main__":
    main()
