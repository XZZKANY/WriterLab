# 编辑器工作台功能重构设计

生成时间：2026-04-04

## 1. 背景与问题

当前编辑器工作台已经具备写作、分析、润色、版本、分支、上下文、运行诊断等多类能力，但这些能力被集中装配在同一页面与同一状态容器中，导致作者体验和前端结构同时失衡。

基于现有实现，当前主要问题如下：

- `editor-workspace.tsx` 同时持有写作、版本、上下文、运行诊断四类状态，页面装配层职责过载。
- `writing-pane.tsx` 混入 `workflowProviderMode`、`fixtureScenario` 和“一键跑全流程”等开发态控制，破坏作者主流程的专注度。
- `sidebar-panels.tsx` 把作者上下文侧栏与 `Workflow Debug`、`Provider Runtime`、`Smoke Console`、`Provider Matrix`、`Context Compiler` 等诊断能力堆叠在同一侧栏中，默认信息密度过高。
- `use-editor-runtime-workbench.ts` 已经形成相对独立的运行诊断域，但仍从编辑器工作台内部暴露，未形成独立入口。

结论：本次重构不应继续在原工作台上加条件渲染，而应进行一次性破坏式重构，彻底分离“作者工作台”和“运行诊断工作台”。

## 2. 重构目标

### 2.1 主要目标

- 让编辑器默认入口回归作者写作主场景。
- 将运行诊断能力整体迁出编辑器，放入独立调试入口。
- 将当前大而全的工作台拆成可维护的状态域与组件边界。
- 在不新增后端协议的前提下，复用现有 API 和成熟组件。
- 让本设计文档可直接作为后续 implementation plan 的输入。

### 2.2 非目标

- 本轮不重做后端场景、版本、分支、工作流协议。
- 本轮不引入新的状态管理库。
- 本轮不追求视觉系统整体翻新，只做与信息架构相匹配的界面重组。
- 本轮不兼容旧工作台结构，采用直接切换的新结构。

## 3. 目标信息架构

重构后形成两个明确入口。

### 3.1 作者工作台

作者工作台是编辑器主入口，只保留作者真实使用的能力：

- 场景头部：标题、状态、保存、重载、主视图切换。
- 写作主区：正文编辑、分析、扩写、润色、候选稿采纳。
- 版本与分支区：版本快照、版本对比、剧情分支、分支采纳。
- 上下文侧栏：分析摘要、一致性问题、时间线、风格记忆、设定命中、近期场景、导出预览。

### 3.2 运行诊断工作台

运行诊断工作台从编辑器完全拆出，作为独立调试入口，承载以下能力：

- Workflow Debug
- Provider Runtime
- Smoke Console
- Provider Matrix
- Context Compiler
- API 配置与运行自检

### 3.3 入口策略

- `app/editor/page.tsx` 继续作为作者工作台入口。
- 新增独立调试入口，例如 `app/runtime/page.tsx` 下的专用工作台，或新增 `app/editor/debug/page.tsx`，由后续实现计划定稿。
- 编辑器页只保留工作流运行状态的轻量摘要，不再内嵌调试控制台。

## 4. 模块边界与复用策略

### 4.1 保留并复用的现有实现

- `workspace-header.tsx`
  - 保留为作者工作台头部组件。
  - 调整文案和输入输出，不再承担诊断入口之外的复杂控制。
- `versions-pane.tsx`
  - 保留版本与分支能力。
  - 改造为更作者化的展示和交互表达。
- `use-editor-runtime-workbench.ts`
  - 迁移为 runtime/debug 域的独立 hook。
  - 继续复用已有 runtime、settings、workflow API 拉取逻辑。
- `app/editor/page.tsx`
  - 继续仅承担路由装配职责。

### 4.2 必须拆分的现有实现

- `editor-workspace.tsx`
  - 从“大一统状态容器”退回“作者工作台装配器”。
- `writing-pane.tsx`
  - 删除开发态控件与调试参数，仅保留写作主流程。
- `sidebar-panels.tsx`
  - 拆分为“作者上下文侧栏”和“运行诊断面板”两条线。
  - 作者侧栏留在编辑器；诊断面板迁出到独立调试页。

### 4.3 推荐目录结构

建议后续收敛为以下结构：

- `features/editor/editor-workspace.tsx`
- `features/editor/authoring-pane.tsx`
- `features/editor/context-sidebar.tsx`
- `features/editor/versioning-pane.tsx`
- `features/editor/workspace-header.tsx`
- `features/editor/hooks/use-authoring-workspace.ts`
- `features/editor/hooks/use-versioning-workspace.ts`
- `features/editor/hooks/use-scene-context.ts`
- `features/runtime/runtime-debug-workbench.tsx`
- `features/runtime/hooks/use-runtime-diagnostics.ts`

## 5. 状态域设计

本次重构以状态域重划为核心，而不是仅调整 UI 摆放。

### 5.1 `authoring`

职责：场景写作主流程。

建议承载：

- `sceneId`
- `title`
- `status`
- `draft`
- `lengthMode`
- `reviseMode`
- `applyMode`
- `analysis`
- `analysisStore`
- `generatedDraft`
- `generatedNotes`
- `revisedDraft`
- `revisionBase`
- `revisionNotes`
- `saveScene`
- `analyzeScene`
- `writeScene`
- `reviseScene`
- `applyRevision`

### 5.2 `versioning`

职责：版本与分支。

建议承载：

