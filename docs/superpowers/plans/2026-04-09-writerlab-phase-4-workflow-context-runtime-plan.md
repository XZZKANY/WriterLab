# WriterLab phase-4 workflow、context 与 runtime 收口 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 以最小改动收口 WriterLab phase-4 第一轮的 workflow、context 与 runtime 联动合同，并为后续实现提供本地可重复验证的任务序列。

**Architecture:** 延续后端契约优先顺序，先用现有 backend test suites 锁定 workflow run、context snapshot 与 runtime 诊断的结构语义，再补最小后端修补，最后锁前端 hooks/workbench 消费边界。前端继续复用 `lib/api/* + hooks + 薄页面入口`，不新建平行页面或系统。

**Tech Stack:** FastAPI、SQLAlchemy、Pydantic、pytest、Next.js 16、React 19、TypeScript strict、node:test

---

## 范围与 Gate

### 本计划覆盖

- `WriterLab-v1/fastapi/backend/app/api/ai.py`
- `WriterLab-v1/fastapi/backend/app/api/runtime.py`
- `WriterLab-v1/fastapi/backend/app/services/workflow/workflow_service.py`
- `WriterLab-v1/fastapi/backend/app/services/context/context_service.py`
- `WriterLab-v1/fastapi/backend/app/services/runtime/smoke_report_service.py`
- `WriterLab-v1/fastapi/backend/app/schemas/workflow.py`
- `WriterLab-v1/fastapi/backend/tests/services/*`
- `WriterLab-v1/fastapi/backend/tests/api/*`
- `WriterLab-v1/fastapi/backend/tests/runtime/*`
- `WriterLab-v1/Next.js/frontend/features/runtime/*`
- `WriterLab-v1/Next.js/frontend/features/editor/hooks/use-scene-context.ts`
- `WriterLab-v1/Next.js/frontend/tests/features/*`
- `.codex/*`
- `docs/superpowers/*`

### 本计划不覆盖

- editor 主工作区重写或 `editor-workspace` 再拆分
- 新建 workflow 中心页、runtime 中心页或统一事件总线控制台
- provider 配置体系重构、模型策略重写或新的实时观测系统
- 超出 phase-4 第一轮收口之外的产品功能
- 推送远端、发版或任何 CI 依赖的验收动作

### Gate 决策

- 只修改真实实现文件，`app/services/workflow_service.py` 与 `app/services/context_service.py` 这两个顶层文件是模块别名，真正改动落在 `app/services/workflow/workflow_service.py` 与 `app/services/context/context_service.py`
- 先锁 backend contracts，再锁 frontend consumption；不允许前端先做页面扩张
- 只补强现有 tests 和 hooks，不新建第二套 runtime hook、第二套 context store 或第二套路由聚合层
- 如果某项失败基线首次即绿，记录为“既有实现已满足合同”，直接进入下一步，不为制造改动而改代码

## 文件职责

- `WriterLab-v1/fastapi/backend/app/services/workflow/workflow_service.py`
  - workflow run 主链路、`_workflow_output()`、resume/override 与 context snapshot 回写的真实实现。
- `WriterLab-v1/fastapi/backend/app/services/context/context_service.py`
  - `build_scene_context()`、候选去重、diversity、summary 触发与 snapshot 结构。
- `WriterLab-v1/fastapi/backend/app/api/ai.py`
  - workflow HTTP 合同入口，负责 run / resume / override / cancel 响应语义。
- `WriterLab-v1/fastapi/backend/app/api/runtime.py`
  - self-check、provider-state、smoke reports 与 runtime events 的读取入口。
- `WriterLab-v1/fastapi/backend/app/services/runtime/smoke_report_service.py`
  - smoke 报告读取、解析与 regression 对比逻辑。
- `WriterLab-v1/fastapi/backend/app/schemas/workflow.py`
  - `ContextCompileSnapshot`、`WorkflowRunResponse`、`WorkflowStepResponse` 等 phase-4 关键 schema。
- `WriterLab-v1/fastapi/backend/tests/services/workflow_service_suite.py`
  - workflow service 级合同与状态流转回归。
- `WriterLab-v1/fastapi/backend/tests/services/context_service_suite.py`
  - context compiler 的 snapshot、summary 与 scope 语义回归。
