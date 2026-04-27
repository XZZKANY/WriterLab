# 当前架构记录

> 反映 2026-04-27 第 1 轮重构后的真实拓扑。涉及目录命名、模块边界、调用链。后续轮次每次产生架构变化时追加"变更"小节。

## 1. 仓库顶层

```
D:\WritierLab\
├─ README.md                 仓库总入口（项目定位、模块概览、快速启动）
├─ AGENTS.md                 历史强制流程文档（保留，本轮不再驱动工作流）
├─ TASKS.md                  长期任务队列（本轮新增）
├─ PROGRESS.md               每轮进度记录（本轮新增）
├─ ARCHITECTURE.md           架构记录（本轮新增）
├─ RESEARCH.md               研究记录（本轮新增）
├─ .gitignore                收紧密钥/缓存/历史产物，允许 .env.example
├─ .codex/                   历史 operations-log / verification-report（保留不动）
├─ docs/superpowers/         设计 spec 与 implementation plan（保留不动）
├─ WriterLab-v1/             主应用工作区
├─ pgvector-src/             pgvector 源码（已 gitignore，物理保留待用户确认是否删）
└─ logs/, .npm-cache/, vs_BuildTools.exe, *.log, codex_probe.obj  历史产物（gitignore 中）
```

## 2. WriterLab-v1 子工作区

```
WriterLab-v1/
├─ readme.md                 子入口
├─ docs/                     运行手册、本地验证、project overview
├─ scripts/                  PowerShell 启动/检查脚本 + node smoke + 后端 fix 脚本
├─ fastapi/backend/          FastAPI 应用（详见 §3）
└─ Next.js/frontend/         Next.js 16 应用（详见 §4）
```

## 3. 后端：fastapi/backend

### 3.1 目录与职责（重构后）

