# WriterLab phase-4 workflow、context 与 runtime 收口设计

生成时间：2026-04-09

## 1. 设计目标

本设计文档用于定义 WriterLab 在 phase-4 第一轮的实施边界：把已有 `workflow / context / runtime` 真实能力收口为稳定合同，而不是把它们当作待从零搭建的新系统。

本轮目标是沿用 phase-1 到 phase-3 已经稳定的项目、场景、资料、时间线与版本数据域，建立一条可重复验证的联动闭环：`build_scene_context()` 产出上下文快照，`workflow run` 回写运行态与快照，`runtime` 暴露自检与 smoke 报告，前端继续通过既有 hooks 消费结果。

本设计明确继续采用“后端契约优先”策略：先锁后端运行态、上下文与诊断边界，再锁前端消费层，最后把本地验证与运行手册收口为 phase-4 的实施基线。

## 2. 范围边界

### 2.1 本轮纳入范围

- `app/api/ai.py` 下现有工作流接口的第一轮合同冻结：`POST /api/ai/workflows/scene`、`POST /api/ai/workflows/scene/run-sync`、`GET /api/ai/workflows/{workflow_id}`、`POST /api/ai/workflows/{workflow_id}/resume`、`POST /api/ai/workflows/{workflow_id}/steps/{step_key}/override`、`POST /api/ai/workflows/{workflow_id}/cancel`
- `app/services/context/context_service.py` 中 `build_scene_context(scene, db, branch_id=...)` 的输入边界、输出结构与 `ContextCompileSnapshot` 字段语义
- `app/api/runtime.py` 与 `docs/runtime-notes.md` 已存在的 `/api/health`、`/api/runtime/self-check`、`/api/runtime/provider-state`、smoke reports、runtime events 等诊断与回归出口
- 前端 `lib/api/workflow.ts`、`lib/api/runtime.ts`、`features/editor/hooks/use-scene-context.ts`、`features/runtime/hooks/use-runtime-diagnostics.ts` 的消费边界
- `.codex`、spec、verification 与 operations-log 的文档留痕

### 2.2 本轮明确不做

- 重写 editor 主工作区或重新拆分 `editor-workspace`
- 重做 runtime 页面壳层或新建平行的 workflow 中心页
- 新建复杂实时观测系统、统一事件总线控制台或大面积 provider 编排 UI
- 把 phase-4 扩张为新的产品功能轮次，例如完整协作中心、模型实验平台或全量自动化运营面板
- 任何 implementation plan、代码实现或超出设计文档与自检之外的交付物

## 3. 当前实现基线

### 3.1 workflow 运行主链路已经存在

当前后端并不存在“尚未开始的 workflow 系统”。`app/api/ai.py` 已经提供工作流启动、同步执行、查询、恢复、步骤覆写与取消接口；`app/services/workflow/workflow_service.py` 也已经具备 `queue_scene_workflow()`、`execute_scene_workflow()`、`resume_workflow_run()`、`override_workflow_step()` 与 runner 启动逻辑。

更关键的是，`_run_scene_workflow()` 已在工作流最前段调用 `build_scene_context(scene, db, branch_id=payload.branch_id)`，并把 `context_compile_snapshot` 回写到 `run.context_compile_snapshot`。这说明 phase-4 的真实任务不是接上线下两套系统，而是把既有“上下文编译 → 工作流执行 → 运行态回写”的合同冻结下来。

### 3.2 context compiler 已有稳定输入输出骨架

`app/schemas/workflow.py` 已定义 `ContextCompileSnapshot` 与 `ContextCompileCandidate`。当前快照至少包含：`hard_filters`、`hard_filter_result`、`candidates`、`budget`、`summary_triggered`、`summary_reason`、`summary_output`、`clipped_sources`、`deduped_sources`、`source_diversity_applied`、`scope_resolution`。

`app/services/context/context_service.py` 中的 `build_scene_context()` 已按项目/分支/章节/场景边界收集 `lore_constraints`、`timeline_events`、`style_memories`、`knowledge_hits` 与 `recent_scenes`，并在预算超限时触发摘要化。这意味着 phase-4 第一轮应把“为什么给出这些上下文”做成可解释、可回归的合同，而不是继续扩字段做新实验。

### 3.3 runtime 诊断与运行手册已经成型

`app/api/runtime.py` 已提供 `GET /api/runtime/provider-state`、`GET /api/runtime/self-check`、`GET /api/runtime/smoke-reports`、`GET /api/runtime/smoke-reports/latest`、`GET /api/runtime/smoke-reports/{filename}`、`GET /api/runtime/smoke-reports/{filename}/regression` 以及 `WS /api/runtime/events`。`docs/runtime-notes.md` 进一步定义了标准启动顺序、live smoke matrix、failure interpretation、recovery semantics 与本地脚本入口。

这说明 phase-4 不需要重新发明“如何判断系统是否可运行”，而应该直接复用 `/api/health`、`/api/runtime/self-check`、provider-state 与 smoke 报告作为统一验收出口。