- `WriterLab-v1/fastapi/backend/tests/api/api_routes_suite.py`
  - workflow 与 runtime 路由响应结构回归。
- `WriterLab-v1/fastapi/backend/tests/runtime/runtime_smoke_reports_suite.py`
  - smoke 报告列表、详情与 regression 浏览合同。
- `WriterLab-v1/Next.js/frontend/features/runtime/runtime-debug-workbench.tsx`
  - runtime 诊断 UI，负责展示 workflow debug、provider runtime、smoke console、provider matrix 与 context compiler。
- `WriterLab-v1/Next.js/frontend/features/runtime/hooks/use-runtime-diagnostics.ts`
  - runtime 页面统一读取 health / self-check / provider-state / smoke reports / provider matrix。
- `WriterLab-v1/Next.js/frontend/features/editor/hooks/use-scene-context.ts`
  - editor 端上下文与一致性结果的集中状态边界。
- `WriterLab-v1/Next.js/frontend/tests/features/runtime-debug-workbench.test.mjs`
  - runtime workbench 的结构与消费边界回归。
- `WriterLab-v1/Next.js/frontend/tests/features/editor-scene-context-contract.test.mjs`
  - 新建，锁定 `use-scene-context()` 的上下文写入与 reset 语义。
- `.codex/operations-log.md`
  - 记录 phase-4 实施顺序、验证结果与提交信息。
- `.codex/verification-report.md`
  - 记录 phase-4 第一轮实现后的本地审查结果。

### Task 1: 锁定 workflow/context 后端失败基线

**Files:**
- Modify: `WriterLab-v1/fastapi/backend/tests/services/workflow_service_suite.py`
- Modify: `WriterLab-v1/fastapi/backend/tests/services/context_service_suite.py`
- Modify: `WriterLab-v1/fastapi/backend/tests/api/api_routes_suite.py`
- Test: `WriterLab-v1/fastapi/backend/tests/test_workflow_service.py`
- Test: `WriterLab-v1/fastapi/backend/tests/test_context_service.py`
- Test: `WriterLab-v1/fastapi/backend/tests/test_api_routes.py`
- Reference: `WriterLab-v1/fastapi/backend/app/services/workflow/workflow_service.py`
- Reference: `WriterLab-v1/fastapi/backend/app/services/context/context_service.py`
- Reference: `WriterLab-v1/fastapi/backend/app/schemas/workflow.py`

- [ ] **Step 1: 为 workflow output 写失败测试，锁定 snapshot 回传合同**

```python
def test_workflow_output_includes_context_compile_snapshot():
    run = _fake_run(
        context_compile_snapshot={
            "schema_version": "context_compile_snapshot.v1",
            "hard_filters": ["project_id=demo"],
            "summary_reason": "recent_scenes_over_budget",
        }
    )
    payload = _workflow_output(run, planner_output=None, final_text="", version_id=None, memory_id=None, guard_output=None, failures=[])
    assert payload["context_compile_snapshot"]["schema_version"] == "context_compile_snapshot.v1"
    assert payload["context_compile_snapshot"]["summary_reason"] == "recent_scenes_over_budget"
```

- [ ] **Step 2: 在现有 context suite 测试中追加断言，锁定 summary / clipped / scope 语义**

```python
assert snapshot.summary_triggered is True
assert snapshot.summary_reason == "recent_scenes_over_2000_tokens"
assert "scene-1" in snapshot.clipped_sources
assert snapshot.scope_resolution["recent_scenes"] == "branch"
```

- [ ] **Step 3: 为 workflow GET 路由写失败测试，锁定 API 响应带出 snapshot**

