# 后端 tests 索引

本目录保留当前稳定的 pytest 入口，并为后续分类迁移预留结构。

## 当前策略

- 根层 `test_*.py` 继续作为直接运行入口。
- 分类子目录用于明确测试归属和后续扩展，而不是在第四轮立即搬迁真实测试文件。

## 当前直接入口

- [`test_api_routes.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/test_api_routes.py)
- [`test_workflow_service.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/test_workflow_service.py)
- 以及同级其他 `test_*.py`

首批已完成的低风险迁移：

- 路由测试真实内容已迁入 [`api/api_routes_suite.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/api/api_routes_suite.py)
- workflow 服务测试真实内容已迁入 [`services/workflow_service_suite.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/services/workflow_service_suite.py)
- 根层同名文件继续作为薄入口，确保现有 pytest 命令不变

第二批已完成的低风险迁移：

- AI 网关服务测试真实内容已迁入 [`services/ai_gateway_service_suite.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/services/ai_gateway_service_suite.py)
- 上下文服务测试真实内容已迁入 [`services/context_service_suite.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/services/context_service_suite.py)
- 运行时 smoke 报告测试真实内容已迁入 [`runtime/runtime_smoke_reports_suite.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/runtime/runtime_smoke_reports_suite.py)
- 对应根层入口文件名保持不变，继续兼容现有命令

## 分类说明

- [`api/README.md`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/api/README.md)
- [`services/README.md`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/services/README.md)
- [`runtime/README.md`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/runtime/README.md)

## 推荐命令

```powershell
D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_api_routes.py D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_workflow_service.py
```