```
fastapi/backend/
├─ requirements.txt          直接依赖清单（本轮重写）
├─ requirements.codex.txt    AGENTS.md 流程旁路保留
├─ alembic.ini, alembic/     Alembic 迁移
├─ .env / .env.example       DB 连接 + DATABASE_ECHO 开关
└─ app/
   ├─ main.py                FastAPI 入口；直接 include 16 个 router（取消中转层）
   ├─ api/                   每文件 = 一个 URL 前缀的 router（health/projects/books/chapters/scenes/branches/timeline_events/vn/characters/locations/lore_entries/ai/knowledge/consistency/settings/runtime）
   ├─ db/
   │  ├─ session.py          Engine / SessionLocal / get_db；echo 由环境变量驱动
   │  ├─ base.py             ORM 模型聚合 import（让 Alembic autogenerate 看到全部表）
   │  └─ schema_upgrades.py  非破坏式 schema patch（startup 阶段调用）
   ├─ models/                23 个 SQLAlchemy ORM 模型（domain object 一一对应）
   ├─ schemas/               21 个 Pydantic v2 请求/响应模型
   ├─ repositories/          5 个仓储层模块（project/scene/lore/timeline/workflow）
   ├─ services/              业务服务（扁平结构，重构后无子包）
   │  ├─ ai_gateway_service.py        296 行；call_ai_gateway 主入口 + state dict + _reset + get_provider_runtime_state + summarize（T-6.B 累计 −539 行 / −65%）
   │  ├─ ai_gateway_constants.py      163 行；常量、dataclass、_env_timeout_ms（T-6.B1）
   │  ├─ ai_gateway_costing.py        74 行；纯计算工具（T-6.B2）
   │  ├─ ai_gateway_fixtures.py       110 行；smoke fixture 文本生成器（T-6.B3）
   │  ├─ ai_gateway_views.py          84 行；只读视图与展示辅助（T-6.B4.1）
   │  ├─ ai_gateway_skip_reason.py    76 行；profile 跳过原因决策链（T-6.B4.2）
   │  ├─ ai_gateway_provider.py       103 行；HTTP/Ollama 实际调用（T-6.B4.3.a）
   │  ├─ ai_gateway_state.py          85 行；D 块 state init + record_*（T-6.B4.3.b）
   │  ├─ ai_gateway_routing.py        131 行；profile 解析 + 路由矩阵（T-6.B4.3.c）
   │  ├─ ai_output_guardrails.py      312 行；输出校验与 sanitize
   │  ├─ ai_prompt_templates.py
   │  ├─ ai_run_service.py            ai_runs 表落库
   │  ├─ branch_service.py            分支创建/diff/采纳
   │  ├─ consistency_service.py       300 行；一致性扫描
   │  ├─ context_service.py           404 行；scene context 编译（聚合角色/地点/lore/记忆/时间线/检索）
   │  ├─ knowledge_service.py         521 行；知识文档分块与向量检索（含 pgvector / cosine 后备）
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
   │  ├─ vn_export_service.py
   │  ├─ workflow_constants.py        115 行；步骤顺序、agent 元数据、配置常量、纯小工具（T-6.A1）
   │  ├─ workflow_prompts.py          60 行；planner/style prompt 与记忆候选文本拼接（T-6.A2）
   │  ├─ workflow_extractors.py       128 行；步骤快照解析与最终输出组装（T-6.A3）
   │  └─ workflow_service.py          774 行；DB 辅助 + 主引擎 _run_scene_workflow + runner 线程 + 公开 API（T-17 又删了 18 行未用代码）
   └─ tasks/                 启动检查
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

## 4. 前端：Next.js/frontend

### 4.1 目录与职责

```
Next.js/frontend/
├─ package.json              dev/build/start/lint/typecheck
├─ next.config.ts, tsconfig.json, eslint.config.mjs
├─ app/                      Next.js App Router（薄页面，几乎只 import feature 组件）
│  ├─ page.tsx, layout.tsx
│  ├─ project/, project/new/, project/[projectId]/{books,chapters,scenes,timeline}/
│  ├─ editor/, lore/{characters,locations,entries}/
│  ├─ runtime/, settings/
├─ features/                 业务功能模块
│  ├─ editor/                EditorWorkspace + 子组件 + hooks + 标签字典（editor-labels.ts，本轮新增）
│  ├─ lore/                  LoreLibraryPage + LoreHub + lore-page-helpers.ts（本轮新增）
│  ├─ project/               ProjectHub / ProjectDetail / ProjectCreatePage / HomeDashboard
│  ├─ runtime/               RuntimeDebugWorkbench + 诊断 hook + RuntimeHub
│  ├─ settings/              SettingsHub
│  └─ timeline/              TimelineLibraryPage
├─ lib/api/                  API 客户端（client.ts 提供 apiGet/apiPost/apiPatch/apiPut/apiDelete + base URL 解析）
├─ shared/ui/                AppShell / WorkspaceShell / InfoCard
└─ tests/features/           7 个 .test.mjs 源码契约测试（无 jest，原生 node:test）
```

### 4.2 数据流 / API 边界

- 所有 `fetch` 走 `lib/api/client.ts` 的 `apiRequest` 封装：浏览器同源 → 相对路径走 Next 同源代理；Node SSR/测试 → `http://127.0.0.1:8000` 默认值；错误响应优先取 `detail` / `message` 字段；网络错误统一加上"请确认后端服务已启动"提示。
- 没有 Redux / Zustand / SWR；`features/*/hooks/*` 是手写的 useEffect+useState 组合（如 `use-runtime-diagnostics`、`use-scene-context`）。

## 5. 架构决策（本轮）

| ID | 决策 | 理由 |
|---|---|---|
| ADR-1 | services 与 routers 取消子包/中转层，回归扁平结构 | 实际所有调用方走扁平路径，子包未被使用；维持双层只是负担，且 `sys.modules[__name__] = ...` 这种 forwarding 让导入链成谜 |
| ADR-2 | DB echo 用环境变量 `DATABASE_ECHO` 控制，默认关闭 | 默认 echo=True 在生产 / 测试都是日志噪音；保留可调试的途径 |
| ADR-3 | `requirements.txt` 写直接依赖 + 精确版本，不写传递依赖 | 保留可读性；依赖 pip 解析传递关系；版本与当前 venv 对齐 |
| ADR-4 | 大文件拆"先抽常量，不动 JSX/handler" | 契约测试不覆盖 hooks 与 setState 时序，重写组件结构风险高；最小动作降复杂度即可 |
| ADR-5 | 不再做 AGENTS.md 那一套 operations-log / verification-report 流程留痕 | 用户最新指引以 TASKS/PROGRESS/ARCHITECTURE/RESEARCH 为准；旧 `.codex/` 保留不动 |
| ADR-6 | 前端 2 个 pre-existing 坏测试用"源码契约风格"修复 | 与项目其它前端测试保持一致；规避 Node 22 不能 import `.ts` 的工具链限制 |

