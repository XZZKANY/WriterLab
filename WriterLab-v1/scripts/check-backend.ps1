param(
  [switch]$FullSmoke,
  [switch]$LiveProviders,
  [string]$Scenario = "all"
)

$ErrorActionPreference = "Stop"

$backend = "D:\WritierLab\WriterLab-v1\fastapi\backend"
$projectRoot = Split-Path (Split-Path $backend -Parent) -Parent
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$logsDir = Join-Path $projectRoot "scripts\logs"
Set-Location $backend

if (-not (Test-Path $venvPython)) {
  throw "Python virtualenv not found. Run scripts\\install-backend.ps1 first."
}

Write-Host "[1/4] Backend import check..."
& $venvPython -c "import fastapi, sqlalchemy, httpx, uvicorn; print('backend imports ok')"

Write-Host "[2/4] Database connection check..."
& $venvPython -c "from app.db.session import engine; conn = engine.connect(); print('database ok'); conn.close()"

Write-Host "[3/4] Alembic state check..."
& $venvPython -m alembic current

Write-Host "[4/4] Runtime API smoke check..."
try {
  $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 5
  $selfCheck = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/runtime/self-check" -TimeoutSec 5
  Write-Host "Health status: $($health.status) | schema_ready=$($health.schema_ready) | runner_started=$($health.workflow_runner_started) | pgvector_ready=$($health.pgvector_ready)"
  Write-Host "Self-check: provider_rules=$($selfCheck.provider_matrix.rule_count) | recovery_scan_completed=$($selfCheck.workflow_runtime.recovery_scan_completed)"
} catch {
  Write-Warning "Backend API is not reachable yet. Static checks passed; start the backend and rerun this script for live smoke checks."
}

if ($FullSmoke) {
  if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
  }
  $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $reportPath = Join-Path $logsDir "backend-full-smoke-$timestamp.json"
  $providerMode = if ($LiveProviders) { "live" } else { "smoke_fixture" }
  Write-Host "[5/5] Backend full smoke..."
  & $venvPython "$projectRoot\scripts\backend_full_smoke.py" --base-url "http://127.0.0.1:8000" --report-path $reportPath --provider-mode $providerMode --scenario $Scenario
  if ($LASTEXITCODE -ne 0) {
    $failureStage = $null
    if (Test-Path $reportPath) {
      try {
        $report = Get-Content -Path $reportPath -Raw | ConvertFrom-Json
        $failureStage = $report.failure_stage
      } catch {
        $failureStage = $null
      }
    }
    if ($failureStage -eq "preflight_blocked") {
      throw "Preflight blocked by provider runtime. See $reportPath"
    }
    if ($failureStage -eq "execution_failed") {
      throw "Workflow execution failed after preflight passed. See $reportPath"
    }
    throw "Backend full smoke failed. See $reportPath"
  }
  Write-Host "Backend full smoke report: $reportPath"
}

Write-Host "Backend checks completed."
