## 项目上下文摘要（phase-4-kickoff）

生成时间：2026-04-09 19:08:00

### 1. 相似实现与现状证据

- **总蓝图定义**: `docs/superpowers/specs/2026-04-06-writerlab-multi-track-backend-first-design.md`
  - phase-4 目标是在稳定数据域之上接入 `workflow / context / runtime` 能力
  - 后端重点：workflow 消费与回写、context compiler 输入边界、一致性扫描与 runtime 自检集成点
  - 前端重点：工作流结果消费、一致性与上下文展示、runtime 工作台继续收口

- **workflow 聚合入口**: `WriterLab-v1/fastapi/backend/app/api/routers/workflow.py`
  - 当前 `workflow` 路由是聚合层，复用 `ai / knowledge / consistency` 三组 router
  - 说明 phase-4 不应新建平行总入口，而应沿用现有聚合边界

- **workflow 运行主链路**: `WriterLab-v1/fastapi/backend/app/services/workflow/workflow_service.py:528-620, 836-905`
  - `_run_scene_workflow()` 在工作流开始阶段直接调用 `build_scene_context()` 并把 `context_compile_snapshot` 回写到 run
  - `queue_scene_workflow()`、`execute_scene_workflow()`、`resume_workflow_run()`、`override_workflow_step()` 已形成可恢复、可重试、可人工覆写的运行态主链路
  - 说明 phase-4 的真实重点不是“从零做 workflow”，而是收口已有运行主链路与上下文/运行时的联动契约

- **context compiler 现状**: `WriterLab-v1/fastapi/backend/app/services/context/context_service.py:1-404`
  - `build_scene_context()` 已收集 `lore / timeline / style_memory / recent_scene / knowledge_hits`
  - 已产出 `ContextCompileSnapshot`，包含 `hard_filters`、`scope_resolution`、`budget`、`candidates`、`deduped_sources`、`summary_output`
  - 当前 context 已被 workflow 主链路消费，说明它不是独立实验模块，而是 phase-4 的核心数据输入层

- **runtime 前端工作台**: `WriterLab-v1/Next.js/frontend/features/runtime/runtime-debug-workbench.tsx`
  - 当前已集中承接 `Workflow Debug / Provider Runtime / Smoke Console / Provider Matrix / Context Compiler`
  - 通过 `useRuntimeDiagnostics()` 与 `lib/api/workflow.ts`、`lib/api/runtime.ts` 连接后端
  - 说明 phase-4 前端不应回退到 editor 内混挂 diagnostics，而应继续复用独立 runtime 工作台

- **editor 侧上下文消费**: `WriterLab-v1/Next.js/frontend/features/editor/hooks/use-scene-context.ts`
  - 已维护 `timeline / memories / knowledgeHits / recentScenes / contextSnapshot / issues`
  - `applySceneContext()` 与 `applyConsistencyResult()` 已把 context 与 consistency 消费收敛在 hook 内
  - 说明 phase-4 可以优先沿用这个 hook 边界，而不是在页面层重新散落上下文状态

- **运行手册与验证出口**: `WriterLab-v1/docs/runtime-notes.md`
  - 已定义 `/api/health`、`/api/runtime/self-check`、`/api/runtime/provider-state`、smoke reports 与 live smoke matrix
  - 说明 phase-4 已有运行与验证基座，下一轮应优先复用这些命令，而不是自造新验证通道

### 2. 项目约定

- **后端分层**: `router + service + repository + schema + model`
- **前端分层**: `lib/api/* + features/* + app/*`，页面保持薄路由入口
- **验证方式**: 后端 `pytest`；前端 `node:test` 结构契约 + `npm.cmd run typecheck`
- **phase-4 推进策略**: 优先收口既有 workflow/context/runtime 契约，不重做 UI 壳层和 editor 主工作台

### 3. 可复用组件清单

- `WriterLab-v1/fastapi/backend/app/services/workflow/workflow_service.py`
- `WriterLab-v1/fastapi/backend/app/services/context/context_service.py`
- `WriterLab-v1/Next.js/frontend/features/runtime/runtime-debug-workbench.tsx`
- `WriterLab-v1/Next.js/frontend/features/runtime/hooks/use-runtime-diagnostics.ts`
- `WriterLab-v1/Next.js/frontend/features/editor/hooks/use-scene-context.ts`
- `WriterLab-v1/Next.js/frontend/lib/api/workflow.ts`
- `WriterLab-v1/Next.js/frontend/lib/api/runtime.ts`
- `WriterLab-v1/docs/runtime-notes.md`
- `WriterLab-v1/fastapi/backend/tests/test_workflow_service.py`
- `WriterLab-v1/fastapi/backend/tests/test_context_service.py`
- `WriterLab-v1/Next.js/frontend/tests/features/runtime-debug-workbench.test.mjs`

### 4. 关键结论

- workflow、context、runtime 三块都已经存在真实实现，phase-4 不是从零搭骨架，而是把三者联动面收口为稳定契约
- 后端真实关键路径是：`build_scene_context()` → `workflow_service._run_scene_workflow()` → runtime/self-check/provider-state
- 前端真实关键路径是：`use-scene-context()` 消费上下文结果，`runtime-debug-workbench.tsx` 承接运行态诊断
- 推荐 phase-4 第一轮顺序：
  1. 先锁 workflow/context/runtime 的后端回归契约
  2. 再锁 editor 与 runtime 工作台的前端消费契约
  3. 最后写 phase-4 设计文档与 implementation plan