## 6. 已知待解 / 与本架构相关的开放问题

- **TASKS.md T-6**：`workflow_service.py` 926 / `ai_gateway_service.py` 835 内部仍可按职责拆，已进入 §7 拆分方案。
- **TASKS.md T-8**：`apps / docs / scripts` 顶层重组（已有 spec + plan 在 `docs/superpowers/`），未启动。
- **`alembic` 与 `app/db/schema_upgrades.py` 的关系**：当前 `assert_schema_is_migrated` 要求 `alembic_version` 存在；`apply_schema_upgrades` 在此之后再做非破坏 patch。两者协议未来如果合并到 alembic 内是更干净的做法，但目前**功能正常，本轮不动**。

## 7. T-6 拆分方案：workflow_service.py（926 行 → 多文件）

### 7.1 现有职责矩阵（按依赖深度从浅到深）

| 块 | 行号 | 内容 | 依赖 | 拆离风险 |
|---|---|---|---|---|
| **A. 常量与元数据** | 38–63 | `STEP_ORDER`、`STEP_SEQUENCE`、`RUN_TERMINAL_STATUSES`、`STEP_REUSABLE_STATUSES`、`LEASE_SECONDS`、`RUNNER_POLL_SECONDS`、`RUNNER_ID`、`WORKFLOW_SCHEMA_VERSION`、`VRAM_LOCK_TTL_SECONDS`、`STEP_AGENT_META` | 仅标准库 + `os` | 极低 |
| **B. 纯工具函数** | 66–85, 125–177 | `_utcnow`、`_hash_json`、`_agent_meta`、`_with_agent_meta`、`_resolve_gateway_tokens`、`_next_step_key`、`_fixture_version_for_mode`、`_run_fixture_scenario` | A 块 + `GatewayCallResult` 类型 | 极低 |
| **C. Prompt 与候选文本构造** | 143–158 | `_planner_prompt`、`_style_prompt`、`_build_memory_candidate` | Scene 模型只读、WorkflowSceneRequest schema | 低 |
| **D. 快照解析与最终输出组装** | 357–434, 510–525 | `_extract_effective_snapshot`、`_build_planner_output`、`_extract_planner_output`、`_fixture_guard_output`、`_extract_final_text`、`_extract_version_id`、`_extract_memory_id`、`_should_reuse_step`、`_workflow_output` | A 块 + Pydantic schema（PlannerOutput / GuardOutput / Violation）、WorkflowStep ORM 只读 | 低 |
| **E. DB 触达辅助** | 87–122, 180–289, 291–354, 437–483, 485–507 | `_attach_step_attempts`、`_resolve_project_id`、`_queue_depth`、`_publish_run_event`、`_attach_run_transient_fields`、`_create_run`、`_set_run_state`、`_heartbeat_run`、`_all_workflow_steps`、`_latest_step_for_key`、`_latest_workflow_steps`、`_stable_resume_checkpoint`、`_create_step`、`_finish_step`、`_record_dedup_response`、`_existing_dedup_response`、`_invalidate_downstream_steps`、`_vram_lock`、`_create_memory_candidate`、`_store_workflow_result` | Session、所有 ORM 模型、runtime_events、scene_version_service | 中（大量交叉调用，且测试 monkeypatch） |
| **F. 主引擎** | 528–786 | `_run_scene_workflow`（约 250 行的步骤序列） | 几乎所有上游块 + `analyze_scene`、`write_scene`、`scan_scene_consistency`、`build_guard_output`、`call_ai_gateway`、`build_scene_context` | 高 |
| **G. 后台 runner 与公开 API** | 789–926 | `recover_expired_workflow_runs`、`_claim_next_workflow_run`、`_workflow_runner_loop`、`ensure_workflow_runner_started`、`is_workflow_runner_started`、`queue_scene_workflow`、`execute_scene_workflow`、`resume_workflow_run`、`override_workflow_step`、`cancel_workflow_run`、`get_workflow_run`、`list_workflow_steps` | 全部 | 中（线程 + 模块级状态） |

