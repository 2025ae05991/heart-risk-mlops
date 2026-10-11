# Heart Risk MLOps Setup and Run Guide

This guide runs Assignment 1 on a Windows laptop using VS Code, PowerShell and Docker
Desktop Kubernetes. Follow the steps in order. The project trains two classifiers, records
experiments in MLflow, serves predictions through FastAPI, runs automated checks, and
deploys two API replicas with Prometheus and Grafana monitoring.

The included model, EDA plots, test logs, local API and dashboard results were executed on Python
3.12.14. The project supports Python 3.11 and 3.12. The Docker image uses Python 3.11.12.
Docker Desktop, GitHub Actions and Kubernetes execution evidence must be collected from
your own setup before submission. The guide includes the exact commands and capture list.

## What you will use

| Item | Address or location |
|---|---|
| Project folder | C:\Ameer\MLOps\heart-risk-mlops |
| Host API and Kubernetes API | http://localhost:8000/docs |
| Live API dashboard | http://localhost:8000/dashboard |
| Docker smoke test API | http://localhost:8001/docs |
| MLflow UI | http://localhost:5000 |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |
| Final assignment report | docs/MLOps_Assignment_1_Report.pdf |

These addresses are local to your laptop. They are not public cloud URLs. A GPU, AWS
account, eksctl and Helm are not required. Keep the API on port 8000 running in only one
mode at a time. Stop the host API before deploying its Kubernetes Service.

<!-- pagebreak -->

## Step 1 Install and check the tools

1. Install Python 3.11 or 3.12 from python.org. If using the Python installer, enable the
   option to add Python to PATH. Do not use Python 3.13 or 3.14 for this pinned project.
2. Install Git from git-scm.com and VS Code from code.visualstudio.com.
3. In VS Code, install the Python extension from Microsoft.
4. Install Docker Desktop for Windows from docker.com. Use its Linux containers mode.
5. Docker Desktop includes kubectl on Windows when Kubernetes is enabled. Install a
   separate kubectl only if Docker Desktop did not provide it.
6. Open a new PowerShell terminal after installing the tools. Restart VS Code if its
   terminal was already open during installation.

Run each command separately:

```powershell
py -0p
py -3.11 --version
git --version
code --version
docker version
kubectl version --client
```

If you choose Python 3.12, use `py -3.12 --version` instead. Docker version must show both
Client and Server. A Client section followed by a connection error means Docker Desktop
is not ready. The kubectl check may work only after Step 2.

Existing Conda users can reuse their Python 3.11 heartml environment. Do not create an
additional virtual environment inside it. Choose one environment method in Step 4.

Download sources: https://www.python.org/downloads/windows/, https://git-scm.com/downloads,
https://code.visualstudio.com/download and https://docs.docker.com/desktop/setup/install/windows-install/.

<!-- pagebreak -->

## Step 2 Enable Docker Desktop Kubernetes

1. Open Docker Desktop and wait until the Docker engine is running.
2. Confirm Linux containers are selected. If the tray menu offers Switch to Linux
   containers, select it. This project uses Linux images rather than Windows IIS images.
3. Open Docker Desktop Settings and enable the WSL 2 based engine if available.
4. Allocate enough resources for the lab. Aim for at least 4 CPU cores and 6 GB of available
   Docker memory. With WSL 2, memory may be controlled by WSL settings rather than a Docker
   slider. Close large applications if necessary.
5. In current Docker Desktop versions, open the Kubernetes view and select Create cluster.
   Choose kubeadm and one node when offered. This matches the local Docker-image workflow.
   Select Create and wait for the cluster to report that it is running.
6. Older versions use Settings, Kubernetes, Enable Kubernetes, then Apply and Restart.
7. Kubernetes downloads its control-plane images during the first setup. Keep Docker
   Desktop open until this finishes. A slow first download is not evidence of a code error.

Check the selected cluster:

```powershell
kubectl config get-contexts
kubectl config use-context docker-desktop
kubectl get nodes
docker info --format '{{.OSType}}'
```

The Docker OS type must be linux. The Kubernetes node must be Ready. If it is not Ready,
resolve the cluster issue before running the deployment script. Do not apply the manifests
to a work or cloud cluster accidentally.

