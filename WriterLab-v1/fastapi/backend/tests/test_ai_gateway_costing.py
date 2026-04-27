"""ai_gateway_costing 直测。

T-6.B2 拆出的 6 个纯计算函数：profile_key / utc_month / provider_enabled /
estimate_cost / resolve_timeout / extract_text。
"""

from app.services.ai_gateway_costing import (
    _estimate_cost_usd,
    _extract_text,
    _provider_enabled,
    _resolve_timeout_ms,
    _runtime_profile_key,
    _utc_month_key,
)


def test_runtime_profile_key_combines_provider_name_model():
    profile = {"provider": "openai", "name": "write-primary", "model": "gpt-4o-mini"}
    assert _runtime_profile_key(profile) == "openai::write-primary::gpt-4o-mini"


def test_utc_month_key_is_iso_year_month():
    out = _utc_month_key()
    assert len(out) == 7
    year, month = out.split("-")
    assert int(year) >= 2025
    assert 1 <= int(month) <= 12


def test_provider_enabled_true_when_env_unset(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER_OPENAI_ENABLED", raising=False)
    enabled, reason = _provider_enabled({"provider": "openai"})
    assert enabled is True
    assert reason is None


def test_provider_enabled_false_when_env_disables(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER_OPENAI_ENABLED", "false")
    enabled, reason = _provider_enabled({"provider": "openai"})
    assert enabled is False
    assert "AI_PROVIDER_OPENAI_ENABLED" in reason


def test_provider_enabled_recognizes_multiple_off_values(monkeypatch):
    for value in ["0", "false", "off", "no", "disabled", "FALSE", "  Off  "]:
        monkeypatch.setenv("AI_PROVIDER_DEEPSEEK_ENABLED", value)
        enabled, _ = _provider_enabled({"provider": "deepseek"})
        assert enabled is False, value


def test_provider_enabled_treats_other_values_as_enabled(monkeypatch):
    for value in ["1", "true", "yes", "on", "enabled", ""]:
        monkeypatch.setenv("AI_PROVIDER_XAI_ENABLED", value)
        enabled, _ = _provider_enabled({"provider": "xai"})
        assert enabled is True, value


def test_estimate_cost_usd_returns_none_for_missing_pricing():
    assert _estimate_cost_usd("unknown-model", {"prompt_tokens": 100}) is None


def test_estimate_cost_usd_returns_none_for_empty_token_usage():
    assert _estimate_cost_usd("gpt-4o-mini", None) is None
    assert _estimate_cost_usd("gpt-4o-mini", {}) is None


def test_estimate_cost_usd_for_known_model():
    # gpt-4o-mini 单价：input 0.00015, output 0.0006 per 1k
    cost = _estimate_cost_usd("gpt-4o-mini", {"prompt_tokens": 1000, "completion_tokens": 1000})
    assert cost == round((1000 * 0.00015 + 1000 * 0.0006) / 1000.0, 8)


def test_estimate_cost_usd_supports_input_output_keys():
    cost = _estimate_cost_usd("deepseek-chat", {"input_tokens": 1000, "output_tokens": 1000})
    assert cost is not None
    assert cost > 0


def test_resolve_timeout_ms_explicit_override_takes_precedence():
    profile = {"timeout_ms": 5000}
    assert _resolve_timeout_ms(profile, "write", "write", 9000) == 9000


def test_resolve_timeout_ms_clamps_explicit_to_min_1000():
    assert _resolve_timeout_ms({}, "write", None, 100) == 1000


def test_resolve_timeout_ms_uses_profile_value_then_step_then_task():
    # profile 给值 → 用 profile 值
    assert _resolve_timeout_ms({"timeout_ms": 8000}, "write", None, None) == 8000

    # profile 没值 → workflow_step 命中 STEP_TIMEOUT_MS
    out = _resolve_timeout_ms({}, "write", "write", None)
    assert out >= 1000  # STEP_TIMEOUT_MS["write"] 至少 1000

    # workflow_step 不在表里 → 看 task_type
    out2 = _resolve_timeout_ms({}, "analyze", "unknown-step", None)
    assert out2 >= 1000  # STEP_TIMEOUT_MS["analyze"]


def test_resolve_timeout_ms_falls_back_to_120000_when_no_signal():
    assert _resolve_timeout_ms({}, "unknown-task", None, None) == 120000


def test_extract_text_handles_string_directly():
    assert _extract_text("  hello  ") == "hello"


def test_extract_text_concatenates_text_parts_in_list():
    content = [
        {"type": "text", "text": "first"},
        {"type": "image", "url": "..."},
        {"type": "text", "text": "second"},
    ]
    assert _extract_text(content) == "first\nsecond"


def test_extract_text_returns_empty_for_unrecognized_input():
    assert _extract_text(None) == ""
    assert _extract_text(123) == ""
    assert _extract_text({"type": "text", "text": "but not in a list"}) == ""


def test_extract_text_skips_text_parts_without_text_field():
    content = [
        {"type": "text", "text": "kept"},
        {"type": "text"},  # missing text field
        {"type": "text", "text": ""},  # empty
    ]
    assert _extract_text(content) == "kept"
