## 项目上下文摘要（第四轮测试与文档收口）

生成时间：2026-04-01 21:08:32

### 1. 相似实现分析

- **实现1**：`D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_api_routes.py`
  - 模式：根层 `test_*.py` 仍是现有 pytest 直接入口。
  - 可复用：继续用这些根层文件作为稳定验证命令入口。
  - 需注意：如果直接把文件迁到 `tests/api|services|runtime`，容易引入 pytest 重复收集风险。
- **实现2**：`D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1`
  - 模式：前端回归以 `typecheck + build + 可选 live smoke` 三段式执行。
  - 可复用：保留现有脚本入口，只增强 live smoke 的覆盖面。
  - 需注意：原脚本只检查 `/editor`，和第二轮新增正式页面不完全匹配。
- **实现3**：`D:\WritierLab\WriterLab-v1\scripts\frontend_live_smoke.mjs`
  - 模式：通过轻量 HTTP 请求读取页面 HTML，再基于标记做 smoke 断言。
  - 可复用：继续沿用脚本式 smoke，不引入浏览器框架。
  - 需注意：原脚本只接受单路由和 editor 专属标记，需要扩展成多路由矩阵。
- **实现4**：`D:\WritierLab\WriterLab-v1\docs\refactor-migration-map-zh.md`
  - 模式：现有迁移映射已经覆盖前三轮结构变化，但内容存在历史乱码。
  - 可复用：继续原文件尾部追加第四轮清单，不整体重写。
  - 需注意：只能追加新的 UTF-8 中文段落，不能试图清洗整个历史文档。

### 2. 项目约定

- **测试入口约定**：根层 `fastapi/backend/tests/test_*.py` 继续作为现有 pytest 直接入口。
- **测试目录约定**：`tests/api`、`tests/services`、`tests/runtime` 与前端 `tests/features`、`tests/smoke` 作为分类落位和后续扩展目录。
- **脚本约定**：继续复用 `scripts/check-backend.ps1`、`scripts/check-frontend.ps1`、`scripts/backend_full_smoke.py`、`scripts/frontend_live_smoke.mjs`。
- **留痕约定**：第四轮继续在 `.codex/` 下新增摘要，并向旧日志与报告尾部追加内容。

### 3. 可复用组件清单

- `D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_api_routes.py`
- `D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_workflow_service.py`
- `D:\WritierLab\WriterLab-v1\scripts\check-backend.ps1`
- `D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1`
- `D:\WritierLab\WriterLab-v1\scripts\frontend_live_smoke.mjs`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\app-shell.tsx`

### 4. 测试策略

- **前端**：
  - `npm.cmd run typecheck`
  - `powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1`
  - `powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1 -LiveUiSmoke`
- **后端**：
  - `D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_api_routes.py D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_workflow_service.py`
  - `powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\check-backend.ps1`

### 5. 依赖和集成点

- `check-frontend.ps1 -> frontend_live_smoke.mjs`
- `frontend_live_smoke.mjs -> /editor /project /lore /runtime /settings`
- `check-backend.ps1 -> backend_full_smoke.py / runtime API`
- `.codex` 报告文件继续承接每轮重构记录

### 6. 技术选型理由

- 第四轮优先补测试与脚本“说明结构”，而不是强搬真实测试文件，避免把现有稳定验证入口打碎。
- 多路由 live smoke 比单路由 editor smoke 更贴合第二轮建立的正式信息架构，且成本很低。
- 迁移映射和验证报告继续采用尾部追加，可在不破坏历史内容的前提下完成收口。

### 7. 关键风险点

- `project` 和 `lore` 页面缺少稳定英文标记，因此 smoke 断言更适合使用通用导航与 HTML 存活检查，而不是过强的业务文案匹配。
- 若直接移动根层测试文件，会影响现有 pytest 命令和潜在的全量收集行为，因此第四轮只做分类说明，不做高风险迁移。
- 历史文档仍有乱码，第四轮只能追加新内容，不能把“清洗旧文档”与当前收口任务耦合在一起。