If you already use Docker Desktop kind, the manifests can still be used, but local image
visibility depends on its image store. See Step 11 if a pod cannot find the image.

Official reference: https://docs.docker.com/desktop/use-desktop/kubernetes/.

<!-- pagebreak -->

## Step 3 Extract the project and open VS Code

1. Download Heart_Risk_MLOps_Docker_Desktop.zip and extract it.
2. Move the heart-risk-mlops folder to C:\Ameer\MLOps. You can choose a different path,
   but use that actual path in all following commands.
3. Confirm the folder contains README.md, requirements.txt, Dockerfile, src, scripts,
   tests, k8s and data. Do not open the parent directory by mistake.
4. Open VS Code and select File, Open Folder, then the heart-risk-mlops folder.
5. Select Terminal, New Terminal. Choose PowerShell as the terminal profile.
6. Run the commands below to confirm the working directory.

```powershell
Set-Location C:\Ameer\MLOps\heart-risk-mlops
Get-Location
Get-ChildItem
```

You should see requirements.txt in the displayed list. Every project command in this guide
starts from this folder. Scripts use project-relative input paths and the installed heartml
package, so installation in Step 4 is required before running them.

The supplied reports and model allow you to inspect results immediately. Run the full
pipeline yourself so your local MLflow database, environment and evidence are created on
your laptop. Historical portable experiment exports are under evidence; the database and
large candidate artifact directories are regenerated locally.

If VS Code does not recognise a command that works in a separate PowerShell window, close
all VS Code windows and reopen VS Code. Then create a new terminal. An old terminal can
retain the PATH that existed before installation.

<!-- pagebreak -->

## Step 4 Create or activate the Python environment

Choose Method A or Method B. Do not run both methods.

### Method A Python virtual environment