### 7.2 测试加在 workflow_service 上的 patch 面（必须保护）

`tests/services/workflow_service_suite.py` 用字符串路径 `monkeypatch.setattr("app.services.workflow_service.<name>", ...)` 替换了：

- 私有符号：`_existing_dedup_response`、`_latest_step_for_key`、`_create_step`、`_finish_step`、`_invalidate_downstream_steps`、`_next_step_key`、`_record_dedup_response`、`_stable_resume_checkpoint`、`_set_run_state`、`_publish_run_event`、`_resolve_project_id`、`_heartbeat_run`、`_latest_workflow_steps`、`_vram_lock`、`_store_workflow_result`、`_create_memory_candidate`
- 已 import 的外部符号：`call_ai_gateway`、`analyze_scene`、`write_scene`、`scan_scene_consistency`、`build_guard_output`、`build_scene_context`、`resolve_style_negative_rules`、`match_style_negative_rules`、`ensure_workflow_runner_started`

**必须保留的不变量**：所有上述名字在拆完后**仍然要作为属性存在于 `app.services.workflow_service` 模块命名空间**。做法是在 `workflow_service.py` 顶部用 `from app.services.workflow_<x> import <name>` 把符号"拉回"主模块，调用点继续通过这些名字调用。这样测试 patch 仍然会替换调用点真正使用的绑定（Python module-level name binding 的标准行为）。

### 7.3 目标文件结构

```
fastapi/backend/app/services/
├─ workflow_constants.py     A + B 块（常量 + 纯工具）
├─ workflow_prompts.py       C 块（prompt 与候选文本构造）
├─ workflow_extractors.py    D 块（快照解析与最终输出组装）
└─ workflow_service.py       E + F + G 块（DB 辅助 + 主引擎 + runner + 公开 API）
                             顶部统一 import 上面 3 个新模块的符号
```

不再用 `app/services/workflow/` 子包（避免重蹈 T-2 双层结构），保持与现有 `ai_*_service.py` / `ai_output_guardrails.py` / `ai_prompt_templates.py` 一致的扁平命名。

### 7.4 阶段拆分（每阶段单独验证）

| 阶段 | 动作 | 移动的符号 | 主要风险 | 验证 |
|---|---|---|---|---|
| **A1** | 新建 `workflow_constants.py`，把 A + B 块整体搬过去；`workflow_service.py` 顶部 `from app.services.workflow_constants import *`（或具名 import）拉回；删除原定义 | A + B 块共 10 常量 + 8 函数 | 漏掉某个 import 名字 → ImportError | `pytest`（110 用例必须全过；含使用 `_next_step_key` 的 monkeypatch 用例） |
| **A2** | 新建 `workflow_prompts.py`；移动 C 块 | `_planner_prompt`、`_style_prompt`、`_build_memory_candidate` | `_create_memory_candidate` 仍留在 workflow_service.py（DB 触达），它会用 `workflow_prompts._build_memory_candidate` 拼正文；要保证名字回拉 | `pytest` 110 |
| **A3** | 新建 `workflow_extractors.py`；移动 D 块 | D 块共 9 个纯函数 | `_run_scene_workflow` 大量调用这些函数；调用方式不变（仍是模块级裸函数名） | `pytest` 110 |
| **A4**（保留判断点） | 评估是否进一步拆 E（DB 辅助） / G（runner）。如要拆，单独成 plan | — | 步骤工厂之间互相调用且与测试 patch 强耦合 | 视实际再定 |

### 7.5 不在本次范围内

- 不动 STEP_SEQUENCE 顺序、不改步骤名 / agent_label。
- 不动 `_run_scene_workflow` 内部分支与失败处理逻辑。
- 不动公开 API（`queue_scene_workflow` 等 7 个函数）签名与返回结构。
- 不动 ORM 字段 / Pydantic schema 形状。
- 不动后台 runner 行为（线程模型、轮询周期、lease 续约）。

## 8. T-6.B 拆分方案：ai_gateway_service.py（835 行 → 多文件）

### 8.1 现有职责矩阵

