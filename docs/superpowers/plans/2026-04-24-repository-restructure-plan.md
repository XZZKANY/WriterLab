# WritierLab 仓库结构标准化重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把当前挂在 `WriterLab-v1/` 下的应用、文档、脚本与验证入口上提为标准仓库结构，形成以 `apps / docs / scripts` 为主的单一主入口，同时不改变现有业务功能语义。

**Architecture:** 继续复用现有前后端资产与脚本入口，只做仓库治理层重构。目录迁移顺序固定为：先建新骨架，再迁 `backend / frontend`，再迁 `scripts`，再重写仓库级文档，之后做全量旧路径修复，最后删除旧 `WriterLab-v1/` 壳层并完成总验证。隐藏运行支持目录也要显式处理：`.venv` 应收敛到仓库根，`.pytest_cache`、`.codex-run` 这类可再生目录不应继续把旧壳层变成运行锚点。

**Tech Stack:** FastAPI、SQLAlchemy、pytest、Next.js 16、React 19、TypeScript、PowerShell、Node.js、Python、Markdown

---

## 范围与 Gate

### 本计划覆盖

- `WriterLab-v1/fastapi/backend`
- `WriterLab-v1/Next.js/frontend`
- `WriterLab-v1/scripts/*`
- `WriterLab-v1/docs/*`
- `WriterLab-v1/readme.md`
- `WriterLab-v1/.venv`
- `WriterLab-v1/.codex-run`
- `README.md`
- `docs/superpowers/*`
- `.codex/*`

### 本计划不覆盖

- 后端 router/service/repository 的业务语义重写
- 前端页面、状态管理与交互逻辑重构
- 新增 `packages/`、workspace manager、统一构建器或 CI 体系
- workflow、timeline、branch、runtime 等业务功能扩张
- 与仓库结构统一无直接关系的美化或技术债清理

### Gate 决策

- 采用破坏式收口，不保留长期双入口兼容层。
- `WriterLab-v1/` 只允许在迁移说明或历史留痕中保留，不再作为主运行路径。
- 业务代码不做语义性修改；如因目录移动导致路径失效，只做最小适配。
- 脚本路径修复必须作为独立任务执行，不能零散混在搬目录步骤里。
- 根 `.venv` 为目标运行环境位置；旧壳层中的 `.pytest_cache`、`.codex-run` 属于可再生目录，可在新结构稳定后清理并按新路径重建。

## 文件职责

- `WriterLab-v1/fastapi/backend`
  - 旧后端目录来源，迁移后归入 `apps/backend`。
- `WriterLab-v1/Next.js/frontend`
  - 旧前端目录来源，迁移后归入 `apps/frontend`。
- `WriterLab-v1/scripts/*`
  - 旧脚本来源，迁移后按 `dev / check / smoke / data / logs` 分层。
- `WriterLab-v1/docs/*`
  - 旧运行手册、本地验证说明与测试索引来源，迁移后重组进仓库级 `docs/`。
- `WriterLab-v1/.venv`
  - 当前后端命令依赖的环境目录，应归一到仓库根 `.venv`。
- `README.md`
  - 仓库总入口，重构后只承担导航职责。
- `docs/architecture/repository-layout.md`
  - 新仓库结构说明与旧 → 新路径映射。
- `docs/project/overview.md`
  - 项目定位、模块组成与能力概览。
- `docs/runbooks/runtime-runbook.md`
  - 启动顺序、运行说明、self-check、smoke matrix 与故障解释。
- `docs/verification/local-verification.md`
  - 本地检查顺序、关键命令与报告位置。
- `docs/verification/backend-tests-index.md`
  - 后端测试入口与薄入口策略。
- `docs/verification/frontend-tests-index.md`
  - 前端验证入口与 smoke 说明。
- `scripts/dev/*`
  - 启动、开发与安装相关脚本。
- `scripts/check/*`
  - 仓库级检查入口脚本。
- `scripts/smoke/*`
  - backend/full smoke 与 frontend/live smoke 脚本。
- `scripts/data/*`
  - 数据修复和一次性维护脚本。
- `scripts/logs/`
  - smoke 与检查报告统一输出目录。
- `.codex/operations-log.md`
  - 记录实施顺序、命令、验证结果与迁移决策。
- `.codex/verification-report.md`
  - 记录本轮 plan 审查与实施后的总审查结论。

### Task 1: 建立标准仓库骨架目录

**Files:**
- Create: `apps/`
- Create: `docs/architecture/`
- Create: `docs/project/`
- Create: `docs/runbooks/`
- Create: `docs/verification/`
- Create: `scripts/dev/`
- Create: `scripts/check/`
- Create: `scripts/smoke/`
- Create: `scripts/data/`
- Create: `scripts/logs/`
- Modify: `.codex/operations-log.md`