Run these commands from the project folder:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
py -3.11 -m venv .venv
. .\.venv\Scripts\Activate.ps1
python --version
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -e .
```

For Python 3.12, replace only `py -3.11` with `py -3.12`. The execution-policy change affects
only the current PowerShell process. The prompt normally starts with (.venv) after activation.

### Method B Conda

If heartml does not exist, create it once. If it already exists with Python 3.11 or 3.12,
skip the first command and activate it.

```powershell
conda create -n heartml python=3.11 -y
conda activate heartml
python --version
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -e .
```

If Conda works in Anaconda Prompt but not VS Code, run `conda init powershell` in Anaconda
Prompt, close VS Code and PowerShell, then reopen them. Select the same interpreter in
VS Code using Ctrl+Shift+P, Python Select Interpreter. Choose .venv or heartml as appropriate.

Check installation:

```powershell
python -c "import heartml, sklearn, mlflow; print(sklearn.__version__)"
python -m pip check
```

Expected scikit-learn version: 1.5.2. requirements.txt includes an SQLAlchemy compatibility
pin, and constraints.txt preserves the validated dependency resolution. Use the same
activated environment in each new Python terminal.

<!-- pagebreak -->

## Step 5 Prepare the data and inspect EDA

Run the acquisition and cleaning script:

```powershell
python scripts/download_data.py
python -m heartml.eda
```

The original UCI file is already included. The script verifies its SHA-256 and recreates
the cleaned CSV. If the raw file is absent, it downloads the UCI archive. To deliberately
download it again, run `python scripts/download_data.py --force`.

Expected output: 303 rows, 13 raw predictors and a binary target. The original diagnosis
codes 1 to 4 become target 1. Diagnosis code 0 becomes target 0. The dataset has four
missing ca values and two missing thal values. The typed CSV keeps these nulls; the model
pipeline learns imputation values only from its training records.

Open these files in VS Code:

| File | What to inspect |
|---|---|
| data/processed/heart_clean.csv | Typed numeric fields and binary target |
| data/processed/data_summary.json | Source, checksums, counts and missing-value policy |
| reports/figures/histograms.png | Numerical feature distributions by class |
| reports/figures/correlation.png | Numerical correlations and target association |
| reports/figures/balance_missing.png | Class counts and six missing cells |

The class counts should be 164 absent and 139 present. Keep the original Cleveland codes.
For example, cp uses 1 to 4 and thal uses 3, 6 and 7. Other heart.csv files on the internet
often use different codes. Mixing those codes with this API causes wrong inputs or HTTP 422.

The two derived interactions are calculated by the pipeline: age multiplied by oldpeak,
and exang multiplied by oldpeak. You still send only the 13 original fields to the API.

<!-- pagebreak -->

## Step 6 Train and compare the models

Run the full pipeline and capture its output:

```powershell
python scripts/run_pipeline.py 2>&1 | Tee-Object evidence/training_local.log
if ($LASTEXITCODE -ne 0) { throw "Training failed" }
python scripts/validate_model.py
python scripts/export_mlflow.py
```

This repeats acquisition and EDA, then trains Logistic Regression and Random Forest.
The split uses seed 42: 242 training records and 61 held-out test records. Five-fold
stratified cross-validation runs inside the training partition. The 12 configurations
include six Logistic Regression settings and six Random Forest settings.

The highest mean CV ROC-AUC selects the model. Only that winner is evaluated on the
held-out set. Each candidate learns its own imputers, scaling and encoders in each fold.
The winner is fitted on the 242 training rows and saved with its preprocessing pipeline.

Inspect the results:

```powershell
Get-Content reports/metrics.json
Import-Csv reports/model_comparison.csv | Format-Table
python scripts/infer.py --input examples/patient.json
```

The supplied full run selected Logistic Regression, C=0.1, no class weighting. Its holdout
accuracy was 0.9016 and ROC-AUC was 0.9643. Small platform differences are possible; compare
the complete metric file and package versions rather than only the last printed number.

`python scripts/run_pipeline.py --quick` uses two candidates and three folds for a fast
smoke run. It replaces the saved model and metric files. Use the full command again before
the final report or submission. The default GitHub workflow uses the full experiment.

Model files: artifacts/model/model.joblib and artifacts/model/metadata.json. Keep them
together. The metadata includes a checksum that the API verifies at startup.

<!-- pagebreak -->

## Step 7 Open and inspect MLflow

Open another PowerShell terminal in the project folder and activate the same environment.
Leave this terminal running:

```powershell
mlflow ui --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1 --port 5000
```

Open http://localhost:5000 in your browser. Select the HeartRisk-Cleveland experiment.
For one full pipeline run, you should see 12 candidate runs nested under a comparison run.
Some views collapse child runs; expand the comparison run or choose all runs.

1. Open a Logistic Regression candidate and inspect C, class_weight, random_state and solver.
2. Inspect cv_accuracy_mean, cv_precision_mean, cv_recall_mean and cv_roc_auc_mean.
3. Inspect the standard deviations and per-fold metric history.
4. Open Artifacts to see the candidate model, CV details, out-of-fold ROC and EDA figures.
5. Open the comparison parent run for the selected-model holdout metrics, metadata and
   final pipeline artifacts.
6. Save a screenshot showing your real runs and comparison metrics.

If MLflow shows old or empty runs, first confirm that the terminal is in this project folder.
Training and UI must use the same mlflow.db. Check whether a custom MLFLOW_TRACKING_URI
environment variable points somewhere else. Remove that variable from the current terminal
only if you deliberately want the project's local database:

```powershell
Get-Item Env:MLFLOW_TRACKING_URI -ErrorAction SilentlyContinue
Remove-Item Env:MLFLOW_TRACKING_URI -ErrorAction SilentlyContinue
```

The JSON and CSV exports in evidence are portable historical records. They do not populate
a new MLflow UI automatically. Running the training pipeline creates your local live runs.
Stop the UI with Ctrl+C when finished, or keep it open for your recording.

<!-- pagebreak -->

## Step 8 Run linting and automated tests

Run these checks in the activated environment:

```powershell
ruff check .
ruff format --check .
python -m pytest --cov=heartml --cov-report=term-missing `
  --cov-report=xml:evidence/coverage.xml `
  --junitxml=evidence/junit.xml | Tee-Object -Variable testLog
