## 操作日志

### 2026-04-01 18:54:02

#### 任务

- 产出 WriterLab-v1 重构方案文档，覆盖新目录结构、模块保留/删除策略、迁移顺序、验收与回滚边界

#### 编码前检查 - 重构方案文档

- 已查阅上下文摘要文件：`.codex/context-summary-refactor-plan.md`
- 将使用以下可复用组件：
  - `fastapi/backend/app/services/workflow_service.py`：作为后端稳定内核保留依据
  - `fastapi/backend/app/services/ai_gateway_service.py`：作为 Provider 路由与能力编排保留依据
  - `fastapi/backend/app/services/context_service.py`：作为上下文编译能力保留依据
  - `fastapi/backend/app/services/knowledge_service.py`：作为知识与记忆能力保留依据
- 将遵循命名约定：文档文件使用中文语义化名称，代码引用沿用仓库现有路径和命名
- 将遵循代码风格：前端按 Next.js App Router 入口约定描述，后端按 FastAPI `api/services/models/schemas` 现有习惯扩展为分层组织
- 确认不重复造轮子，证明：已检查现有 `docs/project-overview-zh.md`，本次新增文档聚焦“重构蓝图”，不重复“项目盘点”

#### 决策记录

- 决定采用“保留后端内核，重做前端壳层，分阶段迁移”的主路线
- 决定前端目标结构采用 `app + features + entities + shared + lib` 的分层组织
- 决定后端目标结构采用 `api + domain + services + repositories + schemas + tasks + infra` 的分层组织
- 决定优先拆分 `app/editor/page.tsx`，再补齐 `/project` 与 `/lore` 正式页面
- 决定在早期阶段尽量保持数据库表结构和核心 API 路径稳定，降低大改联动成本

#### 编码后声明 - 重构方案文档

### 1. 复用了以下既有组件

- `workflow_service.py`：用于界定“必须保留的工作流内核”
- `ai_gateway_service.py`：用于界定“必须保留的 Provider 路由内核”
- `context_service.py`：用于界定“必须保留的上下文编译内核”
- `knowledge_service.py`：用于界定“必须保留的知识检索与记忆能力”

### 2. 遵循了以下项目约定

- 命名约定：沿用现有前端 `app/*/page.tsx` 与后端 `app/api/*.py`、`app/services/*.py` 的路径表达
- 代码风格：未发明新运行时或新框架，仅在现有 Next.js / FastAPI 之上做结构重排
- 文件组织：方案文件写入 `docs/`，过程文件写入项目本地 `.codex/`

### 3. 对比了以下相似实现

- `Next.js/frontend/app/editor/page.tsx`：我的方案不再继续在路由页堆叠逻辑，而是拆到 `features` 和 `entities`
- `fastapi/backend/app/services/workflow_service.py`：我的方案不重写该服务，只调整其外围归属与依赖边界
- `fastapi/backend/app/main.py`：我的方案保留应用装配入口，但将注册和初始化逻辑逐步下沉

### 4. 未重复造轮子的证明

- 检查了 `docs/project-overview-zh.md`、`docs/runtime-notes.md`，确认现有文档没有系统性的重构蓝图
- 检查了前后端核心目录，确认不存在现成的“目标结构 + 迁移阶段 + 模块映射”文档

#### 工具链补充记录

- 已按要求使用 `sequential-thinking -> shrimp-task-manager -> 直接落盘` 的顺序执行
- `shrimp-task-manager.verify_task` 首次调用失败，原因是任务仍处于 `pending` 状态
- 继续尝试 `execute_task` 后发现其被上游规划任务状态阻挡
- 补救措施：保留任务规划结果，并改以本地文件核对完成最终验证；相关结果已写入 `.codex/verification-report.md`

### 2026-04-01 19:27:00

#### 任务

- 按 `docs/refactor-plan-zh.md` 实施首轮结构化重构，覆盖前端拆壳、正式页面入口、后端聚合路由/任务层兼容迁移、测试目录骨架和迁移映射文档

#### 编码前检查 - 重构实施

- 已查阅上下文摘要文件：`.codex/context-summary-refactor-plan.md`
- 将使用以下可复用组件：
  - `Next.js/frontend/app/editor/page.tsx`：迁移为 `features/editor/editor-workspace.tsx`
  - `fastapi/backend/app/api/*.py`：作为新 `api/routers/*` 的兼容协议来源
  - `fastapi/backend/app/services/*`：作为新 `services/*/*` 兼容出口来源
  - `scripts/check-backend.ps1`、`scripts/check-frontend.ps1`：作为阶段验收入口
- 将遵循命名约定：前端保持 `app/*/page.tsx` 路由约定，业务下沉到 `features/*` 与 `lib/api/*`；后端保持 `snake_case` 文件命名并新增 `api/routers`、`tasks`、`repositories`
- 将遵循代码风格：前端保持函数组件和 TypeScript strict；后端保持 FastAPI + SQLAlchemy + pytest 既有风格
- 确认不重复造轮子，证明：复用了现有 API URL、数据库模型、工作流服务和 smoke 脚本，没有另起新的协议或新运行时

#### 决策记录

- 决定通过“移动文件 + 薄装配页”的方式把 `editor` 从路由层剥离到 `features/editor/editor-workspace.tsx`
- 决定优先抽出 `lib/api/*`，确保页面与 feature 不再散落业务 `fetch`
- 决定先为 `/project`、`/lore`、`/runtime`、`/settings` 建立正式入口，再继续细化 editor 各子面板
- 决定后端先搭 `api/routers`、`tasks`、`repositories` 和 `services/*` 兼容层，不直接移动高风险内核文件
- 决定保留现有 `/api/*` 路径，避免协议层回归面扩大

#### 编码后声明 - 重构实施

### 1. 复用了以下既有组件

