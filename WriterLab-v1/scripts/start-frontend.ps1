$ErrorActionPreference = "Stop"

$frontend = "D:\WritierLab\WriterLab-v1\Next.js\frontend"
Set-Location $frontend

node ".\node_modules\next\dist\bin\next" dev -p 3000