| 块 | 行号 | 内容 | 依赖 | 风险 |
|---|---|---|---|---|
| **A. 常量 + dataclass** | 24–169 | `_env_timeout_ms`、`GatewayCallResult`、`PROVIDER_FALLBACK_MATRIX`、`DEFAULT_PROFILES`、`PROVIDER_DEFAULTS`、`STEP_TIMEOUT_MS`、`FIXTURE_PROVIDER/MODEL/VERSION`、`CIRCUIT_BREAKER_THRESHOLD/COOLDOWN`、`_MODEL_PRICING_USD_PER_1K`、`PROVIDER_RUNTIME_STEPS` | 仅 stdlib + os.getenv | 极低 |
| **A1. 模块级 state** | 160–162 | `_REQUEST_WINDOWS`、`_PROFILE_RUNTIME_STATE`、`_PROVIDER_RUNTIME_STATE` | stdlib | **不拆**（测试直接 mutate 同一个 dict 对象） |
| **B. Profile 解析（DB）** | 172–227 | `_resolve_profiles`、`_matrix_rule`、`get_provider_matrix` | Session、DEFAULT_PROFILES、PROVIDER_FALLBACK_MATRIX | 中（`_resolve_profiles` 是 monkeypatch 主目标） |
| **C. 纯工具计算** | 230–277 | `_profile_to_dict`、`_runtime_profile_key`、`_utc_month_key`、`_provider_enabled`、`_estimate_cost_usd`、`_resolve_timeout_ms`、`_extract_text` | os.getenv、_MODEL_PRICING_USD_PER_1K、STEP_TIMEOUT_MS | 低 |
| **D. State 读写** | 280–301, 337–361, 375–407 | `_profile_runtime_state`、`_provider_runtime_state`、`_record_request/_success/_failure`、`_reset_gateway_runtime_state`、`_peek_*` | 三个 state dict、time.time | **不拆**（与 dict 强绑定，分离会让 monkeypatch 失败） |
| **E. Skip / 限流 / 熔断 reason** | 304–334, 364–372 | `_rate_limit_reason`、`_budget_reason`、`_circuit_reason`、`_skip_reason` | state dict + time | **不拆**（紧密依赖 state） |
| **F. 公开 state 查询** | 410–545 | `_runtime_open_until_iso`、`_remaining_cooldown_seconds`、`_known_provider_names`、`_step_runtime_profiles`、`get_provider_runtime_state`、`summarize_provider_runtime_state` | state + DB | 中（公开 API） |
| **G. Fixture 文本生成器** | 650–736 | `_fixture_attempt`、`_fixture_analyze_text`、`_fixture_write_text`、`_fixture_style_text`、`_fixture_planner_text`、`_fixture_check_text`、`_fixture_gateway_result` | 仅 GatewayCallResult、FIXTURE_* 常量 | 低 |
| **H. HTTP / Ollama 调用** | 572–647 | `_openai_compatible_generate`、`_call_provider` | httpx、ollama_generate、provider_settings_service、PROVIDER_DEFAULTS | 中（被 monkeypatch 直接替换） |
| **I. 主入口** | 739–835 | `call_ai_gateway` | 几乎所有上游 + state 写入 | 高（不拆） |

### 8.2 测试 monkeypatch 与直接读写的属性表面（必须保留可访问）

来自 `tests/services/ai_gateway_service_suite.py` 的 `gateway = ai_gateway_service` 模块属性访问：

- **`monkeypatch.setattr(gateway, ...)`**：`_resolve_profiles`、`_call_provider`、`_step_runtime_profiles`、`time`（标准库的 `time` 模块属性）
- **直接读写 `gateway.<attr>`**：`DEFAULT_PROFILES`、`CIRCUIT_BREAKER_THRESHOLD`、`_REQUEST_WINDOWS`、`_PROVIDER_RUNTIME_STATE`、`_PROFILE_RUNTIME_STATE`、`_runtime_profile_key`、`_utc_month_key`、`_reset_gateway_runtime_state`、`call_ai_gateway`、`get_provider_matrix`、`get_provider_runtime_state`、`summarize_provider_runtime_state`、`ProviderRuntimeStateResponse`、`ProviderRuntimeStepState`