$testExit = $LASTEXITCODE
$testLog | Out-File -Encoding utf8 evidence/tests.log
if ($testExit -ne 0) { throw "Unit tests failed" }
python scripts/validate_model.py
```

Expected result for the supplied code: 29 passing tests. Linting and formatting should pass.
Do not ignore an error or continue to deployment after a failed check. Read the first
failing assertion or traceback and fix the cause, then rerun the failed stage.

The tests check the real dataset identity, binary target, original categories and missing
values. They also check deterministic disjoint splits, label-free feature engineering,
training-only imputation, model serialization, API input errors, nullable ca/thal fields,
batch limits, metrics and rejection of an inconsistent model checksum.

Manifest contract tests verify two API replicas, named ports, health probes, the LoadBalancer
Service and pod-based metrics discovery. These are configuration checks. A successful
manifest test does not prove that a Kubernetes cluster has run the workload.

The recorded unit coverage includes orchestration code that is exercised by the separate
full training command. The project does not claim that the unit tests cover every EDA or
training line. Use evidence/tests.log, training logs and the API smoke checks together.

The model quality gate requires holdout ROC-AUC of at least 0.75 and accuracy of at least
0.70. These are educational pipeline checks; they are not clinical validation criteria.

<!-- pagebreak -->

## Step 9 Run and test the local FastAPI service

Start the host API in an activated terminal:

```powershell
uvicorn heartml.api:app --host 127.0.0.1 --port 8000
```

Leave that terminal running. Open http://localhost:8000/docs. Swagger assets are included
in the package, so the documentation page does not depend on an external CDN.

1. Expand POST /predict and select Try it out.
2. Copy the JSON in examples/patient.json into the request body.
3. Select Execute. Expect HTTP 200 with prediction, confidence, probability_disease,
   threshold and model_version.
4. Change cp from 1 to 0 and execute again. Expect HTTP 422 because 0 is not an original
   Cleveland chest-pain code. Restore the valid value afterward.

Test from another activated terminal:

```powershell
python scripts/smoke_api.py --url http://localhost:8000
$body = Get-Content examples/patient.json -Raw
Invoke-RestMethod -Uri http://localhost:8000/predict -Method Post `
  -ContentType "application/json" -Body $body
Invoke-RestMethod -Uri http://localhost:8000/ready
```

For the included model and example, prediction is 0 and probability_disease is approximately
0.3934. Confidence is approximately 0.6066, the probability of the selected class. It is
not the same field as disease probability. The example is a public UCI sample, not a new
clinical assessment.

Open http://localhost:8000/dashboard to inspect live request totals, class counts, response codes,
mean prediction latency and the observed request-rate chart. The dashboard samples one serving
process. Grafana combines both Kubernetes pods. Open /metrics for Prometheus-format metrics. Request logs
contain a request ID, route, response code and duration. They do not contain patient payloads.
Return to the API terminal and press Ctrl+C before Step 12 so port 8000 is available.

<!-- pagebreak -->

## Step 10 Build and test the Docker container

Keep Docker Desktop running in Linux containers mode. The saved model and metadata must
exist before the image build. The Dockerfile installs only serving dependencies and copies
the complete pipeline into the image. It does not download or train a model at startup.

Run the provided isolated test:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\docker_smoke.ps1
```

The script builds heart-risk-api:1.0, starts a temporary container on port 8001, waits for
readiness, verifies a valid prediction, checks invalid input and metrics, saves logs, and
removes that temporary container. It fails if the build, startup or prediction check fails.
No model directory from your laptop is mounted into the container.

Inspect evidence/docker_build_run.txt, evidence/docker_smoke.json and
evidence/docker_container.log. Capture the successful output as screenshots/docker_build_run.png.

To inspect the container manually after the smoke test:

```powershell
docker run -d --name heartml-demo -p 127.0.0.1:8001:8000 heart-risk-api:1.0
docker ps
python scripts/smoke_api.py --url http://localhost:8001
docker logs heartml-demo
docker stop heartml-demo
docker rm heartml-demo
```

The first image build downloads Python and wheels, so it can take longer than later builds.
If the model changes, build the image again so the new model is included. A container cannot
see a replacement model merely because you changed the host file after building the image.

<!-- pagebreak -->

## Step 11 Resolve local image visibility if needed

The local manifests use heart-risk-api:1.0 with imagePullPolicy Never. This deliberately
requires the image to be visible to the Docker Desktop Kubernetes runtime.

Check the image and cluster context:

