## 项目上下文摘要（第三轮后端分层收口）

生成时间：2026-04-01 21:08:32

### 1. 相似实现分析

- **实现1**：`D:\WritierLab\WriterLab-v1\fastapi\backend\app\main.py`
  - 模式：主入口只负责 FastAPI app 初始化、中间件、`include_router` 和启动装配。
  - 可复用：继续把启动流程留在 `app/tasks/startup_checks.py`，主入口不承载业务细节。
  - 需注意：FastAPI 官方已更推荐 `lifespan` 管理启动与关闭资源，适合继续收敛装配边界。
- **实现2**：`D:\WritierLab\WriterLab-v1\fastapi\backend\app\api\routers\project.py`
  - 模式：按领域聚合旧 `api/*.py` 路由，而不是在 `main.py` 里逐个引入所有细分路由。
  - 可复用：`project/story/lore/workflow/runtime/settings/health` 的聚合方式已经成型。
  - 需注意：第三轮应保持 `/api/*` 外部路径不变，只整理内部目录边界。
- **实现3**：`D:\WritierLab\WriterLab-v1\fastapi\backend\app\repositories\scene_repository.py`
  - 模式：把场景与版本读取逻辑从路由层下沉到 repository。
  - 可复用：`get_scene`、`list_scenes_by_chapter`、`list_scene_versions` 等读取入口。
  - 需注意：本轮可以继续补充 `get_scene_version`，减少 route 中直接 `db.query(...)`。
- **实现4**：`D:\WritierLab\WriterLab-v1\fastapi\backend\app\services\workflow\workflow_service.py`
  - 模式：工作流主编排已经是独立实现文件，适合成为新目录下的真实实现位置。
  - 可复用：旧顶层 `app.services.workflow_service` 可改为兼容入口，而不是继续保留真实实现。
  - 需注意：测试会 monkeypatch 旧路径模块，因此兼容层必须保留旧行为，不只是简单重导出名字。

### 2. 项目约定

- **命名约定**：后端目录与文件继续使用 `snake_case`，服务子目录按领域命名。
- **分层约定**：`main.py` 负责装配；`api/routers` 聚合路由；`repositories` 负责 ORM 读取；`services/<domain>` 负责业务实现；`tasks` 负责启动与运维任务。
- **兼容策略**：旧顶层服务路径在过渡期继续保留，但应退化为兼容层，而不是继续承载真实实现。

### 3. 可复用组件清单

- `D:\WritierLab\WriterLab-v1\fastapi\backend\app\tasks\startup_checks.py`：启动阶段的 schema 校验、升级、恢复和 runner 启动。
- `D:\WritierLab\WriterLab-v1\fastapi\backend\app\api\routers\__init__.py`：领域路由统一出口。
- `D:\WritierLab\WriterLab-v1\fastapi\backend\app\repositories\scene_repository.py`：场景域读取入口。
- `D:\WritierLab\WriterLab-v1\fastapi\backend\app\services\workflow\workflow_service.py`：工作流真实实现。
- `D:\WritierLab\WriterLab-v1\scripts\check-backend.ps1`：后端本地体检链路。

### 4. 测试策略

- **关键 pytest**：
  - `D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_api_routes.py D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_workflow_service.py`
- **体检脚本**：
  - `powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\check-backend.ps1`
- **覆盖重点**：
  - 旧导入路径兼容不回退
  - `main.py` 装配入口仍可启动
  - 关键 API 与 workflow 编排行为不变

### 5. 依赖和集成点

- **FastAPI 官方依据**：
  - Context7 `/fastapi/fastapi` 文档确认大应用推荐使用 `APIRouter` 分模块组织。
  - Context7 文档同时指出 `lifespan` 是比旧 `startup/shutdown` 事件更推荐的资源初始化方式。
- **内部依赖**：
  - `main.py -> app.api.routers -> app.api.*`
  - `main.py -> app.tasks.startup_checks`
  - `app.api.* -> repositories + services`
  - 旧顶层 `app.services.*` 继续作为兼容导入入口

### 6. 技术选型理由

- 第三轮不改外部 API，也不大改数据库模型，而是优先让目录职责名副其实。
- 把真实实现迁入 `services/<domain>/`，旧路径变成兼容层，更符合原重构计划，也更便于后续继续切换调用点。
- `lifespan` 比 `@app.on_event("startup")` 更贴合 FastAPI 现行推荐实践，同时仍然保持主入口极薄。

### 7. 关键风险点

- 旧路径兼容层如果只是 `import *`，测试里的 monkeypatch 不会作用到真实实现模块，需要模块别名式兼容。
- 第三轮只继续下沉了部分读取查询，`branches.py`、`knowledge.py` 等仍有直接 `db.query(...)`，后续还可继续仓储化。
- 现有 pytest 仍伴随 6 条 Pydantic `Config` 弃用警告，这不是本轮阻塞项，但属于技术债。
