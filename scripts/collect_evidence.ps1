$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force -Path evidence | Out-Null
function Get-KubeJson {
    param([string[]]$Arguments)
    $raw = & kubectl --context docker-desktop -n heartml @Arguments -o json
    if ($LASTEXITCODE -ne 0) { throw "Cannot query Docker Desktop resources" }
    return $raw | ConvertFrom-Json
}
kubectl --context docker-desktop -n heartml get pods,svc,deploy -o wide 2>&1 | Out-File -Encoding utf8 evidence/kubernetes_resources.txt
if ($LASTEXITCODE -ne 0) { throw "Cannot read Docker Desktop cluster" }
$validation = @{context="docker-desktop"; ready_api_pods=0; service_type=""; passed=$false}
try {
    $pods = Get-KubeJson @("get", "pods", "-l", "app=heart-risk-api")
    $service = Get-KubeJson @("get", "service", "heart-risk-api")
    $deployment = Get-KubeJson @("get", "deployment", "heart-risk-api")
    $readyPods = @($pods.items | Where-Object { $_.status.phase -eq "Running" -and @($_.status.conditions | Where-Object { $_.type -eq "Ready" -and $_.status -eq "True" }).Count -gt 0 })
    $validation.ready_api_pods = $readyPods.Count
    $validation.service_type = $service.spec.type
    if ($readyPods.Count -ne 2 -or $deployment.spec.replicas -ne 2 -or $deployment.status.availableReplicas -ne 2) { throw "Expected two ready API replicas" }
    if ($service.spec.type -ne "LoadBalancer" -or $service.spec.ports[0].port -ne 8000) { throw "Expected LoadBalancer Service on port 8000" }
    $expected = (Get-Content artifacts/model/metadata.json -Raw | ConvertFrom-Json).model_version
    python scripts/smoke_api.py --url http://localhost:8000 --expected-model-version $expected --output evidence/kubernetes_smoke.json
    if ($LASTEXITCODE -ne 0) { throw "Kubernetes endpoint check failed" }
    $snapshot = Invoke-RestMethod -Uri http://localhost:8000/monitoring -TimeoutSec 15
    if ($snapshot.instance.Split(':')[0] -notin @($readyPods | ForEach-Object { $_.metadata.name })) { throw "Port 8000 is not responding from an API pod; stop the host API" }
    $snapshot | ConvertTo-Json -Depth 6 | Out-File -Encoding utf8 evidence/kubernetes_dashboard_snapshot.json
    $validation.passed = $true
    $validation.model_version = $expected
    $validation.api_pods = @($readyPods | ForEach-Object { $_.metadata.name })
    $validation.executed_at = (Get-Date).ToUniversalTime().ToString("o")
    kubectl --context docker-desktop -n heartml logs -l app=heart-risk-api --all-containers=true --prefix=true --tail=500 2>&1 | Out-File -Encoding utf8 evidence/kubernetes_api.log
    if ($LASTEXITCODE -ne 0) { throw "Cannot read API pod logs" }
} catch {
    $validation.passed = $false
    $validation.error = $_.Exception.Message
    throw
} finally {
    $validation | ConvertTo-Json -Depth 6 | Out-File -Encoding utf8 evidence/kubernetes_validation.json
}
Write-Host "Deployment checks passed. Capture the screenshots listed in screenshots/README.md."
