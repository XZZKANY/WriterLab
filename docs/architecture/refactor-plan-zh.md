# WriterLab 重构方案

生成时间：2026-04-01 18:54:02

## 1. 重构目标

本次重构不是重写产品能力，而是把已经成型的后端引擎和分散、拥挤的前端壳层重新组织成一个可长期演进的结构。目标有四个：

- 把前端从“单页调试台”改造成“按领域分层的正式应用”
- 保留后端已有的工作流、上下文、知识、一致性和运行时能力，不重写高风险内核
- 用新目录结构明确“页面入口、领域模块、共享组件、服务边界、测试归属”
- 给出一条可分阶段执行、可中途止损、可局部回滚的迁移路线

## 2. 重构原则

### 2.1 总体策略

- 先保留内核，再重做壳层
- 先拆边界最差的前端单体页，再整理后端目录
- 先保持数据库和核心 API 语义稳定，再考虑协议收口
- 先让结构清晰，再决定哪些历史实现该删除

### 2.2 必须保留的稳定内核

- `fastapi/backend/app/models.py`
  - 原因：承载项目、章节、场景、版本、分支、知识、运行时等核心表结构
- `fastapi/backend/app/alembic/`
  - 原因：现有迁移历史必须延续，不能在大改时丢失数据库演进线索
- `fastapi/backend/app/services/workflow_service.py`
  - 原因：是整套 AI 写作流程的编排核心
- `fastapi/backend/app/services/ai_gateway_service.py`
  - 原因：封装了 Provider Matrix、超时、预算、回退和熔断逻辑
- `fastapi/backend/app/services/context_service.py`
  - 原因：负责上下文编译，是输出质量的关键中枢
- `fastapi/backend/app/services/knowledge_service.py`
  - 原因：负责知识文档、检索、style memory，是后续扩展的重要基础
- `fastapi/backend/app/services/consistency_service.py`
  - 原因：承担规则校验和一致性审查
- `fastapi/backend/app/services/smoke_report_service.py`
  - 原因：承载运行时体检与回归结果，是重构期不可缺少的安全绳

### 2.3 必须删除或下线的对象

- `Next.js/frontend/app/project/page.tsx`
  - 动作：删除占位实现，替换为正式项目工作台入口
- `Next.js/frontend/app/lore/page.tsx`
  - 动作：删除占位实现，替换为正式设定库入口
- 前端页面中的临时说明文案、乱码文本、调试用占位块
  - 动作：统一清理，避免把调试痕迹带进正式信息架构
- 与正式依赖不一致的历史说明
  - 动作：在依赖收口阶段统一收敛，避免 `requirements.txt` 与 `requirements.codex.txt` 长期双轨

### 2.4 必须拆分重组的对象

- `Next.js/frontend/app/editor/page.tsx`
  - 动作：拆成路由页入口、功能区容器、领域组件、共享 hooks、API client
- `fastapi/backend/app/api/*.py`
  - 动作：保留路由能力，但按领域归并，减少“一个文件同时承载协议和业务拼装”
- `fastapi/backend/app/main.py`
  - 动作：保留应用入口，但将初始化、注册和启动逻辑逐步拆到装配层

## 3. 目标目录结构

### 3.1 前端目标结构

前端继续使用 Next.js App Router，但不再让路由页承载大部分业务逻辑。页面只负责装配，状态、请求和领域行为全部下沉。

```text
Next.js/frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── editor/
│   │   ├── page.tsx
│   │   ├── loading.tsx
│   │   └── error.tsx
│   ├── project/
│   │   ├── page.tsx
│   │   └── [projectId]/
│   │       ├── page.tsx
│   │       ├── books/
│   │       ├── chapters/
│   │       └── scenes/
│   ├── lore/
│   │   ├── page.tsx
│   │   ├── characters/
│   │   ├── locations/
│   │   └── entries/
│   ├── settings/
│   │   └── page.tsx
│   └── runtime/
│       └── page.tsx
├── features/
│   ├── editor/
│   │   ├── scene-workbench/
│   │   ├── workflow-panel/
│   │   ├── analysis-panel/
│   │   ├── branch-panel/
│   │   ├── runtime-panel/
│   │   └── vn-export-panel/
│   ├── project/
│   │   ├── project-selector/
│   │   ├── chapter-outline/
│   │   └── scene-list/
│   ├── lore/
│   │   ├── character-library/
│   │   ├── location-library/
│   │   └── lore-entry-library/
│   ├── settings/
│   └── runtime/
├── entities/
│   ├── project/
│   ├── scene/
│   ├── chapter/
│   ├── book/
│   ├── character/
│   ├── location/
│   ├── lore-entry/
│   └── workflow-run/
├── shared/
│   ├── ui/
│   ├── forms/
│   ├── hooks/
│   ├── config/
│   └── utils/
├── lib/
│   ├── api/
│   │   ├── client.ts
│   │   ├── projects.ts
│   │   ├── scenes.ts
│   │   ├── lore.ts
│   │   ├── workflow.ts
│   │   └── runtime.ts
│   ├── adapters/
│   └── constants/
└── tests/
    ├── features/
    └── smoke/
```

