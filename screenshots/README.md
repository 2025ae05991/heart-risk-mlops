# Screenshot capture plan

The files prefixed `local_` are genuine browser captures from the executed host API and
MLflow UI and live API dashboard. They are not Docker, Kubernetes or GitHub Actions proof.

Capture the following on your own running setup. Use Win+Shift+S and save the PNG files here.

| Filename | What the screenshot must show |
|---|---|
| `github_actions.png` | Your repository name, Actions run and successful lint/test/train/build/smoke steps |
| `docker_build_run.png` | Successful Docker build and `docker_smoke.ps1` HTTP checks |
| `kubernetes_resources.png` | `kubectl -n heartml get pods,svc,deploy` with two ready API pods and LoadBalancer |
| `kubernetes_prediction.png` | http://localhost:8000/docs returning HTTP 200 for `examples/patient.json` |
| `prometheus_targets.png` | Prometheus Targets with both heart-risk-api pod targets UP |
| `grafana_dashboard.png` | HeartML API monitoring panels after traffic has run for at least two minutes |

Do not use an EDA plot or a diagram as deployment proof. Do not include passwords or tokens.
The report builder optionally inserts these images into pages 8, 9 and 10.

