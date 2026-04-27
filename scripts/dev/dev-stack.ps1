$ErrorActionPreference = "Stop"

$root = "D:\WritierLab"

Write-Host "[1/4] Installing backend dependencies..."
& "$root\scripts\dev\install-backend.ps1"

Write-Host "[2/4] Running backend checks..."
& "$root\scripts\check\check-backend.ps1"

Write-Host "[3/4] Running frontend checks..."
& "$root\scripts\check\check-frontend.ps1"

Write-Host "[4/4] Start these in separate terminals:"
Write-Host "1. powershell -ExecutionPolicy Bypass -File $root\scripts\dev\start-backend.ps1"
Write-Host "2. powershell -ExecutionPolicy Bypass -File $root\scripts\dev\start-frontend.ps1"
Write-Host "After the backend is up, run: powershell -ExecutionPolicy Bypass -File $root\scripts\check\check-backend.ps1 -FullSmoke"
Write-Host "For real provider verification, run: powershell -ExecutionPolicy Bypass -File $root\scripts\check\check-backend.ps1 -FullSmoke -LiveProviders"
Write-Host "After the frontend is up, run: powershell -ExecutionPolicy Bypass -File $root\scripts\check\check-frontend.ps1 -LiveUiSmoke"