- [ ] **Step 1: 创建目标目录骨架**

```powershell
New-Item -ItemType Directory -Force D:\WritierLab\apps,D:\WritierLab\docs\architecture,D:\WritierLab\docs\project,D:\WritierLab\docs\runbooks,D:\WritierLab\docs\verification,D:\WritierLab\scripts\dev,D:\WritierLab\scripts\check,D:\WritierLab\scripts\smoke,D:\WritierLab\scripts\data,D:\WritierLab\scripts\logs
```

- [ ] **Step 2: 核对骨架目录全部存在**

```powershell
Get-ChildItem D:\WritierLab\apps
Get-ChildItem D:\WritierLab\docs
Get-ChildItem D:\WritierLab\scripts
```

- [ ] **Step 3: 记录骨架已就位，但暂不迁移真实应用内容**

```markdown
## 2026-04-24 仓库结构重构实施
- Task 1：标准骨架目录已建立
```

- [ ] **Step 4: 确认旧 `WriterLab-v1/` 尚未删除**

Expected: `WriterLab-v1/` 仍存在，后续任务才能从中迁移真实内容。

### Task 2: 迁移应用目录与隐藏运行支持目录

**Files:**
- Move: `WriterLab-v1/fastapi/backend` → `apps/backend`
- Move: `WriterLab-v1/Next.js/frontend` → `apps/frontend`
- Move: `WriterLab-v1/.venv` → `.venv`
- Reference: `WriterLab-v1/Next.js/frontend/package.json`
- Reference: `WriterLab-v1/fastapi/backend/requirements.txt`
- Modify: `.codex/operations-log.md`

- [ ] **Step 1: 迁移后端与前端应用目录**

```powershell
Move-Item -LiteralPath D:\WritierLab\WriterLab-v1\fastapi\backend -Destination D:\WritierLab\apps\backend
Move-Item -LiteralPath D:\WritierLab\WriterLab-v1\Next.js\frontend -Destination D:\WritierLab\apps\frontend
```

- [ ] **Step 2: 将旧环境目录规范到仓库根**

```powershell
Move-Item -LiteralPath D:\WritierLab\WriterLab-v1\.venv -Destination D:\WritierLab\.venv
```

- [ ] **Step 3: 确认关键配置文件在新位置可读**

```powershell
Get-Content D:\WritierLab\apps\frontend\package.json
Get-Content D:\WritierLab\apps\backend\requirements.txt
```

- [ ] **Step 4: 记录可再生目录处理策略**

Expected:
- `WriterLab-v1/.pytest_cache`、`WriterLab-v1/.codex-run` 不再作为结构阻塞项
- 必要时在最终清理阶段删除并按新结构重建

- [ ] **Step 5: 记录应用迁移完成**

```markdown
- Task 2：`apps/backend`、`apps/frontend` 与根 `.venv` 已就位
```

### Task 3: 迁移并分层 scripts 目录

**Files:**
- Move: `WriterLab-v1/scripts/start-backend.ps1` → `scripts/dev/start-backend.ps1`
- Move: `WriterLab-v1/scripts/start-frontend.ps1` → `scripts/dev/start-frontend.ps1`
- Move: `WriterLab-v1/scripts/dev-stack.ps1` → `scripts/dev/dev-stack.ps1`
- Move: `WriterLab-v1/scripts/install-backend.ps1` → `scripts/dev/install-backend.ps1`
- Move: `WriterLab-v1/scripts/check-backend.ps1` → `scripts/check/check-backend.ps1`
- Move: `WriterLab-v1/scripts/check-frontend.ps1` → `scripts/check/check-frontend.ps1`
- Move: `WriterLab-v1/scripts/backend_full_smoke.py` → `scripts/smoke/backend_full_smoke.py`
- Move: `WriterLab-v1/scripts/frontend_live_smoke.mjs` → `scripts/smoke/frontend_live_smoke.mjs`
- Move: `WriterLab-v1/scripts/fix_demo_garbled_data.py` → `scripts/data/fix_demo_garbled_data.py`
- Move: `WriterLab-v1/scripts/logs/*` → `scripts/logs/`
- Modify: `scripts/dev/*.ps1`
- Modify: `scripts/check/*.ps1`
- Modify: `scripts/smoke/*`
- Modify: `.codex/operations-log.md`

- [ ] **Step 1: 按职责迁移脚本文件**

