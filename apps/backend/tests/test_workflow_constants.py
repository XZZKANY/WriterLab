"""workflow_constants 模块的纯函数直测。

T-6 拆分后这些函数从 workflow_service.py 移出来；workflow_service 的现有测试
对它们只有间接覆盖。这里补几条边界用例稳定其行为。
"""

from types import SimpleNamespace

from app.services.ai_gateway_service import GatewayCallResult
from app.services.workflow_constants import (
    STEP_AGENT_META,
    STEP_ORDER,
    STEP_REUSABLE_STATUSES,
    STEP_SEQUENCE,
    _agent_meta,
    _fixture_version_for_mode,
    _hash_json,
    _next_step_key,
    _resolve_gateway_tokens,
    _run_fixture_scenario,
    _utcnow,
    _with_agent_meta,
)


def test_step_sequence_matches_order_ascending():
    # STEP_SEQUENCE 必须按 STEP_ORDER 升序，引擎依赖这个顺序判定 reuse 边界。
    assert STEP_SEQUENCE == sorted(STEP_SEQUENCE, key=lambda key: STEP_ORDER[key])
    assert STEP_SEQUENCE[0] == "analyze"
    assert STEP_SEQUENCE[-1] == "memory"


def test_reusable_status_set_is_completed_or_skipped():
    assert STEP_REUSABLE_STATUSES == {"completed", "skipped"}


def test_next_step_key_advances_through_sequence():
    assert _next_step_key(None) == "analyze"
    assert _next_step_key("analyze") == "plan"
    assert _next_step_key("plan") == "write"
    assert _next_step_key("memory") is None


def test_next_step_key_unknown_returns_first():
    # 进入恢复路径如果传了未识别 key，应回退到序列起点而不是抛错。
    assert _next_step_key("unknown_step") == "analyze"


def test_agent_meta_is_independent_copy():
    meta_a = _agent_meta("plan")
    meta_a["agent_label"] = "tampered"
    meta_b = _agent_meta("plan")
    assert meta_b["agent_label"] == STEP_AGENT_META["plan"]["agent_label"]


def test_agent_meta_unknown_key_falls_back_to_bootstrap():
    assert _agent_meta("ghost-step")["agent_key"] == "orchestrator"


def test_with_agent_meta_merges_payload_without_mutating_input():
    payload = {"foo": 1}
    enriched = _with_agent_meta("plan", payload)
    assert enriched["foo"] == 1
    assert enriched["agent_key"] == "planner"
    assert "agent_key" not in payload


def test_hash_json_is_stable_under_key_reordering():
    a = _hash_json({"alpha": 1, "beta": 2})
    b = _hash_json({"beta": 2, "alpha": 1})
    assert a == b
    assert _hash_json(None) is None


def test_hash_json_handles_unicode():
    digest = _hash_json({"summary": "中文内容"})
    assert isinstance(digest, str) and len(digest) == 64


def test_resolve_gateway_tokens_prefers_prompt_completion_keys():
    result = GatewayCallResult(
        text="",
        provider="openai",
        model="gpt-4o-mini",
        task_type="write",
        latency_ms=0,
        fallback_used=False,
        quality_degraded=False,
        profile_name="write-primary",
        attempts=[],
        token_usage={"prompt_tokens": 100, "completion_tokens": 50},
        cost_estimate=0.0,
    )
    assert _resolve_gateway_tokens(result) == (100, 50)


def test_resolve_gateway_tokens_falls_back_to_input_output_keys():
    result = GatewayCallResult(
        text="",
        provider="deepseek",
        model="deepseek-chat",
        task_type="write",
        latency_ms=0,
        fallback_used=False,
        quality_degraded=False,
        profile_name="write-primary",
        attempts=[],
        token_usage={"input_tokens": 11, "output_tokens": 22},
        cost_estimate=0.0,
    )
    assert _resolve_gateway_tokens(result) == (11, 22)


def test_resolve_gateway_tokens_returns_none_pair_when_missing():
    assert _resolve_gateway_tokens(None) == (None, None)
    result = GatewayCallResult(
        text="",
        provider="openai",
        model="gpt-4o-mini",
        task_type="write",
        latency_ms=0,
        fallback_used=False,
        quality_degraded=False,
        profile_name="write-primary",
        attempts=[],
        token_usage=None,
        cost_estimate=0.0,
    )
    assert _resolve_gateway_tokens(result) == (None, None)


def test_fixture_version_only_for_smoke_fixture_mode():
    from app.services.ai_gateway_constants import FIXTURE_VERSION

    assert _fixture_version_for_mode("smoke_fixture") == FIXTURE_VERSION
    assert _fixture_version_for_mode("live") is None
    assert _fixture_version_for_mode("") is None


def test_run_fixture_scenario_extracts_value_when_present():
    run = SimpleNamespace(input_payload={"fixture_scenario": "guard_block"})
    assert _run_fixture_scenario(run) == "guard_block"


def test_run_fixture_scenario_handles_missing_or_empty_payload():
    assert _run_fixture_scenario(SimpleNamespace(input_payload=None)) is None
    assert _run_fixture_scenario(SimpleNamespace(input_payload={})) is None
    assert _run_fixture_scenario(SimpleNamespace(input_payload={"fixture_scenario": ""})) is None


def test_utcnow_returns_recent_naive_datetime():
    now = _utcnow()
    assert now.tzinfo is None  # 当前实现使用 datetime.utcnow()，naive UTC
