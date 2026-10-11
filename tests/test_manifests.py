import json

import yaml

from heartml.settings import ROOT


def test_api_replica_health_and_loadbalancer_contract():
    objects = list(yaml.safe_load_all((ROOT / "k8s/api.yaml").read_text()))
    deployment, service = objects
    assert deployment["spec"]["replicas"] == 2
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert container["imagePullPolicy"] in {"Never", "IfNotPresent"}
    if container["imagePullPolicy"] == "IfNotPresent":
        assert "/" in container["image"], "Registry fallback needs the full repository image name"
    assert container["readinessProbe"]["httpGet"]["path"] == "/ready"
    assert container["livenessProbe"]["httpGet"]["path"] == "/health"
    assert container["ports"][0]["containerPort"] == 8000
    assert service["spec"]["type"] == "LoadBalancer"
    assert service["spec"]["ports"][0]["port"] == 8000
    assert service["spec"]["selector"] == deployment["spec"]["selector"]["matchLabels"]


def test_metrics_discovery_targets_individual_pods_and_dashboard_is_provisioned():
    config = yaml.safe_load((ROOT / "monitoring/prometheus.yml").read_text())
    api_job = config["scrape_configs"][0]
    assert api_job["kubernetes_sd_configs"][0]["role"] == "pod"
    dashboard = json.loads((ROOT / "monitoring/grafana-dashboard.json").read_text())
    assert len(dashboard["panels"]) >= 5
    assert all(panel["datasource"]["uid"] == "heartml-prometheus" for panel in dashboard["panels"])
    objects = list(yaml.safe_load_all((ROOT / "k8s/monitoring.yaml").read_text()))
    assert {o["kind"] for o in objects} >= {"Deployment", "Service", "Role", "RoleBinding"}