```powershell
docker image ls heart-risk-api
kubectl config current-context
kubectl -n heartml describe pods -l app=heart-risk-api
```

For a new cluster, the guide's single-node kubeadm choice is the simplest path. If using
Docker Desktop kind, use its containerd image store as described in Docker's documentation.
Do not reset an existing cluster with unrelated workloads merely to fix this assignment.

If your current runtime still cannot see local images, publish the image to a registry you
control. Replace YOURNAME in the following commands with your Docker Hub account name.

```powershell
docker login
docker tag heart-risk-api:1.0 YOURNAME/heart-risk-api:1.0
docker push YOURNAME/heart-risk-api:1.0
```

Edit k8s/api.yaml. Set image to YOURNAME/heart-risk-api:1.0 and imagePullPolicy to
IfNotPresent. For a private repository, configure an imagePullSecret; for this simple lab,
a public image is easier. Reapply the API manifest and wait for readiness:

```powershell
kubectl apply -f k8s/api.yaml
kubectl -n heartml rollout status deployment/heart-risk-api --timeout=240s
```

Do not change imagePullPolicy to Always while keeping an unqualified local image name.
That makes Kubernetes try to download an image which may not exist in the registry.
The registry fallback is optional and does not change the choice of Docker Desktop Kubernetes.

<!-- pagebreak -->

## Step 12 Deploy to Docker Desktop Kubernetes

Confirm the host API has stopped and the Docker smoke test passed. Run:

```powershell
.\scripts\deploy.ps1 -SkipBuild
```

If the image has not been built, omit -SkipBuild. The script selects docker-desktop, applies
the heartml namespace and API workload, restarts the API to load the current local image, waits for two ready replicas, creates monitoring
configuration, applies Prometheus/Grafana workloads and waits for readiness.

On the first deployment, it asks you to choose a Grafana admin password of at least eight
characters. It creates a Kubernetes Secret without saving that password in the source tree.
Remember the password. The default login username is admin.

Check the deployment:

```powershell
kubectl -n heartml get pods,svc,deploy
kubectl -n heartml rollout status deployment/heart-risk-api
python scripts/smoke_api.py --url http://localhost:8000
.\scripts\collect_evidence.ps1
```

Expected: two API pods Ready, one Prometheus pod and one Grafana pod. The API Service type
must be LoadBalancer with service port 8000. On Docker Desktop, try http://localhost:8000/docs.
The smoke script verifies the endpoint response, not only the pod status.

Save screenshots/kubernetes_resources.png and screenshots/kubernetes_prediction.png.
The collection script saves resource listings, API pod logs, endpoint checks and a deployment
validation JSON. It also verifies that port 8000 responds from an actual API pod and that
the model version matches your current saved model.

If the LoadBalancer is temporarily unavailable, use a diagnostic port forward in another
terminal: `kubectl -n heartml port-forward svc/heart-risk-api 8002:8000`. Test localhost:8002.
Keep the LoadBalancer manifest and resolve its exposure before claiming that requirement is
complete. Port forwarding alone does not demonstrate LoadBalancer access.

<!-- pagebreak -->

## Step 13 Open Prometheus and Grafana

Run each forwarding command in its own terminal and leave both running:

```powershell
kubectl -n heartml port-forward svc/prometheus 9090:9090
```

```powershell
kubectl -n heartml port-forward svc/grafana 3000:3000
```

Open http://localhost:9090 and find the Targets page. The heart-risk-api job should show
two pod targets as UP. Prometheus discovers individual pods so each replica has its own
counters. Scraping the Service alone would alternate between replicas.

Open http://localhost:3000. Log in as admin using the password you chose during deployment.
Open Dashboards, HeartML, HeartML API monitoring. The datasource and dashboard are
provisioned automatically; you do not need to build the panels manually.

Generate traffic from an activated terminal:

```powershell
python scripts/make_load.py --url http://localhost:8000 --requests 240
```

The script intentionally sends an invalid cp once every ten requests. HTTP 422 is expected
for those requests; valid samples return HTTP 200. Wait at least two minutes for the rate
and p95 panels to have a useful time window. The healthy-pod count should be 2.

Verify the live stack after traffic completes. Enter your chosen Grafana password when
prompted. The verifier saves evidence/monitoring_validation.json and fails if either pod
target, required prediction metrics, provisioned panels or Grafana datasource queries fail.

