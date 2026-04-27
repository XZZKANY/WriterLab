# WritierLab

面向长篇小说创作的混合式 AI 写作工作台。FastAPI 后端 + Next.js 前端 + PostgreSQL/pgvector，支持本地 Ollama 与云端模型混合路由。

## 仓库结构

```text
WritierLab/
├─ apps/
│  ├─ backend/          # FastAPI + SQLAlchemy + pytest
│  └─ frontend/         # Next.js 16 + React 19 + TypeScript
├─ docs/
│  ├─ architecture/     # 架构决策与布局说明
│  ├─ project/          # 项目盘点
│  ├─ runbooks/         # 运行手册
│  ├─ verification/     # 本地验证说明
│  ├─ superpowers/      # 设计 spec / plan
│  ├─ ARCHITECTURE.md
│  ├─ TASKS.md
│  ├─ PROGRESS.md
│  └─ RESEARCH.md
├─ scripts/
│  ├─ dev/              # 启动脚本（start-backend / start-frontend / dev-stack / install-backend）
│  ├─ check/            # 验证脚本（check-backend / check-frontend）
│  ├─ smoke/            # Smoke 测试（backend_full_smoke.py / frontend_live_smoke.mjs）
│  └─ data/             # 数据工具脚本
├─ .codex/              # 上下文摘要与操作记录
├─ AGENTS.md
└─ README.md
```

## 快速启动

> **前提**：PostgreSQL 16 可访问，`.env` 已配置 `DATABASE_URL`。新机器先跑 `install-backend.ps1` 建 venv，再跑 `npm install`。

### 初始化（新机器）

```powershell
# 后端 venv + 依赖
powershell -ExecutionPolicy Bypass -File 'D:\WritierLab\scripts\dev\install-backend.ps1'

# 数据库迁移
Set-Location 'D:\WritierLab\apps\backend'
& '.\.venv\Scripts\python.exe' -m alembic upgrade head

# 前端依赖
Set-Location 'D:\WritierLab\apps\frontend'
npm install
```

### 日常启动

```powershell
# 后端（端口 8000）
powershell -ExecutionPolicy Bypass -File 'D:\WritierLab\scripts\dev\start-backend.ps1'

# 前端（端口 3000，另开终端）
powershell -ExecutionPolicy Bypass -File 'D:\WritierLab\scripts\dev\start-frontend.ps1'
```

访问：<http://127.0.0.1:3000/editor>（工作台）｜<http://127.0.0.1:8000/api/health>（健康检查）

## 本地验证

```powershell
# 后端：静态检查 + DB 连通 + Alembic state（加 -FullSmoke 跑完整 smoke）
powershell -ExecutionPolicy Bypass -File 'D:\WritierLab\scripts\check\check-backend.ps1'

# 前端：typecheck + ESLint + build（加 -LiveUiSmoke 跑 UI smoke）
powershell -ExecutionPolicy Bypass -File 'D:\WritierLab\scripts\check\check-frontend.ps1'
```

详细流程见 `docs/verification/local-verification-zh.md`。

## 关键文档

| 文档 | 用途 |
|------|------|
| `docs/usage-guide-zh.md` | **使用指南**：启动、编辑器、AI 功能、工作流、分支、Provider 设置 |
| `docs/project/project-overview-zh.md` | 模块能力、数据模型、API 总览 |
| `docs/verification/local-verification-zh.md` | 验证顺序、smoke 覆盖、报告位置 |
| `docs/runbooks/runtime-notes.md` | 启动顺序、故障说明、环境 caveat |
| `docs/architecture/repository-layout.md` | 旧 → 新路径映射表 |
| `docs/TASKS.md` | 长期任务队列 |
| `docs/PROGRESS.md` | 各轮重构完成记录 |
| `docs/ARCHITECTURE.md` | 架构拓扑与模块职责矩阵 |

## 技术栈

- 前端：Next.js 16、React 19、TypeScript、Tailwind CSS 4
- 后端：FastAPI、Uvicorn、Pydantic、SQLAlchemy
- 数据层：PostgreSQL 16、pgvector
- 模型接入：Ollama、本地/云端 Provider 混合路由
- 验证：pytest（后端）、TypeScript typecheck + ESLint（前端）
