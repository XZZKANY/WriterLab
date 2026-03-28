$ErrorActionPreference = "Stop"

$frontend = "D:\WritierLab\WriterLab-v1\Next.js\frontend"
Set-Location $frontend

npm.cmd run typecheck
Write-Host "Frontend typecheck completed."
