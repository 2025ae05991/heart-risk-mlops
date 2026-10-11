"""Audit measured evidence before producing the final assignment submission."""

import argparse
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime

from heartml.settings import ROOT

CI_STAGES = [
    "Lint and format check",
    "Unit tests",
    "Full EDA and model comparison",
    "Build isolated serving container",
    "Test isolated container",
]
SCREENSHOTS = [
    "github_actions.png",
    "docker_build_run.png",
    "kubernetes_resources.png",
    "kubernetes_prediction.png",
    "prometheus_targets.png",
    "grafana_dashboard.png",
]


def repository_url(value):
    if not value:
        return ""
    value = value.rstrip("/").removesuffix(".git")
    if not re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        raise ValueError("Use the actual HTTPS GitHub repository URL, with owner and repository")
    return value


def load_json(root, relative):
    path = root / relative
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def evaluate(root=ROOT, repo_url="", run_url=""):
    repo_url = repository_url(repo_url)
    checks = []

    def check(identifier, label, paths, condition, details):
        missing = [path for path in paths if not (root / path).is_file()]
        if missing:
            status, detail = "pending", "Missing " + ", ".join(missing)
        else:
            try:
                passed = bool(condition())
                status, detail = ("passed" if passed else "failed"), details
            except (OSError, ValueError, KeyError, TypeError, ET.ParseError):
                status, detail = "failed", "Evidence is invalid or inconsistent; rerun this stage"
        checks.append(
            {
                "id": identifier,
                "label": label,
                "status": status,
                "details": detail,
                "evidence": paths,
            }
        )

    check(
        "model",
        "Data and reusable model",
        [
            "data/processed/heart_clean.csv",
            "artifacts/model/model.joblib",
            "artifacts/model/metadata.json",
        ],
        lambda: hashlib.sha256((root / "artifacts/model/model.joblib").read_bytes()).hexdigest()
        == load_json(root, "artifacts/model/metadata.json")["model_sha256"],
        "Saved pipeline matches its metadata SHA-256",
    )

    def full_experiment():
        metadata = load_json(root, "artifacts/model/metadata.json")
        with (root / "reports/model_comparison.csv").open(newline="", encoding="utf-8") as stream:
            candidates = list(csv.DictReader(stream))
        return (
            metadata["cv_folds"] == 5
            and not metadata["quick_mode"]
            and len(candidates) == 12
            and len(load_json(root, "evidence/mlflow_runs.json")) >= 13
        )

    check(
        "experiments",
        "Full training and MLflow history",
        ["reports/model_comparison.csv", "evidence/mlflow_runs.json"],
        full_experiment,
        "Twelve candidates, five folds, and at least thirteen tracked runs",
    )

    def passing_tests():
        suites = list(ET.parse(root / "evidence/junit.xml").getroot().iter("testsuite"))
        return (
            sum(int(suite.get("tests", "0")) for suite in suites) >= 22
            and sum(int(suite.get("failures", "0")) for suite in suites) == 0
            and sum(int(suite.get("errors", "0")) for suite in suites) == 0
        )

    check(
        "tests",
        "Unit tests",
        ["evidence/junit.xml", "evidence/tests.log"],
        passing_tests,
        "JUnit contains no test failures or errors",
    )
    metadata = load_json(root, "artifacts/model/metadata.json") or {}
    version = metadata.get("model_version")

    def smoke_matches(path):
        result = load_json(root, path)
        return (
            version is not None
            and result["/predict"]["model_version"] == version
            and result["invalid_cp_status"] == 422
            and result["metrics_present"] is True
        )

    check(
        "docker",
        "Isolated Docker build and serving",
        [
            "evidence/docker_smoke.json",
            "evidence/docker_validation.json",
            "evidence/docker_build_run.txt",
        ],
        lambda: smoke_matches("evidence/docker_smoke.json")
        and load_json(root, "evidence/docker_validation.json")["passed"] is True
        and load_json(root, "evidence/docker_validation.json")["host_mount_count"] == 0,
        "Real container checks passed without host-mounted model files",
    )
    check(
        "kubernetes",
        "Docker Desktop Kubernetes and LoadBalancer",
        ["evidence/kubernetes_smoke.json", "evidence/kubernetes_validation.json"],
        lambda: smoke_matches("evidence/kubernetes_smoke.json")
        and load_json(root, "evidence/kubernetes_validation.json")["passed"] is True
        and load_json(root, "evidence/kubernetes_validation.json")["context"] == "docker-desktop"
        and load_json(root, "evidence/kubernetes_validation.json")["ready_api_pods"] == 2
        and load_json(root, "evidence/kubernetes_validation.json")["service_type"]
        == "LoadBalancer",
        "Two ready API pods and a matching model served from the LoadBalancer",
    )
    check(
        "dashboard",
        "Live API monitoring demonstration",
        ["evidence/dashboard_snapshot.json", "screenshots/local_api_dashboard.png"],
        lambda: (
            load_json(root, "evidence/dashboard_snapshot.json")["model_version"] == version
            and load_json(root, "evidence/dashboard_snapshot.json")["model_ready"] is True
            and load_json(root, "evidence/dashboard_snapshot.json")["prediction_http_requests"] > 0
        ),
        "Live serving-process metrics and genuine dashboard screenshot included",
    )
    check(
        "monitoring",
        "Prometheus and Grafana on the cluster",
        ["evidence/monitoring_validation.json"],
        lambda: load_json(root, "evidence/monitoring_validation.json")["passed"] is True
        and load_json(root, "evidence/monitoring_validation.json")["expected_api_pods"] == 2
        and load_json(root, "evidence/monitoring_validation.json")[
            "grafana_datasource_query_passed"
        ]
        is True,
        "Both targets UP, real prediction metrics, and Grafana datasource queries passed",
    )

    github = load_json(root, "evidence/github_run.json") or {}
    actual_run_url = github.get("url", "")
    if actual_run_url and not repo_url:
        repo_url = repository_url(actual_run_url.split("/actions/runs/")[0])
    if run_url and actual_run_url and run_url != actual_run_url:
        raise ValueError("The requested run URL differs from the collected GitHub evidence")

    def passing_ci():
        stages = {
            step["name"]: step.get("conclusion")
            for job in github.get("jobs", [])
            for step in job.get("steps", [])
        }
        return (
            github.get("status") == "completed"
            and github.get("conclusion") == "success"
            and github.get("workflowName") == "HeartML CI"
            and actual_run_url.startswith(repo_url + "/actions/runs/")
            and bool(re.fullmatch(r"[0-9a-f]{40}", github.get("headSha", "")))
            and all(stages.get(name) == "success" for name in CI_STAGES)
        )

    check(
        "ci",
        "Hosted GitHub Actions",
        ["evidence/github_run.json", "evidence/github_actions.log"],
        passing_ci,
        "Successful hosted lint, tests, full training, image build, and smoke stages",
    )
    checks.append(
        {
            "id": "repository",
            "label": "Actual code repository link",
            "status": "passed" if repo_url else "pending",
            "details": repo_url or "Add your actual repository URL",
            "evidence": [],
        }
    )
    for name in SCREENSHOTS:
        path = "screenshots/" + name
        check(
            "image_" + name,
            "Screenshot " + name,
            [path],
            lambda path=path: (root / path).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
            and (root / path).stat().st_size > 2000,
            "PNG present; replay and visually review the actual captured result",
        )
    video = "evidence/Assignment_Full_Pipeline_Demo.mp4"
    check(
        "video",
        "Complete pipeline video",
        [video],
        lambda: b"ftyp" in (root / video).read_bytes()[:40]
        and (root / video).stat().st_size > 100000,
        "MP4 present; manually review that the full Docker/Kubernetes sequence is visible",
    )
    check(
        "documents",
        "Report and setup document",
        ["docs/MLOps_Assignment_1_Report.pdf", "docs/Docker_Desktop_Setup_and_Run_Guide.docx"],
        lambda: (root / "docs/MLOps_Assignment_1_Report.pdf").read_bytes().startswith(b"%PDF"),
        "Documents included; the report builder separately enforces exactly ten pages",
    )
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "repository_url": repo_url,
        "github_run_url": actual_run_url,
        "ready_for_submission": all(c["status"] == "passed" for c in checks),
        "checks": checks,
        "scope": "File and recorded-check audit; screenshots and video require personal review",
    }


