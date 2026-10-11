# Final assignment submission status

Ready for submission: No. Required execution evidence is still missing.

Repository: Pending

| Requirement | Status | Evidence or next action |
|---|---|---|
| Data and reusable model | passed | Saved pipeline matches its metadata SHA-256 |
| Full training and MLflow history | passed | Twelve candidates, five folds, and at least thirteen tracked runs |
| Unit tests | passed | JUnit contains no test failures or errors |
| Isolated Docker build and serving | pending | Missing evidence/docker_smoke.json, evidence/docker_validation.json, evidence/docker_build_run.txt |
| Docker Desktop Kubernetes and LoadBalancer | pending | Missing evidence/kubernetes_smoke.json, evidence/kubernetes_validation.json |
| Live API monitoring demonstration | passed | Live serving-process metrics and genuine dashboard screenshot included |
| Prometheus and Grafana on the cluster | pending | Missing evidence/monitoring_validation.json |
| Hosted GitHub Actions | pending | Missing evidence/github_run.json, evidence/github_actions.log |
| Actual code repository link | pending | Add your actual repository URL |
| Screenshot github_actions.png | pending | Missing screenshots/github_actions.png |
| Screenshot docker_build_run.png | pending | Missing screenshots/docker_build_run.png |
| Screenshot kubernetes_resources.png | pending | Missing screenshots/kubernetes_resources.png |
| Screenshot kubernetes_prediction.png | pending | Missing screenshots/kubernetes_prediction.png |
| Screenshot prometheus_targets.png | pending | Missing screenshots/prometheus_targets.png |
| Screenshot grafana_dashboard.png | pending | Missing screenshots/grafana_dashboard.png |
| Complete pipeline video | pending | Missing evidence/Assignment_Full_Pipeline_Demo.mp4 |
| Report and setup document | passed | Documents included; the report builder separately enforces exactly ten pages |

Run the complete-assignment script on Docker Desktop, collect your real GitHub run,
Save screenshots and the video, rebuild the report, then run this checker with --strict.
A missing check stays pending. A URL or screenshot alone cannot prove a successful run.
