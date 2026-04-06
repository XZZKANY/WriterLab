## 项目上下文摘要（写作与工作台重构拆分方案）

生成时间：2026-04-02

### 1. 相似实现分析

- **实现1**: [editor-workspace.tsx](D:/WritierLab/WriterLab-v1/Next.js/frontend/features/editor/editor-workspace.tsx)
  - 模式：总控容器集中装配多个子面板
  - 可复用：现有页面装配、跨面板状态传递方式
  - 需注意：场景、写作、版本、上下文、诊断状态全部堆在同一容器，职责过载
- **实现2**: [writing-pane.tsx](D:/WritierLab/WriterLab-v1/Next.js/frontend/features/editor/writing-pane.tsx)
  - 模式：作者主流程面板
  - 可复用：正文编辑、分析、扩写、润色、候选稿采纳流程
  - 需注意：当前混入 `workflowProviderMode`、`fixtureScenario` 和“一键跑全流程”等诊断/调试型能力
- **实现3**: [versions-pane.tsx](D:/WritierLab/WriterLab-v1/Next.js/frontend/features/editor/versions-pane.tsx)
  - 模式：版本与分支独立子面板
  - 可复用：版本恢复、支线创建、支线采纳流程
  - 需注意：能力可保留，但术语与交互仍偏技术视角
- **实现4**: [sidebar-panels.tsx](D:/WritierLab/WriterLab-v1/Next.js/frontend/features/editor/sidebar-panels.tsx)
  - 模式：右侧多区块聚合面板
  - 可复用：分析摘要、问题列表、记忆命中、近期场景展示区块
  - 需注意：默认右栏同时包含 Workflow Debug、Provider Matrix、Smoke Console 等开发诊断能力，是作者心智负担的主要来源
- **实现5**: [workspace-header.tsx](D:/WritierLab/WriterLab-v1/Next.js/frontend/features/editor/workspace-header.tsx)
  - 模式：头部状态与主操作区
  - 可复用：场景标题、保存、重新加载、主标签切换
  - 需注意：应继续保持作者可见状态，不承担诊断入口之外的复杂控制

### 2. 现状问题

- `editor-workspace.tsx` 同时承担装配层、业务编排层、诊断控制层三类职责。
- `writing-pane.tsx` 把作者参数与 provider/runtime/smoke 调试参数混在一个主流程面板。
- `sidebar-panels.tsx` 把作者上下文侧栏与开发控制台错误合并，默认信息密度过高。
- `versions-pane.tsx` 的能力方向是对的，但表达方式还不够作者化。

### 3. 重构目标

- 让作者写作成为默认主路径。
- 把开发诊断能力迁出默认工作区。
- 让 `editor-workspace.tsx` 退回到装配层。
- 保留现有 scene、version、branch、workflow API，不在本轮推翻数据模型。

### 4. 推荐信息架构

- **作者工作台**
  - 场景标题、正文编辑、分析、扩写、润色、一致性、保存
- **版本与分支区**
  - 版本对比、版本恢复、支线创建、支线采纳
- **上下文侧栏**
  - 分析摘要、关键问题、记忆命中、近期场景、导出预览
- **开发诊断台**
  - Workflow Debug、Provider Runtime、Smoke Console、Provider Matrix、Context Compiler、Planner Override、Cloud API Config

### 5. 推荐状态域拆分

- `authoring`
  - `sceneId`、`title`、`status`、`draft`
  - `analyzeScene`、`writeScene`、`reviseScene`、`saveScene`
- `versioning`
  - `versions`、`selectedVersionId`、`compareVersionId`
  - `branches`、`selectedBranchId`、`branchDiff`
  - `restoreVersion`、`createBranch`、`adoptBranch`
- `context`
  - `analysisStore`、`memories`、`knowledgeHits`、`recentScenes`、`contextSnapshot`
- `diagnostics`
  - `workflow`、`selectedWorkflowStepId`
  - `workflowProviderMode`、`fixtureScenario`
  - `runtimeConnection`、`plannerOverrideDraft`
  - `runWorkflow`、`retryWorkflow`、`cancelWorkflow`

### 6. 分阶段实施顺序

1. 先拆右侧栏，分离作者上下文侧栏与开发诊断台。
2. 再拆 `editor-workspace.tsx` 的状态域和动作归属。
3. 再收缩 `writing-pane.tsx`，只保留作者主流程。
4. 最后整理 `versions-pane.tsx` 与 `workspace-header.tsx` 的作者化文案与交互。

### 7. 验收标准

- 作者默认界面不再出现 provider/runtime/smoke/planner override 配置。
- `editor-workspace.tsx` 不再直接维护诊断台主要状态。
- 写作主路径只保留分析、扩写、润色、一致性、保存与候选稿采纳。
- 版本与支线能力保持完整，但表达更贴近作者语境。
- 开发诊断能力仍可通过单独入口访问。

### 8. 本轮不建议做的事

- 不建议一次性同时重做视觉、架构和文案。
- 不建议本轮改后端协议或重建版本/分支数据模型。
- 不建议在未拆状态域前继续向默认右侧栏增加新功能。