```python
def test_scene_workflow_get_endpoint_exposes_context_compile_snapshot(monkeypatch):
    app = FastAPI()
    app.include_router(ai_router)
    workflow_id = UUID("66666666-6666-6666-6666-666666666666")
    now = datetime.utcnow()
    fake_run = SimpleNamespace(
        id=workflow_id,
        project_id=None,
        scene_id=None,
        branch_id=None,
        run_type="scene_pipeline",
        status="completed",
        current_step="done",
        provider_mode="smoke_fixture",
        input_payload={},
        output_payload={},
        error_message=None,
        retry_count=0,
        needs_merge=False,
        quality_degraded=False,
        resume_from_step=None,
        resume_checkpoint=None,
        fixture_version="v1",
        fixture_scenario="happy_path",
        context_compile_snapshot={"schema_version": "context_compile_snapshot.v1", "summary_reason": "recent_scenes_over_budget", "clipped_sources": ["scene-1"]},
        queued_at=now,
        heartbeat_at=None,
        lease_expires_at=None,
        cancel_requested_at=None,
        cancelled_at=None,
        started_at=None,
        completed_at=now,
        created_at=now,
        updated_at=now,
        steps=[],
    )
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr("app.api.ai.get_workflow_run", lambda db, workflow_id: fake_run)
    monkeypatch.setattr("app.api.ai.list_workflow_steps", lambda db, workflow_id: [])
    client = TestClient(app)
    response = client.get(f"/api/ai/workflows/{workflow_id}")
    assert response.status_code == 200
    assert response.json()["context_compile_snapshot"]["clipped_sources"] == ["scene-1"]
```

- [ ] **Step 4: 运行三组测试并确认红灯基线稳定**

Run: `D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_workflow_service.py D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_context_service.py D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_api_routes.py -q`
Expected: FAIL；若首次即 PASS，记录为“当前实现已满足本项合同”，并保留测试作为 phase-4 基线。

- [ ] **Step 5: 提交基线测试**

```bash
git add WriterLab-v1/fastapi/backend/tests/services/workflow_service_suite.py WriterLab-v1/fastapi/backend/tests/services/context_service_suite.py WriterLab-v1/fastapi/backend/tests/api/api_routes_suite.py
git commit -m "新增 phase-4 workflow context 合同失败基线"
```

### Task 2: 收口 workflow/context 后端合同

**Files:**
- Modify: `WriterLab-v1/fastapi/backend/app/services/workflow/workflow_service.py`
- Modify: `WriterLab-v1/fastapi/backend/app/services/context/context_service.py`
- Modify: `WriterLab-v1/fastapi/backend/app/schemas/workflow.py`
- Modify: `WriterLab-v1/fastapi/backend/app/api/ai.py`
- Test: `WriterLab-v1/fastapi/backend/tests/test_workflow_service.py`
- Test: `WriterLab-v1/fastapi/backend/tests/test_context_service.py`
- Test: `WriterLab-v1/fastapi/backend/tests/test_api_routes.py`

- [ ] **Step 1: 在 workflow output 中显式带出 `context_compile_snapshot`**

```python
def _workflow_output(
    run: WorkflowRun,
    *,
    planner_output: PlannerOutput | None,
    final_text: str,
    version_id: str | None,
    memory_id: str | None,
    guard_output: GuardOutput | None,
    failures: list[dict],
) -> dict[str, Any]:
    return {
        "planner_output": planner_output.model_dump() if planner_output else None,
        "context_compile_snapshot": run.context_compile_snapshot,
        "final_text": final_text or None,
        "partial_text": (final_text or None) if failures else None,
        "auto_applied": bool(version_id),
        "safe_to_apply": guard_output.safe_to_apply if guard_output else False,
        "needs_merge": run.needs_merge,
        "quality_degraded": run.quality_degraded,
        "version_id": version_id,
        "memory_id": memory_id,
        "step_failures": failures,
    }
```

- [ ] **Step 2: 对照测试补齐 `ContextCompileSnapshot` 关键字段默认值**

```python
class ContextCompileSnapshot(BaseModel):
    schema_version: str = "context_compile_snapshot.v1"
    hard_filters: list[str] = Field(default_factory=list)
    hard_filter_result: dict[str, bool | str | None] = Field(default_factory=dict)
    clipped_sources: list[str] = Field(default_factory=list)
    deduped_sources: list[str] = Field(default_factory=list)
    source_diversity_applied: dict[str, int] = Field(default_factory=dict)
    summary_reason: str | None = None
    summary_output: list[dict[str, Any]] = Field(default_factory=list)
```

- [ ] **Step 3: 如果 API 路由序列化缺字段，保持 run 直出并继续挂 steps**

```python
@router.get("/workflows/{workflow_id}", response_model=WorkflowRunResponse)
def get_scene_workflow(workflow_id: UUID, db: Session = Depends(get_db)):
    run = get_workflow_run(db, workflow_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    run.steps = list_workflow_steps(db, workflow_id)
    return run
```

