"""ai_gateway_constants 直测。

T-6.B1 拆分后这些常量与 dataclass 从 ai_gateway_service.py 移出来；这里补几条
低风险用例守住"matrix → DEFAULT_PROFILES 派生关系"和"GatewayCallResult 可序列化的字段名"。
"""

from app.services.ai_gateway_constants import (
    CIRCUIT_BREAKER_COOLDOWN_SECONDS,
    CIRCUIT_BREAKER_THRESHOLD,
    DEFAULT_PROFILES,
    FIXTURE_MODEL,
    FIXTURE_PROVIDER,
    FIXTURE_VERSION,
    GatewayCallResult,
    PROVIDER_DEFAULTS,
    PROVIDER_FALLBACK_MATRIX,
    PROVIDER_RUNTIME_STEPS,
    STEP_TIMEOUT_MS,
    _MODEL_PRICING_USD_PER_1K,
    _env_timeout_ms,
)


def test_provider_fallback_matrix_covers_all_pipeline_steps():
    expected = {"analyze", "planner", "write", "style", "revise", "check"}
    assert set(PROVIDER_FALLBACK_MATRIX.keys()) == expected


def test_default_profiles_built_from_matrix():
    # 每个 step 应有 1 个 primary + 等量 fallback target。
    for key, rule in PROVIDER_FALLBACK_MATRIX.items():
        profiles = DEFAULT_PROFILES[key]
        expected_count = 1 + len(rule.get("fallback_targets", []))
        assert len(profiles) == expected_count, key
        assert profiles[0]["name"] == f"default-{key}-primary"
        assert profiles[0]["provider"] == rule["default_provider"]
        assert profiles[0]["model"] == rule["default_model"]
        assert profiles[0]["priority"] == 10


def test_default_profiles_fallback_naming_and_priority():
    # check step 没有 fallback；其他 step 至少有 1 条 fallback。
    write_profiles = DEFAULT_PROFILES["write"]
    assert any(p["name"] == "default-write-fallback-1" for p in write_profiles)
    fallback = next(p for p in write_profiles if "fallback" in p["name"])
    assert fallback["priority"] >= 20

    assert len(DEFAULT_PROFILES["check"]) == 1  # check 没有 fallback


def test_step_timeout_ms_aligns_with_matrix():
    for key in PROVIDER_FALLBACK_MATRIX:
        assert STEP_TIMEOUT_MS[key] == int(PROVIDER_FALLBACK_MATRIX[key]["timeout_ms"])
        assert STEP_TIMEOUT_MS[key] >= 1000  # _env_timeout_ms 保底


def test_provider_defaults_keys_are_known_clouds():
    assert set(PROVIDER_DEFAULTS.keys()) == {"openai", "deepseek", "xai"}
    for entry in PROVIDER_DEFAULTS.values():
        assert "base_url" in entry
        assert "api_key_env" in entry


def test_fixture_constants_are_stable():
    assert FIXTURE_PROVIDER == "fixture"
    assert FIXTURE_MODEL == "smoke-fixture"
    assert FIXTURE_VERSION == "v1"


def test_circuit_breaker_constants_are_positive_ints():
    assert isinstance(CIRCUIT_BREAKER_THRESHOLD, int) and CIRCUIT_BREAKER_THRESHOLD > 0
    assert isinstance(CIRCUIT_BREAKER_COOLDOWN_SECONDS, int) and CIRCUIT_BREAKER_COOLDOWN_SECONDS > 0


def test_provider_runtime_steps_covers_pipeline():
    assert PROVIDER_RUNTIME_STEPS == ("analyze", "planner", "write", "style", "check")


def test_model_pricing_dict_has_input_output_for_each_model():
    for model, pricing in _MODEL_PRICING_USD_PER_1K.items():
        assert "input" in pricing, model
        assert "output" in pricing, model
        assert pricing["input"] >= 0
        assert pricing["output"] >= 0


def test_env_timeout_ms_returns_default_when_unset(monkeypatch):
    monkeypatch.delenv("X_TEST_TIMEOUT_MS", raising=False)
    assert _env_timeout_ms("X_TEST_TIMEOUT_MS", 5000) == 5000


def test_env_timeout_ms_clamps_below_1000_to_1000(monkeypatch):
    monkeypatch.setenv("X_TEST_TIMEOUT_MS", "300")
    assert _env_timeout_ms("X_TEST_TIMEOUT_MS", 5000) == 1000


def test_env_timeout_ms_uses_env_value_when_valid(monkeypatch):
    monkeypatch.setenv("X_TEST_TIMEOUT_MS", "60000")
    assert _env_timeout_ms("X_TEST_TIMEOUT_MS", 5000) == 60000


def test_env_timeout_ms_falls_back_when_unparseable(monkeypatch):
    monkeypatch.setenv("X_TEST_TIMEOUT_MS", "not-a-number")
    assert _env_timeout_ms("X_TEST_TIMEOUT_MS", 5000) == 5000


def test_gateway_call_result_dataclass_required_fields():
    result = GatewayCallResult(
        text="x",
        provider="openai",
        model="gpt-4o-mini",
        task_type="write",
        latency_ms=42,
        fallback_used=False,
        quality_degraded=False,
        profile_name="write-primary",
        attempts=[{"status": "success"}],
    )
    assert result.text == "x"
    assert result.token_usage is None
    assert result.cost_estimate is None


def test_gateway_call_result_optional_fields_round_trip():
    result = GatewayCallResult(
        text="x",
        provider="deepseek",
        model="deepseek-chat",
        task_type="analyze",
        latency_ms=10,
        fallback_used=True,
        quality_degraded=True,
        profile_name="analyze-fallback-1",
        attempts=[],
        token_usage={"prompt_tokens": 100, "completion_tokens": 50},
        cost_estimate=0.000123,
    )
    assert result.token_usage == {"prompt_tokens": 100, "completion_tokens": 50}
    assert result.cost_estimate == 0.000123