```powershell
python scripts/verify_monitoring.py
```

Inspect request rate, latency, response codes, predictions by class and resident memory.
Save screenshots/prometheus_targets.png and screenshots/grafana_dashboard.png. Check logs:

```powershell
kubectl -n heartml logs -l app=heart-risk-api --prefix=true --tail=30
```

The lab uses emptyDir monitoring storage. Pod replacement clears historical monitoring
data; configuration recreates the datasource and dashboard. It does not measure accuracy
or data drift without new labelled outcomes. Alerts are visible in Prometheus; notification
delivery is not configured for this assignment.

<!-- pagebreak -->

## Step 14 Upload to GitHub and run CI

1. Sign in to GitHub and create an empty repository named heart-risk-mlops. Do not initialise
   a README there because this project already has one.
2. Use your actual repository URL in the commands below. The package does not invent or
   publish a GitHub repository for you.
3. Confirm the report, clean data, code, model and workflow are present. The gitignore excludes
   environments, local MLflow databases and large candidate artifact directories.

```powershell
git init
git add .
git commit -m "Add heart disease MLOps assignment"
git branch -M main
git remote add origin https://github.com/YOURNAME/heart-risk-mlops.git
git push -u origin main
```

Git may ask you to sign in. If it asks for author identity, set user.name and user.email to
your own details. Do not put passwords or access tokens into source files. If origin already
exists, inspect it with `git remote -v` and change it only if it points to the wrong repository.

Open the repository's Actions tab and select HeartML CI. The workflow installs dependencies,
checks data, lints, runs tests, trains the full experiment, validates the model, builds an
isolated Docker image and checks its API. Failed stages stop the job. Artifact upload still
runs to retain available logs. The workflow does not deploy to your laptop automatically.

Wait for a green run. Open the run and capture screenshots/github_actions.png. Download
the heartml-run artifact if you need its reports or Docker logs. Keep the actual run URL.

The Docker Desktop deployment step is a deliberate local action because a hosted GitHub
runner cannot access your laptop's Kubernetes cluster without extra infrastructure.

<!-- pagebreak -->

## Step 15 Finalise the report and video

The assignment requires a 10-page written report, a repository link, deployment evidence
and a short video. Use the included report as the starting file, then add your actual setup
evidence. Keep the selected model and current metrics consistent.

1. Confirm the full pipeline, tests, Docker smoke, Kubernetes endpoint and monitoring all
   passed on your setup.
2. Keep screenshots in the filenames listed in screenshots/README.md.
3. Rebuild the report using your actual GitHub URL:

```powershell
python -m pip install -r requirements-docs.txt
python tools/build_report.py `
  --repository-url https://github.com/YOURNAME/heart-risk-mlops