- [ ] **Step 4: 运行三组测试转绿**

Run: `D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_workflow_service.py D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_context_service.py D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_api_routes.py -q`
Expected: PASS

- [ ] **Step 5: 提交 workflow/context 后端合同收口**

```bash
git add WriterLab-v1/fastapi/backend/app/services/workflow/workflow_service.py WriterLab-v1/fastapi/backend/app/services/context/context_service.py WriterLab-v1/fastapi/backend/app/schemas/workflow.py WriterLab-v1/fastapi/backend/app/api/ai.py WriterLab-v1/fastapi/backend/tests/services/workflow_service_suite.py WriterLab-v1/fastapi/backend/tests/services/context_service_suite.py WriterLab-v1/fastapi/backend/tests/api/api_routes_suite.py
git commit -m "收口 phase-4 workflow context 后端合同"
```

### Task 3: 收口 runtime 诊断与 smoke 后端合同

**Files:**
- Modify: `WriterLab-v1/fastapi/backend/tests/api/api_routes_suite.py`
- Modify: `WriterLab-v1/fastapi/backend/tests/runtime/runtime_smoke_reports_suite.py`
- Modify: `WriterLab-v1/fastapi/backend/app/api/runtime.py`
- Modify: `WriterLab-v1/fastapi/backend/app/services/runtime/smoke_report_service.py`
- Test: `WriterLab-v1/fastapi/backend/tests/test_api_routes.py`
- Test: `WriterLab-v1/fastapi/backend/tests/test_runtime_smoke_reports.py`

- [ ] **Step 1: 扩展 runtime self-check 失败测试，锁定推荐命令与步骤摘要**

```python
assert payload["provider_matrix"]["steps"] == ["style", "write"]
assert payload["workflow_runtime"]["last_startup_stage"] == "ready"
assert payload["recommended_checks"]["backend"][0].endswith("check-backend.ps1")
assert payload["recommended_checks"]["frontend"][0].endswith("check-frontend.ps1")
```

- [ ] **Step 2: 扩展 smoke report 失败测试，锁定 detail / regression 的诊断字段**

```python
assert payload["scenarios"][0]["resume_checkpoint"] == "style"
assert payload["scenarios"][0]["event_summary"]["counts"]["workflow_resumed"] == 1
assert payload["report"]["provider_preflight"]["summary"]["ok"] is True
```

```python
assert payload["baseline_report"]["filename"] == "backend-full-smoke-20260329-191500.json"
assert payload["regression_free"] is False
assert payload["findings"][0]["scope"] == "scenario"
```

- [ ] **Step 3: 如果红灯，按目标状态补齐 runtime 路由响应结构**

```python
return {
    "backend_root": {"ok": True, "message": "WriterLab backend is running", "endpoint": "/"},
    "health": health,
    "knowledge": {
        "vector_backend": vector_backend_label(db),
        "retrieval_mode": knowledge_status.get("mode") or ("pgvector" if knowledge_status.get("pgvector_ready") else "fallback"),
        "retrieval_reason": knowledge_status.get("reason") or "Knowledge backend status available",
        "pgvector_ready": bool(knowledge_status.get("pgvector_ready")),
    },
    "provider_matrix": {"ok": bool(provider_matrix.rules), "rule_count": len(provider_matrix.rules), "steps": [rule.step for rule in provider_matrix.rules]},
    "provider_runtime": provider_runtime_summary.model_dump(),
    "workflow_runtime": {"workflow_runner_started": bool(runtime_status.get("workflow_runner_started")), "recovery_scan_completed": bool(runtime_status.get("recovery_scan_completed")), "recovered_runs": int(runtime_status.get("recovered_runs") or 0), "last_startup_stage": str(runtime_status.get("last_startup_stage") or "unknown"), "startup_error": runtime_status.get("startup_error")},
    "recommended_checks": {"backend": ["powershell -ExecutionPolicy Bypass -File D:\\WritierLab\\WriterLab-v1\\scripts\\check-backend.ps1"], "frontend": ["powershell -ExecutionPolicy Bypass -File D:\\WritierLab\\WriterLab-v1\\scripts\\check-frontend.ps1"], "notes": ["Frontend build may hit Windows spawn EPERM in restricted shells; treat it as an environment limitation unless TypeScript compilation also fails."]},
}
```