### 3.4 前端消费边界已经初步收拢

`features/editor/hooks/use-scene-context.ts` 已集中维护 `timeline`、`memories`、`knowledgeHits`、`recentScenes`、`contextSnapshot` 与 `issues`，并通过 `applySceneContext()`、`applyConsistencyResult()` 统一接收上下文与一致性结果。`features/runtime/hooks/use-runtime-diagnostics.ts` 则已经把 health、self-check、provider-state、smoke reports、provider matrix 与 provider settings 的读取收敛在同一个 hook 内。

`features/runtime/runtime-debug-workbench.tsx` 与其结构测试表明，runtime 页面已经承接 `Workflow Debug`、`Provider Runtime`、`Smoke Console`、`Provider Matrix`、`Context Compiler` 五个区域。因此 phase-4 第一轮应继续沿用“editor 消费写作上下文，runtime 页面消费运行诊断”的双边界，而不是重新混挂。

### 3.5 测试与验证基线已具备可复用入口

后端已有 `test_workflow_service.py`、`test_context_service.py` 与 `test_runtime_smoke_reports.py` 这类薄入口测试，分别指向 suites 锁定工作流、上下文编译与 runtime smoke 报告行为；前端已有 `tests/features/runtime-debug-workbench.test.mjs` 锁定 runtime 工作台的源码结构契约。这些测试入口意味着 phase-4 第一轮可以先补合同回归，而不是先做页面翻新。

## 4. 设计原则

### 4.1 后端契约优先于前端扩张

phase-4 必须先冻结工作流状态、上下文快照和 runtime 诊断的后端合同，再让前端继续消费。否则 editor 与 runtime 工作台都会被临时兼容逻辑重新拉散。

### 4.2 复用现有聚合入口，不新建平行系统

工作流继续走 `app/api/ai.py`，runtime 继续走 `app/api/runtime.py`，前端继续走 `lib/api/* + hooks + 薄页面入口`。第一轮不新建第二套聚合 router、第二套 runtime 中心页或第二套上下文状态容器。

### 4.3 可解释性优先于花哨自动化

`ContextCompileSnapshot` 已经具备预算、候选、去重与摘要触发信息；phase-4 第一轮应优先保证这些诊断字段可解释、可稳定回归，而不是追求更复杂但不可验证的“智能”编排。

### 4.4 统一使用 runtime 现有出口做验收

`/api/health`、`/api/runtime/self-check`、provider-state、smoke reports 与 runtime notes 中的脚本命令，构成了 phase-4 的统一验收面。任何新增验证都应补到这个体系内，而不是旁路生成新的临时脚本入口。

## 5. 方案选择

### 5.1 方案 A：后端契约优先的联动收口（推荐）

先锁 `workflow run + context snapshot + runtime diagnostics` 的合同，再让前端 hooks 和 runtime workbench 按既有边界消费。这一方案与总蓝图“后端优先”一致，也最符合当前真实代码状态。

### 5.2 方案 B：前端工作台优先

先扩 editor 或 runtime 页面，再倒逼后端补契约。该方案的短期可见度高，但会让页面层背上大量临时兼容逻辑，不适合当前 phase-4。

### 5.3 方案 C：新建统一 workflow/runtime 中心

把 workflow、context、runtime 与 consistency 重新组织成一套新中台。该方案改动面最大，既不符合本轮范围，也会破坏当前已可运行的聚合边界。

### 5.4 第一轮实施顺序

1. 先冻结 `build_scene_context()` 与 `WorkflowRunResponse` / `WorkflowStepResponse` 的关键字段语义
2. 再冻结 `/api/health`、`/api/runtime/self-check`、`/api/runtime/provider-state`、smoke report 浏览接口与 provider matrix 的诊断语义
3. 最后锁前端 `use-scene-context()`、`use-runtime-diagnostics()` 与 runtime workbench 的消费边界和结构契约

## 6. 后端设计

### 6.1 workflow run 合同

- 继续复用 `/api/ai` 作为唯一工作流聚合入口，不新增平行 router
- 第一轮锁定 `WorkflowRunResponse` 中以下字段作为 phase-4 读写合同：`status`、`current_step`、`input_payload`、`output_payload`、`retry_count`、`needs_merge`、`quality_degraded`、`resume_from_step`、`context_compile_snapshot`、`steps`
- 第一轮锁定 `WorkflowStepResponse` 中以下字段用于调试与回归：`step_key`、`version`、`attempt_no`、`status`、`invalidated_by_step`、`provider_mode`、`provider`、`model`、`profile_name`、`machine_output_snapshot`、`effective_output_snapshot`、`error_message`
- `resume` 与 `override` 继续保持“资源不存在返回 404，版本不匹配返回 409”的错误语义；`override` 第一轮仍只支持 `plan` 步骤，不扩大到其他 step

### 6.2 context compiler 合同

