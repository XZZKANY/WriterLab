# 前端 Smoke 测试骨架

本目录用于承接前端 smoke 级验证说明与后续扩展文件。

当前 live smoke 入口：

- [`D:/WritierLab/scripts/check/check-frontend.ps1`](D:/WritierLab/scripts/check/check-frontend.ps1)
- [`D:/WritierLab/scripts/smoke/frontend_live_smoke.mjs`](D:/WritierLab/scripts/smoke/frontend_live_smoke.mjs)

第四轮后的覆盖范围：

- `/editor`
- `/project`
- `/lore`
- `/runtime`
- `/settings`

说明：

- 当前 smoke 仍以脚本执行和 JSON 报告为主，未迁入浏览器测试框架。
- 后续如果引入页面级 smoke 断言文件，可优先补充到本目录。