- [ ] **Step 4: 运行 runtime 两组测试转绿**

Run: `D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_api_routes.py D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_runtime_smoke_reports.py -q`
Expected: PASS

- [ ] **Step 5: 提交 runtime 后端合同收口**

```bash
git add WriterLab-v1/fastapi/backend/app/api/runtime.py WriterLab-v1/fastapi/backend/app/services/runtime/smoke_report_service.py WriterLab-v1/fastapi/backend/tests/api/api_routes_suite.py WriterLab-v1/fastapi/backend/tests/runtime/runtime_smoke_reports_suite.py
git commit -m "收口 phase-4 runtime 诊断与 smoke 合同"
```

### Task 4: 收口前端 runtime 与 editor 消费合同

**Files:**
- Create: `WriterLab-v1/Next.js/frontend/tests/features/editor-scene-context-contract.test.mjs`
- Modify: `WriterLab-v1/Next.js/frontend/tests/features/runtime-debug-workbench.test.mjs`
- Modify: `WriterLab-v1/Next.js/frontend/features/editor/hooks/use-scene-context.ts`
- Modify: `WriterLab-v1/Next.js/frontend/features/runtime/runtime-debug-workbench.tsx`
- Modify: `WriterLab-v1/Next.js/frontend/features/runtime/hooks/use-runtime-diagnostics.ts`

- [ ] **Step 1: 新建 editor scene-context 结构测试**

```javascript
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const hookPath = new URL("../../features/editor/hooks/use-scene-context.ts", import.meta.url);

test("use-scene-context 应集中应用 payload 并在 reset 时清空缓存", async () => {
  const source = await readFile(hookPath, "utf8");
  assert.equal(source.includes("setTimeline(payload.timeline_events ?? []);"), true);
  assert.equal(source.includes("setMemories(payload.style_memories ?? []);"), true);
  assert.equal(source.includes("setContextSnapshot(payload.context_compile_snapshot ?? null);"), true);
  assert.equal(source.includes("setTimeline([]);"), true);
  assert.equal(source.includes("setContextSnapshot(null);"), true);
});
```

- [ ] **Step 2: 扩展 runtime workbench 结构测试，锁定 snapshot 解释字段展示**

```javascript
assert.equal(runtimeHookSource.includes("fetchRuntimeSelfCheck"), true);
assert.equal(source.includes("summary_reason"), true);
assert.equal(source.includes("clipped_sources"), true);
assert.equal(source.includes("deduped_sources"), true);
```

- [ ] **Step 3: 实现最小前端修补，清掉 editor 端陈旧上下文并展示 snapshot 解释字段**

```typescript
function resetSceneContext() {
  setIssues([]);
  setIssueSummary(null);
  setShowAllIssues(false);
  setTimeline([]);
  setMemories([]);
  setKnowledgeHits([]);
  setRecentScenes([]);
  setContextSnapshot(null);
  setVnExport(null);
}
```

```tsx
<Status
  title="Snapshot Summary"
  lines={[
    `summary_reason: ${activeContextSnapshot.summary_reason || "none"}`,
    `clipped_sources: ${(activeContextSnapshot.clipped_sources ?? []).join(", ") || "none"}`,
    `deduped_sources: ${(activeContextSnapshot.deduped_sources ?? []).join(", ") || "none"}`,
  ]}
/>
```

- [ ] **Step 4: 运行前端结构测试与类型检查**

Run: `node D:\WritierLab\WriterLab-v1\Next.js\frontend\tests\features\editor-scene-context-contract.test.mjs`
Expected: PASS

Run: `node D:\WritierLab\WriterLab-v1\Next.js\frontend\tests\features\runtime-debug-workbench.test.mjs`
Expected: PASS

Run: `node D:\WritierLab\WriterLab-v1\Next.js\frontend\tests\features\editor-workspace-structure.test.mjs`
Expected: PASS

Run: `Set-Location D:\WritierLab\WriterLab-v1\Next.js\frontend; npm.cmd run typecheck`
Expected: PASS

- [ ] **Step 5: 提交前端消费合同收口**

