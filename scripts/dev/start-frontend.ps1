$ErrorActionPreference = "Stop"

$frontend = "D:\WritierLab\apps\frontend"
Set-Location $frontend

node ".\node_modules\next\dist\bin\next" dev -p 3000
