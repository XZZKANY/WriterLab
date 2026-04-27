"""工作流快照解析与最终输出组装。

承接来自 workflow_service.py 的纯函数：
- 步骤快照取值（_extract_effective_snapshot 与 _extract_*）
- planner output 解析（_build_planner_output / _extract_planner_output）
- guard fixture（_fixture_guard_output）
- 步骤复用判定（_should_reuse_step）
- 最终 workflow 输出组装（_workflow_output）

这些函数都不触达 DB，输入都是 ORM 只读属性 / Pydantic 模型 / 普通 dict。
"""

from __future__ import annotations

from typing import Any

from app.models.scene import Scene
from app.models.workflow_run import WorkflowRun
from app.models.workflow_step import WorkflowStep
from app.schemas.workflow import GuardOutput, PlannerOutput, Violation
from app.services.workflow_constants import STEP_ORDER, STEP_REUSABLE_STATUSES


def _extract_effective_snapshot(step: WorkflowStep | None) -> dict[str, Any]:
    if not step:
        return {}
    return step.effective_output_snapshot or step.output_payload or {}


def _build_planner_output(raw_plan: str, *, scene: Scene, guidance: list[str]) -> PlannerOutput:
    normalized = (raw_plan or "").strip()
    if not normalized or normalized == "[fixture-malformed-planner]":
        raise ValueError("planner output is not valid plan text")
    return PlannerOutput(
        summary=normalized[:500] or "No summary",
        writing_goals=guidance[:5],
        constraints=list(scene.must_avoid or []),
        next_prompt_hints=list(scene.must_include or []),
        raw_plan=normalized,
    )


def _extract_planner_output(step: WorkflowStep | None) -> PlannerOutput | None:
    snapshot = _extract_effective_snapshot(step)
    if not snapshot:
        return None
    try:
        return PlannerOutput(**snapshot)
    except Exception:
        raw_plan = str(snapshot.get("raw_plan") or snapshot.get("plan") or "").strip()
        return PlannerOutput(summary=raw_plan[:500] or "No summary", raw_plan=raw_plan) if raw_plan else None


def _fixture_guard_output(final_text: str, *, fixture_scenario: str) -> GuardOutput | None:
    if fixture_scenario != "guard_block":
        return None
    return GuardOutput(
        safe_to_apply=False,
        needs_rewrite=True,
        needs_user_review=True,
        violations=[
            Violation(
                type="guard_violation",
                span=None,
                rule_id="guard.fixture_block",
                severity="high",
                reason="Fixture scenario forced a guard block for acceptance coverage.",
                suggestion="Review the deterministic guard-block scenario output before applying.",
            )
        ],
    )


def _extract_final_text(step_map: dict[str, WorkflowStep]) -> str:
    style_step = step_map.get("style")
    if style_step and style_step.status == "completed":
        value = _extract_effective_snapshot(style_step).get("styled_text")
        if isinstance(value, str) and value.strip():
            return value.strip()
    write_step = step_map.get("write")
    if write_step and write_step.status == "completed":
        value = _extract_effective_snapshot(write_step).get("draft_text")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_version_id(step_map: dict[str, WorkflowStep]) -> str | None:
    value = _extract_effective_snapshot(step_map.get("store")).get("version_id") if step_map.get("store") else None
    return str(value) if value else None


def _extract_memory_id(step_map: dict[str, WorkflowStep]) -> str | None:
    value = _extract_effective_snapshot(step_map.get("memory")).get("memory_id") if step_map.get("memory") else None
    return str(value) if value else None


def _should_reuse_step(step: WorkflowStep | None, resume_from_step: str | None, step_key: str) -> bool:
    if not step or step.status not in STEP_REUSABLE_STATUSES:
        return False
    return not resume_from_step or STEP_ORDER[step_key] < STEP_ORDER.get(resume_from_step, 0)


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
        "final_text": final_text or None,
        "partial_text": (final_text or None) if failures else None,
        "auto_applied": bool(version_id),
        "safe_to_apply": guard_output.safe_to_apply if guard_output else False,
        "needs_rewrite": guard_output.needs_rewrite if guard_output else False,
        "needs_user_review": guard_output.needs_user_review if guard_output else False,
        "violations": [item.model_dump() for item in (guard_output.violations if guard_output else [])],
        "needs_merge": run.needs_merge,
        "quality_degraded": run.quality_degraded,
        "version_id": version_id,
        "memory_id": memory_id,
        "step_failures": failures,
    }