**核心约束**：
1. 三个模块级 state dict（`_REQUEST_WINDOWS / _PROFILE_RUNTIME_STATE / _PROVIDER_RUNTIME_STATE`）**保持在 `ai_gateway_service.py` 不动**。它们被测试直接 `gateway._PROVIDER_RUNTIME_STATE["x"] = {...}` 这样赋值，要让所有读路径看到同一对象。
2. 拆出去的纯函数都要在 `ai_gateway_service.py` 顶部用 `from app.services.ai_gateway_<x> import <name>` 拉回（包括 `_estimate_cost_usd / _resolve_timeout_ms / _runtime_profile_key / _utc_month_key` 等被测试直接调用或被 record_*/peek_* 间接使用的纯函数）。
3. 拆出去的常量也要在 `ai_gateway_service.py` 拉回（`DEFAULT_PROFILES / CIRCUIT_BREAKER_THRESHOLD` 被测试直接读）。

### 8.3 阶段拆分（每阶段单独验证）

| 阶段 | 动作 | 风险 | 验证 |
|---|---|---|---|
| **B1** | 新建 `ai_gateway_constants.py`，移走 A 块（常量 + `GatewayCallResult` + `_env_timeout_ms`） | 极低（纯数据 + 1 个 env helper） | pytest 全过；workflow_constants 中 `from ... import FIXTURE_VERSION, GatewayCallResult` 仍可用 |
| **B2** | 新建 `ai_gateway_costing.py`，移走 C 块的纯函数：`_estimate_cost_usd`、`_resolve_timeout_ms`、`_extract_text`、`_runtime_profile_key`、`_utc_month_key`、`_provider_enabled` | 低 | pytest 全过；测试通过 `gateway._runtime_profile_key()` 等仍可用（import 拉回） |
| **B3** | 新建 `ai_gateway_fixtures.py`，移走 G 块全部 fixture 函数 | 低（自成一体，无 state，无外部 import） | pytest 全过 |
| **B4**（评估） | 是否再拆 H 块（HTTP / Ollama 调用） / B 块（profile 解析）。**保守默认不拆**，因为它们都是 monkeypatch 主目标，分离需要更细致的 import 表面验证。 | 中-高 | 视实际再定 |
| **B5+** | 模块级 state、record_*、reason_*、call_ai_gateway 主体均**不拆**。 | 高（强耦合 + monkeypatch） | — |

### 8.4 不在本次范围内（高风险冻结）

- 不动 `call_ai_gateway` 主循环结构（profile 迭代 + retry + state 记录是协调中枢）。
- 不动模块级 `_REQUEST_WINDOWS / _PROFILE_RUNTIME_STATE / _PROVIDER_RUNTIME_STATE` 的归属。
- 不动 `_resolve_profiles / _step_runtime_profiles`（DB 触达 + 公开 monkeypatch 入口）。
- 不动 `_record_request / _record_success / _record_failure`（与 state dict 强耦合）。
- 不动 `_skip_reason / _rate_limit_reason / _budget_reason / _circuit_reason`（依赖 state + time）。
- 不动 `get_provider_runtime_state / summarize_provider_runtime_state` 的签名。
- 不动 fixture 与 live 模式的边界（fixture 与 live 共享 `call_ai_gateway` 入口，许多测试依赖这一点）。

## 8.5 T-6.B4 拆分方案：ai_gateway_service.py（571 行 → 进一步拆）

### 8.5.1 当前职责矩阵（B1+B2+B3 后的 571 行重新测绘）

