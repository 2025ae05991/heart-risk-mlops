import json

import pytest

from heartml.submission import evaluate, repository_url


def test_missing_deployment_evidence_cannot_be_marked_submission_ready(tmp_path):
    result = evaluate(tmp_path, "https://github.com/example/heart-risk-mlops")
    assert result["ready_for_submission"] is False
    states = {check["id"]: check["status"] for check in result["checks"]}
    assert states["repository"] == "passed"
    assert states["ci"] == "pending"
    assert states["docker"] == "pending"
    assert states["kubernetes"] == "pending"
    assert states["video"] == "pending"


def test_repository_url_rejects_non_github_or_injected_text():
    with pytest.raises(ValueError):
        repository_url("https://example.org/owner/repo")
    with pytest.raises(ValueError):
        repository_url("https://github.com/owner/repo\n|passed|")
    assert repository_url("https://github.com/owner/repo.git") == "https://github.com/owner/repo"


def test_github_url_without_passed_stage_evidence_is_rejected(tmp_path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "github_run.json").write_text(
        json.dumps(
            {
                "url": "https://github.com/example/repo/actions/runs/123",
                "status": "completed",
                "conclusion": "success",
                "workflowName": "HeartML CI",
                "headSha": "a" * 40,
            }
        )
    )
    (evidence / "github_actions.log").write_text("Fixture for a URL without required CI stages")
    result = evaluate(tmp_path, "https://github.com/example/repo")
    assert next(c for c in result["checks"] if c["id"] == "ci")["status"] == "failed"
    assert result["ready_for_submission"] is False


def test_failed_kubernetes_validation_never_counts_as_passed(tmp_path):
    evidence = tmp_path / "evidence"
    model = tmp_path / "artifacts/model"
    evidence.mkdir()
    model.mkdir(parents=True)
    (model / "metadata.json").write_text(json.dumps({"model_version": "fixture"}))
    (evidence / "kubernetes_smoke.json").write_text(
        json.dumps(
            {
                "/predict": {"model_version": "fixture"},
                "invalid_cp_status": 422,
                "metrics_present": True,
            }
        )
    )
    (evidence / "kubernetes_validation.json").write_text(
        json.dumps(
            {
                "context": "docker-desktop",
                "ready_api_pods": 2,
                "service_type": "LoadBalancer",
                "passed": False,
            }
        )
    )
    result = evaluate(tmp_path)
    assert next(c for c in result["checks"] if c["id"] == "kubernetes")["status"] == "failed"
