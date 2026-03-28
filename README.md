# WritierLab

WritierLab is a hybrid AI writing workspace for long-form fiction.

It combines:

- a FastAPI backend for project, chapter, scene, memory, workflow, branch, and consistency APIs
- a Next.js editor for drafting, workflow control, branch comparison, and VN export preview
- PostgreSQL + pgvector for worldbuilding memory and retrieval
- Ollama + cloud providers for a hybrid local/cloud writing pipeline

## What It Can Do

- Manage projects, books, chapters, scenes, characters, locations, and lore
- Run multi-step writing workflows with planner, writer, style, consistency, guardrail, and memory stages
- Retrieve long-term setting memory with pgvector-backed RAG
- Detect consistency issues across scenes, chapters, timeline anchors, and style memory
- Compare and adopt story branches inside the editor
- Export scene text into VN-friendly structured output
- Save provider API settings from the frontend

## Repository Layout

- `WriterLab-v1/`
  Main application workspace
- `WriterLab-v1/fastapi/backend/`
  Backend API and workflow services
- `WriterLab-v1/Next.js/frontend/`
  Frontend editor
- `WriterLab-v1/docs/runtime-notes.md`
  Runtime notes and troubleshooting

## Stack

- Backend: FastAPI, SQLAlchemy, Alembic
- Frontend: Next.js, React, TypeScript
- Database: PostgreSQL 16, pgvector
- Local inference: Ollama
- Cloud routing: OpenAI, DeepSeek, xAI

## Quick Start

### Backend

```powershell
& 'D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir 'D:\WritierLab\WriterLab-v1\fastapi\backend'
```

### Frontend

```powershell
Set-Location 'D:\WritierLab\WriterLab-v1\Next.js\frontend'
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

Then open:

- Backend health: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Editor: [http://127.0.0.1:3000/editor](http://127.0.0.1:3000/editor)

## Notes

- This repository currently keeps the application under `WriterLab-v1/`.
- In restricted Windows shells, Next.js may hit `spawn EPERM`; when that happens, use a normal local shell.
- Runtime and troubleshooting details are documented in `WriterLab-v1/docs/runtime-notes.md`.