- `fastapi/backend/app/api/*.py`：继续承载真实协议实现，新 `api/routers/*` 只做聚合
- `fastapi/backend/app/services/workflow_service.py`：继续承载工作流内核，新 `services/workflow/*` 只做兼容出口
- `fastapi/backend/app/services/ai_gateway_service.py`、`context_service.py`、`knowledge_service.py`、`consistency_service.py`：均通过新子目录包装而非重写
- `scripts/check-backend.ps1`、`scripts/check-frontend.ps1`、`scripts/frontend_live_smoke.mjs`：直接作为本地回归入口复用

### 2. 遵循了以下项目约定

- 命名约定：前端路由目录沿用 App Router 约定，后端新文件沿用 `snake_case`
- 代码风格：前端继续使用 TypeScript/React 函数组件与 `@/*` 别名，后端继续使用 FastAPI `APIRouter`
- 文件组织：重构产生的过程文件仍写入项目本地 `.codex/`；正式迁移说明写入 `docs/refactor-migration-map-zh.md`

### 3. 对比了以下相似实现

- 原 `Next.js/frontend/app/editor/page.tsx`：当前改为薄路由页，实际工作区迁入 `features/editor/editor-workspace.tsx`
- 原 `fastapi/backend/app/main.py`：当前改为装配入口，启动顺序迁入 `app/tasks/startup_checks.py`
- 原 `fastapi/backend/app/api/*.py`：当前通过 `app/api/routers/*` 归组，但旧文件继续保留，避免测试和调用点断裂

### 4. 未重复造轮子的证明

- 检查并直接复用了现有项目、设定、场景、工作流、运行时、设置接口，没有新造平行 API
- 检查并复用了现有 pytest 与 smoke 验证链路，没有新增仓库外验证方式
- 检查并复用了现有核心服务语义，没有重写 workflow/context/knowledge/provider 内核

#### 本地验证结果

- `npm.cmd run typecheck`：通过
- `powershell -ExecutionPolicy Bypass -File scripts/check-frontend.ps1`：通过
- `powershell -ExecutionPolicy Bypass -File scripts/check-frontend.ps1 -LiveUiSmoke`：通过
- `..\\..\\.venv\\Scripts\\python.exe -m pytest tests\\test_api_routes.py tests\\test_workflow_service.py`：33 项通过
- `powershell -ExecutionPolicy Bypass -File scripts/check-backend.ps1`：通过

---

## 第二轮收尾记录

时间：2026-04-01 20:42:31

### 编码前检查

- 已查阅上下文摘要文件：`D:\WritierLab\WriterLab-v1\.codex\context-summary-refactor-plan-round2.md`
- 将使用以下可复用组件：
  - `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\editor\editor-workspace.tsx`：作为第二轮 editor 装配事实来源。
  - `D:\WritierLab\WriterLab-v1\Next.js\frontend\lib\api\client.ts`：作为“页面不再直接 fetch”的边界事实来源。
  - `D:\WritierLab\WriterLab-v1\fastapi\backend\app\repositories\project_repository.py`：作为 repository 路由迁移事实来源。
  - `D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1` 与 `D:\WritierLab\WriterLab-v1\scripts\check-backend.ps1`：作为本地验证入口。
- 将遵循命名约定：前端沿用 App Router 文件命名；后端沿用 `snake_case` 模块命名；文档留痕统一使用简体中文。
- 将遵循代码风格：本轮只追加 markdown 留痕，不改动既有代码风格。
- 确认不重复造轮子，证明：直接复用现有验证脚本、现有 editor 组件与既有后端服务，不引入新的验证链路或新协议。

### 证据采集记录