- `build_scene_context(scene, db, branch_id=None)` 继续作为唯一上下文编译入口，不拆第二套 compiler service
- 第一轮冻结输出中的 `timeline_events`、`style_memories`、`knowledge_hits`、`recent_scenes` 与 `context_compile_snapshot`，把它们视为 workflow 与 editor 共享的稳定输入
- `ContextCompileSnapshot` 保持 `schema_version=context_compile_snapshot.v1`，并把 `hard_filters`、`hard_filter_result`、`scope_resolution`、`budget`、`candidates`、`clipped_sources`、`deduped_sources`、`source_diversity_applied`、`summary_reason`、`summary_output` 作为核心解释字段
- 分支相关语义继续沿用当前实现：`timeline` 与 `recent_scenes` 在存在 `branch_id` 时走 branch 作用域；`canonical_lore` 与 style seed 仍保持 project 作用域
- 当 recent scenes 超过预算或超过 2000 tokens 时，摘要化逻辑继续只改变 `recent_scenes` 与 snapshot 的摘要字段，不发明新的旁路输出格式

### 6.3 runtime 与自检合同

- `/api/health` 继续提供 readiness 总览，作为 runtime self-check 的基础输入，而不是被替代
- `/api/runtime/self-check` 继续聚合 backend root、health、knowledge、provider matrix、provider runtime 与 workflow runtime，并保留 recommended local checks
- `/api/runtime/provider-state` 继续承载 provider、profile、step 三层运行态，不把这些状态拆散到多个新接口
- smoke report 继续以 `list / latest / detail / regression` 四个读取接口为主；回归对比在读取时计算，不修改历史 JSON
- `/api/runtime/events` 继续作为运行事件观察面，但第一轮只把它视为诊断证据，不扩张为新的编排总线

## 7. 前端设计

### 7.1 editor 侧继续复用 `use-scene-context()`

editor 继续通过 `use-scene-context()` 消费 `timeline_events`、`style_memories`、`knowledge_hits`、`recent_scenes` 与 `context_compile_snapshot`，并由 `applyConsistencyResult()` 统一接收一致性问题。第一轮不把这些状态回退到页面层散落管理。

### 7.2 runtime 侧继续复用 `use-runtime-diagnostics()`

runtime 页面继续通过 `use-runtime-diagnostics()` 统一读取 health、self-check、provider runtime、smoke latest、smoke reports、smoke regression、provider matrix 与 provider settings。第一轮不新增第二套 runtime hook，也不允许页面层直接散落 `fetch('/api/...')`。

### 7.3 页面与工作台边界

`runtime-debug-workbench.tsx` 继续作为 runtime 诊断工作台，承接 `Workflow Debug`、`Provider Runtime`、`Smoke Console`、`Provider Matrix` 与 `Context Compiler`；`app/runtime/page.tsx` 与现有 hub 继续保持薄入口。editor 侧只消费写作相关上下文与一致性结果，不把完整 runtime 诊断重新搬回主编辑页。

## 8. 测试与验证设计

### 8.1 后端验证

- 继续沿用 `pytest` 入口锁定 `workflow_service`、`context_service` 与 `runtime_smoke_reports` suites
- phase-4 第一轮应重点验证：工作流 run/step 状态流转、resume/override 版本语义、`context_compile_snapshot` 关键字段、runtime self-check/provider-state/smoke reports 的响应结构

### 8.2 前端验证

- 继续沿用 `node:test` 结构契约测试锁定 runtime workbench 与 hooks 边界
- phase-4 第一轮应重点验证：runtime 页面继续复用 workbench、hook 继续集中管理诊断状态、editor 侧上下文消费不退回页面级原始请求
- 继续要求 `npm.cmd run typecheck` 通过，防止前后端合同漂移后静态类型失配

### 8.3 推荐验证命令

```powershell
D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_workflow_service.py -q
D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_context_service.py -q
D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_runtime_smoke_reports.py -q
node D:\WritierLab\WriterLab-v1\Next.js\frontend\tests\features\runtime-debug-workbench.test.mjs
Set-Location D:\WritierLab\WriterLab-v1\Next.js\frontend
npm.cmd run typecheck
```

## 9. 风险与约束

- 如果在后端合同未冻结前先改 editor 或 runtime 页面，前端很容易重新堆积临时兼容分支
- `ContextCompileSnapshot` 一旦继续无节制扩字段，会削弱可解释性并放大回归成本
- runtime smoke 与 self-check 已承担验收职责，若再新增平行验证入口，会让故障解释分裂
- phase-4 第一轮必须克制范围，不把 workflow、context、runtime 与 consistency 混成一次性“大中台改造”

## 10. 交付结论

phase-4 第一轮设计完成后，应得到以下明确结论：继续采用方案 A，以后端契约优先方式收口 `workflow / context / runtime` 的联动闭环；前端继续沿用 `use-scene-context()` 与 `use-runtime-diagnostics()` 两条消费边界；本地验证继续以 `pytest`、`node:test`、`typecheck` 与 runtime notes 中既有脚本为准。

该设计文档确认后，下一步才进入 implementation plan。implementation plan 必须继承本文件的范围边界，不允许重新定义 phase-4。