Expected:
- 启动/安装脚本进入 `scripts/dev`
- 检查脚本进入 `scripts/check`
- smoke 脚本进入 `scripts/smoke`
- 数据修复脚本进入 `scripts/data`
- 报告目录进入 `scripts/logs`

- [ ] **Step 2: 修复脚本内部旧路径**

```pseudocode
for each script in scripts/dev + scripts/check + scripts/smoke:
    replace WriterLab-v1/fastapi/backend with apps/backend
    replace WriterLab-v1/Next.js/frontend with apps/frontend
    replace WriterLab-v1/.venv with .venv
    replace WriterLab-v1/scripts/logs with scripts/logs
    where possible, compute repo root from script location instead of hardcoding full old path
```

- [ ] **Step 3: 确认关键脚本入口存在**

```powershell
Get-ChildItem D:\WritierLab\scripts\dev
Get-ChildItem D:\WritierLab\scripts\check
Get-ChildItem D:\WritierLab\scripts\smoke
Get-ChildItem D:\WritierLab\scripts\data
```

- [ ] **Step 4: 做路径级检查**

```powershell
Select-String -Path D:\WritierLab\scripts\**\* -Pattern 'WriterLab-v1' -SimpleMatch
```

Expected: 若还有命中，必须是迁移说明、注释或明确的历史说明，而不是脚本主运行路径。

- [ ] **Step 5: 记录脚本层迁移完成**

```markdown
- Task 3：scripts 已按职责分层，入口路径改为新结构
```

### Task 4: 重写仓库级文档体系

**Files:**
- Modify: `README.md`
- Create: `docs/architecture/repository-layout.md`
- Create: `docs/project/overview.md`
- Create: `docs/runbooks/runtime-runbook.md`
- Create: `docs/verification/local-verification.md`
- Create: `docs/verification/backend-tests-index.md`
- Create: `docs/verification/frontend-tests-index.md`
- Reference: `WriterLab-v1/readme.md`
- Reference: `WriterLab-v1/docs/local-verification-zh.md`
- Reference: `WriterLab-v1/docs/runtime-notes.md`
- Reference: `WriterLab-v1/fastapi/backend/tests/README.md`
- Reference: `WriterLab-v1/Next.js/frontend/tests/README.md`
- Modify: `.codex/operations-log.md`

- [ ] **Step 1: 重写根 README 为仓库总导航**

Expected:
- 只保留项目定位、结构导航、快速启动、验证入口与关键文档链接
- 不再复制 runbook 或 tests index 的大段内容

- [ ] **Step 2: 写结构说明文档**

`docs/architecture/repository-layout.md` 至少包含：
- 目标拓扑
- 目录职责
- 旧 → 新路径映射
- 不保留双入口的说明

- [ ] **Step 3: 写项目总览与运行文档**

Expected:
- `docs/project/overview.md` 承接项目定位与模块组成
- `docs/runbooks/runtime-runbook.md` 承接启动顺序、self-check、smoke matrix 与故障解释

- [ ] **Step 4: 写验证文档与测试索引**

Expected:
- `docs/verification/local-verification.md` 承接本地检查顺序、关键命令与报告位置
- `docs/verification/backend-tests-index.md` 与 `frontend-tests-index.md` 分别承接测试入口说明

- [ ] **Step 5: 记录文档体系已统一**

```markdown
- Task 4：根 README 与 docs 四层职责已重写完成
```

### Task 5: 全量修复旧路径与命令引用

**Files:**
- Modify: `README.md`
- Modify: `docs/**/*`
- Modify: `scripts/**/*`
- Modify: `apps/**/*` 中的说明性文本与脚本引用
- Modify: `.codex/operations-log.md`

- [ ] **Step 1: 全仓搜索旧路径引用**

```powershell
Get-ChildItem D:\WritierLab -Recurse -File | Select-String -Pattern 'WriterLab-v1' -SimpleMatch
```

- [ ] **Step 2: 按类型分类处理命中**

```pseudocode
if hit is runtime script or command:
    replace with apps/docs/scripts path
elif hit is migration document:
    keep as old->new mapping evidence
elif hit is historical spec or .codex note:
    keep only if it describes history, not current runtime
else:
    rewrite to new main path
```

- [ ] **Step 3: 统一关键命令表达**

目标命令应至少统一为：

