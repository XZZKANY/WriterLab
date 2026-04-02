# 后端服务测试分组

本目录用于承接服务层和业务编排测试的长期落位。

当前阶段保留根层 `test_*.py` 文件，避免在第四轮收口时打断既有 pytest 入口。

当前主要映射：

- 根层 [`test_workflow_service.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/test_workflow_service.py)
- 根层 [`test_ai_gateway_service.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/test_ai_gateway_service.py)
- 根层 [`test_context_service.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/test_context_service.py)
- 根层 [`test_knowledge_service.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/test_knowledge_service.py)
- 根层 [`test_consistency_service.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/test_consistency_service.py)
- 根层 [`test_scene_analysis_service.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/test_scene_analysis_service.py)
- 根层 [`test_branch_service.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/test_branch_service.py)
- 根层 [`test_style_negative_service.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/test_style_negative_service.py)
- 根层 [`test_vn_export_service.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/test_vn_export_service.py)
- 根层 [`test_ai_output_guardrails.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/test_ai_output_guardrails.py)
- 已迁入本目录的真实 suite：[`workflow_service_suite.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/services/workflow_service_suite.py)
- 已迁入本目录的真实 suite：[`ai_gateway_service_suite.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/services/ai_gateway_service_suite.py)
- 已迁入本目录的真实 suite：[`context_service_suite.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/services/context_service_suite.py)

后续新增测试建议：

- 以业务域或服务名命名，例如 `test_runtime_status_service.py`、`test_scene_write_service.py`。
- 与 ORM 读取无关、主要验证编排和领域规则的测试优先归入本目录。

推荐运行命令：

```powershell
D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_workflow_service.py
```
