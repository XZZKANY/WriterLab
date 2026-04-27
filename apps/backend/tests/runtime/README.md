# 后端运行时测试分组

本目录用于承接运行时诊断、自检、smoke 报告与事件流相关测试。

当前映射：

- 根层 [`test_runtime_smoke_reports.py`](D:/WritierLab/apps/backend/tests/test_runtime_smoke_reports.py)
- 已迁入本目录的真实 suite：[`runtime_smoke_reports_suite.py`](D:/WritierLab/apps/backend/tests/runtime/runtime_smoke_reports_suite.py)

说明：

- 第四轮暂不移动原测试文件，以保持现有 `pytest` 命令和检查脚本稳定。
- 当前已开始采用“根层薄入口 + 分类目录真实 suite”模式，`test_runtime_smoke_reports.py` 继续保留为直接入口。
- 后续如新增 `runtime_status_service`、`runtime events`、`self-check` 相关测试，应优先落在本目录。

推荐运行命令：

```powershell
D:\WritierLab\apps\backend\.venv\Scripts\python.exe -m pytest D:\WritierLab\apps\backend\tests\test_runtime_smoke_reports.py
```
