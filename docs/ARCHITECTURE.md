# 当前架构记录

> 反映 2026-04-28 T-8 仓库重组后的真实拓扑。涉及目录命名、模块边界、调用链。后续轮次每次产生架构变化时追加"变更"小节。

## 1. 仓库顶层

```
D:\WritierLab\
├─ README.md                 仓库总入口（项目定位、快速启动、关键文档链接）
├─ AGENTS.md                 历史强制流程文档（保留，本轮不再驱动工作流）
├─ .gitignore                收紧密钥/缓存/历史产物，允许 .env.example
├─ .codex/                   历史 operations-log / verification-report（保留不动）
├─ apps/
│  ├─ backend/               FastAPI + SQLAlchemy + pytest（详见 §3）
│  └─ frontend/              Next.js 16 + React 19 + TypeScript（详见 §4）
├─ docs/
│  ├─ architecture/          架构决策与布局说明（repository-layout.md 等）
│  ├─ project/               project-overview-zh.md
│  ├─ runbooks/              runtime-notes.md（启动顺序、smoke、故障解读）
│  ├─ verification/          local-verification-zh.md
│  ├─ superpowers/           设计 spec 与 implementation plan
│  ├─ ARCHITECTURE.md        本文件
│  ├─ TASKS.md               长期任务队列
│  ├─ PROGRESS.md            每轮进度记录
│  └─ RESEARCH.md            研究记录
└─ scripts/
   ├─ dev/                   start-backend / start-frontend / dev-stack / install-backend
   ├─ check/                 check-backend / check-frontend（静态 + smoke）
   ├─ smoke/                 backend_full_smoke.py / frontend_live_smoke.mjs
   ├─ data/                  fix_demo_garbled_data.py
   └─ logs/                  smoke 报告输出目录（gitignore）
```

## 2. 应用工作区 apps/

```
apps/
├─ backend/                  FastAPI 应用根（详见 §3）
│  ├─ .venv/                 Python 虚拟环境（gitignore）
│  ├─ requirements.txt       直接依赖 + 精确版本
│  ├─ alembic.ini, alembic/  Alembic 迁移
│  └─ app/                   应用主体
└─ frontend/                 Next.js 应用根（详见 §4）
   ├─ node_modules/          npm 依赖（gitignore）
   └─ ...
```

## 3. 后端：apps/backend

### 3.1 目录与职责（重构后）

