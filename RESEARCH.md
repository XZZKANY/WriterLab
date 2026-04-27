# 项目研究记录

> 在本仓库内调研得到的、不直接体现在代码 / git log 中的事实与判断。日期标 ISO 8601。

## 2026-04-27

### 1. 项目用途与现状

- **领域**：长篇小说创作的 AI 工作台（不是通用办公写作工具）。
- **覆盖范围**：项目/书/章节/场景对象管理 → 角色/地点/世界观/知识/风格记忆上下文 → 多阶段 AI 工作流（分析/写作/润色/规划/审查）→ 一致性扫描 / 分支对比 / 版本恢复 / VN 导出预览。
- **运行形态**：本地运行（PostgreSQL + pgvector + 本地 Ollama + 可选云 Provider），不是 SaaS。
- **当前阶段**：根据 `docs/superpowers/specs/` 与 `plans/` 的迭代节奏，phase-3（timeline/version/branch）与 phase-4（workflow/context/runtime）已陆续推进。前端定位仍是"工作台 / 调试台"，非最终用户产品。

### 2. 技术栈实测

| 层 | 实测版本 | 说明 |
|---|---|---|
| Python | 3.10.11 | venv 在 `WriterLab-v1/fastapi/backend/.venv/`（注意：不是 `WriterLab-v1/.venv/`，README 早期版本写错了路径） |
| FastAPI | 0.135.2 | |
| Starlette | 1.0.0 | |
| Pydantic | 2.12.5 | 全部 schema 已用 pydantic v2 ConfigDict 风格 |
| SQLAlchemy | 2.0.43 | 用 DeclarativeBase 新风格 |
| psycopg | 3.2.10 | URL 用 `postgresql+psycopg://...` |
| psycopg2-binary | 2.9.10 | 同时安装；alembic env 可能需要 |
| pgvector | 由 `pgvector-src/` 编译 | 失败时 `knowledge_service` 用 cosine 后备 |
| Node | 22.15.0 | 已经 npm install |
| Next.js | 16.2.1 | **有破坏性变更**；frontend 目录下 `AGENTS.md` 明确要求"读 `node_modules/next/dist/docs/`" |
| React | 19.2.4 | |
| TypeScript | ^5（实际 tsc 由 node_modules 提供） | tsconfig 使用 `@/*` path alias 指向 `./` |
| Tailwind CSS | 4 | 使用 `@tailwindcss/postcss` |

### 3. 安装 / 启动 / 测试 / 构建命令实测可跑

```powershell
# 后端依赖（新机器）
& 'D:\WritierLab\WriterLab-v1\fastapi\backend\.venv\Scripts\python.exe' -m pip install -r 'D:\WritierLab\WriterLab-v1\fastapi\backend\requirements.txt'

# 后端启动（必须有可访问的 PostgreSQL，且 alembic 已迁移）
& 'D:\WritierLab\WriterLab-v1\fastapi\backend\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir 'D:\WritierLab\WriterLab-v1\fastapi\backend'

# 后端测试（不依赖真实 DB；使用 in-memory 或 mock）
cd D:\WritierLab\WriterLab-v1\fastapi\backend
.venv\Scripts\python.exe -m pytest                            # 110 passed

# 前端依赖（新机器）
cd D:\WritierLab\WriterLab-v1\Next.js\frontend
npm install

# 前端启动
npm run dev -- --hostname 127.0.0.1 --port 3000

# 前端类型检查
node ./node_modules/typescript/bin/tsc --noEmit               # 干净

# 前端契约测试（原生 node:test，无 jest）
for /f %f in ('dir /b tests\features\*.test.mjs') do node tests\features\%f

# 前端构建
npm run build                                                 # Windows 受限 shell 下可能 spawn EPERM；脚本已视为环境 caveat
```

### 4. 关键模块速读（按重要性）

**后端**：

- `app/main.py`：直接 include 所有路由，14 行就能看完所有 URL 命名空间归属。
- `app/services/workflow_service.py`：核心。`STEP_SEQUENCE = [analyze, plan, write, style, check, guard, store, memory]`。`_run_scene_workflow` 是主调度；`_workflow_runner_loop` 后台线程；`recover_expired_workflow_runs` 启动期扫救。
- `app/services/ai_gateway_service.py`：**所有 AI 调用唯一出口**。`call_ai_gateway(profile, prompt, params, *, task_type, workflow_step)` → 内部按 `_resolve_profiles` 找匹配 profile，跑 `_call_provider`，记录 `_record_request/_record_success/_record_failure`，触发熔断与预算守卫。`get_provider_runtime_state` 是诊断快照。
- `app/services/context_service.py`：场景上下文编译。组合：scope 解析（最近场景）+ 角色/地点/lore 命中 + 时间线邻近事件 + 风格记忆 + pgvector 检索。结果作为 `ContextCompileSnapshot` 落进 workflow run。
- `app/services/knowledge_service.py`：知识文档分块 + 向量检索。pgvector 不可用时用纯 Python cosine 后备。
- `app/services/consistency_service.py`：规则与 LLM 复核混合扫描，产出 `ConsistencyIssue`。