```

The builder reads the current metrics, model comparison, figures and optional screenshots.
It produces exactly 10 pages. Open docs/MLOps_Assignment_1_Report.pdf and review all pages.
If you use a public registry fallback, update the report's deployment discussion to match it.

4. Follow docs/Video_Recording_Guide.md and record a continuous 3 to 5 minute demonstration
   of the complete pipeline. Include the real container and Kubernetes portion. The included
   Local_Pipeline_Walkthrough.mp4 records the executed host part only.
5. Save your final recording as evidence/Assignment_Full_Pipeline_Demo.mp4.
6. Review SUBMISSION_CHECKLIST.md. Add your repository link and local access instructions
   to the submission. Local access is http://localhost:8000; it works while your cluster runs.
7. Review and personalise the report. Be ready to explain the preprocessing, CV selection,
   confidence calculation, Docker isolation, Kubernetes probes and monitoring queries.

When the screenshots or report change, commit and push those final files so the repository
contains the same material that you submit. Follow your course's independent-work and
tool-use rules; understand and take responsibility for the final implementation.

<!-- pagebreak -->

## Step 16 Stop and clean up the lab

Press Ctrl+C in the API, MLflow and port-forward terminals when they are no longer needed.
The Kubernetes workloads continue running until you scale them down or delete the namespace.

To pause the workloads while preserving their configuration:

```powershell
kubectl -n heartml scale deployment/heart-risk-api --replicas=0
kubectl -n heartml scale deployment/prometheus --replicas=0
kubectl -n heartml scale deployment/grafana --replicas=0
```

To resume, reapply the manifests or run deploy.ps1 -SkipBuild. The API returns to two
replicas, while Prometheus and Grafana return to one each. Monitoring history may be lost
because the lab storage is temporary.

To remove only the assignment's namespace after saving your evidence:

```powershell
kubectl --context docker-desktop delete namespace heartml
```

This deletes the assignment's pods, services, configuration, secret and temporary monitoring
storage. It does not delete your source code, dataset, model, report or Docker image.
Do not use this command before collecting the screenshots and recording.

After retraining, rebuild the image and restart the deployment so new containers use it:

```powershell
docker build -t heart-risk-api:1.0 .
kubectl apply -f k8s/api.yaml
kubectl -n heartml rollout restart deployment/heart-risk-api
kubectl -n heartml rollout status deployment/heart-risk-api
```

For this local cached tag, restarting creates new pods with the rebuilt local image. In
production, use a new immutable image tag or digest for every released model version.

<!-- pagebreak -->

## Troubleshooting

### Conda or Python works outside VS Code only

Restart VS Code after installation or conda init. Open a new PowerShell terminal, activate
the environment and select that exact interpreter. Check `where.exe python` and
`python --version`. Do not mix commands from different interpreters.

### ModuleNotFoundError for heartml

You have not installed the package in the active environment. Return to the project root
and run `python -m pip install -r requirements.txt -e .`.

### MLflow cannot import a SQLAlchemy pool

Use the supplied pins and constraints. Run `python -m pip install -r requirements.txt -e .`
in a clean environment. Do not upgrade SQLAlchemy independently; the project pins 2.0.40.

### Docker says the daemon is unavailable

Open Docker Desktop and wait for the engine. Confirm Linux containers. Run docker version
again and require both Client and Server. Do not proceed with only the Client result.

### ErrImageNeverPull or ImagePullBackOff

Check the local image tag, context and image store. Follow Step 11. Describe the pod to see
the exact event. For the registry fallback, change the image name and pull policy together.

### Port 8000 is already in use

Stop the local uvicorn process before using the Kubernetes LoadBalancer on the same port.
Do not leave a Docker container mapped to port 8000. The Docker smoke script uses port 8001.

### Grafana has no data

Check Prometheus Targets first. Both API pod targets must be UP. Generate traffic for two
minutes and choose a recent time range in Grafana. Review prometheus and grafana pod logs.

### Pod startup fails or is killed

Use `kubectl -n heartml describe pod PODNAME` and `kubectl -n heartml logs PODNAME`.
Look for missing model files, checksum errors, image download errors or memory pressure.
Ensure model.joblib and metadata.json were copied together before building the image.



<!-- pagebreak -->

## Automatic run for the remaining stages

Use this shortcut after Steps 1 to 4. Docker Desktop must be running with its Kubernetes
node Ready. Activate the Python environment in VS Code. Stop the host API and any existing
port forwarding terminals before starting. Ports 8000, 8001, 3000 and 9090 must be free.

```powershell
Set-Location C:\Ameer\MLOps\heart-risk-mlops
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\complete_assignment.ps1
```

The script performs the following stages and stops at the first failure:

1. Check Python 3.11 or 3.12, Docker Linux mode, docker-desktop and the local ports.
2. Install the pinned dependencies, check them and verify the dataset.
3. Run lint, formatting and all unit tests; save JUnit, coverage and logs.
4. Run full training and EDA, validate the model and export MLflow records.
5. Build and test an isolated Docker container without host model mounts.
6. Deploy to Docker Desktop Kubernetes, restart the API pods and check two ready replicas.
7. Verify the LoadBalancer response and confirm that it comes from an actual API pod.
8. Temporarily forward Prometheus and Grafana and generate two minutes of traffic.
9. Verify both pod targets, real counters, latency, dashboard panels and Grafana queries.
10. Rebuild the report and write an honest list of any submission evidence still missing.

The first deployment asks for a Grafana password. The monitoring verifier reads the lab's
Kubernetes Secret and sends the credentials through stdin without logging or saving the
password. The script stops only its own forwarding processes when it finishes; the cluster
workloads keep running. Reopen the forwards from Step 13 to inspect and capture the panels.

If the full model is already trained on this laptop and the local MLflow database exists,
use `-SkipTraining`. The report rejects quick-mode training. The Docker image is still rebuilt
and verified. Do not skip training on a freshly extracted project because its MLflow database
has not yet been created locally.

The automatic run saves evidence/complete_run_status.json. This file reports local execution
checks. It does not certify hosted CI, screenshots or the final video. Read
`docs/Final_Submission_Status.md` after the run for the remaining items.

<!-- pagebreak -->

## Collect verified GitHub Actions evidence

Complete Step 14 first. For automated evidence collection, install GitHub CLI from
https://cli.github.com, restart VS Code, then sign in:

```powershell
gh --version
gh auth login
```

Choose GitHub.com, HTTPS and browser authentication. Keep the token in GitHub CLI's
credential storage. The project has no token field and does not need a token in a file.

After committing and pushing your code, wait for the HeartML CI workflow to finish.
Replace YOURNAME with the owner of your actual repository:

```powershell
.\scripts\collect_github_evidence.ps1 `
  -Repository YOURNAME/heart-risk-mlops
```

