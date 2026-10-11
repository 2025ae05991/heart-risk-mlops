param([switch]$SkipBuild, [string]$GrafanaPassword)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
function Run-Native {
    param([string]$Command, [string[]]$Arguments)
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Command failed: $($Arguments -join ' ')" }
}
Run-Native kubectl @("config", "use-context", "docker-desktop")
Run-Native kubectl @("get", "nodes")
if (-not $SkipBuild) { Run-Native docker @("build", "-t", "heart-risk-api:1.0", ".") }
Run-Native kubectl @("apply", "-f", "k8s/namespace.yaml")
Run-Native kubectl @("apply", "-f", "k8s/api.yaml")
# A rebuilt local tag has the same manifest value. Restart so pods load the current image.
Run-Native kubectl @("-n", "heartml", "rollout", "restart", "deployment/heart-risk-api")
Run-Native kubectl @("-n", "heartml", "rollout", "status", "deployment/heart-risk-api", "--timeout=240s")

# Set the secret through stdin. Passwords are not placed on a process command line or saved to disk.
$existingSecret = & kubectl -n heartml get secret grafana-admin --ignore-not-found -o name
if ($LASTEXITCODE -ne 0) { throw "Cannot inspect Grafana secret" }
if (-not $existingSecret) {
    if (-not $GrafanaPassword) {
        $securePassword = Read-Host "Choose a Grafana admin password" -AsSecureString
        $GrafanaPassword = [System.Net.NetworkCredential]::new("", $securePassword).Password
    }
    if ($GrafanaPassword.Length -lt 8) { throw "Use a password with at least 8 characters" }
    $secret = @{apiVersion="v1"; kind="Secret"; metadata=@{name="grafana-admin"; namespace="heartml"};
        type="Opaque"; data=@{username=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("admin"));
        password=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($GrafanaPassword))}}
    $secret | ConvertTo-Json -Depth 6 -Compress | kubectl apply -f - | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Cannot create Grafana secret" }
    $GrafanaPassword = $null
}
function Apply-ConfigMap {
    param([string]$Name, [string[]]$Sources)
    $yaml = & kubectl --context docker-desktop -n heartml create configmap $Name @Sources --dry-run=client -o yaml
    if ($LASTEXITCODE -ne 0) { throw "Cannot generate ConfigMap $Name" }
    $yaml | kubectl --context docker-desktop apply -f -
    if ($LASTEXITCODE -ne 0) { throw "Cannot apply ConfigMap $Name" }
}
Apply-ConfigMap "prometheus-config" @("--from-file=prometheus.yml=monitoring/prometheus.yml", "--from-file=alerts.yml=monitoring/alerts.yml")
Apply-ConfigMap "grafana-datasource" @("--from-file=datasource.yml=monitoring/datasource.yml")
Apply-ConfigMap "grafana-provider" @("--from-file=provider.yml=monitoring/dashboard-provider.yml")
Apply-ConfigMap "grafana-dashboard" @("--from-file=heartml.json=monitoring/grafana-dashboard.json")
Run-Native kubectl @("apply", "-f", "k8s/monitoring.yaml")
Run-Native kubectl @("-n", "heartml", "rollout", "status", "deployment/prometheus", "--timeout=240s")
Run-Native kubectl @("-n", "heartml", "rollout", "status", "deployment/grafana", "--timeout=240s")
Run-Native kubectl @("-n", "heartml", "get", "pods,svc")
Write-Host "API: http://localhost:8000/docs"
Write-Host "Grafana: run kubectl -n heartml port-forward svc/grafana 3000:3000 in another terminal."

