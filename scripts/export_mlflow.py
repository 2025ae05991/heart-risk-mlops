"""Create a portable evidence snapshot; a fresh local MLflow UI is populated by training."""

import json

import mlflow
from mlflow.tracking import MlflowClient

from heartml.settings import EXPERIMENT, ROOT
from heartml.train import configure_mlflow

if __name__ == "__main__":
    configure_mlflow()
    experiment = mlflow.get_experiment_by_name(EXPERIMENT)
    runs = MlflowClient().search_runs([experiment.experiment_id], max_results=1000)
    result = [
        {
            "run_id": r.info.run_id,
            "status": r.info.status,
            "run_name": r.data.tags.get("mlflow.runName"),
            "params": r.data.params,
            "metrics": r.data.metrics,
            "tags": r.data.tags,
        }
        for r in runs
    ]
    destination = ROOT / "evidence"
    destination.mkdir(exist_ok=True)
    (destination / "mlflow_runs.json").write_text(json.dumps(result, indent=2))
    mlflow.search_runs([experiment.experiment_id]).to_csv(
        destination / "mlflow_runs.csv", index=False
    )
    print(f"Exported {len(result)} genuine MLflow run records.")
