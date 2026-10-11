param([string]$Image = "heart-risk-api:1.0")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force -Path evidence | Out-Null
$name = "heartml-smoke-" + [Guid]::NewGuid().ToString("N").Substring(0,8)
$started = $false
$validation = @{passed=$false; host_mount_count=-1; image=$Image}
Start-Transcript -Path evidence/docker_build_run.txt -Force
try {
    docker build -t $Image .
    if ($LASTEXITCODE -ne 0) { throw "Docker build failed" }
    docker run -d --name $name -p 127.0.0.1:8001:8000 $Image
    if ($LASTEXITCODE -ne 0) { throw "Docker run failed" }
    $started = $true
    $ready = $false
    for ($i = 0; $i -lt 60; $i++) {
        try {
            $null = Invoke-RestMethod -Uri "http://localhost:8001/ready" -TimeoutSec 3
            $ready = $true
            break
        } catch { Start-Sleep -Seconds 2 }
    }
    if (-not $ready) { throw "Container did not become ready" }
    $expected = (Get-Content artifacts/model/metadata.json -Raw | ConvertFrom-Json).model_version
    python scripts/smoke_api.py --url http://localhost:8001 --expected-model-version $expected --output evidence/docker_smoke.json
    if ($LASTEXITCODE -ne 0) { throw "Container smoke test failed" }
    $inspection = docker inspect $name | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw "Cannot inspect the running container" }
    $validation.host_mount_count = @($inspection[0].Mounts).Count
    if ($validation.host_mount_count -ne 0) { throw "Isolation check requires no host mounts" }
    $validation.passed = $true
    $validation.container_id = $inspection[0].Id
    $validation.image_id = $inspection[0].Image
    $validation.model_version = $expected
    $validation.executed_at = (Get-Date).ToUniversalTime().ToString("o")
} catch {
    $validation.error = $_.Exception.Message
    throw
} finally {
    $validation | ConvertTo-Json -Depth 5 | Out-File -Encoding utf8 evidence/docker_validation.json
    if ($started) {
        cmd /c "docker logs $name > evidence\docker_container.log 2>&1"
        docker rm -f $name | Out-Null
    }
    Stop-Transcript
}
