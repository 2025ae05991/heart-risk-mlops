"""Verify live Prometheus discovery, real metric values, and Grafana provisioning."""

import argparse
import getpass
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx


def response_json(client, url, **kwargs):
    response = client.get(url, **kwargs)
    response.raise_for_status()
    return response.json()


def query(client, url, expression, **kwargs):
    payload = response_json(client, url, params={"query": expression}, **kwargs)
    if payload.get("status") != "success":
        raise RuntimeError("Prometheus query failed")
    result = payload["data"]["result"]
    if len(result) != 1:
        raise RuntimeError(f"Expected one result for: {expression}")
    value = float(result[0]["value"][1])
    if not math.isfinite(value):
        raise RuntimeError(f"Metric has no finite value yet: {expression}")
    return value


def verify(client, prometheus_url, grafana_url, username, password, expected_pods=2):
    prometheus_url = prometheus_url.rstrip("/")
    grafana_url = grafana_url.rstrip("/")
    targets = response_json(client, prometheus_url + "/api/v1/targets")["data"]["activeTargets"]
    api_targets = [t for t in targets if t["labels"].get("job") == "heart-risk-api"]
    pod_names = {t["labels"].get("pod") for t in api_targets}
    if len(api_targets) != expected_pods or len(pod_names - {None}) != expected_pods:
        raise RuntimeError(f"Expected {expected_pods} distinct API pod targets")
    if any(t.get("health") != "up" for t in api_targets):
        raise RuntimeError("An API pod target is not UP")
    endpoint = prometheus_url + "/api/v1/query"
    expressions = {
        "healthy_api_pods": 'sum(up{job="heart-risk-api"})',
        "served_predictions": 'sum(heartml_predictions_total{job="heart-risk-api"})',
        "successful_predictions": (
            'sum(heartml_http_requests_total{job="heart-risk-api",route="/predict",status="200"})'
        ),
        "validation_errors": (
            'sum(heartml_http_requests_total{job="heart-risk-api",route="/predict",status="422"})'
        ),
        "prediction_p95_seconds": (
            "histogram_quantile(0.95, sum by (le) "
            '(rate(heartml_http_duration_seconds_bucket{job="heart-risk-api",'
            'route="/predict"}[2m])))'
        ),
    }
    values = {name: query(client, endpoint, expr) for name, expr in expressions.items()}
    if values["healthy_api_pods"] != expected_pods:
        raise RuntimeError("The up metric does not match the expected replica count")
    if any(values[key] <= 0 for key in expressions if key != "prediction_p95_seconds"):
        raise RuntimeError("Run valid and deliberately invalid traffic before verification")
    if values["prediction_p95_seconds"] < 0:
        raise RuntimeError("Prediction p95 must not be negative")
    health = response_json(client, grafana_url + "/api/health")
    if health.get("database") != "ok":
        raise RuntimeError("Grafana database health is not OK")
    auth = httpx.BasicAuth(username, password)
    datasource = response_json(
        client, grafana_url + "/api/datasources/uid/heartml-prometheus", auth=auth
    )
    if datasource.get("type") != "prometheus":
        raise RuntimeError("Provisioned Grafana datasource is not Prometheus")
    dashboard = response_json(client, grafana_url + "/api/dashboards/uid/heartml-api", auth=auth)[
        "dashboard"
    ]
    if len(dashboard.get("panels", [])) < 6:
        raise RuntimeError("Expected the six provisioned dashboard panels")
    proxy_up = query(
        client,
        grafana_url + "/api/datasources/proxy/uid/heartml-prometheus/api/v1/query",
        expressions["healthy_api_pods"],
        auth=auth,
    )
    if proxy_up != expected_pods:
        raise RuntimeError("Grafana cannot query both API pods through its datasource")
    return {
        "passed": True,
        "executed_at": datetime.now(UTC).isoformat(),
        "expected_api_pods": expected_pods,
        "healthy_pods": sorted(pod_names),
        "prometheus_values": values,
        "grafana_database": "ok",
        "grafana_dashboard_uid": dashboard["uid"],
        "grafana_panel_count": len(dashboard["panels"]),
        "grafana_datasource_query_passed": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prometheus-url", default="http://localhost:9090")
    parser.add_argument("--grafana-url", default="http://localhost:3000")
    parser.add_argument("--credentials-stdin", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("evidence/monitoring_validation.json"))
    args = parser.parse_args()
    if args.credentials_stdin:
        credentials = json.load(sys.stdin)
        username, password = credentials["username"], credentials["password"]
    else:
        username = "admin"
        password = getpass.getpass("Grafana admin password: ")
    try:
        with httpx.Client(timeout=30, trust_env=False) as client:
            result = verify(client, args.prometheus_url, args.grafana_url, username, password)
    except (httpx.HTTPError, RuntimeError, KeyError, ValueError) as error:
        result = {
            "passed": False,
            "executed_at": datetime.now(UTC).isoformat(),
            "error": str(error),
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1
