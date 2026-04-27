## 项目上下文摘要（phase-4-task2）

生成时间：2026-04-09 21:20:00

### 1. 任务目标

- 收口 phase-4 Task 2 的 workflow/context 后端合同。
- 当前真实红灯：`_workflow_output()` 未返回 `context_compile_snapshot`。
- 优先最小修复 `workflow_service.py`，只在必要时再触碰 `context_service.py`、`schemas/workflow.py`、`api/ai.py`。

### 2. 关键证据

- `WriterLab-v1/fastapi/backend/tests/services/workflow_service_suite.py`
  - 已新增 `test_workflow_output_includes_context_compile_snapshot_contract`
  - 当前报错：`KeyError: 'context_compile_snapshot'`
- `WriterLab-v1/fastapi/backend/app/services/workflow/workflow_service.py:510-525`
  - `_workflow_output()` 当前返回中缺少 `context_compile_snapshot`
- `WriterLab-v1/fastapi/backend/app/api/ai.py:164-170`
  - `/api/ai/workflows/{workflow_id}` 已直接返回 `run` 且挂上 `steps`
- `WriterLab-v1/fastapi/backend/app/schemas/workflow.py:63-79`
  - `ContextCompileSnapshot` 默认字段已存在

### 3. 当前判断

- Task 2 大概率只需修改 `workflow_service.py`
- `ai.py` 与 `schemas/workflow.py` 目前看已满足 Task 2 计划中的最小要求
- 必须以 fresh pytest 结果为准，不能凭静态阅读直接宣布完成

### 4. 验证命令

- `D:/WritierLab/.worktrees/phase4-workflow-context-runtime-exec/WriterLab-v1/.venv/Scripts/python.exe -m pytest D:/WritierLab/.worktrees/phase4-workflow-context-runtime-exec/WriterLab-v1/fastapi/backend/tests/test_workflow_service.py D:/WritierLab/.worktrees/phase4-workflow-context-runtime-exec/WriterLab-v1/fastapi/backend/tests/test_context_service.py D:/WritierLab/.worktrees/phase4-workflow-context-runtime-exec/WriterLab-v1/fastapi/backend/tests/test_api_routes.py -q`
