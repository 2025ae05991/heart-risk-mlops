import httpx
import pytest

from heartml.monitoring import verify


def transport_with_targets(healthy=True):
    def respond(request):
        path = request.url.path
        if path.endswith("/targets"):
            data = {
                "activeTargets": [
                    {
                        "labels": {"job": "heart-risk-api", "pod": f"api-{i}"},
                        "health": "up" if healthy or i == 0 else "down",
                    }
                    for i in range(2)
                ]
            }
            payload = {"status": "success", "data": data}
        elif path.endswith("/query"):
            expression = request.url.params["query"]
            value = "0.015" if expression.startswith("histogram") else "2"
            payload = {
                "status": "success",
                "data": {"resultType": "vector", "result": [{"metric": {}, "value": [123, value]}]},
            }
        elif path.endswith("/health"):
            payload = {"database": "ok"}
        elif "/datasources/uid/" in path:
            assert request.headers["Authorization"].startswith("Basic ")
            payload = {"uid": "heartml-prometheus", "type": "prometheus"}
        else:
            payload = {"dashboard": {"uid": "heartml-api", "panels": [{} for _ in range(6)]}}
        return httpx.Response(200, json=payload)

    return httpx.MockTransport(respond)


def test_monitoring_requires_real_targets_and_grafana_datasource_query():
    with httpx.Client(transport=transport_with_targets()) as client:
        result = verify(client, "http://prometheus", "http://grafana", "admin", "unit-secret")
    assert result["passed"] is True
    assert result["healthy_pods"] == ["api-0", "api-1"]
    assert result["grafana_datasource_query_passed"] is True
    assert "unit-secret" not in str(result)


def test_monitoring_rejects_a_down_pod():
    with httpx.Client(transport=transport_with_targets(healthy=False)) as client:
        with pytest.raises(RuntimeError, match="not UP"):
            verify(client, "http://prometheus", "http://grafana", "admin", "unit-secret")
