# Record the complete assignment demonstration

`evidence/Local_Pipeline_Walkthrough.mp4` is a genuine browser recording of the executed
host API, MLflow experiment, EDA plots, tests, metrics and the live API dashboard. The on-screen labels identify
host execution. Complete the container and Kubernetes segment on your laptop.

Record one continuous 3 to 5 minute walkthrough after the complete setup passes. Use
Windows Snipping Tool screen recording or OBS. Start recording a region containing VS Code,
your terminal and the browser. Show your actual repository name and successful execution.

| Time | Show | Explain in your own words |
|---|---|---|
| 0:00 to 0:25 | Repository folders, raw/clean data and EDA figures | Source, binary target and fold-local missing-value handling |
| 0:25 to 1:00 | model_comparison.csv, holdout ROC and confusion matrix | Two models, five-fold CV selection and untouched test results |
| 1:00 to 1:30 | MLflow run list, candidate parameters, metrics and plots | How experiment tracking supports reproducibility |
| 1:30 to 2:00 | pytest output and your green GitHub Actions run | Pipeline fails on code, tests, training or container errors |
| 2:00 to 2:25 | docker_smoke.ps1 and Docker container checks | Serving works without the training environment mounted |
| 2:25 to 3:15 | Docker Desktop cluster, two ready pods, LoadBalancer and prediction | Kubernetes runs the same packaged model in two replicas |
| 3:15 to 4:00 | Live /dashboard, Prometheus Targets, Grafana panels and API pod logs | Latency, request codes, prediction counters and safe request logs |

Save the video as `evidence/Assignment_Full_Pipeline_Demo.mp4`. Replay it to verify legibility
and audio before submission. A local-only walkthrough does not establish cluster deployment.

