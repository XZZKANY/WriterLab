# 后端 API 测试分组

本目录用于承接 API 协议层相关测试的长期落位。

当前阶段仍保留根目录下的 `test_*.py` 作为 pytest 直接入口，原因是：

- 现有本地验证脚本和命令已经稳定使用根层文件。
- 直接移动测试文件会引入 pytest 重复收集或路径兼容风险。
- 第四轮的目标是先把目录职责和运行说明收口，再逐步迁移真实测试文件。

当前对应关系：

- 根层 [`test_api_routes.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/test_api_routes.py)
- 根层 [`test_acceptance_api_contracts.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/test_acceptance_api_contracts.py)
- 已迁入本目录的真实 suite：[`api_routes_suite.py`](D:/WritierLab/WriterLab-v1/fastapi/backend/tests/api/api_routes_suite.py)

后续新增测试建议：

- 纯路由、响应码、协议契约测试优先落到本目录。
- 新增文件应优先按 API 领域命名，例如 `test_runtime_routes.py`、`test_project_routes.py`。

推荐运行命令：

```powershell
D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_api_routes.py
```
