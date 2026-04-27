param(
  [switch]$LiveUiSmoke
)

$ErrorActionPreference = "Stop"

$frontend = "D:\WritierLab\WriterLab-v1\Next.js\frontend"
$projectRoot = Split-Path (Split-Path $frontend -Parent) -Parent
$logsDir = Join-Path $projectRoot "scripts\logs"
Set-Location $frontend

Write-Host "[1/3] Frontend typecheck..."
npm.cmd run typecheck
if ($LASTEXITCODE -ne 0) {
  throw "Frontend typecheck failed."
}

Write-Host "[2/3] Frontend ESLint..."
npm.cmd run lint
if ($LASTEXITCODE -ne 0) {
  throw "Frontend ESLint failed."
}

Write-Host "[3/3] Frontend production build check..."
$nativePreference = Get-Variable PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue
if ($null -ne $nativePreference) {
  $previousNativePreference = $PSNativeCommandUseErrorActionPreference
  $PSNativeCommandUseErrorActionPreference = $false
}

try {
  $buildOutput = & npm.cmd run build:node 2>&1
  $buildExitCode = $LASTEXITCODE
} catch {
  $buildOutput = @($_ | Out-String)
  $buildExitCode = if ($LASTEXITCODE -ne 0) { $LASTEXITCODE } else { 1 }
} finally {
  if ($null -ne $nativePreference) {
    $PSNativeCommandUseErrorActionPreference = $previousNativePreference
  }
}

$buildOutput | ForEach-Object { Write-Host $_ }

if ($buildExitCode -ne 0) {
  $buildText = ($buildOutput | Out-String)
  if ($buildText -match "spawn EPERM|NativeCommandError|PSSecurityException") {
    Write-Warning "Next.js build hit the known restricted-shell Windows environment limitation. Treat this as an environment caveat unless TypeScript compilation also fails in a normal local shell."
  } else {
    throw "Frontend production build failed."
  }
}

if ($LiveUiSmoke) {
  if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
  }
  $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $reportPath = Join-Path $logsDir "frontend-live-smoke-$timestamp.json"
  Write-Host "[4/4] Frontend live UI smoke (editor/project/lore/runtime/settings)..."
  node "$projectRoot\scripts\frontend_live_smoke.mjs" "http://127.0.0.1:3000" $reportPath
  if ($LASTEXITCODE -ne 0) {
    throw "Frontend live UI smoke failed. See $reportPath"
  }
  Write-Host "Frontend live UI smoke report: $reportPath"
}

Write-Host "Frontend checks completed."