```
apps/backend/
├─ requirements.txt          直接依赖清单（本轮重写）
├─ alembic.ini, alembic/     Alembic 迁移
├─ .env / .env.example       DB 连接 + DATABASE_ECHO 开关
└─ app/
   ├─ main.py                FastAPI 入口；直接 include 16 个 router（取消中转层）
   ├─ api/                   每文件 = 一个 URL 前缀的 router
   │                         （health/projects/books/chapters/scenes/branches/
   │                          timeline_events/vn/characters/locations/lore_entries/
   │                          ai/knowledge/consistency/settings/runtime）
   ├─ db/
   │  ├─ session.py          Engine / SessionLocal / get_db；echo 由环境变量驱动
   │  ├─ base.py             ORM 模型聚合 import（让 Alembic autogenerate 看到全部表）
   │  └─ schema_upgrades.py  非破坏式 schema patch（startup 阶段调用）
   ├─ models/                23 个 SQLAlchemy ORM 模型
   ├─ schemas/               21 个 Pydantic v2 请求/响应模型
   ├─ repositories/          5 个仓储层模块（project/scene/lore/timeline/workflow）
   ├─ services/              业务服务（扁平结构，无子包）
   │  │
   │  │── ai_gateway 子模块群（T-6.B 完成）
   │  ├─ ai_gateway_service.py        296 行；call_ai_gateway 主入口 + state dict + _reset + 公开视图
   │  ├─ ai_gateway_constants.py      163 行；常量、dataclass、_env_timeout_ms
   │  ├─ ai_gateway_costing.py         74 行；纯计算工具
   │  ├─ ai_gateway_fixtures.py       110 行；smoke fixture 文本生成器
   │  ├─ ai_gateway_views.py           84 行；只读视图与展示辅助
   │  ├─ ai_gateway_skip_reason.py     76 行；profile 跳过原因决策链
   │  ├─ ai_gateway_provider.py       103 行；HTTP/Ollama 实际调用
   │  ├─ ai_gateway_state.py           85 行；state init + record_*
   │  ├─ ai_gateway_routing.py        131 行；profile 解析 + 路由矩阵
   │  │
   │  │── workflow 子模块群（T-6.A 完成）
   │  ├─ workflow_service.py          191 行；facade + re-export（公开 API 入口）
   │  ├─ workflow_execution.py        294 行；_run_scene_workflow 主流程编排
   │  ├─ workflow_persistence.py      366 行；DB 触达辅助（~20 个函数）
   │  ├─ workflow_runtime.py           72 行；runner/recovery 内核
   │  ├─ workflow_constants.py        115 行；步骤顺序、agent 元数据、配置常量、纯小工具
   │  ├─ workflow_prompts.py           60 行；planner/style prompt 与记忆候选文本拼接
   │  ├─ workflow_extractors.py       128 行；步骤快照解析与最终输出组装
   │  │
   │  │── 其他 services
   │  ├─ ai_output_guardrails.py      312 行；输出校验与 sanitize
   │  ├─ ai_prompt_templates.py       prompt 工具（stringify_list / clip_context / build_context_block）
   │  ├─ ai_run_service.py            ai_runs 表落库
   │  ├─ branch_service.py            分支创建/diff/采纳
   │  ├─ consistency_service.py       300 行；一致性扫描
   │  ├─ context_service.py           404 行；scene context 编译（角色/地点/lore/记忆/时间线/检索）
   │  ├─ knowledge_service.py         521 行；知识文档分块与向量检索
   │  ├─ ollama_service.py            本地 Ollama 调用
   │  ├─ provider_settings_service.py provider API key 读写
   │  ├─ runtime_events.py            in-memory 运行事件队列
   │  ├─ runtime_status_service.py    启动阶段状态 snapshot
   │  ├─ scene_analysis_service.py    分析 scene
   │  ├─ scene_analysis_store_service.py 落库已分析项
   │  ├─ scene_revise_service.py      润色
   │  ├─ scene_status_service.py      场景 status 标记
   │  ├─ scene_version_service.py     版本快照
   │  ├─ scene_write_service.py       289 行；写作主调用
   │  ├─ smoke_report_service.py      496 行；smoke 报告读取与回归对比
   │  ├─ style_negative_service.py    禁写规则匹配
   │  ├─ timeline_service.py
   │  └─ vn_export_service.py
   └─ tasks/
      └─ startup_checks.py   schema 校验 + 自愈 schema 升级 + 工作流恢复扫描 + workflow runner 启动
```

### 3.2 启动与运行链

```
uvicorn → app.main:app
  └─ lifespan
      └─ run_startup_sequence
          1. assert_schema_is_migrated    # alembic_version 必须存在
          2. apply_schema_upgrades         # 非破坏 schema 修补
          3. recover_expired_workflow_runs # 启动期扫过期 run
          4. ensure_workflow_runner_started# 启动后台 workflow 调度线程
          → 标记 runtime_status 为 ready
```

### 3.3 API 命名空间（共 74 条业务路由）

- `/api/health`、`/api/projects`、`/api/books`、`/api/chapters`、`/api/scenes/...`
- `/api/branches`、`/api/timeline-events`、`/api/vn`
- `/api/characters`、`/api/locations`、`/api/lore-entries`
- `/api/ai/...`（analyze / write / revise / workflow run / resume / override / cancel）
- `/api/knowledge`、`/api/consistency-scan`
- `/api/settings/providers`
- `/api/runtime/...`（provider state / smoke 报告 / WS）

## 4. 前端：apps/frontend

### 4.1 目录与职责

