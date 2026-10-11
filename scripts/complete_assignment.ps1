param([string]$RepositoryUrl = "", [string]$GitHubRunUrl = "", [switch]$SkipTraining)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force -Path evidence | Out-Null
function Run-Native {
    param([string]$Command, [string[]]$Arguments, [string]$LogPath = "")
    if ($LogPath) {
        $outputLines = @()
        & $Command @Arguments | Tee-Object -Variable outputLines
        $nativeCode = $LASTEXITCODE
        $outputLines | Out-File -Encoding utf8 $LogPath
    } else {
        & $Command @Arguments
        $nativeCode = $LASTEXITCODE
    }
    if ($nativeCode -ne 0) { throw "$Command failed: $($Arguments -join ' ')" }
}
function Wait-Http {
    param([string]$Url)
    for ($i=0; $i -lt 40; $i++) {
        try { $null = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 3; return }
        catch { Start-Sleep -Seconds 1 }
    }
    throw "Service did not become available: $Url"
}
$forwards = @()
$status = @{passed=$false; stage="preflight"; context="docker-desktop"}
try {
    Get-Command python, docker, kubectl -ErrorAction Stop | Out-Null
    Run-Native python @("-c", "import sys; assert (3,11) <= sys.version_info[:2] <= (3,12), 'Activate Python 3.11 or 3.12'")
    $dockerOS = docker info --format '{{.OSType}}'
    if ($LASTEXITCODE -ne 0 -or $dockerOS -ne "linux") { throw "Start Docker Desktop in Linux containers mode" }
    Run-Native kubectl @("--context", "docker-desktop", "get", "nodes")
    foreach ($port in @(8000,8001,3000,9090)) {
        $probe = [System.Net.Sockets.TcpClient]::new()
        try {
            $connect = $probe.ConnectAsync("127.0.0.1", $port)
            try { $null = $connect.Wait(500) } catch { }
            if ($probe.Connected) { throw "Port $port is busy. Stop the host API or your existing forwarding terminal, then retry." }
        } finally { $probe.Dispose() }
    }
    $status.stage = "dependencies and data"
    Run-Native python @("-m", "pip", "install", "-r", "requirements.txt", "-e", ".")
    Run-Native python @("-m", "pip", "check")
    Run-Native python @("scripts/download_data.py")
    $status.stage = "lint and unit tests"
    Run-Native python @("-m", "ruff", "check", ".") "evidence/lint.log"
    Run-Native python @("-m", "ruff", "format", "--check", ".") "evidence/format.log"
    Run-Native python @("-m", "pytest", "--cov=heartml", "--cov-report=term-missing", "--cov-report=xml:evidence/coverage.xml", "--junitxml=evidence/junit.xml") "evidence/tests.log"
    $status.stage = "full training"
    if (-not $SkipTraining) { Run-Native python @("scripts/run_pipeline.py") "evidence/training.log" }
    Run-Native python @("scripts/validate_model.py")
    Run-Native python @("scripts/export_mlflow.py")
    $status.stage = "isolated Docker build and serving"
    & ./scripts/docker_smoke.ps1
    $status.stage = "Docker Desktop Kubernetes deployment"
    & ./scripts/deploy.ps1 -SkipBuild
    & ./scripts/collect_evidence.ps1
    $status.stage = "monitoring verification"
    foreach ($service in @(@{name="prometheus";port=9090}, @{name="grafana";port=3000})) {
        $forward = Start-Process -FilePath (Get-Command kubectl).Source -ArgumentList @("--context", "docker-desktop", "-n", "heartml", "port-forward", "svc/$($service.name)", "$($service.port):$($service.port)", "--address", "127.0.0.1") -PassThru -RedirectStandardOutput "evidence/$($service.name)_forward.log" -RedirectStandardError "evidence/$($service.name)_forward_error.log"
        $forwards += $forward
    }
    Wait-Http "http://localhost:9090/-/ready"
    Wait-Http "http://localhost:3000/api/health"
    Run-Native python @("scripts/make_load.py", "--url", "http://localhost:8000", "--requests", "240") "evidence/monitoring_traffic.log"
    # Read only this lab's chosen credentials. Send through stdin; never log or save the password.
    $secret = kubectl --context docker-desktop -n heartml get secret grafana-admin -o json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw "Cannot read the lab Grafana credentials" }
    $credentials = @{username=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($secret.data.username)); password=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($secret.data.password))}
    $credentials | ConvertTo-Json -Compress | python scripts/verify_monitoring.py --credentials-stdin
    if ($LASTEXITCODE -ne 0) { throw "Live monitoring checks failed" }
    $credentials = $null; $secret = $null
    $status.stage = "report and submission audit"
    Run-Native python @("-m", "pip", "install", "-r", "requirements-docs.txt")
    $documentArguments = @()
    if ($RepositoryUrl) { $documentArguments += @("--repository-url", $RepositoryUrl) }
    if ($GitHubRunUrl) { $documentArguments += @("--github-run-url", $GitHubRunUrl) }
    Run-Native python (@("scripts/finalize_submission.py") + $documentArguments)
    Run-Native python (@("tools/build_report.py") + $documentArguments)
    Run-Native python (@("scripts/finalize_submission.py") + $documentArguments)
    $status.passed = $true
    $status.stage = "local checks passed; capture screenshots, hosted CI and final video"
    Write-Host "Local execution checks passed. API: http://localhost:8000/docs"
    Write-Host "Open /dashboard for built-in live monitoring. Follow docs/Final_Submission_Status.md for evidence still required."
} catch {
    $status.error = $_.Exception.Message
    throw
} finally {
    foreach ($forward in $forwards) { if (-not $forward.HasExited) { Stop-Process -Id $forward.Id -ErrorAction SilentlyContinue } }
    $status.executed_at = (Get-Date).ToUniversalTime().ToString("o")
    $status | ConvertTo-Json -Depth 5 | Out-File -Encoding utf8 evidence/complete_run_status.json
}