**前端**：

- `app/`：极薄页面，主要把 `features/<page>` 直接渲染。
- `features/editor/editor-workspace.tsx`：作者写作台主组件，700+ 行。`use-authoring-workspace` / `use-scene-context` / `use-versioning-workspace` 三个 hook 提供主要状态。
- `features/runtime/runtime-debug-workbench.tsx`：运行诊断主台。**测试中提到的多个英文区块名（Workflow Debug / Smoke Console / Provider Matrix / Context Compiler）实际是 `<h2>` 标题的字面量**；运行时就绪度块用了中文标题（`运行时就绪度`）。
- `lib/api/client.ts`：唯一的 fetch 封装。所有 `lib/api/*.ts` 都通过它。

### 5. 易踩的"知识与代码不一致"

- **`WriterLab-v1/.venv/` 不存在**；旧 README 的启动命令 `& 'D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe' ...` 会失败。真实 venv 在 `WriterLab-v1/fastapi/backend/.venv/`。
- **`requirements.txt`（重写前）严重缺依赖**：缺 SQLAlchemy/alembic/psycopg/dotenv/pytest/httpx/Mako 等。本轮已修。
- **`db/session.py` 之前 `echo=True` 写死**：每次启动 / 每条 SQL 都打印；本轮已改为 `DATABASE_ECHO` 环境变量驱动。
- **services / api/routers 之前的双层结构**是半成品迁移：调用方实际只走扁平路径，子包层是 dead weight。本轮已收口。
- **`runtime-debug-workbench.test.mjs` 与真实组件文案不一致**（`Provider Runtime` ↔ `运行时就绪度`）。本轮已修。
- **`api-client.test.mjs` 用 Node 原生 import 跑 `.ts` 文件**，永远报 `ERR_UNKNOWN_FILE_EXTENSION`。本轮重写为源码契约风格。

### 6. 文档存量与价值

`.codex/` 与 `docs/` 都堆了大量历史材料，几条最有价值的：

- `WriterLab-v1/docs/project-overview-zh.md`：最完整的中文项目盘点（数据模型 + API 总览）。
- `WriterLab-v1/docs/runtime-notes.md`：启动顺序、smoke 报告位置、Windows EPERM caveat。
- `WriterLab-v1/docs/local-verification-zh.md`：前后端验证顺序与 smoke 覆盖范围。
- `docs/superpowers/specs/2026-04-24-repository-restructure-design.md` + `plans/2026-04-24-repository-restructure-plan.md`：仓库结构 `apps/docs/scripts` 重组完整方案，未实施。
- `.codex/operations-log.md` / `verification-report.md`：phase-3/4 的开发留痕，按 AGENTS.md 重型流程产出，量大但已成历史档案。

### 7. 历史产物盘点（仓库根）

| 路径 | 性质 | 是否在 .gitignore | 处理建议 |
|---|---|---|---|
| `pgvector-src/` | pgvector 源码 + 构建产物 | 是 | 装机历史，建议确认装机文档后清理 |
| `vs_BuildTools.exe` | 4.5 MB 安装器 | 是 | 同上 |
| `install-pgvector.cmd` | pgvector 安装脚本 | 是 | 同上 |
| `codex_probe.obj` | codex 探针生成物 | 是 | 可清理 |
| `uvicorn-8012.{out,err}.log` | 空日志文件 | 是（`uvicorn-*.log`） | 可清理 |
| `logs/` | 历史日志目录 | 是 | 可清理 |
| `.npm-cache/`, `.pytest_cache/` | 缓存 | 是 | 可清理 |
| `.worktrees/` | 本地 git worktree | 是 | 保留 |

清理这些属于"删大量文件"，按用户最新指引必须先确认。

### 8. 后续重型重构应当避免的坑

- **不要先动 `app/main.py` 的 import 顺序**：lifespan 内 `run_startup_sequence` 依赖 `app/db/session` 的 engine 已经创建；如果把 startup_checks 上移到 import-time 会让单测崩。
- **不要轻易合并 alembic 迁移与 `db/schema_upgrades.py`**：后者是非破坏式 patch（CREATE TABLE IF NOT EXISTS 类），混入 alembic 后可能让回滚链断裂。等 schema 稳定后再合。
- **不要把 `fixture` 模式的处理逻辑从 `ai_gateway_service` 单独拆出**：fixture 与 live 走完全相同的 `call_ai_gateway` 入口，许多测试依赖这一点。拆开会大幅增加 mock 表面积。
- **前端契约测试是断字符串 + import 路径**：拆 sub-component 时要保证测试断言到的标识符（如 `setBusyKey("loadWorkflow")`）继续出现在指定文件中。否则会破测试。
- **拆出 workflow_service 的子模块要"回拉名字"**：`workflow_service.py` 的测试用 `monkeypatch.setattr("app.services.workflow_service.<name>", ...)` 字符串路径替换 18+ 个私有符号。任何拆出的符号都必须在 workflow_service.py 顶部用 `from app.services.workflow_<x> import <name>` import 回来；否则 monkeypatch 失效但测试还是会"看似通过"。

