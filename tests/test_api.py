import hashlib
import json

import joblib
import pytest
from fastapi.testclient import TestClient
from sklearn.linear_model import LogisticRegression

from heartml.api import create_app
from heartml.features import build_pipeline
from heartml.settings import FEATURES


@pytest.fixture
def client(frame, tmp_path):
    model = build_pipeline(LogisticRegression(max_iter=2000)).fit(frame[FEATURES], frame.target)
    path = tmp_path / "model.joblib"
    joblib.dump(model, path)
    metadata = {
        "model_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "model_version": "unit-test",
        "threshold": 0.5,
    }
    path.with_name("metadata.json").write_text(json.dumps(metadata))
    with TestClient(create_app(path)) as test_client:
        yield test_client


def test_health_readiness_and_prediction_contract(client, patient):
    assert client.get("/docs").status_code == 200
    assert client.get("/static/swagger-ui-bundle.js").status_code == 200
    assert client.get("/health").status_code == 200
    assert client.get("/ready").json()["status"] == "ready"
    response = client.post("/predict", json=patient)
    assert response.status_code == 200
    result = response.json()
    assert result["prediction"] in [0, 1]
    assert 0.5 <= result["confidence"] <= 1
    expected = (
        result["probability_disease"] if result["prediction"] else 1 - result["probability_disease"]
    )
    assert result["confidence"] == pytest.approx(expected)
    assert response.headers["X-Request-ID"]


@pytest.mark.parametrize(
    "change", [{"cp": 0}, {"thal": 2}, {"age": -10}, {"target": 1}, {"oldpeak": "not-a-number"}]
)
def test_invalid_payloads_are_rejected(client, patient, change):
    assert client.post("/predict", json=dict(patient, **change)).status_code == 422


def test_required_fields_and_nulls(client, patient):
    incomplete = dict(patient)
    incomplete.pop("chol")
    assert client.post("/predict", json=incomplete).status_code == 422
    assert client.post("/predict", json=dict(patient, ca=None, thal=None)).status_code == 200


def test_batch_limit_and_metrics(client, patient):
    assert len(client.post("/predict/batch", json={"patients": [patient, patient]}).json()) == 2
    assert client.post("/predict/batch", json={"patients": []}).status_code == 422
    assert client.post("/predict/batch", json={"patients": [patient] * 101}).status_code == 422
    metrics = client.get("/metrics")
    assert "heartml_predictions_total" in metrics.text
    assert "heartml_http_duration_seconds" in metrics.text


def test_corrupt_model_is_not_served(frame, tmp_path):
    path = tmp_path / "model.joblib"
    path.write_bytes(b"tampered")
    path.with_name("metadata.json").write_text(json.dumps({"model_sha256": "wrong"}))
    with pytest.raises(RuntimeError, match="checksum"):
        with TestClient(create_app(path)):
            pass


def test_dashboard_observes_valid_and_rejected_requests_without_patient_data(client, patient):
    before = client.get("/monitoring").json()
    assert client.post("/predict", json=patient).status_code == 200
    assert client.post("/predict", json=dict(patient, cp=0)).status_code == 422
    after = client.get("/monitoring").json()
    assert after["prediction_http_requests"] == before["prediction_http_requests"] + 2
    assert sum(after["prediction_count_by_class"].values()) == (
        sum(before["prediction_count_by_class"].values()) + 1
    )
    statuses = after["prediction_responses_by_status"]
    assert statuses["422"] == before["prediction_responses_by_status"].get("422", 0) + 1
    assert after["model_ready"] is True
    assert after["model_version"] == "unit-test"
    assert after["mean_prediction_latency_ms"] >= 0
    assert not set(patient).intersection(after)
    assert client.get("/dashboard").status_code == 200
