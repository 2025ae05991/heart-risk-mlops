# Heart Risk MLOps Assignment 1

End-to-end UCI Cleveland classification with Logistic Regression, Random Forest, MLflow,
FastAPI, GitHub Actions, Docker, and Docker Desktop Kubernetes. CPU execution is sufficient.

Start with **docs/Docker_Desktop_Setup_and_Run_Guide.docx**. The written assignment is
**docs/MLOps_Assignment_1_Report.pdf**, exactly 10 pages.

## Measured results

- Original Cleveland data: 303 records, 13 raw predictors, six missing cells.
- Two explicit interactions produce 15 predictors before one-hot encoding.
- Five-fold training-only CV compares 12 configurations. Selection uses mean CV ROC-AUC.
- Selected Logistic Regression: C=0.1, no class weighting, threshold=0.5.
- Untouched 61-record holdout: accuracy 0.9016, precision 0.8667, recall 0.9286, ROC-AUC 0.9643.
- 29 unit tests passed; actual logs, scores and experiment records are under `evidence/` and `reports/`.

The local Python pipeline and host API and live dashboard were executed. Docker builds, a GitHub Actions run,
Docker Desktop Kubernetes, and the Prometheus/Grafana stack must be executed on your laptop
or GitHub. Their evidence is deliberately marked pending. The supplied browser recording
shows the executed local API, MLflow, EDA, tests and live dashboard; record the Docker/Kubernetes
portion after deployment. See `SUBMISSION_CHECKLIST.md`.

## Quick start in PowerShell

Open this folder in VS Code. Use Python 3.11 or 3.12, select that interpreter, then:

```powershell
py -3.11 -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -e .
python scripts/run_pipeline.py
ruff check .
ruff format --check .
pytest
python scripts/validate_model.py
uvicorn heartml.api:app --host 127.0.0.1 --port 8000
```

Open http://localhost:8000/docs. The input example is `examples/patient.json`.
In a second activated terminal: `python scripts/smoke_api.py --url http://localhost:8000`.
Stop the local API with Ctrl+C before exposing Kubernetes on port 8000.

```powershell
mlflow ui --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1 --port 5000
```

Open http://localhost:5000. Training creates a new local database and artifacts; the supplied
`evidence/mlflow_runs.json` and CSV are portable snapshots of the measured runs.

## Docker Desktop Kubernetes

Enable Linux containers and create a single-node Kubernetes cluster in Docker Desktop.
Choose kubeadm when offered for this local-image workflow. Select context `docker-desktop`.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\docker_smoke.ps1
.\scripts\deploy.ps1 -SkipBuild
.\scripts\collect_evidence.ps1
```

`deploy.ps1` prompts for your Grafana administrator password the first time. The API uses
two replicas and a LoadBalancer Service at http://localhost:8000. The local manifests use
image `heart-risk-api:1.0` and `imagePullPolicy: Never`. If the cluster cannot see that image,
follow the image-store or registry steps in the guide before reapplying.

```powershell
kubectl -n heartml port-forward svc/grafana 3000:3000
# Run in another terminal:
kubectl -n heartml port-forward svc/prometheus 9090:9090
# Run in another activated Python terminal:
python scripts/make_load.py --url http://localhost:8000 --requests 120
```

Grafana: http://localhost:3000, user `admin`, your chosen password. Open HeartML / HeartML API
monitoring. Prometheus: http://localhost:9090, check Targets and Alerts.

## Project files

| Folder or file | Purpose |
|---|---|
| `src/heartml/` | Cleaning, features, EDA, CV training, evaluation and API |
| `scripts/` | Pipeline execution, offline inference, smoke tests and deployment helpers |
| `tests/` | Data, leakage, persistence, validation and manifest contract tests |
| `data/raw/`, `data/processed/` | Verified original data, typed CSV and provenance |
| `artifacts/model/` | Complete fitted joblib pipeline and matching metadata |
| `reports/` | Real EDA figures, 12-model comparison and holdout predictions |
| `evidence/` | Real test/training/API logs, MLflow exports and local walkthrough |
| `k8s/`, `monitoring/` | API and monitoring workloads, dashboard and alerts |
| `.github/workflows/ci.yml` | Lint, tests, full training, image build and isolated smoke checks |
| `docs/` | 10-page report, detailed guide and video capture instructions |
| `screenshots/` | Executed local screenshots and the remaining capture checklist |
| `constraints.txt` | Validated transitive dependency versions |

## Rebuild the written report

After capturing your real screenshots and creating your GitHub repository:

```powershell
python -m pip install -r requirements-docs.txt
python tools/build_report.py --repository-url https://github.com/YOURNAME/heart-risk-mlops
```

The builder uses current result files and inserts optional screenshots when they exist.
Screenshots do not automatically certify deployment; the report checks smoke-test evidence
and asks you to verify the corresponding workflow/cluster results. See the guide.

## Reproducibility and scope

The raw SHA-256 is verified before cleaning. Imputers, scaling and one-hot encoders are fitted
inside each CV fold. The selected pipeline is trained on 242 records and remains unchanged
for the holdout evaluation and serving. API responses contain a class prediction, class
confidence, disease-class probability and model hash version. Probabilities are uncalibrated
dataset classifier outputs, not validated medical risk estimates.

Monitoring storage uses `emptyDir` for a reproducible local lab. Pod replacement clears its
stored time series or Grafana session state. Provisioned dashboards are recreated. Production
use would require persistent storage, authentication/TLS and clinical/external validation.

## Data attribution

Janosi, A., Steinbrunn, W., Pfisterer, M., and Detrano, R. (1989).
Heart Disease [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C52P4X.
License: CC BY 4.0. Original data page: https://archive.ics.uci.edu/dataset/45/heart+disease.
The dataset is preserved with original category codes and the documented binary target mapping.


## Finish the remaining execution and evidence

After enabling Docker Desktop Kubernetes and activating Python in VS Code:

```powershell
.\scripts\complete_assignment.ps1
```

This verifies real container isolation, model-version parity, two ready API pods,
LoadBalancer routing, Prometheus targets and Grafana datasource queries. It stops
on errors and closes only its own temporary port forwards. The served `/dashboard`
provides an additional live API metrics view without external services.

After pushing the project and waiting for a successful Actions run:

```powershell
.\scripts\collect_github_evidence.ps1 -Repository YOURNAME/heart-risk-mlops
python scripts/finalize_submission.py --repository-url https://github.com/YOURNAME/heart-risk-mlops
```

Read `docs/Final_Submission_Status.md`, add real screenshots and the full video, then
rerun the checker with `--strict`. GitHub CLI must be installed and authenticated
for the collector. The included documents explain the manual route as well.