The collector finds a successful run for the current commit. It verifies the workflow name
and successful lint, unit-test, full-training, Docker-build and container-smoke stages.
It writes evidence/github_run.json and evidence/github_actions.log. A run for another
commit or a URL without successful stages is rejected.

If you want to inspect a specific run, copy its numeric run ID from the Actions URL:

```powershell
.\scripts\collect_github_evidence.ps1 `
  -Repository YOURNAME/heart-risk-mlops -RunId 123456789
```

The numeric ID above is an example. Use the real ID from your repository. If the run is
still active, wait for it or use `gh run watch REAL_RUN_ID --exit-status`. If a stage fails,
read its logs and fix the error before collecting evidence again.

Open the real run URL and use Win+Shift+S to save screenshots/github_actions.png. A local
pytest log and the local API video are separate evidence and cannot establish hosted CI.
Keep the repository private unless your course requires public access; give the evaluator
the repository access required by your course.

Official CLI references: https://cli.github.com/manual/gh_run_list,
https://cli.github.com/manual/gh_run_view and https://cli.github.com/manual/gh_run_watch.

<!-- pagebreak -->

## Verify and package the final submission

Use the screenshot names in screenshots/README.md. Capture real Docker output, Kubernetes
resources and prediction, Prometheus targets, Grafana panels and the GitHub Actions run.
Record the complete video using docs/Video_Recording_Guide.md and save it as
`evidence/Assignment_Full_Pipeline_Demo.mp4`. The bundled video shows the measured host
pipeline and live API dashboard; it does not show Docker Desktop deployment.

Run the checker using your real repository URL:

```powershell
python scripts/finalize_submission.py `
  --repository-url https://github.com/YOURNAME/heart-risk-mlops
```

Read docs/Final_Submission_Status.md. A missing file is pending. Invalid or inconsistent
recorded checks fail. A repository URL alone does not mark GitHub CI passed. A screenshot
file alone does not mark the Docker or Kubernetes execution checks passed.

After every required item is present, use strict mode:

```powershell
python scripts/finalize_submission.py `
  --repository-url https://github.com/YOURNAME/heart-risk-mlops `
  --strict
```

Strict mode exits with a nonzero status until all recorded requirements pass. It checks
file types and recorded execution results. Personally inspect screenshots and replay the
video because file presence cannot establish what is visible in them.

Rebuild the report after collecting the GitHub run and deployment screenshots:

```powershell
python -m pip install -r requirements-docs.txt
python tools/build_report.py `
  --repository-url https://github.com/YOURNAME/heart-risk-mlops
```

The builder reads current JUnit and coverage results, smoke evidence and submission status.
It picks up the collected CI run URL and enforces exactly 10 report pages. Open every page
and review it. Rebuild the setup document only if you edited its Markdown source:

```powershell
python tools/build_guide.py
```

Commit and push your final documents and evidence. Confirm that the final repository,
submitted files and demonstrated model agree. Submit the repository URL, report, code,
local access instructions and the complete video as requested by your course.