| 块 | 当前行号 | 内容 | 风险 |
|---|---|---|---|
| **import 头** | 1–42 | 标准库 + 6 schema/model + 3 已拆模块拉回 | — |
| **state dict** | 46–48 | `_REQUEST_WINDOWS / _PROFILE_RUNTIME_STATE / _PROVIDER_RUNTIME_STATE` | **不动** |
| **B 块 profile 解析** | 51–106 | `_resolve_profiles`(DB) / `_matrix_rule` / `get_provider_matrix` / `_profile_to_dict` | 中-高（B 块是 DB 触达 + monkeypatch 主目标） |
| **D 块 state init/read** | 129–150 | `_profile_runtime_state` / `_provider_runtime_state` | 中（lazy init state dict） |
| **E 块 skip-reason 链** | 153–221 | `_rate_limit_reason` / `_budget_reason` / `_circuit_reason` / `_skip_reason` | 中（读 state + time） |
| **D 块 record 写入** | 186–210 | `_record_request` / `_record_success` / `_record_failure` | 中-高（state dict 写入） |
| **D 块 reset** | 224–227 | `_reset_gateway_runtime_state` | **不动**（测试 monkeypatch 主目标，必须留可访问） |
| **F 块 state views** | 230–281 | `_peek_profile_runtime_state` / `_peek_provider_runtime_state` / `_runtime_open_until_iso` / `_remaining_cooldown_seconds` / `_known_provider_names` | 低 |
| **G 块 step profiles** | 284–295 | `_step_runtime_profiles` | 中（DB + monkeypatch 主目标） |
| **G 块 公开查询** | 298–394 | `get_provider_runtime_state` / `summarize_provider_runtime_state` | 中（公开 API + DB） |
| **H 块 HTTP/Ollama** | 397–472 | `_openai_compatible_generate` / `_call_provider` | 中-高（monkeypatch 主目标） |
| **I 块 主入口** | 475–571 | `call_ai_gateway` | **不动** |

### 8.5.2 跨模块的 state dict 访问难题

剩余可拆出的多组函数（D/E/F）都需要读或写 `_PROFILE_RUNTIME_STATE` / `_PROVIDER_RUNTIME_STATE` / `_REQUEST_WINDOWS`。这三个 dict **必须留在主模块**（测试直接 mutate 同一对象）。

子模块要访问主模块 dict，候选方案：
- **A. 参数注入**：函数签名增加 `state_dict: dict` 参数。改调用点（侵入大），但避免任何 import 顺序问题。
- **B. 顶层 import**：子模块顶部 `from app.services.ai_gateway_service import _PROFILE_RUNTIME_STATE`。Python 允许循环 import 在某些条件下成立（前提是被引用的名字在 import 之前已经定义），但**脆弱**。
- **C. lazy import（推荐）**：函数体内 `from app.services.ai_gateway_service import _PROFILE_RUNTIME_STATE`。每次调用都做（实际上 sys.modules 缓存，开销可忽略），完全避开 import 顺序问题。

测试影响（关键）：
- `dict.mutate`（`gateway._PROVIDER_RUNTIME_STATE["x"] = {...}`）：方案 C 下子模块每次 lazy import 拿到的是同一 dict 对象引用，mutation 在两边都可见 ✓
- `monkeypatch.setattr(gateway, "_PROVIDER_RUNTIME_STATE", new_dict)`：方案 C 下子模块下次调用会 lazy import 拿到 patched 后的 attribute 绑定 ✓（Python 的 `from X import Y` 在每次执行时都从 X.\_\_dict\_\_ 重新查 Y）
- `gateway._reset_gateway_runtime_state()` 调用 `_REQUEST_WINDOWS.clear()`：清空了同一 dict 对象，子模块的 lazy import 引用看到的是被清空后的状态 ✓

**结论**：方案 C（lazy import）满足所有现有测试 patch 模式，是最低侵入选择。

### 8.5.3 阶段拆分（每阶段单独验证）

| 阶段 | 动作 | 风险 | 注释 |
|---|---|---|---|
| **B4.1** | 新建 `ai_gateway_views.py`，移走 F 块 5 个函数：`_peek_profile_runtime_state` / `_peek_provider_runtime_state` / `_runtime_open_until_iso` / `_remaining_cooldown_seconds` / `_known_provider_names` | **低**：3 个零 state 函数 + 2 个 lazy-import 读 state 的 peek | F 块没有被任何测试直接 monkeypatch；只在 `get_provider_runtime_state` 内部被调用 |
| **B4.2** | 新建 `ai_gateway_skip_reason.py`，移走 E 块 4 个函数：`_rate_limit_reason` / `_budget_reason` / `_circuit_reason` / `_skip_reason` | **中**：读 state + time；`_skip_reason` 内部链 `_provider_enabled / _circuit_reason / _rate_limit_reason / _budget_reason` | 测试不直接 monkeypatch reason 链；它们仅在 `call_ai_gateway` 与 `get_provider_runtime_state` 内部被调用 |
| **B4.3**（保留判断点） | 视 B4.1/B4.2 稳定后再评估是否拆 D 块 record / state init / H 块 HTTP+Ollama | **中-高** | record 写入与 state dict 强绑定；H 块 `_call_provider` 是 monkeypatch 主目标 |

