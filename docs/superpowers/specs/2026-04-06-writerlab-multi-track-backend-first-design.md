# WriterLab 多轨并行开发设计

生成时间：2026-04-06

## 1. 文档目标

本设计文档用于定义 WriterLab 的中期工程蓝图，服务于后续多个 Subagent 并行开发，而不是替代单次迭代任务单或产品愿景文档。

本轮设计已经确认以下约束：

- 采用“后端优先”的推进策略。
- 采用“按技术层拆轨”的组织方式。
- 后端主轴优先聚焦“项目 / 场景 / 资料”核心数据域。
- 设计文档先行，得到确认后再进入 implementation plan 和实施阶段。

## 2. 适用范围

本设计覆盖以下代码与文档边界：

- `WriterLab-v1/fastapi/backend/app/*`
- `WriterLab-v1/fastapi/backend/tests/*`
- `WriterLab-v1/Next.js/frontend/app/*`
- `WriterLab-v1/Next.js/frontend/features/*`
- `WriterLab-v1/Next.js/frontend/lib/api/*`
- `WriterLab-v1/scripts/*`
- `docs/superpowers/*`
- `.codex/*`

本设计不覆盖以下内容：

- 纯视觉翻新或品牌重做
- 独立于核心数据域之外的模型矩阵实验
- 没有本地验证出口的探索性实现

## 3. 现有架构基础

### 3.1 前端基础

现有前端已形成较清晰的 App Router + feature 工作台模式：

- `app/editor/page.tsx` 保持薄路由入口，只装配 `EditorWorkspace`
- `features/editor/editor-workspace.tsx` 负责页面装配
- `features/editor/hooks/use-authoring-workspace.ts`
- `features/editor/hooks/use-scene-context.ts`
- `features/editor/hooks/use-versioning-workspace.ts`

这一模式说明复杂页面应继续沿用“路由页薄入口 + feature 装配层 + 分域 hooks”的结构，而不是回退到大而全页面组件。

### 3.2 后端基础

现有后端采用 FastAPI 分模块注册与 repository 函数式组织：

- `app/main.py` 负责应用装配和 router 注册
- `app/repositories/project_repository.py` 展示了典型的数据级联清理模式

这一模式说明后端后续应继续沿用“router / service / repository / schema”边界，而不是把复杂业务逻辑回灌到单一路由文件。

### 3.3 测试基础

现有测试模式分为两类：

- 前端：`node:test` + 源码级结构契约测试
- 后端：`pytest` + 根层薄入口 + 分类 suite

这意味着后续多轨并行开发时，测试轨道应优先补“契约锁定”和“本地 smoke”，而不是只做人工点测。

## 4. 设计原则

### 4.1 一条主线带动多轨并行

后端核心数据域是主线，前端、测试验证、文档运维三条轨道围绕该主线推进。

### 4.2 接口先于接线

后端必须先稳定 schema、错误语义和 API 契约，前端才开始大面积接入，避免反复返工。

### 4.3 文件所有权隔离

多个 Subagent 并行时必须按目录和文件边界划定责任，避免同轮交叉写入。

### 4.4 每阶段必须有本地验证出口

每条轨道的阶段收口都必须带本地可重复执行的验证命令或结构性证明，不接受无验证交付。

## 5. 总体结构

本设计采用“1 条主线 + 4 条技术轨道 + 4 个阶段 + 依赖闸门”的结构。

### 5.1 主线

后端核心数据域演进是主线，顺序为：

1. 项目与场景主数据稳定化
2. 资料域稳定化
3. 时间线与版本联动
4. 在稳定数据域上接入 workflow / context / runtime 能力

### 5.2 四条技术轨道

- 轨道 A：后端数据域主轨
- 轨道 B：前端接入与工作台收口
- 轨道 C：测试与验证基建
- 轨道 D：文档与运维留痕

## 6. 中期阶段划分

### 6.1 阶段一：稳住项目与场景主数据

目标：先把“项目能建、场景能进、基础数据不乱、删除可控”做成稳定地基。

后端重点：

- `Project / Book / Chapter / Scene` 的 schema、repository、router、service 收敛
- 明确项目删除、章节挂载、场景读取和场景保存的级联规则

前端重点：

- 项目首页、场景入口、基础编辑入口的数据读取、错误态和空态跟进

测试重点：

- 项目删除
- 场景读写
- 章节列表
- 基础入口 smoke

文档重点：

- 主数据接口说明
- 验证命令
- 数据迁移与回滚说明

当前实施状态（2026-04-07）：

- 阶段一已完成首轮收口。
- 后端已落地 `/api/projects/{project_id}/overview`、项目删除链路与场景版本冲突契约。
- 前端项目详情已改为优先消费项目概览接口，浏览器默认 API 访问已收敛到同源 `/api` 代理。
- 本地验证已覆盖 `test_project_scene_contracts.py`、`api-client.test.mjs`、`project-detail-contract.test.mjs` 与 `typecheck`。

### 6.2 阶段二：补齐资料域

目标：让角色、设定、地点等写作基础资料能够稳定录入、读取和引用。

后端重点：

- `Character / Lore / Location / Terminology` 模型、schema、repository、router、service 稳定化

前端重点：

- 资料库页面
- 场景资料消费
- 基础引用展示

测试重点：

- 资料域 CRUD
- 资料与场景引用关系验证

文档重点：

- 资料域字段规范
- 录入约束
- 验证命令更新

### 6.3 阶段三：建立时间线与版本联动

目标：把“剧情事实”和“写作历史”做成可追溯闭环。

后端重点：

- `Timeline / SceneVersion / StoryBranch` 与场景域的关联关系稳定化
- 版本恢复、分支采纳和时间线联动规则收敛

