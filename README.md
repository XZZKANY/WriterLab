# WritierLab

WritierLab 是一个面向长篇小说创作的混合式 AI 写作工作台仓库。当前主应用位于 `WriterLab-v1/`，由 FastAPI 后端、Next.js 前端、PostgreSQL + pgvector 检索层，以及本地 / 云端模型路由能力共同组成。

## 项目定位

这个仓库当前重点解决的是“场景级写作工作流”问题，而不是通用办公型写作工具。它更像一个为长篇叙事创作准备的工作台，覆盖：

- 项目、书、章节、场景的基础创作对象管理
- 角色、地点、世界观、知识文档与风格记忆的上下文组织
- 场景分析、写作、润色、规划、审查等多阶段 AI 工作流
- 一致性扫描、分支对比与版本恢复
- VN 结构化导出预览
- 本地 Ollama 与云端 Provider 的混合模型调用

## 仓库结构

```text
WritierLab/
├─ README.md
├─ AGENTS.md
├─ WriterLab-v1/
│  ├─ readme.md
│  ├─ docs/
│  ├─ fastapi/backend/
│  ├─ Next.js/frontend/
│  └─ scripts/
├─ pgvector-src/
└─ .codex/
```

关键目录说明：

- `WriterLab-v1/`：主应用工作区
- `WriterLab-v1/fastapi/backend/`：FastAPI 后端、数据模型、服务层与 pytest 测试
- `WriterLab-v1/Next.js/frontend/`：Next.js 16 前端工作台
- `WriterLab-v1/docs/`：项目盘点、验证说明、运行手册等深度文档
- `WriterLab-v1/scripts/`：启动、检查与 smoke 脚本
- `pgvector-src/`：本地保留的 pgvector 相关源码与构建产物
- `.codex/`：仓库本地的上下文摘要、操作记录和验证报告

## 技术栈

- 前端：Next.js 16、React 19、TypeScript、Tailwind CSS 4
- 后端：FastAPI、Uvicorn、Pydantic、Starlette
- 数据层：PostgreSQL 16、pgvector
- 模型接入：Ollama、本地 / 云端 Provider 混合路由
- 验证方式：pytest、TypeScript typecheck、前后端检查脚本、live smoke

## 当前能力概览

- 管理项目、书、章节、场景等核心创作对象
- 构建场景上下文，聚合角色、地点、时间线、知识命中和风格记忆
- 执行完整场景工作流，包括分析、规划、写作、润色与一致性检查
- 记录场景版本，支持剧情分支、差异查看和采纳
- 暴露运行时健康检查、自检、Provider 状态与 smoke 报告接口
- 提供前端工作台，用于编辑、调试和观察运行时状态

## 快速启动

建议先使用现有脚本，再手工启动单个模块。

### 1. 启动后端

```powershell
powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\start-backend.ps1
```

如果只想直接运行 Uvicorn，也可以使用：

```powershell
& 'D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir 'D:\WritierLab\WriterLab-v1\fastapi\backend'
```

### 2. 启动前端

```powershell
powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\start-frontend.ps1
```

如果只想进入前端目录直接起开发服务：

```powershell
Set-Location 'D:\WritierLab\WriterLab-v1\Next.js\frontend'
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

### 3. 打开本地页面

- 后端根路径：<http://127.0.0.1:8000/>
- 后端健康检查：<http://127.0.0.1:8000/api/health>
- 前端编辑台：<http://127.0.0.1:3000/editor>

## 本地验证

推荐把验证拆成前端、后端两部分执行。

### 前端

```powershell
cd D:\WritierLab\WriterLab-v1\Next.js\frontend
npm.cmd run typecheck
```

```powershell
powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1
```

### 后端

```powershell
D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_api_routes.py D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_workflow_service.py
```

```powershell
powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\check-backend.ps1
```

完整说明见下方“关键文档”中的本地验证文档。

## 关键文档

- `WriterLab-v1/readme.md`
  - 子工作区入口，适合快速理解应用由哪些模块组成
- `WriterLab-v1/docs/project-overview-zh.md`
  - 当前最完整的中文项目盘点，包含模块能力、数据模型和 API 总览
- `WriterLab-v1/docs/local-verification-zh.md`
  - 前后端验证顺序、smoke 覆盖范围和报告位置
- `WriterLab-v1/docs/runtime-notes.md`
  - 启动顺序、运行时 smoke、故障解释和环境 caveat
- `WriterLab-v1/fastapi/backend/tests/README.md`
  - 后端 pytest 入口说明
- `WriterLab-v1/Next.js/frontend/tests/README.md`
  - 前端测试与 smoke 目录说明

## 已知说明

- 当前主应用仍集中在 `WriterLab-v1/`，根目录更偏仓库容器与入口层。
- 前端当前定位更接近“工作台 / 调试台”，不是完全收口的最终用户产品。
- Windows 受限 shell 下，Next.js 构建可能触发 `spawn EPERM`；现有脚本已经把它视为环境 caveat，而不是直接判定业务回归。
- 更细的运行时行为、Smoke 报告和 Provider 状态说明，请优先查看 `WriterLab-v1/docs/runtime-notes.md`。
