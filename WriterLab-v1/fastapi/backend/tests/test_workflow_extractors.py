"""workflow_extractors 模块的纯函数直测。

T-6.A3 拆分后这些函数从 workflow_service.py 移出来；它们都是纯函数（不触达 DB），
适合用 SimpleNamespace 模拟 ORM 步骤对象做边界覆盖。
"""

from types import SimpleNamespace

import pytest

from app.schemas.workflow import GuardOutput, PlannerOutput, Violation
from app.services.workflow_extractors import (
    _build_planner_output,
    _extract_effective_snapshot,
    _extract_final_text,
    _extract_memory_id,
    _extract_planner_output,
    _extract_version_id,
    _fixture_guard_output,
    _should_reuse_step,
    _workflow_output,
)


def _step(**fields):
    """构造一个最小的 step 对象，模拟 SQLAlchemy WorkflowStep 行为。"""
    defaults = {
        "status": "completed",
        "effective_output_snapshot": None,
        "output_payload": None,
    }
    defaults.update(fields)
    return SimpleNamespace(**defaults)


# ---------- _extract_effective_snapshot ----------

def test_extract_effective_snapshot_handles_none():
    assert _extract_effective_snapshot(None) == {}


def test_extract_effective_snapshot_prefers_effective_over_payload():
    step = _step(effective_output_snapshot={"a": 1}, output_payload={"a": 2})
    assert _extract_effective_snapshot(step) == {"a": 1}


def test_extract_effective_snapshot_falls_back_to_output_payload():
    step = _step(effective_output_snapshot=None, output_payload={"x": 9})
    assert _extract_effective_snapshot(step) == {"x": 9}


def test_extract_effective_snapshot_returns_empty_when_both_missing():
    assert _extract_effective_snapshot(_step()) == {}


# ---------- _build_planner_output ----------

def test_build_planner_output_truncates_summary_to_500_chars():
    long_plan = "a" * 1200
    scene = SimpleNamespace(must_avoid=["x"], must_include=["y"])
    out = _build_planner_output(long_plan, scene=scene, guidance=["g1", "g2"])
    assert isinstance(out, PlannerOutput)
    assert len(out.summary) == 500
    assert out.raw_plan == long_plan
    assert out.writing_goals == ["g1", "g2"]
    assert out.constraints == ["x"]
    assert out.next_prompt_hints == ["y"]


def test_build_planner_output_rejects_empty_plan():
    scene = SimpleNamespace(must_avoid=[], must_include=[])
    with pytest.raises(ValueError):
        _build_planner_output("   ", scene=scene, guidance=[])


def test_build_planner_output_rejects_fixture_malformed_token():
    scene = SimpleNamespace(must_avoid=[], must_include=[])
    with pytest.raises(ValueError):
        _build_planner_output("[fixture-malformed-planner]", scene=scene, guidance=[])


def test_build_planner_output_caps_writing_goals_at_5():
    scene = SimpleNamespace(must_avoid=[], must_include=[])
    guidance = [f"g{i}" for i in range(10)]
    out = _build_planner_output("plan", scene=scene, guidance=guidance)
    assert out.writing_goals == guidance[:5]


# ---------- _extract_planner_output ----------

def test_extract_planner_output_returns_none_for_empty_step():
    assert _extract_planner_output(None) is None
    assert _extract_planner_output(_step()) is None


def test_extract_planner_output_parses_full_snapshot():
    step = _step(effective_output_snapshot={"summary": "S", "raw_plan": "R", "writing_goals": ["g"]})
    parsed = _extract_planner_output(step)
    assert isinstance(parsed, PlannerOutput)
    assert parsed.summary == "S"
    assert parsed.raw_plan == "R"
    assert parsed.writing_goals == ["g"]


def test_extract_planner_output_falls_back_to_raw_plan_when_schema_invalid():
    step = _step(effective_output_snapshot={"raw_plan": "fallback"})
    parsed = _extract_planner_output(step)
    assert isinstance(parsed, PlannerOutput)
    assert parsed.raw_plan == "fallback"
    assert parsed.summary.startswith("fallback")


def test_extract_planner_output_returns_none_when_only_garbage():
    step = _step(effective_output_snapshot={"unrelated": True})
    assert _extract_planner_output(step) is None


# ---------- _fixture_guard_output ----------

def test_fixture_guard_output_only_triggers_for_guard_block_scenario():
    assert _fixture_guard_output("any text", fixture_scenario="happy_path") is None
    assert _fixture_guard_output("", fixture_scenario="planner_wait_review") is None


def test_fixture_guard_output_for_guard_block_returns_unsafe_with_violation():
    out = _fixture_guard_output("draft", fixture_scenario="guard_block")
    assert isinstance(out, GuardOutput)
    assert out.safe_to_apply is False
    assert out.needs_rewrite is True
    assert out.needs_user_review is True
    assert len(out.violations) == 1
    assert out.violations[0].rule_id == "guard.fixture_block"
    assert out.violations[0].severity == "high"


# ---------- _extract_final_text ----------

def test_extract_final_text_prefers_styled_text_from_completed_style_step():
    step_map = {
        "style": _step(status="completed", effective_output_snapshot={"styled_text": " styled "}),
        "write": _step(status="completed", effective_output_snapshot={"draft_text": "drafted"}),
    }
    assert _extract_final_text(step_map) == "styled"