### 9. T-6 拆分后的工作流模块速记

经过 T-6.A1 / A2 / A3，workflow 调用链如下：

- `app/services/workflow_constants.py`（115 行）：步骤顺序、agent 元数据、配置常量、纯小工具
- `app/services/workflow_prompts.py`（60 行）：planner / style prompt 与候选记忆文本拼接
- `app/services/workflow_extractors.py`（128 行）：步骤快照解析与最终输出组装
- `app/services/workflow_service.py`（774 行）：DB 触达辅助 + `_run_scene_workflow` 主引擎 + 后台 runner + 公开 API

调用方仍然只需要 `from app.services.workflow_service import ...` 一行；上述 4 个文件的拆分是物理拆分，逻辑命名空间不变。

### 9.1 T-6.B 拆分后的 ai_gateway 模块速记（含 B4.1 / B4.2）

经过 T-6.B1 / B2 / B3 / B4.1 / B4.2，ai_gateway 调用链如下：

- `app/services/ai_gateway_constants.py`（163 行）：常量 + dataclass + `_env_timeout_ms`
- `app/services/ai_gateway_costing.py`（74 行）：6 个纯计算工具
- `app/services/ai_gateway_fixtures.py`（110 行）：smoke fixture 模式下的确定性文本生成器
- `app/services/ai_gateway_views.py`（84 行）：5 个只读视图函数（_peek_* + 3 个零 state 辅助）。两个 _peek_* 用 lazy import 读主模块 state dict
- `app/services/ai_gateway_skip_reason.py`（76 行）：4 个决策链（rate_limit / budget / circuit / skip_reason）。lazy import 主模块 _REQUEST_WINDOWS 与 D 块函数
- `app/services/ai_gateway_service.py`（487 行）：state 字典 + state init/read（D 块）+ record_* + DB profile 解析 + HTTP 调用 + 公开入口

**关键不变量**：
- `_REQUEST_WINDOWS / _PROFILE_RUNTIME_STATE / _PROVIDER_RUNTIME_STATE` 三个 state 字典**必须留在 ai_gateway_service.py**。测试 `gateway._PROVIDER_RUNTIME_STATE["ollama"] = {...}` 直接 mutate；分离会让多个模块持有不同对象。
- 拆出的常量/纯函数都在 `ai_gateway_service.py` 顶部用 `from app.services.ai_gateway_<x> import <name>` 拉回。
- views / skip_reason 子模块的 import 必须放在主模块 state dict 与 D 块函数（`_profile_runtime_state / _provider_runtime_state`）定义之后；标 `# noqa: E402`。
- views / skip_reason 内部用 **lazy import**（函数体内）访问主模块 state，避开循环 import 加载顺序问题。Python 的 `from X import Y` 每次执行都从 X.\_\_dict\_\_ 重新查 Y，所以测试的 monkeypatch + dict mutation 在两边都能命中。
- `_resolve_profiles / _call_provider / _step_runtime_profiles` 是测试 monkeypatch 主目标，**目前留在主模块不动**。

### 9.2 进一步拆分的高风险点（剩余 T-6.B4.3 / T-6.A4 候选，需独立 plan）

- ai_gateway_service 的 H 块（HTTP / Ollama 调用 `_openai_compatible_generate / _call_provider`）：被测试 monkeypatch.setattr 直接接管，分离要重新审视
- ai_gateway_service 的 state 写入（`_record_request / _record_success / _record_failure`）与 D 块 init（`_profile_runtime_state / _provider_runtime_state`）：与三个 state 字典强绑定，写入逻辑与熔断阈值强耦合
- ai_gateway_service 的 B 块 profile 解析（`_resolve_profiles / _step_runtime_profiles / _profile_to_dict`）：DB 触达 + monkeypatch 主目标
- workflow_service 的 DB 辅助层（`_create_run / _set_run_state / _create_step / _finish_step / _stable_resume_checkpoint`）：互相调用且与 ORM commit 节奏强耦合
- workflow_service 的后台 runner（`_workflow_runner_loop / _claim_next_workflow_run`）：模块级 `_WORKFLOW_RUNNER_LOCK` + `_WORKFLOW_RUNNER_STARTED` 状态

### 10. 测试套件覆盖（截至 T-6.B4 后续维护）

后端 pytest 总数从 110 增长到 **353**（+243）。新覆盖的纯函数模块：

- workflow_constants / workflow_extractors / workflow_prompts（T-6.A 拆出的）
- runtime_status_service / runtime_events / scene_status_service / provider_settings_service
- vn_export_service / style_negative_service / ai_prompt_templates
- scene_version_service（带 FakeQuery / FakeDB）
- branch_service 边界与错误路径
- scene_write_service / scene_revise_service / scene_analysis_service 的 helper 函数
- ai_gateway_constants / ai_gateway_costing / ai_gateway_fixtures（T-6.B 拆出的）
- **ai_gateway_views / ai_gateway_skip_reason（T-6.B4.1 / B4.2 拆出的）**

这些直测让 T-6 后续阶段（A4 / B4.3 进一步拆分）的拆分有了更扎实的"安全网"。