### 3.2 前端各层职责

- `app/`
  - 只放路由入口、布局、加载态、错误态，不堆业务逻辑
- `features/`
  - 以用户能力为边界组织功能模块，是主要迁移落点
- `entities/`
  - 放领域实体的类型、显示片段、轻量状态与变换逻辑
- `shared/`
  - 放可跨页面复用的 UI、表单、hooks、配置、工具函数
- `lib/api/`
  - 统一所有后端接口调用，不允许页面散落 `fetch`

### 3.3 后端目标结构

后端继续以 FastAPI 为入口，但从“路由文件 + 大服务文件”过渡到“按领域组织的接口层、服务层、仓储层和任务层”。

```text
fastapi/backend/app/
├── main.py
├── api/
│   ├── deps.py
│   ├── routers/
│   │   ├── health.py
│   │   ├── project.py
│   │   ├── story.py
│   │   ├── lore.py
│   │   ├── workflow.py
│   │   ├── runtime.py
│   │   └── settings.py
├── domain/
│   ├── models/
│   ├── enums/
│   └── value_objects/
├── schemas/
│   ├── common.py
│   ├── project.py
│   ├── story.py
│   ├── lore.py
│   ├── workflow.py
│   ├── runtime.py
│   └── settings.py
├── services/
│   ├── workflow/
│   │   ├── workflow_service.py
│   │   ├── workflow_runner.py
│   │   └── workflow_review.py
│   ├── ai/
│   │   ├── ai_gateway_service.py
│   │   ├── provider_matrix.py
│   │   └── output_guard.py
│   ├── context/
│   │   ├── context_service.py
│   │   └── context_snapshot_builder.py
│   ├── knowledge/
│   │   ├── knowledge_service.py
│   │   ├── retriever.py
│   │   └── style_memory_service.py
│   ├── consistency/
│   │   └── consistency_service.py
│   ├── story/
│   ├── lore/
│   └── runtime/
├── repositories/
│   ├── project_repository.py
│   ├── scene_repository.py
│   ├── lore_repository.py
│   └── workflow_repository.py
├── tasks/
│   ├── schema_upgrades.py
│   ├── startup_checks.py
│   └── smoke_report_jobs.py
├── infra/
│   ├── db/
│   ├── settings/
│   ├── runtime/
│   └── logging/
├── models.py
└── alembic/
```

### 3.4 后端各层职责

- `api/routers/`
  - 只负责协议、参数、响应和错误码，不拼业务流程
- `services/`
  - 承载工作流、AI 路由、上下文、知识、一致性等核心业务
- `repositories/`
  - 吸收分散的数据库读写细节，减少服务层直接操作 ORM 细节
- `tasks/`
  - 放启动期任务、schema 修补、异步维护任务
- `infra/`
  - 放配置、数据库接线、运行时状态、日志等基础设施

## 4. 模块保留 / 删除 / 合并 / 重写清单

### 4.1 前端

| 现状模块 | 动作 | 目标去向 | 理由 |
| --- | --- | --- | --- |
| `app/page.tsx` | 保留并瘦身 | `app/page.tsx` + `features/project/project-selector` | 作为首页入口保留，但不再直接承担过多状态探测 |
| `app/editor/page.tsx` | 拆分重写 | `app/editor/page.tsx` + `features/editor/*` + `lib/api/*` | 当前过大且职责混杂 |
| `app/project/page.tsx` | 删除占位并重建 | `app/project/page.tsx`、`app/project/[projectId]/...` | 项目工作台需要正式信息架构 |
| `app/lore/page.tsx` | 删除占位并重建 | `app/lore/*` + `features/lore/*` | 设定库需要独立入口和细分视图 |
| 页面内散落的 `fetch` | 合并 | `lib/api/*` | 避免请求协议分散 |
| 调试块、临时按钮、占位提示 | 删除或迁入 `runtime` | `features/runtime/*` | 正式业务界面和诊断界面应分离 |