### 8.5.4 B4.1+B4.2 完成；下面进入 B4.3

B4.1+B4.2 已完成。剩余 B/D/H 三块进入 §8.6 的 B4.3 三阶段。

## 8.6 T-6.B4.3 拆分方案：剩余 487 行的 B/D/H 三块

### 8.6.1 当前 monkeypatch 关键约束（再次确认）

测试用 `monkeypatch.setattr(gateway, "<name>", ...)` 替换主模块属性的 3 个目标符号：
- `_resolve_profiles`（7 处）— B 块
- `_call_provider`（3 处）— H 块
- `_step_runtime_profiles`（3 处）— B 块

**正确性原理**：当符号被拆到子模块、再通过 `from app.services.ai_gateway_<x> import <name>` 在主模块拉回时，主模块命名空间里 `<name>` 是子模块函数对象的引用。`monkeypatch.setattr(gateway, "<name>", fake)` 只替换主模块 `__dict__` 里的绑定。**但调用方必须从主模块 namespace 解析这个名字**。

`call_ai_gateway` 留在主模块，内部 `_call_provider(...)` 走 LOAD_GLOBAL，从主模块 `__dict__` 取最新绑定 → monkeypatch 命中 ✓

`get_provider_runtime_state` 留在主模块，内部 `_step_runtime_profiles(...)` 同理 ✓

**风险点**：子模块内部对 monkeypatch 目标的调用不会被替换。需检查：
- `_step_runtime_profiles` 内部调 `_resolve_profiles`：如果二者在**同一**子模块，monkeypatch 替换主模块的 `_resolve_profiles` 不会影响子模块内部的同名调用

**应对策略**：B 块 `_step_runtime_profiles` 与 `_resolve_profiles` 放到**同一**子模块（routing），但子模块内部 `_step_runtime_profiles` 调 `_resolve_profiles` 时**走 lazy import 主模块**（`from app.services.ai_gateway_service import _resolve_profiles`），让 monkeypatch 在主模块的替换被看到。这是 B4.2 已验证的 lazy-import 模式。

### 8.6.2 阶段拆分（每阶段单独验证）

| 阶段 | 动作 | 风险 | 验证关键 |
|---|---|---|---|
| **B4.3.a** | 新建 `ai_gateway_provider.py`，移走 `_openai_compatible_generate` + `_call_provider` | **中**（`_call_provider` 是 monkeypatch 主目标） | `test_call_ai_gateway_opens_circuit_after_repeated_failures` 等 3 处用 setattr 替换 `_call_provider` 必须仍生效 |
| **B4.3.b** | 新建 `ai_gateway_state.py`，移走 D 块 5 个：`_profile_runtime_state` / `_provider_runtime_state` / `_record_request` / `_record_success` / `_record_failure` | **中**（D 块 state init/write 与 3 个 state dict 强绑定） | record_* 必须能写入主模块的 dict（lazy import 解决）；`_reset_gateway_runtime_state` 仍在主模块直接清空 dict |
| **B4.3.c** | 新建 `ai_gateway_routing.py`，移走 B 块 + 路由矩阵：`_resolve_profiles` / `_step_runtime_profiles` / `_profile_to_dict` / `_matrix_rule` / `get_provider_matrix` | **中-高**（_resolve_profiles + _step_runtime_profiles 都是 monkeypatch 主目标，且互相调用） | 测试中所有 7+3 处 monkeypatch.setattr 仍生效；`_step_runtime_profiles` 内部调 `_resolve_profiles` 用 lazy import 走主模块 |

### 8.6.3 始终不动（高风险冻结）

- 三个 state dict（`_REQUEST_WINDOWS / _PROFILE_RUNTIME_STATE / _PROVIDER_RUNTIME_STATE`）
- `_reset_gateway_runtime_state`（测试主入口，必须直接清空 dict）
- `call_ai_gateway` 主体（fixture 分流 + 重试循环 + 与 D 块 record_* 协作）
- `get_provider_runtime_state` / `summarize_provider_runtime_state`（公开 API 签名）
