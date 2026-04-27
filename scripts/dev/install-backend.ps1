$ErrorActionPreference = "Stop"

# 后端 venv 与 requirements.txt 都落在 backend 目录内，与 alembic.ini / .env 一起。
$backend = "D:\WritierLab\apps\backend"
Set-Location $backend

$venvPath = Join-Path $backend ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$pythonCmd = (Get-Command python -ErrorAction Stop).Source

$needsRecreate = $true
if (Test-Path $venvPython) {
  try {
    & $venvPython --version | Out-Null
    $needsRecreate = $false
  } catch {
    $backupPath = "$venvPath.broken-" + (Get-Date -Format "yyyyMMdd-HHmmss")
    Rename-Item -Path $venvPath -NewName (Split-Path $backupPath -Leaf)
  }
}

if ($needsRecreate) {
  & $pythonCmd -m venv $venvPath
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r ".\requirements.txt"

Write-Host "Backend dependencies installed."