def test_extract_final_text_falls_back_to_write_when_style_missing_or_failed():
    step_map = {
        "write": _step(status="completed", effective_output_snapshot={"draft_text": "drafted"}),
    }
    assert _extract_final_text(step_map) == "drafted"

    step_map_failed_style = {
        "style": _step(status="failed", effective_output_snapshot={"styled_text": "leaked"}),
        "write": _step(status="completed", effective_output_snapshot={"draft_text": "fallback"}),
    }
    assert _extract_final_text(step_map_failed_style) == "fallback"


def test_extract_final_text_returns_empty_when_neither_step_completed():
    step_map = {
        "style": _step(status="running", effective_output_snapshot={"styled_text": "x"}),
        "write": _step(status="failed", effective_output_snapshot={"draft_text": "y"}),
    }
    assert _extract_final_text(step_map) == ""


def test_extract_final_text_ignores_empty_strings():
    step_map = {
        "style": _step(status="completed", effective_output_snapshot={"styled_text": "   "}),
        "write": _step(status="completed", effective_output_snapshot={"draft_text": "actual"}),
    }
    assert _extract_final_text(step_map) == "actual"


# ---------- _extract_version_id / _extract_memory_id ----------

def test_extract_version_id_reads_from_store_step_snapshot():
    step_map = {
        "store": _step(effective_output_snapshot={"version_id": "v-123"}),
    }
    assert _extract_version_id(step_map) == "v-123"


def test_extract_version_id_returns_none_without_store_step():
    assert _extract_version_id({}) is None


def test_extract_memory_id_reads_from_memory_step_snapshot():
    step_map = {
        "memory": _step(effective_output_snapshot={"memory_id": "mem-9"}),
    }
    assert _extract_memory_id(step_map) == "mem-9"


def test_extract_memory_id_returns_none_when_snapshot_missing_field():
    step_map = {"memory": _step(effective_output_snapshot={})}
    assert _extract_memory_id(step_map) is None


# ---------- _should_reuse_step ----------

def test_should_reuse_step_returns_false_when_step_missing():
    assert _should_reuse_step(None, None, "analyze") is False


def test_should_reuse_step_returns_false_when_status_not_reusable():
    assert _should_reuse_step(_step(status="failed"), None, "analyze") is False
    assert _should_reuse_step(_step(status="running"), None, "analyze") is False


def test_should_reuse_step_returns_true_when_no_resume_target():
    assert _should_reuse_step(_step(status="completed"), None, "analyze") is True
    assert _should_reuse_step(_step(status="skipped"), None, "memory") is True


def test_should_reuse_step_only_reuses_steps_before_resume_point():
    # 从 "write" 开始重跑，则 "analyze"（10 < 30）和 "plan"（20 < 30）应复用，
    # "write" 自身（30）和后续步骤不能复用。
    assert _should_reuse_step(_step(status="completed"), "write", "analyze") is True
    assert _should_reuse_step(_step(status="completed"), "write", "plan") is True
    assert _should_reuse_step(_step(status="completed"), "write", "write") is False
    assert _should_reuse_step(_step(status="completed"), "write", "style") is False


# ---------- _workflow_output ----------

def test_workflow_output_assembles_payload_with_guard_and_failures():
    run = SimpleNamespace(needs_merge=True, quality_degraded=False)
    guard = GuardOutput(safe_to_apply=False, needs_rewrite=True, needs_user_review=True, violations=[
        Violation(type="t", rule_id="r", severity="high", reason="bad")
    ])
    payload = _workflow_output(
        run,
        planner_output=PlannerOutput(summary="S"),
        final_text="text",
        version_id=None,
        memory_id=None,
        guard_output=guard,
        failures=[{"step": "style", "error": "boom"}],
    )
    assert payload["safe_to_apply"] is False
    assert payload["needs_rewrite"] is True
    assert payload["needs_user_review"] is True
    assert payload["auto_applied"] is False
    assert payload["partial_text"] == "text"  # failures 非空才暴露 partial_text
    assert payload["needs_merge"] is True
    assert len(payload["violations"]) == 1
    assert payload["violations"][0]["rule_id"] == "r"
    assert payload["step_failures"] == [{"step": "style", "error": "boom"}]


def test_workflow_output_marks_auto_applied_when_version_id_present():
    run = SimpleNamespace(needs_merge=False, quality_degraded=False)
    payload = _workflow_output(
        run,
        planner_output=None,
        final_text="text",
        version_id="v-1",
        memory_id="m-1",
        guard_output=GuardOutput(safe_to_apply=True),
        failures=[],
    )
    assert payload["auto_applied"] is True
    assert payload["partial_text"] is None  # 无 failures 不暴露 partial_text
    assert payload["version_id"] == "v-1"
    assert payload["memory_id"] == "m-1"


def test_workflow_output_handles_missing_guard():
    run = SimpleNamespace(needs_merge=False, quality_degraded=False)
    payload = _workflow_output(
        run,
        planner_output=None,
        final_text="",
        version_id=None,
        memory_id=None,
        guard_output=None,
        failures=[],
    )
    assert payload["safe_to_apply"] is False
    assert payload["needs_rewrite"] is False
    assert payload["needs_user_review"] is False
    assert payload["violations"] == []
    assert payload["final_text"] is None