前端重点：

- 时间线查看
- 版本对比
- 分支基础交互

测试重点：

- 时间线关联回归
- 版本恢复回归
- 分支采纳回归

文档重点：

- 影响范围
- 恢复路径
- 操作说明

### 6.4 阶段四：在稳定数据域上接工作流与一致性能力

目标：让 workflow、context compiler、一致性扫描和 runtime 观测建立在稳定主数据之上，而不是反向牵引基础结构。

后端重点：

- workflow 与数据域的消费和回写
- context compiler 的输入边界
- 一致性扫描与 runtime 自检的集成点

前端重点：

- 工作流结果消费
- 一致性与上下文展示
- runtime 工作台继续收口

测试重点：

- 端到端回归
- workflow smoke
- context / runtime 关键链路校验

文档重点：

- 完整运行手册
- 验收基线
- 常见故障排查

## 7. 各技术轨道职责

### 7.1 轨道 A：后端数据域主轨

长期职责：

- 维护核心数据模型、schema、repository、service、router 和 pytest 契约
- 对前端提供稳定 API，而不是暴露内部实现细节

阶段职责：

- 阶段一：`Project / Book / Chapter / Scene`
- 阶段二：`Character / Lore / Location / Terminology`
- 阶段三：`Timeline / SceneVersion / StoryBranch`
- 阶段四：workflow / context / runtime 对稳定数据域的消费与回写

交接条件：

- 给出稳定接口清单
- 给出错误语义
- 给出测试入口
- 给出迁移说明

### 7.2 轨道 B：前端接入与工作台收口

长期职责：

- 将后端稳定数据域映射成工作台、资料页、时间线页和版本页等交互入口
- 维护 `frontend/lib/api/*` 与 feature 层的契约适配

阶段职责：

- 阶段一：项目与场景基础入口、错误态、空态
- 阶段二：资料域管理页与场景资料消费
- 阶段三：时间线与版本/分支交互
- 阶段四：workflow、一致性和 runtime 结果消费

交接条件：

- 仅消费已冻结接口
- 不在前端堆积临时兼容分支
- 每个阶段补齐最小结构契约与 smoke

### 7.3 轨道 C：测试与验证基建

长期职责：

- 锁定 API 契约、结构契约、smoke 与关键回归面
- 为阶段推进提供客观门槛

阶段职责：

- 阶段一：项目删除、场景读写、章节列表、基础前端入口 smoke
- 阶段二：资料域 CRUD 与引用关系验证
- 阶段三：时间线、版本、分支回归
- 阶段四：workflow / context / runtime 端到端与 smoke 收口

交接条件：

- 先有失败基线，再有通过验证
- 所有验证必须本地可执行

### 7.4 轨道 D：文档与运维留痕

长期职责：

- 维护计划、设计、运行命令、迁移说明、回滚说明和验证记录
- 保证多个 Subagent 并行后仍然可审计、可接手

阶段职责：

- 阶段一：主数据域说明、基础命令、环境约束
- 阶段二：资料域字段与录入规范
- 阶段三：版本/时间线使用说明与风险说明
- 阶段四：完整运行与验收手册

交接条件：

- 每阶段收口前必须补齐文档
- 文档必须包含本地验证命令与结果

## 8. 多 Subagent 协作规则

### 8.1 文件所有权

建议后续按以下边界派发 Subagent：

- 后端 worker：
  - `WriterLab-v1/fastapi/backend/app/*`
  - `WriterLab-v1/fastapi/backend/tests/*`
- 前端 worker：
  - `WriterLab-v1/Next.js/frontend/*`
- 验证 worker：
  - 前后端测试文件
  - `WriterLab-v1/scripts/*` 中的检查与 smoke 脚本
- 文档 worker：
  - `docs/*`
  - `.codex/*`

### 8.2 依赖闸门

- Gate 1：后端 schema 与 API 契约先稳定，前端再大面积接线
- Gate 2：测试轨先锁失败基线，再允许功能轨大改
- Gate 3：阶段结束前必须补齐文档、迁移说明和本地命令
- Gate 4：同一轮中不允许两个 Subagent 同时改同一组文件

### 8.3 交接格式

每个轨道在交接时至少提供：

- 变更范围
- 输入输出契约
- 本地验证命令
- 已知风险
- 对下一轨道的依赖说明

## 9. 主要风险

### 9.1 前端再次膨胀

如果前端在后端契约未稳定前继续快速接线，`feature` 装配层和 hooks 边界会重新模糊。

### 9.2 后端级联复杂度继续上升

以 `project_repository.py` 为代表的级联删除和跨实体清理逻辑，随着数据域扩大最容易出现漏删、误删和回归。

### 9.3 测试覆盖落后于并行开发速度

多个 Subagent 并行推进时，若测试轨道没有先行锁基线，会导致阶段完成的判断失真。

### 9.4 文档留痕滞后

如果实施快于文档更新，后续 agent 会失去统一上下文，导致重复分析和错误集成。

## 10. 验收标准

这份设计文档的成功标准是：

- 明确后端优先的中期主线
- 明确四条技术轨道职责
- 明确四个阶段的推进顺序
- 明确多 Subagent 文件所有权与依赖闸门
- 能直接作为下一步 implementation plan 的输入

## 11. 过渡到实施计划的要求

本设计确认后，下一步 implementation plan 应做到：

- 将四个阶段拆成可在 1 到 2 个工作日内完成的原子任务
- 为每条轨道定义具体文件、接口与验证命令
- 标注哪些任务可并行、哪些任务必须等待 Gate 解锁
- 保持“后端先行、前端跟进、验证先锁基线、文档同步收口”的顺序
