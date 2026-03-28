$ErrorActionPreference = "Stop"

$backend = "D:\WritierLab\WriterLab-v1\fastapi\backend"
Set-Location $backend

& ".\.venv\Scripts\python.exe" -c "import fastapi, sqlalchemy, httpx, uvicorn; print('backend imports ok')"
& ".\.venv\Scripts\python.exe" -c "from app.db.session import engine; conn = engine.connect(); print('database ok'); conn.close()"
Write-Host "Backend checks completed."