- 当前环境 `rg` 不可用，第二轮检索改用 PowerShell 的 `Get-Content`、`Get-ChildItem`、`Select-String`。
- 已确认 `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\editor\` 下存在以下四个目标文件：
  - `workspace-header.tsx`
  - `writing-pane.tsx`
  - `versions-pane.tsx`
  - `sidebar-panels.tsx`
- 已确认仓库根误写目录 `D:\WritierLab\Next.js` 仅包含上述四个组件副本，可安全清理。

### 决策记录

- 决定为第二轮单独新建 `context-summary-refactor-plan-round2.md`，而不是覆盖旧摘要文件。
- 决定对 `operations-log.md` 和 `verification-report.md` 采用尾部追加，避免破坏已有历史内容和乱码证据。
- 决定在日志中明确记录 `editor-workspace.tsx` 采用“重建而非继续修补”的方式恢复可编译状态。
- 决定把第二轮后端 repository 迁移点明确写入留痕：
  - `projects.py -> list_projects`
  - `books.py -> list_books_by_project`
  - `chapters.py -> list_chapters_by_book`
  - `characters.py -> list_characters_by_project`
  - `locations.py -> list_locations_by_project`
  - `lore_entries.py -> list_lore_entries_by_project`
  - `scenes.py -> list_scenes_by_chapter`、`get_scene_record`、`list_scene_version_records`

### 编码后声明

#### 1. 复用了以下既有组件

- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\editor\editor-workspace.tsx`：用于说明 editor 工作区已经从路由页中抽离。
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\lib\api\client.ts`：用于证明请求入口已经统一到 `lib/api/*`。
- `D:\WritierLab\WriterLab-v1\fastapi\backend\app\repositories\project_repository.py`：用于证明后端查询入口已开始向 repository 下沉。
- `D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1`、`D:\WritierLab\WriterLab-v1\scripts\check-backend.ps1`：用于复用既有本地验证能力。

#### 2. 遵循了以下项目约定

- 命名约定：新增文档文件名沿用既有 `.codex/context-summary-*.md` 风格。
- 代码风格：未对现有实现风格做改写，只补充中文 markdown 留痕。
- 文件组织：所有本轮工作文件继续写入项目本地 `.codex/`，没有写入全局目录。

#### 3. 对比了以下相似实现

- 对比 `D:\WritierLab\WriterLab-v1\.codex\context-summary-refactor-plan.md`：本轮没有重写旧摘要，而是新增 round2 摘要，目的是避免覆盖历史内容。
- 对比 `D:\WritierLab\WriterLab-v1\Next.js\frontend\app\editor\page.tsx`：当前留痕聚焦其已瘦身后的装配职责，而不是再回到单页大组件模式。
- 对比 `D:\WritierLab\WriterLab-v1\fastapi\backend\app\main.py`：当前留痕强调其装配职责收敛，与任务层分离保持一致。

#### 4. 未重复造轮子的证明

- 检查了现有前端与后端验证脚本，继续使用既有命令，不新增并行的手工验证文档体系。
- 检查了现有 editor 和 repository 代码，当前只把事实整理为文档，没有再造新的中间抽象层。
- 检查了误写目录内容，确认仅为已回收组件副本，因此采用清理而非继续保留。

---

## 第三轮收尾记录

时间：2026-04-01 21:08:32

### 编码前检查

- 已查阅上下文摘要文件：`D:\WritierLab\WriterLab-v1\.codex\context-summary-refactor-plan-round3.md`
- 已分析的相似实现至少包括：
  - `D:\WritierLab\WriterLab-v1\fastapi\backend\app\main.py`
  - `D:\WritierLab\WriterLab-v1\fastapi\backend\app\api\routers\project.py`
  - `D:\WritierLab\WriterLab-v1\fastapi\backend\app\repositories\scene_repository.py`
  - `D:\WritierLab\WriterLab-v1\fastapi\backend\app\services\workflow\workflow_service.py`
- 已查询 Context7 官方文档：FastAPI 大应用推荐使用 `APIRouter` 分模块组织，并推荐用 `lifespan` 统一承接启动资源管理。
- 确认第三轮不改 `/api/*` 协议，不改数据库模型，只收敛后端内部目录职责。

### 决策记录

- 决定把 `main.py` 从 `@app.on_event("startup")` 切换为 `lifespan`，继续收敛装配边界。
- 决定把以下真实实现迁入子目录，并让旧顶层文件变成兼容层：
  - `workflow_service -> services/workflow/workflow_service.py`
  - `ai_gateway_service -> services/ai/ai_gateway_service.py`
  - `context_service -> services/context/context_service.py`
  - `knowledge_service -> services/knowledge/knowledge_service.py`
  - `consistency_service -> services/consistency/consistency_service.py`
  - `smoke_report_service -> services/runtime/smoke_report_service.py`
- 决定兼容层使用“模块别名”而不是简单 `import *`，因为 `test_workflow_service.py` 会 monkeypatch 旧模块路径中的内部函数。
- 决定继续把 `scene/version` 的读取下沉到 `scene_repository.py`，并让 `api/ai.py`、`api/consistency.py`、`api/scenes.py` 复用这些读取入口。

### 执行记录

- 已更新 `D:\WritierLab\WriterLab-v1\fastapi\backend\app\main.py`，使用 `lifespan` 装配启动流程。
- 已把旧顶层服务文件改为兼容入口，并把 `tasks/startup_checks.py`、`tasks/smoke_report_jobs.py`、`api/runtime.py` 等调用点切到新子目录路径。
- 已更新 `services/workflow/workflow_service.py`、`services/context/context_service.py`、`services/ai/provider_matrix.py`、`services/context/context_snapshot_builder.py`、`services/knowledge/retriever.py`、`services/knowledge/style_memory_service.py`，减少对子层外旧路径的反向依赖。
- 已在 `repositories/scene_repository.py` 新增 `get_scene_version()`，并让相关路由复用 repository 读取。

### 调试与修复记录

- 第一次 pytest 回归失败，原因是旧顶层兼容层仅做名字重导出，导致 monkeypatch 旧模块时无法影响新模块内部全局变量。
- 解决方式：把旧顶层 `app.services.*` 文件改为 `sys.modules[__name__] = 新模块对象` 的模块别名兼容层。
- 修复后关键 pytest 全部恢复通过。

### 编码后声明

#### 1. 复用了以下既有组件

- `D:\WritierLab\WriterLab-v1\fastapi\backend\app\tasks\startup_checks.py`：继续承载启动序列。
- `D:\WritierLab\WriterLab-v1\fastapi\backend\app\api\routers\*.py`：继续承载领域路由聚合。
- `D:\WritierLab\WriterLab-v1\fastapi\backend\app\repositories\scene_repository.py`：承载场景域读取入口。
- `D:\WritierLab\WriterLab-v1\scripts\check-backend.ps1`：作为本地体检验证链路。

#### 2. 遵循了以下项目约定

- 命名约定：后端目录与文件继续使用 `snake_case`。
- 文件组织：实现放入 `services/<domain>/`，旧顶层文件只保留兼容层职责。
- 架构边界：`main.py` 只做装配，业务逻辑不回流主入口。

#### 3. 未重复造轮子的证明

- 没有新增新的 API 路径或新协议，仍使用现有 `/api/*`。
- 没有新造第二套 workflow 或 runtime 逻辑，只是把真实实现迁入既定目录并保留旧导入兼容。
- 没有新建额外验证脚本，全部复用现有 pytest 与 `check-backend.ps1`。

---

## 第四轮收尾记录

时间：2026-04-01 21:23:20

### 编码前检查

- 已查阅上下文摘要文件：`D:\WritierLab\WriterLab-v1\.codex\context-summary-refactor-plan-round4.md`
- 已分析的相似实现包括：
  - `D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_api_routes.py`
  - `D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_workflow_service.py`
  - `D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1`
  - `D:\WritierLab\WriterLab-v1\scripts\frontend_live_smoke.mjs`
  - `D:\WritierLab\WriterLab-v1\docs\refactor-migration-map-zh.md`
- 确认第四轮不直接搬迁根层测试文件，避免 pytest 重复收集和命令入口回退。
- 确认优先增强脚本覆盖和目录说明骨架，而不是引入新的测试框架。

### 决策记录

- 决定为后端 `tests/api`、`tests/services`、`tests/runtime` 和前端 `tests/features`、`tests/smoke` 新增 README，而不是继续保留空 `.gitkeep` 骨架。
- 决定把 `frontend_live_smoke.mjs` 从单页 `/editor` 检查升级为五路由矩阵检查。
- 决定保留 `check-frontend.ps1` 和 `check-backend.ps1` 作为统一入口，不新建平行脚本。
- 决定继续对历史乱码文档采用尾部追加，而不是整体重写。

### 执行记录

- 已新增五个测试目录 README，明确根层入口保留策略、目录职责和推荐命令。
- 已更新 `scripts/check-frontend.ps1`，使 `-LiveUiSmoke` 直接检查站点根地址。
- 已重写 `scripts/frontend_live_smoke.mjs`，当前覆盖 `/editor`、`/project`、`/lore`、`/runtime`、`/settings`。
- 第一次 live smoke 失败，原因是 `/editor` 并不使用 `AppShell`，因此不应强制检查通用导航标记。
- 已修正 smoke 条件：`/editor` 只检查 editor 专属标记，其余正式页面继续检查通用导航和路由专属标记。

### 编码后声明

#### 1. 复用了以下既有组件

- `D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1`：继续作为前端验证入口。
- `D:\WritierLab\WriterLab-v1\scripts\check-backend.ps1`：继续作为后端体验证入口。
- `D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_api_routes.py` 与 `test_workflow_service.py`：继续作为关键 pytest 入口。
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\app-shell.tsx`：作为正式页面通用 smoke 标记的事实来源。

#### 2. 遵循了以下项目约定

- 继续保留根层 `test_*.py` 作为现有 pytest 直接入口。
- 所有第四轮新增说明和日志均使用简体中文。
- 所有留痕仍写入项目本地 `.codex/`。

#### 3. 未重复造轮子的证明

- 没有引入新的测试框架，只增强了现有 smoke 脚本。
- 没有新建额外检查入口，仍使用 `check-frontend.ps1` 和 `check-backend.ps1`。
- 没有强搬测试文件到新目录，避免制造第二套并行测试体系。

---

## 第四轮延续记录

时间：2026-04-01 21:55:53

### 延续目标

- 补齐统一的本地验证说明文档
- 为前后端 `tests/` 根目录补索引 README
- 不移动真实测试文件，只增强可交接性

### 新增文档

- `D:\WritierLab\WriterLab-v1\docs\local-verification-zh.md`
- `D:\WritierLab\WriterLab-v1\fastapi\backend\tests\README.md`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\tests\README.md`

### 决策记录

- 决定不继续扩展脚本实现，而是把第四轮已有结果汇总成统一文档，降低新人接手成本。
- 决定继续保留根层 `test_*.py` 作为稳定入口，在根目录 README 中显式说明这一点。
- 决定复用上一轮刚通过的前后端验证结果，不为纯文档变更重复跑完整业务回归。

### 复用证明

- 统一验证说明完全复用了现有 `check-frontend.ps1`、`frontend_live_smoke.mjs`、`check-backend.ps1`、`backend_full_smoke.py` 的事实入口。
- tests 根目录索引复用了前面已经补好的分类 README，而不是再造一套平行说明。

### 最小复核

- 已确认三份新增文档创建成功并可读取。
- 已复用本轮稍早通过的验证结果：
  - 前端 `typecheck` 通过
  - 前端 `check-frontend.ps1` 通过
  - 前端 `check-frontend.ps1 -LiveUiSmoke` 通过
  - 后端关键 pytest 通过
  - 后端 `check-backend.ps1` 通过

---

## 第四轮继续：首批测试迁移记录

时间：2026-04-01 21:55:53

### 目标

- 在不改变现有 pytest 命令的前提下，开始把真实测试内容迁入分类目录。
- 验证“根层薄入口 + 分类目录 `*_suite.py`”这条迁移路线是否可行。

### 执行结果

- 已新增：
  - `D:\WritierLab\WriterLab-v1\fastapi\backend\tests\api\api_routes_suite.py`
  - `D:\WritierLab\WriterLab-v1\fastapi\backend\tests\services\workflow_service_suite.py`
- 已将根层入口改为薄包装：
  - `D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_api_routes.py`
  - `D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_workflow_service.py`
- 已更新 tests 相关 README，说明首批真实 suite 已落入分类目录。

### 关键决策

- 分类目录中的真实测试文件使用 `*_suite.py` 命名，而不是 `test_*.py`，避免 pytest 自动重复收集。
- 根层入口采用 `runpy.run_path()` 加载分类 suite，避免引入包结构依赖。
- 继续保持 `pytest tests\\test_api_routes.py tests\\test_workflow_service.py` 可直接运行。

### 验证结果

- `D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_api_routes.py D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_workflow_service.py`
  - 结果：33 个测试全部通过
  - 备注：仍有 6 条 Pydantic `Config` 弃用警告

---

## 第四轮继续：第二批测试迁移记录

时间：2026-04-01 21:55:53

### 迁移范围

- `test_ai_gateway_service.py`
- `test_context_service.py`
- `test_runtime_smoke_reports.py`

### 真实 suite 去向

- `D:\WritierLab\WriterLab-v1\fastapi\backend\tests\services\ai_gateway_service_suite.py`
- `D:\WritierLab\WriterLab-v1\fastapi\backend\tests\services\context_service_suite.py`
- `D:\WritierLab\WriterLab-v1\fastapi\backend\tests\runtime\runtime_smoke_reports_suite.py`

### 兼容策略

- 根层同名 `test_*.py` 文件继续保留，并通过 `runpy.run_path()` 加载分类目录真实 suite。
- 分类目录真实文件继续使用 `*_suite.py` 命名，避免 pytest 重复收集。

### 验证结果

- `D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_ai_gateway_service.py D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_context_service.py D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_runtime_smoke_reports.py`
  - 结果：24 个测试全部通过
  - 备注：伴随 3 条 Pydantic `Config` 弃用警告

---

## 项目详情页动态路由参数修复记录

时间：2026-04-02 00:28:03

### 编码前检查 - 项目详情页动态路由参数修复

□ 已查阅上下文摘要文件：`.codex/context-summary-project-detail-route-fix.md`
□ 将使用以下可复用组件：
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-detail.tsx`：复用项目详情聚合视图
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-hub.tsx`：复用项目列表到详情页的跳转入口
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\lib\api\projects.ts`：复用项目、书籍、章节请求
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\lib\api\scenes.ts`：复用场景请求
□ 将遵循命名约定：动态路由页继续使用 PascalCase 页面导出函数，API 请求继续使用 `fetch*`
□ 将遵循代码风格：`app/*` 只做路由装配，`features/*` 负责页面能力，TypeScript 与 React 风格保持一致
□ 确认不重复造轮子，证明：已检查 `app/project/[projectId]/*`、`features/project/*`、`lib/api/*`，本轮只修复参数读取和空值保护，不新增并行实现

### 事实证据

- `D:\WritierLab\WriterLab-v1\Next.js\frontend\package.json` 显示当前前端使用 Next.js `16.2.1`
- Context7 的 Next.js 16 官方文档明确要求 App Router 动态路由 `page.tsx` 使用 `params: Promise<...>` 并 `await params`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\app\project\[projectId]\page.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\app\project\[projectId]\books\page.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\app\project\[projectId]\chapters\page.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\app\project\[projectId]\scenes\page.tsx`
  - 以上 4 个动态路由页均已改为异步读取 `params`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-detail.tsx`
  - 已增加空 `projectId` 保护，避免请求 `/api/books?project_id=undefined`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-hub.tsx`
  - 详情入口通过 `Link href={`/project/${project.id}`}` 生成真实 UUID 路径

### 执行步骤

1. 复核项目详情页相关文件，确认 4 个动态路由页补丁仍在，`ProjectDetail` 的空值保护仍在
2. 复核 `scripts/check-frontend.ps1` 与 `scripts/frontend_live_smoke.mjs`，确认项目前端标准验证入口
3. 临时启动本地前端 dev 服务，在 3000 端口完成验证后关闭
4. 运行 `powershell -ExecutionPolicy Bypass -File scripts/check-frontend.ps1 -LiveUiSmoke`
5. 使用真实 UUID `04290b27-d6aa-409a-b8fd-87a6b8d7618e` 定向检查：
   - `/project/04290b27-d6aa-409a-b8fd-87a6b8d7618e`
   - `/project/04290b27-d6aa-409a-b8fd-87a6b8d7618e/books`
   - `/project/04290b27-d6aa-409a-b8fd-87a6b8d7618e/chapters`
   - `/project/04290b27-d6aa-409a-b8fd-87a6b8d7618e/scenes`
6. 确认 4 条路径均返回 HTTP 200，响应中包含真实 UUID，且不再包含 `project_id=undefined`

### 编码后声明 - 项目详情页动态路由参数修复

### 1. 复用了以下既有组件

- `project-detail.tsx`：继续承担详情聚合加载，只在开头增加空参数短路
- `project-hub.tsx`：继续提供项目详情入口，无需新增导航实现
- `lib/api/projects.ts` 与 `lib/api/scenes.ts`：继续作为唯一请求入口

### 2. 遵循了以下项目约定

- 命名约定：动态路由页仍使用 `ProjectDetailPage`、`ProjectBooksPage`、`ProjectChaptersPage`、`ProjectScenesPage`
- 代码风格：路由页保持薄装配，业务聚合仍在 `features/project/project-detail.tsx`
- 文件组织：没有把请求逻辑塞回 `app/*`，仍沿用 `app/* -> features/* -> lib/api/*`

### 3. 对比了以下相似实现

- `app/project/[projectId]/page.tsx` 与 3 个子路由页：本次统一采用同一套异步 `params` 模式，避免主路由和子路由行为分裂
- `project-hub.tsx`：本次没有新增其他详情入口，而是继续复用现有列表页跳转方式
- `project-detail.tsx`：本次没有另起详情组件，而是在现有聚合加载逻辑上补齐边界保护

### 4. 未重复造轮子的证明

- 已检查 `features/project`、`lib/api/projects.ts`、`lib/api/scenes.ts`、`scripts/check-frontend.ps1`
- 本轮没有新增新的 API 封装、页面容器或 smoke 脚本，只修复现有路由参数边界并复用既有验证入口

### 本地验证结果

- `npm.cmd run typecheck`
  - 结果：通过
- `powershell -ExecutionPolicy Bypass -File 'D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1' -LiveUiSmoke`
  - 结果：通过
- 定向详情页 HTTP 验证
  - 结果：`/project/[projectId]` 及 books/chapters/scenes 4 条路径均返回 200
  - 结果：响应包含真实 UUID `04290b27-d6aa-409a-b8fd-87a6b8d7618e`
  - 结果：响应不再包含 `project_id=undefined`

### 残余风险

- 当前定向验证基于本地前端服务端输出与 HTTP 响应，不是浏览器交互级自动化
- 本轮没有处理 `project-detail.tsx` 与 `project-hub.tsx` 中历史乱码文案，该问题仍建议单独清理

---

## 项目页乱码误判复核记录

时间：2026-04-02 00:40:33

### 复核目标

- 确认 `project-hub.tsx`、`project-detail.tsx` 与 `app-shell.tsx` 是否存在真实源码乱码
- 区分“终端显示错码”与“UTF-8 文件内容损坏”
- 决定是否需要继续修改项目页中文文案

### 编码前检查

□ 已查阅上下文摘要文件：`.codex/context-summary-project-page-encoding-check.md`
□ 已参考既有实现：
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-hub.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-detail.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\app-shell.tsx`
□ 已确认本轮不改 API 路径、不改数据流，只做源码编码与页面响应复核

### 执行步骤

1. 使用 Python 按 UTF-8 读取目标文件，并输出 `unicode_escape` 片段复核真实文案
2. 核对 `project-hub.tsx`、`project-detail.tsx`、`app-shell.tsx` 中的标题、描述、导航标签
3. 临时启动本地前端 dev 服务
4. 请求 `/project` 与真实 `/project/04290b27-d6aa-409a-b8fd-87a6b8d7618e` 页面，检查响应层中文关键字
5. 运行 `npm.cmd run typecheck`
6. 关闭本地 dev 服务，避免残留进程

### 事实结论

- `project-hub.tsx` 实际包含正常中文文案，如“项目工作台”“项目总览”“暂无项目说明。”
- `project-detail.tsx` 实际包含正常中文文案，如“项目详情”“结构摘要”“返回项目列表”“打开编辑器”
- `app-shell.tsx` 实际包含正常导航标签，如“项目”“编辑器”“设定库”“运行时”“设置”
- 之前在 PowerShell 直接 `Get-Content` 中看到的乱码，是终端输出编码问题，不是源码文件损坏
- 因此本轮没有修改任何业务源码，避免把正常中文误改成真正的问题

### 本地验证结果

- UTF-8 + `unicode_escape` 复核
  - 结果：源码中的中文文案正常
- `Invoke-WebRequest http://127.0.0.1:3000/project`
  - 结果：HTTP 200
  - 结果：响应命中“项目工作台”“项目总览”
  - 结果：未命中 `project_id=undefined`
- `Invoke-WebRequest http://127.0.0.1:3000/project/04290b27-d6aa-409a-b8fd-87a6b8d7618e`
  - 结果：HTTP 200
  - 结果：响应命中“项目详情”“结构摘要”“返回项目列表”“打开编辑器”
  - 结果：未命中 `project_id=undefined`
- `npm.cmd run typecheck`
  - 结果：通过

### 更正说明

- 上一轮把“历史乱码文案仍然存在”列为残余风险，这一判断已被本轮证据推翻
- 正确结论应为：源码中文正常，需注意的是终端查看方式，而不是前端文案本身

---

## Claude 风格项目管理页实现记录

时间：2026-04-02 00:54:47

### 编码前检查 - Claude 风格项目管理页

□ 已查阅上下文摘要文件：`.codex/context-summary-project-claude-layout.md`
□ 将使用以下可复用组件与接口：
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-hub.tsx`：保留项目列表数据加载入口
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\lib\api\projects.ts`：继续使用 `fetchProjects`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\app-shell.tsx`：参考现有一级导航信息架构
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\home-dashboard.tsx`：参考标题区与 CTA 节奏
□ 将遵循命名约定：页面级组件保持 PascalCase，数据请求继续使用 `fetch*`
□ 将遵循代码风格：React + Tailwind 原子类，不引入额外样式文件
□ 确认不重复造轮子：保留真实项目数据、详情跳转与前端检查脚本，只替换 `/project` 的视觉布局

### 执行步骤

1. 读取 `project-hub.tsx`、`app-shell.tsx`、`home-dashboard.tsx`、`package.json` 与 `globals.css`
2. 确认当前 `/project` 仍是浅色入口页，`lucide-react` 依赖尚未声明
3. 安装 `lucide-react`
4. 重写 `features/project/project-hub.tsx`，实现 Claude / Shadcn 风格暗色项目管理布局
5. 保留真实项目数据加载、搜索过滤、详情跳转与导航链接
6. 运行 `typecheck`、`check-frontend.ps1` 与 `check-frontend.ps1 -LiveUiSmoke`
7. 根据 smoke 结果补齐缺失导航链接后重新验证

### 编码后声明 - Claude 风格项目管理页

### 1. 复用了以下既有能力

- `fetchProjects`：继续读取真实项目数据
- `/project/${project.id}`：继续作为项目详情入口
- Geist 字体：继续使用 `app/layout.tsx` 注入的系统无衬线字体方案
- 既有前端检查脚本：继续复用 `check-frontend.ps1` 与 `frontend_live_smoke.mjs`

### 2. 这次新增或调整的内容

- `project-hub.tsx` 改为独立暗色布局，包含侧边栏、标题区、搜索栏和项目卡片网格
- 新增 `lucide-react` 依赖，用于 `Search`、`Plus`、`MoreVertical`、`FolderKanban` 等图标
- 新页面显式保留 `/project`、`/editor`、`/lore`、`/runtime`、`/settings` 导航入口，兼容现有 smoke

### 3. 本地验证结果

- `npm.cmd run typecheck`
  - 结果：通过
- `powershell -ExecutionPolicy Bypass -File 'D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1'`
  - 结果：通过
- `powershell -ExecutionPolicy Bypass -File 'D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1' -LiveUiSmoke`
  - 首次结果：失败，原因是新侧边栏缺少 `/lore` 与 `/settings` 链接
  - 修正后结果：通过

### 4. 风险与后续建议

- 当前只重构了 `/project` 入口页，`/project/[projectId]` 详情页仍沿用现有结构；如果要统一成整套 Claude 风格，下一步可以继续扩展详情页
- 右上角 `MoreVertical` 目前是视觉操作点，还没有挂接具体菜单行为；若需要可再补 Shadcn 风格下拉菜单

---

## 统一暗色项目工作区壳层记录

时间：2026-04-02 01:14:20

### 编码前检查 - 统一暗色项目工作区壳层

□ 已查阅上下文摘要文件：`.codex/context-summary-workspace-dark-shell.md`
□ 已参考至少 3 个既有实现：
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\app-shell.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\info-card.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-hub.tsx`
□ 已确认本轮优先复用 shared/ui，不改 API 路径与数据流
□ 已确认 `LiveUiSmoke` 依赖 `WriterLab` 和 5 个主导航链接，侧边栏必须保留这些入口

### 执行步骤

1. 读取 `AppShell`、`InfoCard`、`ProjectHub`、`ProjectDetail`、`RuntimeHub`、`SettingsHub`、`LoreHub`
2. 确认多个业务页都依赖 `AppShell`，适合从共享层统一改造
3. 新增 `shared/ui/workspace-shell.tsx` 作为暗色项目工作区壳层
4. 让 `AppShell` 改为复用 `WorkspaceShell`
5. 让 `InfoCard` 切到暗色卡片风格
6. 重写 `ProjectHub`，使其复用共享暗色壳层，并把侧边栏语义改成项目相关内容
7. 运行 `typecheck`、`check-frontend.ps1`、`check-frontend.ps1 -LiveUiSmoke`

### 编码后声明 - 统一暗色项目工作区壳层

### 1. 复用了以下既有能力

- `AppShell` 的标题/描述/actions/children 接口没有变
- `InfoCard` 继续作为各页面内容容器，只更新视觉风格
- `fetchProjects` 继续驱动 `/project` 项目数据加载
- 现有前端 smoke 脚本继续作为统一验证入口

### 2. 这次新增或调整的内容

- 新增 `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\workspace-shell.tsx`
- `AppShell` 改为包装新的 `WorkspaceShell`
- `InfoCard` 改为深色卡片与低对比边框
- `ProjectHub` 改为复用共享壳层，不再单独维护另一套侧边栏
- 侧边栏语义调整为：新建项目、搜索项目、项目总览、项目列表、写作编辑、设定资料、运行诊断、偏好设置

### 3. 本地验证结果

- `npm.cmd run typecheck`
  - 结果：通过
- `powershell -ExecutionPolicy Bypass -File 'D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1'`
  - 结果：通过
- `powershell -ExecutionPolicy Bypass -File 'D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1' -LiveUiSmoke`
  - 结果：通过
  - 报告：`D:\WritierLab\WriterLab-v1\scripts\logs\frontend-live-smoke-20260402-011405.json`

### 4. 残余风险与后续建议

- 这轮已经把共享壳层和项目入口统一到同一暗色工作区，但部分页面内部的细粒度内容块仍保留旧的浅色 utility class 组合，后续可以继续逐页压暗
- 如果下一步要继续提升一致性，最值得做的是统一 `project-detail.tsx`、`runtime-hub.tsx`、`settings-hub.tsx`、`lore-hub.tsx` 内部的按钮、标签和次级卡片颜色

---

## Claude 暗色业务页继续统一记录

时间：2026-04-02 01:35:40

### 编码前检查 - Claude 暗色业务页继续统一

□ 已查阅上下文摘要文件：`.codex/context-summary-claude-dark-pages-round2.md`
□ 已参考至少 3 个既有实现：
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\workspace-shell.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\info-card.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-hub.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-detail.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\runtime\runtime-hub.tsx`
□ 将使用以下可复用组件：
- `AppShell`：继续承载页面标题区与 actions 插槽
- `InfoCard`：继续作为统一暗色内容卡片
- `fetchProviderSettings` / `updateProviderSettings` / `fetchProjects` / `fetchLoreEntries` / `fetchHealth`：保持既有数据协议不变
□ 将遵循命名约定：页面级组件保持 PascalCase，数据请求继续使用 `fetch*` / `update*`
□ 将遵循代码风格：React + Tailwind 原子类；深色块统一使用 `text-zinc-*`、`border-white/8`、`bg-[#171717/#1d1d1d/#212121]`
□ 确认不重复造轮子：直接复用共享壳层与现有暗色页面模式，不新建第二套 UI 抽象
□ 工具说明：当前会话没有 `github.search_code`，本轮以本地现有实现分析为主

### 执行步骤

1. 读取 `workspace-shell.tsx`、`info-card.tsx`、`project-hub.tsx`、`project-detail.tsx`、`runtime-hub.tsx`
2. 读取 `settings-hub.tsx`、`lore-hub.tsx`、`lore-library-page.tsx`、`home-dashboard.tsx`
3. 定位浅色 `stone` / `white` utility class 残留点
4. 重写设置页、设定总览页、设定子页和首页概览页的按钮、输入框、摘要块、列表卡、空态与错误态
5. 把仍残留的英文展示文案同步调整为中文
6. 根据新页面文案同步更新 `frontend_live_smoke.mjs` 的运行时和设置页标记
7. 串行运行 `npm.cmd run typecheck`、`check-frontend.ps1` 与 `check-frontend.ps1 -LiveUiSmoke`

### 编码后声明 - Claude 暗色业务页继续统一

### 1. 复用了以下既有能力

- `WorkspaceShell`：继续提供暗色侧边栏和标题区
- `AppShell`：继续承接页面标题、描述和操作区
- `InfoCard`：继续提供统一卡片容器和语义色块
- `project-hub.tsx`：继续作为暗色搜索栏、CTA 按钮和空态块的样式参考
- `project-detail.tsx` 与 `runtime-hub.tsx`：继续作为列表卡、错误块和统计块的样式参考
- `check-frontend.ps1` 与 `frontend_live_smoke.mjs`：继续作为本地前端验证入口

### 2. 这次新增或调整的内容

- `settings-hub.tsx` 改为暗色 Provider 配置面板，统一按钮、输入框、状态 pill 和反馈块
- `lore-hub.tsx` 改为暗色项目上下文与设定摘要总览
- `lore-library-page.tsx` 改为暗色数据列表页，补齐空态和“正典/非正典”标识
- `home-dashboard.tsx` 改为暗色 CTA、迁移摘要块和后端状态区
- `runtime-hub.tsx` 与 `workspace-shell.tsx` 的残留英文界面文案同步改成中文
- `frontend_live_smoke.mjs` 的运行时页、设置页标记同步更新为中文

### 3. 本地验证结果

- `npm.cmd run typecheck`
  - 结果：通过
- `powershell -ExecutionPolicy Bypass -File 'D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1'`
  - 结果：通过
- `powershell -ExecutionPolicy Bypass -File 'D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1' -LiveUiSmoke`
  - 首次结果：失败，原因是 smoke 仍匹配旧的英文页面标记
  - 修正后结果：通过
  - 报告：`D:\WritierLab\WriterLab-v1\scripts\logs\frontend-live-smoke-20260402-013443.json`

### 4. 风险与后续建议

- 本轮已经把主要业务页内部控件统一到暗色工作区，但 `/editor` 内部仍保留一部分旧的调试语义和英文标记，后续若继续统一视觉，优先从编辑器子面板继续拆
- `frontend_live_smoke.mjs` 仍有 `/editor` 的旧英文标记要求；如果后续继续中文化编辑器界面，需要同步更新这部分规则

---

## 按建议文档调整项目工作区记录

时间：2026-04-02 02:17:10

### 编码前检查 - 按建议文档调整项目工作区

□ 已查阅上下文摘要文件：`.codex/context-summary-suggestion-driven-project-shell.md`
□ 已查阅外部建议来源：`D:\记事本\建议.md`
□ 已参考至少 3 个既有实现：
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\workspace-shell.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-hub.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-detail.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\lore\lore-hub.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\editor\editor-workspace.tsx`
□ 将使用以下可复用能力：
- `WorkspaceShell`：调整全局导航语义
- `AppShell` / `InfoCard`：维持项目页暗色布局骨架
- `fetchProjects` / `fetchBooksByProject` / `fetchLoreEntries`：保持既有数据流
□ 将遵循命名约定：继续沿用 `fetch*` / `update*`、页面组件 PascalCase、Tailwind 原子类暗色模式
□ 确认不重复造轮子：不新增路由和后端接口，只重组入口语义、卡片交互和项目内工作台
□ 工具说明：当前会话无 `github.search_code`，本轮依据本地建议文档和仓库现有实现完成

### 执行步骤

1. 读取 `D:\记事本\建议.md`，提炼“项目内入口”“模型设置”“hover 三点菜单”等要求
2. 读取 `workspace-shell.tsx`、`project-hub.tsx`、`project-detail.tsx`、`lore-hub.tsx`、`editor-workspace.tsx`
3. 收口全局侧栏，移除未落地快操作，去掉全局“写作编辑”“设定资料”，并将“偏好设置”改名为“模型设置”
4. 重写 `project-hub.tsx`，实现 hover 才显示的三点按钮和展开菜单
5. 重写 `project-detail.tsx`，增加左侧“写作台功能”区，把写作编辑、设定资料、书籍、章节、场景入口收回项目内
6. 让 `lore-hub.tsx` 与 `lore-library-page.tsx` 支持通过 `?projectId=` 预选项目
7. 因 Next 16 对 `useSearchParams()` 的 suspense 约束，改为浏览器端读取查询参数
8. 同步更新 `frontend_live_smoke.mjs` 的公共导航标记
9. 串行执行 `typecheck`、`check-frontend.ps1` 与 `check-frontend.ps1 -LiveUiSmoke`

### 编码后声明 - 按建议文档调整项目工作区

### 1. 复用了以下既有能力

- `WorkspaceShell`：继续作为全局工作区壳层，只调整导航配置
- `AppShell` 与 `InfoCard`：继续承载项目页和设定页的暗色布局
- `project-detail.tsx` 原有书籍/章节/场景数据加载逻辑：完整保留
- `lore-hub.tsx` / `lore-library-page.tsx` 原有项目选择与设定拉取逻辑：完整保留
- `editor-workspace.tsx` 现有查询参数模式：用于验证项目内跳转透传上下文的可行性

### 2. 这次新增或调整的内容

- 全局侧栏删除未落地的新建项目/搜索项目快操作
- 全局侧栏删除“写作编辑”“设定资料”一级入口，并把“偏好设置”改成“模型设置”
- `project-hub.tsx` 增加 hover 才显示的三点按钮与展开菜单
- `project-detail.tsx` 改为带左侧“写作台功能”的项目内工作台
- `lore-hub.tsx` 与 `lore-library-page.tsx` 支持从 `?projectId=` 预选项目
- `settings-hub.tsx` 和首页文案同步改成“模型设置”
- `frontend_live_smoke.mjs` 的公共导航标记改为当前这套项目中心化导航

### 3. 本地验证结果

- `npm.cmd run typecheck`
  - 结果：通过
- `powershell -ExecutionPolicy Bypass -File 'D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1'`
  - 首次结果：通过，但此前在并发验证时出现过 “Another next build process is already running”，已改为串行执行规避
  - 最终结果：通过
- `powershell -ExecutionPolicy Bypass -File 'D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1' -LiveUiSmoke`
  - 首次结果：构建中暴露 `useSearchParams()` suspense 约束
  - 修正后结果：通过
  - 报告：`D:\WritierLab\WriterLab-v1\scripts\logs\frontend-live-smoke-20260402-021645.json`

### 4. 风险与后续建议

- 本轮已经把“项目内入口”和“卡片交互”按建议落地，但 `editor-workspace.tsx` 的内部视觉仍然基本保持旧布局；如果继续按建议推进，下一步应直接重构编辑器内部工作台
- 项目卡片的“归档项目”“删除项目”当前提供的是展开菜单与占位反馈，若后端后续提供实际接口，可继续接上真实动作
