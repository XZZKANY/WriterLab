$ErrorActionPreference = "Stop"

$backend = "D:\WritierLab\WriterLab-v1\fastapi\backend"
Set-Location $backend

$projectRoot = Split-Path $backend -Parent -Parent
$venvPath = Join-Path $projectRoot ".venv"
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
& $venvPython -m pip install -r ".\requirements.codex.txt"

Write-Host "Backend dependencies installed."