```
apps/frontend/
├─ package.json              dev/build/start/lint/typecheck
├─ next.config.ts, tsconfig.json, eslint.config.mjs
├─ app/                      Next.js App Router（薄页面，几乎只 import feature 组件）
│  ├─ page.tsx, layout.tsx
│  ├─ project/, project/new/, project/[projectId]/{books,chapters,scenes,timeline}/
│  ├─ editor/, lore/{characters,locations,entries}/
│  ├─ runtime/, settings/
├─ features/                 业务功能模块
│  ├─ editor/                EditorWorkspace + 子组件 + hooks + editor-labels.ts
│  ├─ lore/                  LoreLibraryPage + LoreHub + lore-page-helpers.ts
│  ├─ project/               ProjectHub / ProjectDetail / ProjectCreatePage / HomeDashboard
│  ├─ runtime/               RuntimeDebugWorkbench + 诊断 hook + RuntimeHub
│  ├─ settings/              SettingsHub
│  └─ timeline/              TimelineLibraryPage
├─ lib/api/                  API 客户端（client.ts 提供 apiGet/apiPost/apiPatch/apiPut/apiDelete）
├─ shared/ui/                AppShell / WorkspaceShell / InfoCard
└─ tests/features/           9 个 .test.mjs 源码契约测试（无 jest，原生 node:test）
                             （api-client / runtime-debug-workbench / lore-library /
                              scenes-workflow-contract / projects-settings-contract 等）
```

### 4.2 数据流 / API 边界

- 所有 `fetch` 走 `lib/api/client.ts` 的 `apiRequest` 封装：浏览器同源 → 相对路径走 Next 同源代理；Node SSR/测试 → `http://127.0.0.1:8000` 默认值；错误响应优先取 `detail` / `message` 字段；网络错误统一加上"请确认后端服务已启动"提示。
- 没有 Redux / Zustand / SWR；`features/*/hooks/*` 是手写的 useEffect+useState 组合。

## 5. 架构决策

| ID | 决策 | 理由 |
|---|---|---|
| ADR-1 | services 与 routers 取消子包/中转层，回归扁平结构 | 实际所有调用方走扁平路径，子包未被使用；维持双层只是负担 |
| ADR-2 | DB echo 用环境变量 `DATABASE_ECHO` 控制，默认关闭 | 默认 echo=True 在生产 / 测试都是日志噪音；保留可调试的途径 |
| ADR-3 | `requirements.txt` 写直接依赖 + 精确版本，不写传递依赖 | 保留可读性；版本与当前 venv 对齐 |
| ADR-4 | 大文件拆"先抽常量，不动 JSX/handler" | 契约测试不覆盖 hooks 与 setState 时序，重写组件结构风险高 |
| ADR-5 | 不再做 AGENTS.md 那一套 operations-log / verification-report 流程留痕 | 用户最新指引以 TASKS/PROGRESS/ARCHITECTURE/RESEARCH 为准 |
| ADR-6 | 前端坏测试用"源码契约风格"修复 | 与项目其它前端测试保持一致；规避 Node 22 不能 import `.ts` 的工具链限制 |
| ADR-7 | 仓库顶层重组为 `apps / docs / scripts`（T-8） | 消除无意义的 WriterLab-v1 壳层；标准化目录职责边界 |
| ADR-8 | workflow_service + ai_gateway_service 各拆为 7/9 个子模块（T-6） | 单文件 926/835 行；按职责切分降低可读性负担；lazy import 保护 monkeypatch 路径 |

## 6. 已知待解 / 与本架构相关的开放问题

- **`alembic` 与 `app/db/schema_upgrades.py` 的关系**：当前 `assert_schema_is_migrated` 要求 `alembic_version` 存在；`apply_schema_upgrades` 在此之后再做非破坏 patch。两者协议未来如果合并到 alembic 内是更干净的做法，但目前**功能正常，不改**。

## 7. T-6 完成记录：workflow_service.py 拆分（926 行 → 7 个文件）

**状态：✅ 全部完成（2026-04-27/28）**

