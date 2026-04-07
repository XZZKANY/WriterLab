## 项目上下文摘要（phase-3-kickoff）

生成时间：2026-04-07 22:11:00

### 1. 相似实现与现状证据

- **蓝图定义**: `docs/superpowers/specs/2026-04-06-writerlab-multi-track-backend-first-design.md:165-190`
  - 阶段三目标是“建立时间线与版本联动”
  - 后端重点：`Timeline / SceneVersion / StoryBranch`
  - 前端重点：时间线查看、版本对比、分支基础交互

- **产品约束**: `WriterLab-v1/guidance.md:275-309, 404-428`
  - 时间线第一版不做炫酷时间轴，只做结构化事件列表
  - 版本页第一版强调 diff、恢复旧版本、满意样本
  - Timeline Event 需要 `knowledge_scope` 语义，但当前模型尚未落地该字段

- **版本已有实现**: `WriterLab-v1/fastapi/backend/app/api/scenes.py:134-158`
  - 已有版本列表与恢复接口
  - `scene_version_service.py:7-70` 已有创建、列表、恢复逻辑
  - `scene_repository.py:11-28` 已有版本查询函数

- **分支已有实现**: `WriterLab-v1/fastapi/backend/app/api/branches.py:51-109`
  - 已有创建、列表、diff、adopt 接口
  - `branch_service.py:27-146` 已有分支创建、diff、采纳逻辑
  - `test_branch_service.py:7-80` 已有最小服务测试

- **时间线现状**:
  - `fastapi/backend/app/models/timeline_event.py:11-26` 只有模型
  - `fastapi/backend/app/schemas/timeline_event.py:7-35` 只有 create/response schema
  - 未发现 timeline repository / service / router / pytest 合同 / frontend API

- **前端版本/分支已有实现**:
  - `Next.js/frontend/features/editor/hooks/use-versioning-workspace.ts:45-91`
  - `Next.js/frontend/features/editor/versions-pane.tsx:57-249`
  - `Next.js/frontend/lib/api/scenes.ts:15-40`
  - `features/editor/editor-workspace.tsx:18-37, 180-200` 已接入版本与分支 API

- **时间线已被上下文消费**:
  - `fastapi/backend/app/services/context/context_service.py:242-349`
  - 当前会查询 `TimelineEvent` 并写入 `timeline_events`，说明 timeline 数据域对 context 已有消费入口，但缺少正式维护接口

### 2. 项目约定

- **后端分层**: `router + repository + service + schema + model`
- **前端分层**: 薄路由 + feature 装配 + hooks + pane/ui
- **验证方式**: 后端 `pytest`；前端 `node:test` 结构契约 + `npm.cmd run typecheck`
- **推进策略**: 后端优先，再前端最小接线

### 3. 可复用组件清单

- `fastapi/backend/app/api/scenes.py`
- `fastapi/backend/app/services/scene_version_service.py`
- `fastapi/backend/app/api/branches.py`
- `fastapi/backend/app/services/branch_service.py`
- `Next.js/frontend/lib/api/scenes.ts`
- `Next.js/frontend/features/editor/hooks/use-versioning-workspace.ts`
- `Next.js/frontend/features/editor/versions-pane.tsx`
- `fastapi/backend/tests/test_project_scene_contracts.py`
- `fastapi/backend/tests/test_branch_service.py`

### 4. 关键结论

- `SceneVersion` 与 `StoryBranch` 不是从零开始，已经有后端与前端最小链路。
- `Timeline` 才是 phase-3 当前最大的真实缺口。
- 推荐 phase-3 第一轮先做：
  1. Timeline 最小后端合同与 pytest
  2. SceneVersion / StoryBranch 合同收口与回归测试
  3. 前端最小时间线查看接线
- 不建议一开始就做复杂时间轴 UI 或重写版本页。
