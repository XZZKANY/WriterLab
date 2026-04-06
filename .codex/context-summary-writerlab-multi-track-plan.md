# 项目上下文摘要（WriterLab 多轨并行计划）

生成时间：2026-04-06

## 1. 目标

为 WriterLab 生成一份项目级中期工程蓝图，支持后续多个 Subagent 按技术层并行开发。

## 2. 现有实现模式

### 实现 1：前端路由页薄入口

- 文件：`D:/WritierLab/WriterLab-v1/Next.js/frontend/app/editor/page.tsx`
- 事实：
  - 路由页只装配 `EditorWorkspace`
- 模式：
  - 薄路由入口 + feature 组件承接复杂 UI
- 规划启示：
  - 后续前端页面继续保持 `page.tsx` 轻量，不把复杂状态回灌到路由层

### 实现 2：前端复杂工作台的 hooks 分域

- 文件：
  - `D:/WritierLab/WriterLab-v1/Next.js/frontend/features/editor/editor-workspace.tsx`
  - `D:/WritierLab/WriterLab-v1/Next.js/frontend/features/editor/hooks/use-authoring-workspace.ts`
  - `D:/WritierLab/WriterLab-v1/Next.js/frontend/features/editor/hooks/use-scene-context.ts`
  - `D:/WritierLab/WriterLab-v1/Next.js/frontend/features/editor/hooks/use-versioning-workspace.ts`
- 事实：
  - 编辑器工作台已从大容器收缩为装配层，状态拆到多个 hook
- 模式：
  - 装配层负责组合，子域 hook 负责局部状态与动作
- 规划启示：
  - 新的复杂前端能力应延续按子域拆分的模式

### 实现 3：后端 router + repository 分层

- 文件：
  - `D:/WritierLab/WriterLab-v1/fastapi/backend/app/main.py`
  - `D:/WritierLab/WriterLab-v1/fastapi/backend/app/repositories/project_repository.py`
- 事实：
  - `main.py` 负责应用装配和 router 注册
  - `project_repository.py` 使用函数式仓储辅助函数实现级联清理
- 模式：
  - FastAPI 路由模块化 + repository 函数式数据访问
- 规划启示：
  - 后端数据域计划必须沿用该边界，不新增平行抽象体系

### 实现 4：前后端测试组织

- 文件：
  - `D:/WritierLab/WriterLab-v1/Next.js/frontend/tests/features/editor-workspace-structure.test.mjs`
  - `D:/WritierLab/WriterLab-v1/fastapi/backend/tests/README.md`
  - `D:/WritierLab/WriterLab-v1/fastapi/backend/tests/test_api_routes.py`
- 事实：
  - 前端使用 `node:test` 做结构契约测试
  - 后端使用根层薄入口 + suite 迁移模式
- 模式：
  - 结构契约优先，分类 suite 扩展
- 规划启示：
  - 测试轨道适合先锁契约，再跟阶段推进

## 3. 已有文档与近期主线

### 既有设计/计划文档

- `D:/WritierLab/docs/superpowers/specs/2026-04-04-editor-workspace-refactor-design.md`
- `D:/WritierLab/docs/superpowers/plans/2026-04-04-editor-workspace-refactor-plan.md`

### 最近提交主线

来自最近 8 条提交的事实：

- `1795214 重构编辑器工作台并补齐前端验证`
- `0a93c96 feat: move runtime diagnostics into dedicated workbench`
- `22e3a2a test: lock editor workspace authoring-only contract`
- `9209591 新增编辑器工作台重构设计文档`

结论：

- 最近工作集中在前端编辑器工作台、runtime 诊断独立化和本地验证收口
- 当前新的项目级计划不应重复写前端专项计划，而应提升到后端牵引的中期蓝图层

## 4. 技术栈与官方依据

### Next.js

- 依据：Context7 `/vercel/next.js/v16.2.2`
- 事实：
  - App Router 使用文件系统路由
  - `page.tsx` 是路由入口
  - 复杂迁移应分阶段推进
- 推论：
  - 前端计划适合让 `app/*/page.tsx` 继续保持轻量，复杂逻辑放进 feature 目录

### FastAPI

- 依据：Context7 `/fastapi/fastapi/0.128.0`
- 事实：
  - 官方推荐使用 `TestClient` 做本地测试
  - 更大应用建议用 `APIRouter` 按模块拆分
- 推论：
  - 后端计划应继续以 router 分域和本地 pytest 验证为主

## 5. 阶段拆分依据

用户已确认的设计选择：

- 计划类型：多 Subagent 并行开发计划
- 拆分主轴：按技术层拆分
- 时间尺度：中期蓝图
- 第一优先级：后端
- 后端主轴：项目 / 场景 / 资料核心数据域

## 6. 建议的多轨结构

- 主线：后端核心数据域演进
- 轨道 A：后端数据域
- 轨道 B：前端接入与工作台收口
- 轨道 C：测试与验证基建
- 轨道 D：文档与运维留痕

## 7. 关键依赖与风险

### 依赖

- 前端依赖后端冻结后的接口与错误语义
- 测试轨依赖各阶段的目标契约
- 文档轨依赖每轮实际变更和验证结果

### 风险

- 前端在接口不稳时提前接线，导致返工
- 后端级联删除和跨实体逻辑继续扩张，放大数据一致性风险
- 多个 Subagent 同时修改同一片文件，导致冲突和覆盖
- 验证轨道滞后，无法提供阶段门槛

## 8. 后续行动

- 先让用户复核 `docs/superpowers/specs/2026-04-06-writerlab-multi-track-backend-first-design.md`
- 用户确认后，再进入 implementation plan
- implementation plan 需要把四阶段拆成可并行执行的原子任务，并标注 Gate 与文件所有权