### 7.1 最终文件结构

| 文件 | 行数 | 职责 |
|------|------|------|
| `workflow_service.py` | 191 | facade + re-export（公开 API 入口） |
| `workflow_execution.py` | 294 | `_run_scene_workflow` 主流程编排 |
| `workflow_persistence.py` | 366 | DB 触达辅助（~20 个函数） |
| `workflow_runtime.py` | 72 | runner/recovery 内核 |
| `workflow_constants.py` | 115 | 步骤顺序、agent 元数据、配置常量、纯工具 |
| `workflow_prompts.py` | 60 | planner/style prompt 与记忆候选文本拼接 |
| `workflow_extractors.py` | 128 | 步骤快照解析与最终输出组装 |

**削减比例**：主模块 926 → 191 行（−79%）；子模块合计 732 行（6 个文件）。

### 7.2 关键设计约束（lazy import 保护 monkeypatch）

所有从 `workflow_service.py` 拆出的符号，都通过 `from app.services.workflow_<x> import <name>` 在主模块顶部拉回，保证 `monkeypatch.setattr("app.services.workflow_service.<name>", ...)` 仍命中调用方真正使用的绑定。

子模块内部对被 monkeypatch 的目标的调用，通过 lazy import 主模块（`from app.services.workflow_service import <name>`）解决，使 patch 对子模块内部调用也生效。

## 8. T-6.B 完成记录：ai_gateway_service.py 拆分（835 行 → 9 个文件）

**状态：✅ 全部完成（2026-04-27）**

### 8.1 最终文件结构

| 文件 | 行数 | 职责 |
|------|------|------|
| `ai_gateway_service.py` | 296 | call_ai_gateway 主入口 + state dict + _reset + 公开视图 |
| `ai_gateway_constants.py` | 163 | 常量、dataclass、_env_timeout_ms |
| `ai_gateway_costing.py` | 74 | 纯计算工具（cost / timeout / text 提取） |
| `ai_gateway_fixtures.py` | 110 | smoke fixture 文本生成器 |
| `ai_gateway_views.py` | 84 | 只读视图与展示辅助（含 lazy import） |
| `ai_gateway_skip_reason.py` | 76 | profile 跳过原因决策链（含 lazy import） |
| `ai_gateway_provider.py` | 103 | HTTP/Ollama 实际调用 |
| `ai_gateway_state.py` | 85 | state init + record_*（含 lazy import） |
| `ai_gateway_routing.py` | 131 | profile 解析 + 路由矩阵（含 lazy import） |

**削减比例**：主模块 835 → 296 行（−65%）；子模块合计 826 行（8 个文件）。

### 8.2 三个 state dict 的归属原则

`_REQUEST_WINDOWS / _PROFILE_RUNTIME_STATE / _PROVIDER_RUNTIME_STATE` 永久留在 `ai_gateway_service.py`。测试直接 mutate 这三个 dict 对象；子模块通过 lazy import 主模块读写同一对象，保证 monkeypatch 与 dict mutation 在测试与运行时行为一致。

## 9. 测试覆盖现状（2026-04-28）

| 层级 | 数量 | 工具 |
|------|------|------|
| 后端单元 + 集成测试 | **576 passed** | pytest（无真实 DB，FakeDB/SimpleNamespace 模式） |
| 前端源码契约测试 | **19 passed**（9 个 .test.mjs 文件） | 原生 node:test |

后端测试覆盖模块：ai_gateway（常量/计算/fixture/视图/跳过决策/provider/state/routing/主服务）、workflow（常量/prompt/extractors/execution/persistence/runtime）、所有 repositories、所有 routes、核心 services（ollama / analysis_store / ai_run / branch / vn_export / style_negative / ai_prompt_templates / scene_version / scene_write / scene_revise / scene_analysis / runtime_status / provider_settings）。

前端测试覆盖模块：api-client 基础行为、runtime-debug-workbench 标记、lore-library 渲染契约、scenes-workflow API 路径契约、projects/settings API 路径契约。
