# 仓库目录布局

本文记录 T-8 重组（2026-04-28）后的目录结构，并附旧路径 → 新路径映射表供历史参考。

## 当前布局

```text
WritierLab/
├─ apps/
│  ├─ backend/          FastAPI 后端（app/ + tests/ + alembic/ + requirements.txt）
│  └─ frontend/         Next.js 16 前端（app/ + tests/ + public/ + package.json）
├─ docs/
│  ├─ architecture/     架构文档（含本文件、refactor 记录）
│  ├─ project/          项目盘点
│  ├─ runbooks/         运行手册
│  ├─ verification/     本地验证说明
│  ├─ superpowers/      设计 spec / plan（原 WriterLab-v1/docs/superpowers/）
│  ├─ ARCHITECTURE.md
│  ├─ TASKS.md
│  ├─ PROGRESS.md
│  └─ RESEARCH.md
├─ scripts/
│  ├─ dev/              start-backend.ps1  start-frontend.ps1  dev-stack.ps1  install-backend.ps1
│  ├─ check/            check-backend.ps1  check-frontend.ps1
│  ├─ smoke/            backend_full_smoke.py  frontend_live_smoke.mjs
│  └─ data/             fix_demo_garbled_data.py
├─ .codex/              上下文摘要、操作记录、验证报告
├─ AGENTS.md
└─ README.md
```

## 旧 → 新路径映射表

| 旧路径（WriterLab-v1 时代） | 新路径 |
|-----------------------------|--------|
| `WriterLab-v1/fastapi/backend/` | `apps/backend/` |
| `WriterLab-v1/Next.js/frontend/` | `apps/frontend/` |
| `WriterLab-v1/scripts/start-backend.ps1` | `scripts/dev/start-backend.ps1` |
| `WriterLab-v1/scripts/start-frontend.ps1` | `scripts/dev/start-frontend.ps1` |
| `WriterLab-v1/scripts/dev-stack.ps1` | `scripts/dev/dev-stack.ps1` |
| `WriterLab-v1/scripts/install-backend.ps1` | `scripts/dev/install-backend.ps1` |
| `WriterLab-v1/scripts/check-backend.ps1` | `scripts/check/check-backend.ps1` |
| `WriterLab-v1/scripts/check-frontend.ps1` | `scripts/check/check-frontend.ps1` |
| `WriterLab-v1/scripts/backend_full_smoke.py` | `scripts/smoke/backend_full_smoke.py` |
| `WriterLab-v1/scripts/frontend_live_smoke.mjs` | `scripts/smoke/frontend_live_smoke.mjs` |
| `WriterLab-v1/scripts/fix_demo_garbled_data.py` | `scripts/data/fix_demo_garbled_data.py` |
| `WriterLab-v1/docs/local-verification-zh.md` | `docs/verification/local-verification-zh.md` |
| `WriterLab-v1/docs/runtime-notes.md` | `docs/runbooks/runtime-notes.md` |
| `WriterLab-v1/docs/project-overview-zh.md` | `docs/project/project-overview-zh.md` |
| `WriterLab-v1/docs/refactor-migration-map-zh.md` | `docs/architecture/refactor-migration-map-zh.md` |
| `WriterLab-v1/docs/refactor-plan-zh.md` | `docs/architecture/refactor-plan-zh.md` |
| `ARCHITECTURE.md`（根） | `docs/ARCHITECTURE.md` |
| `TASKS.md`（根） | `docs/TASKS.md` |
| `PROGRESS.md`（根） | `docs/PROGRESS.md` |
| `RESEARCH.md`（根） | `docs/RESEARCH.md` |

## venv 路径

| 阶段 | venv 位置 |
|------|-----------|
| T-8 前 | `WriterLab-v1/fastapi/backend/.venv/` |
| T-8 后（目标） | `apps/backend/.venv/` |

T-8 完成后用户需在 `apps/backend/` 重建 venv：
```powershell
cd D:\WritierLab\apps\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```
