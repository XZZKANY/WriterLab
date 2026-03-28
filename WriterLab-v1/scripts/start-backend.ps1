$ErrorActionPreference = "Stop"

$backend = "D:\WritierLab\WriterLab-v1\fastapi\backend"
$projectRoot = Split-Path $backend -Parent -Parent
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
Set-Location $backend

& $venvPython -m uvicorn app.main:app --host 127.0.0.1 --port 8000
