# WriterLab v1

WriterLab v1 is the main application workspace inside this repository.

## Included Modules

- `fastapi/backend`
  FastAPI backend, workflow engine, knowledge retrieval, consistency scan, branch APIs, and provider settings APIs
- `Next.js/frontend`
  Next.js editor UI for writing, workflow control, branch adoption, consistency review, and VN export preview
- `docs`
  Runtime notes and troubleshooting
- `scripts`
  Helper scripts for local setup and demo data repair

## Core Capabilities

- Scene-based writing workflow
- Hybrid local/cloud model routing
- pgvector-backed setting memory retrieval
- Consistency checking across lore, timeline, and chapter context
- Branch compare and adopt flow
- VN export preview
- Saved API key settings from the frontend

## Run Locally

### Backend

```powershell
& 'D:\WritierLab\WriterLab-v1\fastapi\backend\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir 'D:\WritierLab\WriterLab-v1\fastapi\backend'
```

### Frontend

```powershell
Set-Location 'D:\WritierLab\WriterLab-v1\Next.js\frontend'
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

## Runtime Notes

See `docs/runtime-notes.md` for:

- startup commands
- `spawn EPERM` notes
- live self-check steps
- demo data repair script usage
