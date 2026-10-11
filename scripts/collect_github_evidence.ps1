param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')][string]$Repository,
    [long]$RunId = 0
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force -Path evidence | Out-Null
Get-Command gh, git -ErrorAction Stop | Out-Null
gh auth status
if ($LASTEXITCODE -ne 0) { throw "Sign in first with gh auth login" }
$sha = git rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw "Upload and commit this project before collecting hosted CI evidence" }
if ($RunId -eq 0) {
    $runs = gh run list --repo $Repository --workflow ci.yml --commit $sha --limit 20 --json databaseId,status,conclusion,headSha | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw "Cannot find workflow runs" }
    $run = @($runs | Where-Object { $_.status -eq "completed" -and $_.conclusion -eq "success" }) | Select-Object -First 1
    if (-not $run) { throw "No successful HeartML CI run exists for your current commit. Wait for Actions or inspect its failure." }
    $RunId = $run.databaseId
}
$json = gh run view $RunId --repo $Repository --json databaseId,url,headSha,status,conclusion,workflowName,jobs
if ($LASTEXITCODE -ne 0) { throw "Cannot read the GitHub run" }
$run = $json | ConvertFrom-Json
if ($run.status -ne "completed" -or $run.conclusion -ne "success" -or $run.workflowName -ne "HeartML CI" -or $run.headSha -ne $sha) { throw "The run must be a successful HeartML CI run for the current commit" }
$required = @("Lint and format check", "Unit tests", "Full EDA and model comparison", "Build isolated serving container", "Test isolated container")
$steps = @($run.jobs | ForEach-Object { $_.steps })
foreach ($name in $required) {
    if (-not @($steps | Where-Object { $_.name -eq $name -and $_.conclusion -eq "success" }).Count) { throw "Required CI stage did not pass: $name" }
}
$json | Out-File -Encoding utf8 evidence/github_run.json
gh run view $RunId --repo $Repository --log 2>&1 | Out-File -Encoding utf8 evidence/github_actions.log
if ($LASTEXITCODE -ne 0) { throw "Cannot collect workflow logs" }
Write-Host "Hosted CI evidence saved: $($run.url)"
Write-Host "Open that URL and save screenshots/github_actions.png."
