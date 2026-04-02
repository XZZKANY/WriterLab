# WriterLab 重构迁移映射

## 前端

- `Next.js/frontend/app/editor/page.tsx` → `Next.js/frontend/features/editor/editor-workspace.tsx`
  - 新的 `app/editor/page.tsx` 只保留路由装配职责。
- `Next.js/frontend/app/project/page.tsx` → `Next.js/frontend/features/project/project-hub.tsx`
- `Next.js/frontend/app/project/[projectId]/page.tsx` → `Next.js/frontend/features/project/project-detail.tsx`
- `Next.js/frontend/app/lore/page.tsx` → `Next.js/frontend/features/lore/lore-hub.tsx`
- `Next.js/frontend/app/lore/{characters,locations,entries}/page.tsx` → `Next.js/frontend/features/lore/lore-library-page.tsx`
- `Next.js/frontend/app/runtime/page.tsx` → `Next.js/frontend/features/runtime/runtime-hub.tsx`
- `Next.js/frontend/app/settings/page.tsx` → `Next.js/frontend/features/settings/settings-hub.tsx`
- 页面内散落请求 → `Next.js/frontend/lib/api/{client,projects,lore,scenes,workflow,runtime,settings}.ts`

## 后端

- `fastapi/backend/app/main.py`
  - 启动流程迁出到 `fastapi/backend/app/tasks/startup_checks.py`
  - 路由装配改为从 `fastapi/backend/app/api/routers/*` 聚合
- `fastapi/backend/app/api/*.py`
  - 聚合入口新增到 `fastapi/backend/app/api/routers/{project,story,lore,workflow,runtime,settings,health}.py`
  - 旧路由文件暂时保留，作为兼容层和真实协议实现
- `fastapi/backend/app/db/schema_upgrades.py`
  - 兼容出口新增为 `fastapi/backend/app/tasks/schema_upgrades.py`
- 核心服务旧路径保留：
  - `services/workflow_service.py`
  - `services/ai_gateway_service.py`
  - `services/context_service.py`
  - `services/knowledge_service.py`
  - `services/consistency_service.py`
  - `services/smoke_report_service.py`
- 核心服务新分层兼容出口新增：
  - `services/workflow/*`
  - `services/ai/*`
  - `services/context/*`
  - `services/knowledge/*`
  - `services/consistency/*`
  - `services/runtime/*`

## 最小回滚单元

- 前端：单个 `features/*` 目录或单个 `lib/api/*` 模块
- 后端：单个 `api/routers/*` 聚合模块或单个 `tasks/*` 启动模块
- 文档与测试骨架：单文件独立回滚

---

## 第四轮补充映射（测试、脚本与文档收口）

### 测试分组策略

- 后端继续保留根层 `fastapi/backend/tests/test_*.py` 作为 pytest 直接入口。
- 后端新增说明骨架目录：
  - `fastapi/backend/tests/api/README.md`
  - `fastapi/backend/tests/services/README.md`
  - `fastapi/backend/tests/runtime/README.md`
- 前端新增说明骨架目录：
  - `Next.js/frontend/tests/features/README.md`
  - `Next.js/frontend/tests/smoke/README.md`
- 当前策略是不在第四轮直接搬迁真实测试文件，避免 pytest 全量收集重复和脚本入口回退；后续新增测试可直接落到对应分类目录。

### 脚本入口收口

- `scripts/check-frontend.ps1`
  - `-LiveUiSmoke` 现在调用站点根地址，而不是只检查 `/editor`
- `scripts/frontend_live_smoke.mjs`
  - 从单路由 smoke 升级为多路由矩阵 smoke
  - 当前覆盖：`/editor`、`/project`、`/lore`、`/runtime`、`/settings`
- `scripts/check-backend.ps1`
  - 继续作为后端导入、数据库、Alembic、runtime self-check 的统一体检入口

### 最小回滚单元

- 测试说明骨架：单个 `README.md`
- 前端 smoke 收口：`scripts/frontend_live_smoke.mjs` 与 `scripts/check-frontend.ps1`
- 第四轮留痕：`.codex/context-summary-refactor-plan-round4.md`、`.codex/operations-log.md`、`.codex/verification-report.md`
