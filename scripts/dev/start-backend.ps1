$ErrorActionPreference = "Stop"

$backend = "D:\WritierLab\apps\backend"
$venvPython = Join-Path $backend ".venv\Scripts\python.exe"
Set-Location $backend

if (-not (Test-Path $venvPython)) {
  throw "Python virtualenv not found. Run scripts\\install-backend.ps1 first."
}

Write-Host "[1/2] Applying Alembic migrations..."
& $venvPython -m alembic upgrade head
if ($LASTEXITCODE -ne 0) {
  throw "Alembic migration failed."
}

Write-Host "[2/2] Starting FastAPI backend..."
& $venvPython -m uvicorn app.main:app --host 127.0.0.1 --port 8000
