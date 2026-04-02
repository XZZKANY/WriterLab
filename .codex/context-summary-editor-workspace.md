## 项目上下文摘要（editor-workspace）

生成时间：2026-04-02 14:33:12

### 1. 相似实现分析

- **实现1**: `D:/WritierLab/WriterLab-v1/Next.js/frontend/shared/ui/workspace-shell.tsx`
  - 模式：统一暗色工作区壳层
  - 可复用：页面标题、侧栏导航、操作区布局
  - 需注意：标题、副标题和 actions 已经形成固定视觉节奏，不应再额外套壳
- **实现2**: `D:/WritierLab/WriterLab-v1/Next.js/frontend/features/project/project-hub.tsx`
  - 模式：项目列表页在 `AppShell` 内组合搜索、排序和卡片网格
  - 可复用：项目类型定义、菜单展开模式、列表加载/错误状态
  - 需注意：原删除动作是占位，接真功能时要保留现有卡片交互结构
- **实现3**: `D:/WritierLab/WriterLab-v1/fastapi/backend/tests/api/api_routes_suite.py`
  - 模式：FastAPI `TestClient + monkeypatch + dependency_overrides`
  - 可复用：路由级单测写法、假数据库注入、返回体断言
  - 需注意：后端删除能力应先由测试锁定接口契约，再进入实现
- **实现4**: `D:/WritierLab/WriterLab-v1/fastapi/backend/app/api/projects.py`
  - 模式：`router + Depends(get_db) + repository alias`
  - 可复用：创建/列表接口组织方式
  - 需注意：删除路由应沿用同一组织方式，不新建额外 service 层

### 2. 项目约定

- **命名约定**: 前端 `camelCase`，React 组件 `PascalCase`；后端函数 `snake_case`
- **文件组织**: 路由入口在 `app/**/page.tsx`；页面实现放在 `features/**`；后端采用 `api + repositories + models + schemas`
- **导入顺序**: 先框架/第三方，再本地模块
- **代码风格**: 前端使用 Tailwind 内联类名和函数组件；后端使用显式 repository 调用与 Pydantic schema

### 3. 可复用组件清单

- `D:/WritierLab/WriterLab-v1/Next.js/frontend/shared/ui/app-shell.tsx`: 项目域页面公共壳层
- `D:/WritierLab/WriterLab-v1/Next.js/frontend/shared/ui/workspace-shell.tsx`: 统一暗色工作区样式
- `D:/WritierLab/WriterLab-v1/Next.js/frontend/lib/api/client.ts`: `apiGet/apiPost/apiPut/apiPatch` 请求封装，已在本轮补 `apiDelete`
- `D:/WritierLab/WriterLab-v1/Next.js/frontend/features/editor/use-editor-runtime-workbench.ts`: 编辑器 runtime/provider/smoke 状态管理
- `D:/WritierLab/WriterLab-v1/fastapi/backend/tests/api/api_routes_suite.py`: 后端 API 路由单测模式

### 4. 测试策略

- **测试框架**: 后端 `pytest + FastAPI TestClient`；前端使用 `typecheck + eslint + frontend_live_smoke + build`
- **测试模式**: 路由单测 + 页面活体 smoke + 生产构建检查
- **参考文件**:
  - `D:/WritierLab/WriterLab-v1/fastapi/backend/tests/api/api_routes_suite.py`
  - `D:/WritierLab/WriterLab-v1/scripts/frontend_live_smoke.mjs`
- **覆盖要求**: 删除接口契约、项目页与创建页稳定标记、编辑器入口可渲染

### 5. 依赖和集成点

- **前端依赖**: Next.js 16、React 19、`lucide-react`
- **后端依赖**: FastAPI、SQLAlchemy、Pydantic
- **集成方式**:
  - 前端通过 `lib/api/projects.ts` 访问 `/api/projects`
  - 后端通过 `app/api/projects.py` 暴露接口，通过 `project_repository.py` 落库
- **配置来源**:
  - 前端 API 基址：`NEXT_PUBLIC_API_BASE_URL` 或 `http://127.0.0.1:8000`
  - 前端构建验证：`D:/WritierLab/WriterLab-v1/scripts/check-frontend.ps1`

### 6. 技术选型理由

- **为什么沿用 `AppShell/WorkspaceShell`**: 现有项目已经建立统一工作区视觉，不需要再引入新壳层
- **为什么删除逻辑放在 repository**: 后端已有 `router -> repository` 模式，保持职责清晰且便于复测
- **为什么显式清理依赖数据**: 代码搜索确认多个模型只定义了 `ForeignKey`，未建立 ORM 级联关系

### 7. 关键风险点

- **外键链复杂**: `project -> books/scenes/branches/documents/workflow_runs -> chapters/scene_versions/knowledge_chunks/workflow_steps...`
- **页面风格断层**: 编辑器左侧主面板和右侧诊断栏此前均保留浅色卡片，需要同时收敛
- **仓库遗留 lint 问题**: 全量 `npm run lint` 仍被 `D:/WritierLab/WriterLab-v1/Next.js/frontend/fork-test.js` 阻塞，与本轮改动无关
### 8. 本轮缺点修复补充

- **优先级判断**：
  - 第一优先：`lib/api/client.ts` 响应解析，直接影响错误提示与 `204 No Content` 兼容性
  - 第二优先：`sidebar-panels.tsx` 暗色工作区可读性，直接影响编辑台可用性
  - 第三优先：`app/schemas/*.py` 的 Pydantic v2 弃用配置，会持续制造升级噪音
  - 第四优先：`project_repository.py` 删除链路的维护性，属于中长期技术债收敛
- **新增可复用模式**：
  - `model_config = ConfigDict(from_attributes=True)`：后端 ORM 响应 schema 的统一写法
  - `_collect_ids / _delete_matching / _delete_by_ids`：项目删除清理的集中式工具函数
  - 深色告警卡片模式：`border-*-400/15 + bg-*-500/10 + text-*-100`
- **新增验证模式**：
  - 前端用源码级回归测试锁住已知浅色 class 回退
  - 后端用子进程导入 schema，显式阻断 `class Config` 弃用回归
