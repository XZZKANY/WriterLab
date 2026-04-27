"""ai_gateway_fixtures 直测。

T-6.B3 拆出的 7 个 fixture 文本生成器：覆盖每条 step 的 happy-path 输出与
特定 scenario 分支（malformed_planner / guard_block / check_issue / style_fail）。
"""

import json

import pytest

from app.services.ai_gateway_constants import FIXTURE_MODEL, FIXTURE_PROVIDER
from app.services.ai_gateway_fixtures import (
    _fixture_analyze_text,
    _fixture_attempt,
    _fixture_check_text,
    _fixture_gateway_result,
    _fixture_planner_text,
    _fixture_style_text,
    _fixture_write_text,
)


def test_fixture_attempt_uses_fixture_provider_and_model():
    attempt = _fixture_attempt("write", "happy_path")
    assert attempt["provider"] == FIXTURE_PROVIDER
    assert attempt["model"] == FIXTURE_MODEL
    assert attempt["profile_name"] == "fixture-write-happy_path"
    assert attempt["status"] == "success"
    assert attempt["latency_ms"] == 0
    assert attempt["cost_estimate"] == 0.0


def test_fixture_analyze_text_is_valid_json_with_required_fields():
    parsed = json.loads(_fixture_analyze_text())
    assert "summary" in parsed
    assert "scene_goal_detected" in parsed
    assert isinstance(parsed["emotional_flow"], list)
    assert isinstance(parsed["problems"], list)
    assert isinstance(parsed["suggestions"], list)


def test_fixture_write_text_is_nonempty_prose():
    text = _fixture_write_text()
    assert isinstance(text, str)
    assert len(text) > 50


def test_fixture_style_text_default_returns_prose():
    assert "Rain stitched silver lines" in _fixture_style_text("happy_path")


def test_fixture_style_text_guard_block_returns_summary_with_rewrite_notes():
    text = _fixture_style_text("guard_block")
    assert "Rewrite notes" in text


def test_fixture_planner_text_default_includes_goals_constraints_hints():
    text = _fixture_planner_text("happy_path")
    assert "Goals:" in text
    assert "Constraints:" in text
    assert "Hints:" in text


def test_fixture_planner_text_malformed_returns_marker():
    # malformed_planner 场景必须返回特定 marker，让上层 _build_planner_output 能识别
    assert _fixture_planner_text("malformed_planner") == "[fixture-malformed-planner]"


def test_fixture_check_text_default_is_empty_array():
    assert _fixture_check_text("happy_path") == "[]"
    assert json.loads(_fixture_check_text("happy_path")) == []


def test_fixture_check_text_check_issue_returns_one_issue():
    issues = json.loads(_fixture_check_text("check_issue"))
    assert isinstance(issues, list) and len(issues) == 1
    assert issues[0]["type"] == "timeline_conflict"


def test_fixture_gateway_result_for_analyze_step_returns_analysis_text():
    result = _fixture_gateway_result(task_type="analyze", workflow_step=None, fixture_scenario="happy_path")
    assert "Fixture analysis summary" in result.text
    assert result.provider == FIXTURE_PROVIDER
    assert result.model == FIXTURE_MODEL
    assert result.task_type == "analyze"
    assert result.fallback_used is False
    assert result.quality_degraded is False


def test_fixture_gateway_result_workflow_step_overrides_task_type():
    result = _fixture_gateway_result(task_type="analyze", workflow_step="planner", fixture_scenario="happy_path")
    # planner 模板 → 内容里有 Goals/Constraints/Hints
    assert "Goals:" in result.text
    assert result.task_type == "planner"


def test_fixture_gateway_result_uses_fixture_token_usage_zero():
    result = _fixture_gateway_result(task_type="write", workflow_step="write", fixture_scenario="happy_path")
    assert result.token_usage == {"prompt_tokens": 0, "completion_tokens": 0}
    assert result.cost_estimate == 0.0


def test_fixture_gateway_result_unknown_step_returns_default_marker():
    result = _fixture_gateway_result(task_type="anything", workflow_step="ghost-step", fixture_scenario="happy_path")
    assert result.text == "fixture output"


def test_fixture_gateway_result_style_fail_first_attempt_raises():
    # style_fail 场景在 attempt_no=1 时必须抛 RuntimeError，让上层 retry 走第二次。
    with pytest.raises(RuntimeError, match="fixture style failure"):
        _fixture_gateway_result(
            task_type="revise",
            workflow_step="style",
            fixture_scenario="style_fail",
            params={"fixture_attempt_no": 1},
        )


def test_fixture_gateway_result_style_fail_second_attempt_succeeds():
    result = _fixture_gateway_result(
        task_type="revise",
        workflow_step="style",
        fixture_scenario="style_fail",
        params={"fixture_attempt_no": 2},
    )
    assert "Rain stitched silver lines" in result.text


def test_fixture_gateway_result_attempts_field_has_one_record():
    result = _fixture_gateway_result(task_type="check", workflow_step="check", fixture_scenario="check_issue")
    assert len(result.attempts) == 1
    assert result.attempts[0]["profile_name"] == "fixture-check-check_issue"
