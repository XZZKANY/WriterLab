# WriterLab 本地验证说明

本文档用于统一说明当前仓库的本地验证入口、推荐执行顺序、smoke 覆盖范围和已知环境限制。

## 1. 验证目标

当前本地验证分为两层：

- 快速验证：用于确认本轮改动没有破坏主要构建、关键路由和核心 API。
- 完整 smoke：用于确认联调链路、运行时状态和多页面入口仍能跑通。

## 2. 推荐执行顺序

### 前端

1. 类型检查

```powershell
cd D:\WritierLab\WriterLab-v1\Next.js\frontend
npm.cmd run typecheck
```

2. 前端检查脚本

```powershell
powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1
```

3. 前端 live smoke

```powershell
powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1 -LiveUiSmoke
```

### 后端

1. 关键 pytest

```powershell
D:\WritierLab\WriterLab-v1\fastapi\backend\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_api_routes.py D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_workflow_service.py
```

2. 后端检查脚本

```powershell
powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\check-backend.ps1
```

3. 后端完整 smoke

```powershell
powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\check-backend.ps1 -FullSmoke
```

## 3. 脚本入口说明

### `scripts/check-frontend.ps1`

用途：

- 运行前端 `typecheck`
- 执行生产构建检查
- 在 `-LiveUiSmoke` 模式下调用 `scripts/frontend_live_smoke.mjs`

### `scripts/frontend_live_smoke.mjs`

用途：

- 以轻量 HTTP 方式检查前端页面是否返回 HTML
- 生成 JSON 报告
- 当前覆盖正式路由：
  - `/editor`
  - `/project`
  - `/lore`
  - `/runtime`
  - `/settings`

### `scripts/check-backend.ps1`

用途：

- 检查后端依赖导入
- 检查数据库连接
- 检查 Alembic 状态
- 调用运行时健康检查与 self-check
- 在 `-FullSmoke` 模式下调用 `scripts/backend_full_smoke.py`

### `scripts/backend_full_smoke.py`

用途：

- 执行后端完整 smoke 场景
- 产出 JSON 报告
- 适合在接口、workflow、runtime 有较大变更时使用

## 4. 测试分组说明

### 后端

- 根层 `fastapi/backend/tests/test_*.py` 仍是当前稳定的 pytest 直接入口。
- 分类目录用途：
  - [`tests/api`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/api/README.md)
  - [`tests/services`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/services/README.md)
  - [`tests/runtime`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/runtime/README.md)

当前不直接搬迁真实测试文件，原因是：

- 现有命令和脚本已经稳定依赖根层入口。
- 直接搬迁容易触发 pytest 重复收集和路径兼容问题。

### 前端

- 前端当前以 `typecheck + build + live smoke` 为主。
- 预留目录：
  - [`tests/features`](D:/WritierLab/WriterLab-v1/Next.js/frontend/tests/features/README.md)
  - [`tests/smoke`](D:/WritierLab/WriterLab-v1/Next.js/frontend/tests/smoke/README.md)

## 5. 已知环境限制

- Windows 受限 shell 下，Next.js 构建偶尔会出现 `spawn EPERM` 或“Another next build process is already running”一类现象。
- 当前项目约定是：如果 `typecheck` 正常且在常规本地 shell 中可复现通过，则将其视为环境 caveat，而不是直接判定业务代码回退。

## 6. 报告位置

- 前端 live smoke 报告：`D:\WritierLab\WriterLab-v1\scripts\logs\frontend-live-smoke-*.json`
- 后端 full smoke 报告：`D:\WritierLab\WriterLab-v1\scripts\logs\backend-full-smoke-*.json`
- 每轮重构留痕：`D:\WritierLab\WriterLab-v1\.codex\`