### 4.2 后端

| 现状模块 | 动作 | 目标去向 | 理由 |
| --- | --- | --- | --- |
| `app/main.py` | 保留并瘦身 | `main.py` + `api/routers` + `tasks` | 入口文件只保留装配职责 |
| `app/api/ai.py` | 拆分 | `api/routers/workflow.py`、`api/routers/settings.py` | AI 请求、工作流编排、设置查询不应混在一起 |
| `app/api/scenes.py` | 拆分并并入故事域 | `api/routers/story.py` | 场景是故事域的一部分 |
| `app/api/books.py`、`chapters.py`、`projects.py` | 合并归域 | `api/routers/project.py`、`story.py` | 按领域收口 API |
| `app/api/characters.py`、`locations.py`、`lore_entries.py` | 合并归域 | `api/routers/lore.py` | 设定域统一入口 |
| `workflow_service.py` | 保留并局部拆文件 | `services/workflow/*` | 高价值内核，不能推倒重写 |
| `ai_gateway_service.py` | 保留并局部拆文件 | `services/ai/*` | Provider 策略应成为稳定基础设施 |
| `context_service.py` | 保留并局部拆文件 | `services/context/*` | 上下文编译是能力中枢 |
| `knowledge_service.py` | 保留并局部拆文件 | `services/knowledge/*` | 检索与记忆应继续复用 |
| `schema_upgrades.py` | 保留并迁入任务层 | `tasks/schema_upgrades.py` | 启动修补逻辑必须保留但要显式隔离 |

### 4.3 测试、脚本与文档

| 现状模块 | 动作 | 目标去向 | 理由 |
| --- | --- | --- | --- |
| `fastapi/backend/tests/test_*` | 保留并按领域归组 | `tests/services/`、`tests/api/`、`tests/runtime/` | 让测试结构跟业务结构一致 |
| `scripts/check-backend.ps1` | 保留 | `scripts/check-backend.ps1` | 作为阶段验收入口继续使用 |
| `scripts/check-frontend.ps1` | 保留 | `scripts/check-frontend.ps1` | 作为前端冒烟入口继续使用 |
| `scripts/backend_full_smoke.py`、`frontend_live_smoke.mjs` | 保留并补文档 | 原地或迁入 `scripts/smoke/` | 重构期非常关键 |
| `docs/project-overview-zh.md` | 保留 | `docs/project-overview-zh.md` | 作为项目盘点基线 |
| 历史说明和乱码内容 | 清理 | 对应文档原位修复 | 降低认知噪音 |

## 5. 推荐迁移顺序

这次大改建议走五个阶段，不建议“一次性改完再看能不能跑”。

### 阶段 0：准备期

- 目标：
  - 冻结当前关键 API 语义
  - 记录现有页面与后端能力映射
  - 明确 `editor` 页中的功能块拆分清单
- 主要动作：
  - 建立前端模块台账
  - 建立后端服务映射表
  - 固化 Smoke 入口与基线文档
- 验收门槛：
  - 当前前后端本地可启动
  - 后端核心测试与 Smoke 能跑通
  - 有一份明确的模块拆分清单
- 回滚点：
  - 这一阶段只做文档和清单，无需代码回滚

### 阶段 1：前端拆页，但不改业务语义

- 目标：
  - 把 `app/editor/page.tsx` 拆成页面入口 + 多个功能面板
  - 建立统一 API Client
- 主要动作：
  - 抽离工作流面板、分析面板、分支面板、运行时面板、导出面板
  - 把页面内散落的请求迁到 `lib/api/*`
  - 建立共享 hooks 和共享 UI 目录
- 验收门槛：
  - `/editor` 页面功能不减少
  - 页面代码体积明显下降
  - 所有请求不再散落在多个 UI 片段里
- 回滚点：
  - 若拆分后交互失真，可回滚单个 feature 目录，不必回滚全部前端