```powershell
powershell -ExecutionPolicy Bypass -File D:\WritierLab\scripts\dev\start-backend.ps1
powershell -ExecutionPolicy Bypass -File D:\WritierLab\scripts\dev\start-frontend.ps1
powershell -ExecutionPolicy Bypass -File D:\WritierLab\scripts\check\check-backend.ps1
powershell -ExecutionPolicy Bypass -File D:\WritierLab\scripts\check\check-frontend.ps1
Set-Location D:\WritierLab\apps\frontend; npm.cmd run typecheck
D:\WritierLab\.venv\Scripts\python.exe -m pytest D:\WritierLab\apps\backend\tests\test_api_routes.py D:\WritierLab\apps\backend\tests\test_workflow_service.py
```

- [ ] **Step 4: 复查旧路径搜索结果**

Expected:
- 不再把 `WriterLab-v1/` 作为主运行路径
- 剩余命中只在迁移说明、历史 spec 或 `.codex` 历史留痕中存在

- [ ] **Step 5: 记录路径修复完成**

```markdown
- Task 5：主运行路径和命令表达已全部切换到新结构
```

### Task 6: 删除旧壳并完成总验证与留痕

**Files:**
- Delete/Archive: `WriterLab-v1/` 剩余主入口内容
- Modify: `.codex/operations-log.md`
- Modify: `.codex/verification-report.md`
- Modify: `docs/superpowers/specs/2026-04-24-repository-restructure-design.md`
- Modify: `docs/superpowers/plans/2026-04-24-repository-restructure-plan.md`

- [ ] **Step 1: 确认旧壳只剩历史残留**

Expected:
- `backend`、`frontend`、`scripts`、`docs` 主内容已迁出
- `WriterLab-v1/` 不再承载真实主入口

- [ ] **Step 2: 清理旧壳层**

```pseudocode
remove remaining WriterLab-v1 runtime role
keep only migration evidence elsewhere
clear disposable caches under old shell if still present
```

- [ ] **Step 3: 运行总验证**

Run: `Get-ChildItem D:\WritierLab\apps`
Expected: `backend` 与 `frontend` 存在

Run: `Get-ChildItem D:\WritierLab\docs`
Expected: `architecture`、`project`、`runbooks`、`verification` 存在

Run: `Get-ChildItem D:\WritierLab\scripts`
Expected: `dev`、`check`、`smoke`、`data`、`logs` 存在

Run: `Set-Location D:\WritierLab\apps\frontend; npm.cmd run typecheck`
Expected: PASS

Run: `D:\WritierLab\.venv\Scripts\python.exe -m pytest D:\WritierLab\apps\backend\tests\test_api_routes.py D:\WritierLab\apps\backend\tests\test_workflow_service.py -q`
Expected: PASS

Run: `powershell -ExecutionPolicy Bypass -File D:\WritierLab\scripts\check\check-backend.ps1`
Expected: PASS 或只暴露文档已记录的环境 caveat

Run: `powershell -ExecutionPolicy Bypass -File D:\WritierLab\scripts\check\check-frontend.ps1`
Expected: PASS 或只暴露文档已记录的环境 caveat

- [ ] **Step 4: 回填留痕与审查结果**

Expected:
- `.codex/operations-log.md` 记录实施顺序、关键命令与异常说明
- `.codex/verification-report.md` 记录本轮总审查评分
- 本 plan 在末尾回填执行结果

- [ ] **Step 5: 完成最终提交**

```bash
git add -A
git commit -m "完成仓库结构标准化重构"
```

## 完成标准

- 仓库主结构以 `apps / docs / scripts` 为唯一主入口
- `apps/backend`、`apps/frontend` 已承接原应用内容
- 根 `.venv` 成为统一运行环境位置，旧壳层不再承载运行环境锚点
- `scripts/dev`、`scripts/check`、`scripts/smoke`、`scripts/data`、`scripts/logs` 职责清晰
- 根 `README.md` 与 `docs/*` 文档职责清晰，导航成立
- 仓库中不再把 `WriterLab-v1/` 当作主运行路径引用
- `.codex`、spec、plan 与 verification 留痕完整

## 2026-04-24 实施回填

- [ ] Task 1：标准骨架目录已建立
- [ ] Task 2：应用目录与根 `.venv` 已迁移
- [ ] Task 3：scripts 已分层并修复内部路径
- [ ] Task 4：仓库级文档体系已重写
- [ ] Task 5：旧路径与命令引用已清理
- [ ] Task 6：旧壳已删除，总验证与留痕完成

## 执行交接

- 推荐执行方式：`superpowers:subagent-driven-development`
- 备选执行方式：`superpowers:executing-plans`
- 执行时必须保持任务顺序，不允许跳过脚本路径修复或旧路径复查
- 每个 Task 完成后立即更新 `.codex/operations-log.md`
- 若验证命令因环境限制失败，必须记录失败类型、是否属于既有 caveat、补偿验证方式和最终结论
