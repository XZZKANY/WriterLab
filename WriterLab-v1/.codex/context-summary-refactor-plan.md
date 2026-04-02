## 项目上下文摘要（重构方案）

生成时间：2026-04-01 18:54:02

### 1. 相似实现分析

- **实现1**：`Next.js/frontend/app/editor/page.tsx`
  - 模式：单路由页内聚合多个领域状态、请求和调试能力
  - 可复用：现有编辑器中的 API 调用、面板拆分点、状态切片
  - 需注意：文件体积过大、职责混杂，是本次重构的首要拆分对象
- **实现2**：`fastapi/backend/app/services/workflow_service.py`
  - 模式：以服务为中心的工作流编排，承载步骤推进、恢复、取消、审查与运行时事件
  - 可复用：工作流状态机、步骤语义、恢复逻辑、运行时通知
  - 需注意：不能在重构中重写业务语义，应优先保留并外层整理边界
- **实现3**：`fastapi/backend/app/services/ai_gateway_service.py`
  - 模式：按能力路由 Provider，并处理预算、超时、重试、熔断
  - 可复用：Provider Matrix、调用策略、失败回退逻辑
  - 需注意：与工作流和设置模块耦合较深，适合下沉为稳定内核
- **实现4**：`fastapi/backend/app/services/context_service.py`
  - 模式：聚合角色、地点、设定、近期场景、知识检索结果形成上下文快照
  - 可复用：上下文编译链路、预算控制、快照结构
  - 需注意：这是后端核心价值模块，不应在前几阶段改写

### 2. 项目约定

- **命名约定**：前端以 `page.tsx`、`layout.tsx` 等 App Router 约定文件为入口；后端以 `snake_case` 文件名组织路由和服务
- **文件组织**：前端目前偏路由直连；后端目前偏 `api + services + models + schemas`
- **导入顺序**：整体以标准库、第三方、项目内模块递进
- **代码风格**：前端使用 TypeScript/React 函数组件；后端使用 FastAPI + SQLAlchemy + Pydantic

### 3. 可复用组件清单

- `fastapi/backend/app/models.py`：领域模型与表结构
- `fastapi/backend/app/alembic/`：迁移体系
- `fastapi/backend/app/services/workflow_service.py`：工作流编排内核
- `fastapi/backend/app/services/ai_gateway_service.py`：Provider 路由与调用策略
- `fastapi/backend/app/services/context_service.py`：上下文编译
- `fastapi/backend/app/services/knowledge_service.py`：知识检索与 style memory
- `fastapi/backend/app/services/consistency_service.py`：一致性扫描
- `fastapi/backend/app/services/smoke_report_service.py`：运行时自检与 Smoke 结果

### 4. 测试策略

- **测试框架**：后端为 `pytest`
- **测试模式**：单元测试 + API 合约测试 + 服务测试 + Smoke 脚本
- **参考文件**：
  - `fastapi/backend/tests/test_workflow_service.py`
  - `fastapi/backend/tests/test_ai_gateway_service.py`
  - `fastapi/backend/tests/test_context_service.py`
  - `fastapi/backend/tests/test_runtime_smoke_reports.py`
- **覆盖要求**：重构阶段至少保证工作流、Provider 路由、上下文编译、核心 API 与 Smoke 能力不回退

### 5. 依赖和集成点

- **外部依赖**：Next.js 16、React 19、FastAPI、SQLAlchemy、Alembic、httpx、psycopg
- **内部依赖**：前端通过 HTTP 调用后端；后端路由依赖服务层；服务层依赖模型、仓储式查询与运行时状态
- **集成方式**：FastAPI `APIRouter` 暴露接口；前端 App Router 页面与组件消费 API；脚本负责本地 Smoke
- **配置来源**：
  - `Next.js/frontend/package.json`
  - `fastapi/backend/requirements*.txt`
  - `fastapi/backend/app/main.py`

### 6. 技术选型理由

- **前端目录策略**：参考 Next.js App Router 的 route segment 和 colocate 组织方式，适合将页面入口与业务实现分离
- **后端目录策略**：参考 FastAPI “bigger applications” 模式，保留 `APIRouter`，但按领域与层次整理
- **总体方案**：优先保留后端稳定内核，先拆前端单体页，再整理后端边界，降低一次性推倒重建风险

### 7. 关键风险点

- **单页风险**：`app/editor/page.tsx` 过大，任何改动都容易牵动多个功能
- **占位风险**：`/project` 与 `/lore` 仍为占位页，信息架构尚未稳定
- **编码风险**：部分中文文本出现显示乱码，需要统一文件编码与展示链路
- **依赖风险**：`requirements.txt` 与 `requirements.codex.txt` 职责分裂，后续需要收敛
- **迁移风险**：后端同时存在 Alembic 与启动时 schema 修补逻辑，目录重组必须避免误伤数据路径

### 8. 外部资料

- **Context7 / Next.js 官方文档**：用于确认 App Router、route segment、嵌套路由与 colocate 组织建议
- **Context7 / FastAPI 官方文档**：用于确认大应用推荐组织方式、`APIRouter` 分组和分层组织边界