### 阶段 2：补齐正式页面信息架构

- 目标：
  - 用正式页面替换 `/project` 和 `/lore` 占位页
  - 建立“项目工作台 / 设定库 / 运行时 / 设置”四个一级入口
- 主要动作：
  - 新建项目列表与项目详情路由
  - 新建设定总览、角色、地点、词条子路由
  - 把运行时诊断从编辑器页剥离到 `/runtime`
- 验收门槛：
  - 不再存在明显占位页
  - 一级导航完整
  - 业务界面与诊断界面边界清晰
- 回滚点：
  - 先保留旧入口链接，必要时可短期回退到旧 `/editor` 聚合入口

### 阶段 3：后端分层整理

- 目标：
  - 将后端从“按文件堆功能”过渡到“按领域分层”
  - 保持数据库模型和核心服务语义不变
- 主要动作：
  - 建立 `api/routers`、`repositories`、`tasks`、`infra`
  - 把路由协议层与服务编排拆开
  - 将数据库访问逻辑逐步收拢到仓储层
- 验收门槛：
  - 对外 API 路径保持稳定或提供一次性迁移说明
  - `workflow_service`、`ai_gateway_service`、`context_service` 行为不回退
  - 现有测试套件仍可运行
- 回滚点：
  - 以“文件迁移 + import 兼容层”为单位回滚，不碰数据表结构

### 阶段 4：测试、脚本与文档收口

- 目标：
  - 让测试目录、Smoke 脚本、依赖说明和文档与新结构一致
- 主要动作：
  - 测试按领域重组
  - 收敛依赖文件职责
  - 修复乱码与历史说明噪音
  - 更新运行文档和开发文档
- 验收门槛：
  - 有统一的启动、测试、Smoke 说明
  - 关键目录名称和文档一致
  - 新成员能根据目录直接定位业务模块
- 回滚点：
  - 文档和脚本变更可独立回退，不影响主业务代码

## 6. 实施优先级

如果你准备马上开工，建议按下面顺序推进：

1. 先拆 `app/editor/page.tsx`
2. 再补 `/project` 与 `/lore` 正式页面
3. 再统一前端 API Client 和共享 hooks
4. 再整理后端 `api` 与 `services` 边界
5. 最后收口测试、脚本、依赖与文档

原因很简单：当前最影响迭代速度的不是后端功能不够，而是前端入口过大、页面边界不清。

## 7. 不建议现在做的事

- 不建议先重写数据库模型
- 不建议先替换工作流引擎
- 不建议先改 Provider 路由策略
- 不建议在结构未定前大规模改 UI 视觉
- 不建议同时改前端信息架构、后端协议和数据结构

这些动作都很贵，而且会让问题从“结构混乱”变成“结构和行为一起不确定”。

## 8. 第一批落地任务

为了把这份方案变成执行计划，第一批任务建议只有 6 个：

1. 列出 `app/editor/page.tsx` 的功能块与状态块清单
2. 建立 `lib/api/` 并把现有请求分组
3. 建立 `features/editor/` 并迁出第一个面板
4. 设计 `/project` 的正式信息架构
5. 设计 `/lore` 的正式信息架构
6. 制定后端 `api -> services -> repositories` 的第一轮迁移表

## 9. 验收与回滚规则

### 9.1 阶段验收规则

- 每阶段结束都必须满足“页面能打开、后端能启动、核心测试或 Smoke 不回退”
- 每阶段只允许一个主目标，不能同时改信息架构、协议和数据结构
- 每阶段都要留下迁移说明，写清旧模块对应的新去向

### 9.2 回滚规则

- 前端以 `feature` 目录为最小回滚单元
- 后端以“单个 router / 单个 service 子目录” 为最小回滚单元
- 数据库模型与 Alembic 历史在前 3 个阶段不做破坏式修改

## 10. 最终建议

最适合这个项目的重构路线不是“全部推翻”，而是：

**保留后端能力内核，先把前端壳层拆开，再把后端目录整理成长期可维护的形态。**

如果你下一步要我继续，我建议直接进入实施级文档：

- 第一步：把 `app/editor/page.tsx` 拆分成具体子模块清单
- 第二步：出一版 `/project` 与 `/lore` 的页面结构图
- 第三步：给你一份“第一阶段改动清单 + 文件级迁移表”