- `versions`
- `selectedVersionId`
- `compareVersionId`
- `branches`
- `selectedBranchId`
- `branchDiff`
- `branchName`
- `branchDescription`
- `restoreVersion`
- `createBranch`
- `adoptBranch`

### 5.3 `context`

职责：作者辅助上下文，而不是开发诊断。

建议承载：

- `issueSummary`
- `issues`
- `showAllIssues`
- `timeline`
- `memories`
- `knowledgeHits`
- `recentScenes`
- `contextSnapshot` 中作者可读的摘要部分
- `vnExport`

### 5.4 `workspaceChrome`

职责：页面装配层的共享反馈。

建议承载：

- `tab`
- `busyKey`
- `statusMessage`
- `errorMessage`
- 页面初始化加载与主视图切换

### 5.5 `runtimeDiagnostics`

职责：所有运行诊断与开发排障能力。

建议承载：

- `workflow`
- `selectedWorkflowStepId`
- `workflowProviderMode`
- `fixtureScenario`
- `runtimeConnection`
- `plannerOverrideDraft`
- `providerSettings`
- `providerRuntime`
- `smokeLatest`
- `smokeReports`
- `providerMatrix`
- runtime self-check 相关状态

## 6. 数据流设计

### 6.1 页面初始化

作者工作台初始化时，`editor-workspace` 仅负责获取 `sceneId` 和初始化时机，然后分别触发：

- `authoring` 域加载正文与分析结果。
- `versioning` 域加载版本与分支。
- `context` 域加载时间线、记忆、设定命中、近期场景与一致性信息。

### 6.2 写作动作流

作者在主工作台执行以下动作时：

- 分析
- 扩写
- 润色
- 应用修订
- 保存

这些动作只应直接更新 `authoring` 域；随后按需要通知 `versioning` 与 `context` 做局部刷新。

### 6.3 版本动作流

版本恢复、分支创建、分支采纳只应在 `versioning` 域内闭环处理，并在完成后通知 `authoring` 刷新当前正文。

### 6.4 诊断动作流

运行态读取、provider 配置、smoke 报告、workflow step 诊断都应在独立的 `runtimeDiagnostics` 域内闭环。

编辑器主入口只保留轻量摘要，例如：

- 工作流运行中
- 工作流失败
- 等待人工处理

但不再暴露详细诊断面板。

## 7. 一次性重构实施顺序

虽然目标是一次性切换到新结构，但实现上建议按以下四个阶段推进。

### 阶段一：建立新骨架

- 新建作者工作台与运行诊断工作台的页面骨架。
- 新建 authoring、versioning、context、runtimeDiagnostics 对应的 hook 边界。
- 建立独立调试入口。

### 阶段二：迁移状态域

- 将 `use-editor-runtime-workbench.ts` 迁移为 runtime/debug 独立 hook。
- 将 `editor-workspace.tsx` 中的 authoring、versioning、context 状态拆分到各自域中。
- 保持旧 API 不变，先让新骨架完成数据拉取与展示。

### 阶段三：替换主界面

- 重写作者写作主区。
- 重写作者上下文侧栏。
- 从 `writing-pane.tsx` 删除开发态控件。
- 从 `sidebar-panels.tsx` 移除诊断板块。

### 阶段四：清理旧实现

- 删除 editor feature 中残留的 runtime/debug 依赖。
- 清理旧的 props 透传和无效状态。
- 统一命名、文案和导入路径。
- 更新 smoke 标记点与相关文档。

## 8. 风险评估

### 8.1 状态拆分后的刷新时序风险

当前多个动作默认依赖同一容器中的共享状态。拆域后若未明确“谁触发谁刷新”，容易出现正文已更新但上下文或版本仍显示旧数据。

### 8.2 调试入口迁移后的使用习惯风险

诊断能力迁出后，开发者短期内需要适应新的入口位置。因此实现阶段必须同步更新导航文案、文档和验证脚本。

### 8.3 隐式耦合风险

版本、分析、上下文之间当前存在隐式耦合。实施计划里必须显式列出各动作完成后的刷新矩阵，避免遗漏。

### 8.4 前端 smoke 回归风险

当前 smoke 逻辑可能依赖旧工作台标记点。重构后需要同步更新：

- `scripts/frontend_live_smoke.mjs`
- 相关前端检查脚本

## 9. 验收标准

- 编辑器默认界面不再出现 provider、runtime、smoke、planner override、fixture 相关控件或面板。
- 作者工作台完整保留分析、扩写、润色、保存、候选稿采纳、版本恢复、分支创建与分支采纳能力。
- 运行诊断能力可以在独立页面使用，且不依赖编辑器页面挂载。
- `editor-workspace.tsx` 明显收缩为装配层，不再持有大块诊断状态。
- 前端本地验证能够证明作者工作台入口与独立诊断入口都能稳定打开。

## 10. 本地验证建议

后续实现阶段至少应执行以下本地验证：

- 作者工作台页面 smoke 验证
- 运行诊断页面 smoke 验证
- 关键作者动作的回归验证：
  - 分析
  - 扩写
  - 润色
  - 保存
  - 版本恢复
  - 分支创建与采纳
- 类型检查与静态检查

如果某些验证能力当前缺失，必须在 implementation plan 中补上，而不是带着不可验证状态进入交付。

## 11. 后续计划输入

本设计文档将作为后续 implementation plan 的直接输入。后续计划需要进一步明确：

- 独立调试入口的最终路由落点
- 新旧组件的删除与迁移清单
- 状态域拆分后的刷新矩阵
- 本地验证脚本与 smoke 标记点调整清单
