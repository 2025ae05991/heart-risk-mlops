"""Black-box smoke test; works with host, Docker, or Kubernetes URLs."""

import argparse
import json
from pathlib import Path

import httpx


def run(base_url: str, output: Path | None = None, expected_model_version: str | None = None):
    base_url = base_url.rstrip("/")
    sample = json.loads(Path("examples/patient.json").read_text())
    records = {"base_url": base_url}
    with httpx.Client(timeout=30, trust_env=False) as client:
        for route in ["/health", "/ready", "/model-info"]:
            response = client.get(base_url + route)
            response.raise_for_status()
            records[route] = response.json()
        response = client.post(base_url + "/predict", json=sample)
        response.raise_for_status()
        prediction = response.json()
        if expected_model_version:
            assert prediction["model_version"] == expected_model_version, "Stale model is serving"
        assert prediction["prediction"] in (0, 1)
        assert 0 <= prediction["probability_disease"] <= 1
        assert 0.5 <= prediction["confidence"] <= 1
        records["/predict"] = prediction
        invalid = dict(sample, cp=0)
        response = client.post(base_url + "/predict", json=invalid)
        assert response.status_code == 422, response.text
        records["invalid_cp_status"] = response.status_code
        response = client.get(base_url + "/metrics")
        response.raise_for_status()
        assert "heartml_predictions_total" in response.text
        records["metrics_present"] = True
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(records, indent=2))
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--expected-model-version")
    args = parser.parse_args()
    run(args.url, args.output, args.expected_model_version)