def write_status(result, root=ROOT):
    evidence = root / "evidence/submission_status.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    document = root / "docs/Final_Submission_Status.md"
    document.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Final assignment submission status",
        "",
        "Ready for submission: "
        + (
            "Yes after personal evidence review"
            if result["ready_for_submission"]
            else "No. Required execution evidence is still missing."
        ),
        "",
        "Repository: " + (result["repository_url"] or "Pending"),
        "",
        "| Requirement | Status | Evidence or next action |",
        "|---|---|---|",
    ]
    lines += [f"| {c['label']} | {c['status']} | {c['details']} |" for c in result["checks"]]
    lines += [
        "",
        "Run the complete-assignment script on Docker Desktop, collect your real GitHub run,",
        "Save screenshots and the video, rebuild the report, then run this checker with --strict.",
        "A missing check stays pending. A URL or screenshot alone cannot prove a successful run.",
    ]
    document.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-url", default="")
    parser.add_argument("--github-run-url", default="")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    result = evaluate(ROOT, args.repository_url, args.github_run_url)
    write_status(result)
    for check in result["checks"]:
        print(f"{check['status'].upper():7} {check['label']}")
    print("Submission ready:", result["ready_for_submission"])
    return 1 if args.strict and not result["ready_for_submission"] else 0
