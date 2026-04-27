# 前端 tests 索引

本目录用于承接前端测试和 smoke 说明骨架。

## 当前策略

- 当前前端验证以 `typecheck + build + live smoke` 为主。
- 第四轮先把目录职责和脚本覆盖说明补齐，不直接引入新的测试框架或搬迁真实测试文件。

## 分类说明

- [`features/README.md`](D:/WritierLab/apps/frontend/tests/features/README.md)
- [`smoke/README.md`](D:/WritierLab/apps/frontend/tests/smoke/README.md)

## 当前主要验证入口

- [`D:/WritierLab/scripts/check/check-frontend.ps1`](D:/WritierLab/scripts/check/check-frontend.ps1)
- [`D:/WritierLab/scripts/smoke/frontend_live_smoke.mjs`](D:/WritierLab/scripts/smoke/frontend_live_smoke.mjs)

## 当前 smoke 覆盖

- `/editor`
- `/project`
- `/lore`
- `/runtime`
- `/settings`
