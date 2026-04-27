# 前端功能测试骨架

本目录用于承接前端功能层测试，例如：

- `features/editor/*` 的组件行为
- `features/project/*` 的数据装配逻辑
- `features/lore/*`、`features/runtime/*`、`features/settings/*` 的页面能力测试

当前第四轮不直接新增测试实现，原因是：

- 现有前端回归链路以 `typecheck`、`build` 和 live smoke 为主。
- 先把目录职责、脚本入口和 smoke 覆盖范围收口，后续再逐步补充真实测试文件。

推荐的后续落位方式：

- 组件级行为测试放在本目录。
- 与 smoke 检查相关的脚本级验证放在 [`../smoke`](D:/WritierLab/apps/frontend/tests/smoke/README.md)。
