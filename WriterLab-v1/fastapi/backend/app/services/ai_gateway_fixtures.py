"""AI 网关 smoke fixture 模式下的确定性文本生成器。

承接来自 ai_gateway_service.py 的：
- 五个 step 的 fixture 文本（analyze / write / style / planner / check）
- `_fixture_attempt`：填一条假的 attempt 记录
- `_fixture_gateway_result`：把以上所有拼成 `GatewayCallResult`，并模拟 style_fail 场景
  在第一次 attempt 时抛 RuntimeError 让上层 retry 机制走一遍真实流程

这些函数都是**纯字符串/dict**生成，不触达 DB、不读写共享 state、不调用网络。
ai_gateway_service.py 顶部会 import 回来，保持测试 monkeypatch 的属性面。
"""

from __future__ import annotations

from typing import Any

from app.services.ai_gateway_constants import (
    FIXTURE_MODEL,
    FIXTURE_PROVIDER,
    GatewayCallResult,
)


def _fixture_attempt(step_key: str, fixture_scenario: str) -> dict[str, Any]:
    return {
        "provider": FIXTURE_PROVIDER,
        "model": FIXTURE_MODEL,
        "profile_name": f"fixture-{step_key}-{fixture_scenario}",
        "status": "success",
        "timeout_ms": 0,
        "latency_ms": 0,
        "cost_estimate": 0.0,
        "retry_index": 0,
    }


def _fixture_analyze_text() -> str:
    return (
        '{"summary":"Fixture analysis summary.","scene_goal_detected":"Protect the letter.",'
        '"emotional_flow":["unease","hesitation","resolve"],'
        '"problems":[{"type":"logic","severity":"medium","message":"Delay opening the letter until the final beat."}],'
        '"suggestions":["Keep the station imagery grounded.","Preserve the rain-soaked tension."]}'
    )


def _fixture_write_text() -> str:
    return (
        "Rain threaded down the old city gate while the station whistle throbbed in the distance. "
        "Shen Yan pressed the damp letter into her palm and held her breath before unfolding it."
    )


def _fixture_style_text(fixture_scenario: str) -> str:
    if fixture_scenario == "guard_block":
        return "Summary: revised scene.\n\nRewrite notes: tighten the imagery and explain the emotional stakes."
    return (
        "Rain stitched silver lines across the old city gate, and the distant station whistle bent the night around Shen Yan. "
        "She pressed the damp letter into her palm, letting the silence tighten before she finally touched the seal."
    )


def _fixture_planner_text(fixture_scenario: str) -> str:
    if fixture_scenario == "malformed_planner":
        return "[fixture-malformed-planner]"
    return (
        "Summary: Keep the scene focused on Shen Yan, the rain, and the unopened letter.\n"
        "Goals: build suspense, preserve melancholy, end on a forward pull.\n"
        "Constraints: stay concise, avoid exposition, keep the station whistle as the audible hook.\n"
        "Hints: open with rain texture, close on delayed action."
    )


def _fixture_check_text(fixture_scenario: str) -> str:
    if fixture_scenario == "check_issue":
        return '[{"type":"timeline_conflict","severity":"medium","message":"The station whistle timing should align with the current night setting.","suggestion":"Keep the whistle in the same late-night window.","evidence":{"source":"fixture"}}]'
    return "[]"


def _fixture_gateway_result(
    *,
    task_type: str,
    workflow_step: str | None,
    fixture_scenario: str,
    params: dict | None = None,
) -> GatewayCallResult:
    step_key = workflow_step or task_type
    fixture_attempt_no = int((params or {}).get("fixture_attempt_no") or 1)
    if step_key == "style" and fixture_scenario == "style_fail" and fixture_attempt_no <= 1:
        raise RuntimeError("fixture style failure")
    text = {
        "analyze": _fixture_analyze_text(),
        "planner": _fixture_planner_text(fixture_scenario),
        "write": _fixture_write_text(),
        "style": _fixture_style_text(fixture_scenario),
        "revise": _fixture_style_text(fixture_scenario),
        "check": _fixture_check_text(fixture_scenario),
    }.get(step_key, "fixture output")
    return GatewayCallResult(
        text=text,
        provider=FIXTURE_PROVIDER,
        model=FIXTURE_MODEL,
        task_type=step_key,
        latency_ms=0,
        fallback_used=False,
        quality_degraded=False,
        profile_name=f"fixture-{step_key}-{fixture_scenario}",
        attempts=[_fixture_attempt(step_key, fixture_scenario)],
        token_usage={"prompt_tokens": 0, "completion_tokens": 0},
        cost_estimate=0.0,
    )