```bash
git add WriterLab-v1/Next.js/frontend/tests/features/editor-scene-context-contract.test.mjs WriterLab-v1/Next.js/frontend/tests/features/runtime-debug-workbench.test.mjs WriterLab-v1/Next.js/frontend/features/editor/hooks/use-scene-context.ts WriterLab-v1/Next.js/frontend/features/runtime/runtime-debug-workbench.tsx WriterLab-v1/Next.js/frontend/features/runtime/hooks/use-runtime-diagnostics.ts
git commit -m "接入 phase-4 runtime 与 editor 消费合同"
```

### Task 5: 留痕、总验证与收口

**Files:**
- Modify: `.codex/operations-log.md`
- Modify: `.codex/verification-report.md`
- Modify: `docs/superpowers/specs/2026-04-09-writerlab-phase-4-workflow-context-runtime-design.md`
- Modify: `docs/superpowers/plans/2026-04-09-writerlab-phase-4-workflow-context-runtime-plan.md`

- [ ] **Step 1: 更新 operations-log，记录 phase-4 第一轮实施顺序与提交点**

```markdown
## 2026-04-09 phase-4 第一轮实施
- Task 1：workflow/context 失败基线
- Task 2：workflow/context 后端合同收口
- Task 3：runtime 诊断与 smoke 合同收口
- Task 4：前端 runtime 与 editor 消费合同收口
```

- [ ] **Step 2: 更新 verification-report，补 phase-4 第一轮审查结论**

````markdown
## 2026-04-09 phase-4 第一轮审查报告

```Scoring
score: 92
```

summary: 'phase-4 第一轮已形成 workflow / context / runtime 的稳定联动合同与本地验证闭环。'
````

- [ ] **Step 3: 运行总验证**

Run: `D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_workflow_service.py D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_context_service.py D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_api_routes.py D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_runtime_smoke_reports.py -q`
Expected: PASS

Run: `node D:\WritierLab\WriterLab-v1\Next.js\frontend\tests\features\editor-scene-context-contract.test.mjs`
Expected: PASS

Run: `node D:\WritierLab\WriterLab-v1\Next.js\frontend\tests\features\runtime-debug-workbench.test.mjs`
Expected: PASS

Run: `node D:\WritierLab\WriterLab-v1\Next.js\frontend\tests\features\editor-workspace-structure.test.mjs`
Expected: PASS

Run: `Set-Location D:\WritierLab\WriterLab-v1\Next.js\frontend; npm.cmd run typecheck`
Expected: PASS

- [ ] **Step 4: 提交留痕与计划回填**

```bash
git add .codex/operations-log.md .codex/verification-report.md docs/superpowers/specs/2026-04-09-writerlab-phase-4-workflow-context-runtime-design.md docs/superpowers/plans/2026-04-09-writerlab-phase-4-workflow-context-runtime-plan.md
git commit -m "完成 phase-4 第一轮 workflow context runtime 收口"
```

- [ ] **Step 5: 在计划末尾回填实施结果**

```markdown
## 实施回填
- [x] Task 1：workflow/context 合同基线已落地
- [x] Task 2：workflow/context 后端合同已收口
- [x] Task 3：runtime 诊断与 smoke 合同已收口
- [x] Task 4：前端 runtime 与 editor 消费合同已收口
- [x] Task 5：总验证与留痕完成
```

## 完成标准

- `WorkflowRunResponse` 与 `workflow output` 都能稳定带出 `context_compile_snapshot`
- `ContextCompileSnapshot` 的 `summary_reason`、`clipped_sources`、`deduped_sources`、`scope_resolution` 有后端测试锁定
- `/api/runtime/self-check`、`/api/runtime/provider-state`、smoke report 浏览接口有可重复 pytest 回归
- `use-scene-context()` 的 reset 不再保留陈旧上下文
- runtime workbench 可展示 snapshot 解释字段，且继续通过 `use-runtime-diagnostics()` 统一取数
- `.codex`、spec、plan 与 verification 留痕完整

## 执行交接

- 推荐执行方式：`superpowers:subagent-driven-development`
- 备选执行方式：`superpowers:executing-plans`
- 执行时保持每个 Task 一个提交点，并在 Task 结束后立即更新 `.codex/operations-log.md`
- 如某项失败基线首次即绿，保留测试与验证结果，不为制造差异而强行改代码
