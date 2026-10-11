# Assignment evidence checklist

This package contains an implemented project and measured local results. Complete the
remaining execution evidence before submitting the assignment.

| Requirement | Included evidence | Status |
|---|---|---|
| Data acquisition and cleaning | Original file, SHA check, script, clean CSV, provenance | Executed |
| EDA | Histograms, correlation, class balance and missing-value plots | Executed |
| Two classification models and CV | 12 candidate configurations, five folds, real metrics | Executed |
| Experiment tracking | 13 genuine MLflow runs, exported parameters/metrics and UI screenshot | Executed locally |
| Packaging and reproducibility | Joblib pipeline, metadata, pins, transitive constraints | Executed locally |
| Unit tests | 29 passing tests, coverage XML and JUnit/log evidence | Executed |
| CI/CD | GitHub Actions workflow with lint, tests, full training and Docker smoke | Capture your GitHub run |
| Docker isolation proof | Dockerfile and `scripts/docker_smoke.ps1` | Execute and collect logs |
| Docker Desktop Kubernetes | Two API replicas, probes and LoadBalancer manifests | Execute and capture screenshots |
| Monitoring and logging | Executed live API dashboard, snapshot, screenshot and safe request logs | Host dashboard executed; cluster stack pending |
| Final written report | Exactly 10 pages, `docs/MLOps_Assignment_1_Report.pdf` | Add repository URL and final evidence |
| Repository link | Upload-ready tree and GitHub instructions | Create repository and add URL |
| Short video | Genuine local browser walkthrough and complete recording storyboard | Add Docker/Kubernetes portion |

Use the setup guide in order. After deployment, run the two evidence scripts and add real
screenshots using the names in `screenshots/README.md`. Rebuild the report with your actual
repository URL. Review and personalize the discussion and be ready to explain every step,
as required by the assignment's independent-work instruction.


Run `scripts/complete_assignment.ps1` to verify the laptop stages, then
`collect_github_evidence.ps1` for hosted CI. `finalize_submission.py --strict`
returns a nonzero exit status while required evidence is missing. The generated
`docs/Final_Submission_Status.md` lists the exact remaining files.
