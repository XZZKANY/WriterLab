from app.services import ai_gateway_service as gateway


def test_default_profiles_use_cloud_first_for_analyze():
    profiles = gateway.DEFAULT_PROFILES["analyze"]

    assert profiles[0]["provider"] == "deepseek"
    assert profiles[1]["provider"] == "ollama"


def test_default_profiles_use_cloud_first_for_revise():
    profiles = gateway.DEFAULT_PROFILES["revise"]

    assert profiles[0]["provider"] == "xai"
    assert profiles[1]["provider"] == "ollama"


def test_call_ai_gateway_skips_rate_limited_profile(monkeypatch):
    gateway._reset_gateway_runtime_state()
    profile = {
        "name": "limited-write",
        "provider": "ollama",
        "model": "qwen2.5:3b",
        "requests_per_minute": 1,
    }
    gateway._REQUEST_WINDOWS[gateway._runtime_profile_key(profile)].append(0)
    monkeypatch.setattr(gateway.time, "time", lambda: 30)
    monkeypatch.setattr(gateway, "_resolve_profiles", lambda db, task_type, workflow_step=None: [profile])

    try:
        gateway.call_ai_gateway(object(), task_type="write", prompt="test")
        assert False, "expected rate limit error"
    except RuntimeError as exc:
        assert "requests_per_minute" in str(exc)


def test_call_ai_gateway_skips_provider_when_env_disabled(monkeypatch):
    gateway._reset_gateway_runtime_state()
    monkeypatch.setenv("AI_PROVIDER_OLLAMA_ENABLED", "false")
    monkeypatch.setattr(
        gateway,
        "_resolve_profiles",
        lambda db, task_type, workflow_step=None: [
            {"name": "disabled", "provider": "ollama", "model": "qwen2.5:3b"},
        ],
    )

    try:
        gateway.call_ai_gateway(object(), task_type="write", prompt="test")
        assert False, "expected provider disabled error"
    except RuntimeError as exc:
        assert "disabled" in str(exc)


def test_call_ai_gateway_opens_circuit_after_repeated_failures(monkeypatch):
    gateway._reset_gateway_runtime_state()
    profile = {"name": "fail-openai", "provider": "openai", "model": "gpt-4o-mini"}
    monkeypatch.setattr(gateway, "_resolve_profiles", lambda db, task_type, workflow_step=None: [profile])
    monkeypatch.setattr(gateway, "_call_provider", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(gateway.time, "time", lambda: 100)

    for _ in range(gateway.CIRCUIT_BREAKER_THRESHOLD):
        try:
            gateway.call_ai_gateway(object(), task_type="write", prompt="test")
        except RuntimeError:
            pass

    try:
        gateway.call_ai_gateway(object(), task_type="write", prompt="test")
        assert False, "expected circuit open error"
    except RuntimeError as exc:
        assert "circuit open" in str(exc)


def test_call_ai_gateway_records_budget_cost(monkeypatch):
    gateway._reset_gateway_runtime_state()
    profile = {
        "name": "budgeted-openai",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "monthly_budget_usd": 1.0,
    }
    monkeypatch.setattr(gateway, "_resolve_profiles", lambda db, task_type, workflow_step=None: [profile])
    monkeypatch.setattr(gateway, "_call_provider", lambda *args, **kwargs: ("正文", {"prompt_tokens": 1000, "completion_tokens": 1000}))

    result = gateway.call_ai_gateway(object(), task_type="write", prompt="test")

    assert result.cost_estimate is not None
    assert result.attempts[0]["status"] == "success"


def test_get_provider_matrix_exposes_explicit_rules():
    matrix = gateway.get_provider_matrix()

    assert any(rule.step == "style" for rule in matrix.rules)
    style_rule = next(rule for rule in matrix.rules if rule.step == "style")
    assert style_rule.default_provider in {"xai", "openai", "deepseek", "ollama"}
    assert style_rule.retry_count >= 0


def test_call_ai_gateway_marks_quality_degraded_after_fallback(monkeypatch):
    gateway._reset_gateway_runtime_state()
    profiles = [
        {"name": "primary-style", "provider": "xai", "model": "grok-2-latest"},
        {"name": "fallback-style", "provider": "ollama", "model": "qwen2.5:3b"},
    ]
    monkeypatch.setattr(gateway, "_resolve_profiles", lambda db, task_type, workflow_step=None: profiles)
    calls = {"count": 0}

    def _fake_call_provider(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] <= 2:
            raise RuntimeError("timeout")
        return "styled prose", {"prompt_tokens": 12, "completion_tokens": 34}

    monkeypatch.setattr(gateway, "_call_provider", _fake_call_provider)

    result = gateway.call_ai_gateway(object(), task_type="revise", workflow_step="style", prompt="test")

    assert result.provider == "ollama"
    assert result.fallback_used is True
    assert result.quality_degraded is True
    assert [attempt["status"] for attempt in result.attempts] == ["error", "error", "success"]


def test_get_provider_runtime_state_reports_open_circuit(monkeypatch):
    gateway._reset_gateway_runtime_state()
    monkeypatch.setattr(gateway.time, "time", lambda: 100.0)
    monkeypatch.setattr(gateway, "_step_runtime_profiles", lambda db, step: [])
    gateway._PROVIDER_RUNTIME_STATE["ollama"] = {
        "consecutive_failures": 3,
        "open_until": 145.0,
        "last_error": "ollama timeout",
    }

    state = gateway.get_provider_runtime_state(object())

    ollama = next(item for item in state.providers if item.provider == "ollama")
    assert ollama.remaining_cooldown_seconds == 45
    assert ollama.last_error == "ollama timeout"
    assert ollama.open_until is not None


def test_get_provider_runtime_state_reports_disabled_provider_and_budget(monkeypatch):
    gateway._reset_gateway_runtime_state()
    monkeypatch.setenv("AI_PROVIDER_OLLAMA_ENABLED", "false")
    profile = {
        "name": "budgeted-style",
        "provider": "ollama",
        "model": "qwen2.5:3b",
        "workflow_step": "style",
        "task_type": "revise",
        "monthly_budget_usd": 1.0,
    }
    gateway._PROFILE_RUNTIME_STATE[gateway._runtime_profile_key(profile)] = {"month": gateway._utc_month_key(), "spent_usd": 1.2}
    monkeypatch.setattr(gateway, "_step_runtime_profiles", lambda db, step: [profile] if step == "style" else [])

    state = gateway.get_provider_runtime_state(object())
    ollama = next(item for item in state.providers if item.provider == "ollama")
    style_profile = next(item for item in state.profiles if item.profile_name == "budgeted-style")

    assert ollama.enabled is False
    assert "AI_PROVIDER_OLLAMA_ENABLED" in (ollama.enabled_reason or "")
    assert style_profile.spent_usd == 1.2
    assert "disabled" in (style_profile.skip_reason or "")


def test_get_provider_runtime_state_reports_rate_limited_profile(monkeypatch):
    gateway._reset_gateway_runtime_state()
    profile = {
        "name": "limited-write",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "workflow_step": "write",
        "task_type": "write",
        "requests_per_minute": 1,
    }
    gateway._REQUEST_WINDOWS[gateway._runtime_profile_key(profile)].append(0)
    monkeypatch.setattr(gateway.time, "time", lambda: 30.0)
    monkeypatch.setattr(gateway, "_step_runtime_profiles", lambda db, step: [profile] if step == "write" else [])

    state = gateway.get_provider_runtime_state(object())
    summary = gateway.summarize_provider_runtime_state(state)
    limited = next(item for item in state.profiles if item.profile_name == "limited-write")

    assert "requests_per_minute" in (limited.skip_reason or "")
    assert "openai" in summary.providers_rate_limited


def test_summarize_provider_runtime_state_marks_step_ready_only_with_executable_profile():
    runtime_state = gateway.ProviderRuntimeStateResponse(
        providers=[],
        profiles=[],
        steps=[
            gateway.ProviderRuntimeStepState(step="planner", ready=False, candidate_profiles=["planner-a"], blocking_reasons=["provider deepseek circuit open for 30s"]),
            gateway.ProviderRuntimeStepState(step="write", ready=True, candidate_profiles=["write-a"], blocking_reasons=[]),
        ],
    )

    summary = gateway.summarize_provider_runtime_state(runtime_state)

    assert summary.ok is False
    assert summary.blocked_steps == ["planner"]


def test_call_ai_gateway_smoke_fixture_isolated_from_live_runtime_state():
    gateway._reset_gateway_runtime_state()
    gateway._PROVIDER_RUNTIME_STATE["ollama"] = {
        "consecutive_failures": 3,
        "open_until": 9999.0,
        "last_error": "live state should stay untouched",
    }

    result = gateway.call_ai_gateway(
        object(),
        task_type="analyze",
        workflow_step="planner",
        prompt="fixture prompt",
        provider_mode="smoke_fixture",
        fixture_scenario="happy_path",
    )

    assert result.provider == "fixture"
    assert result.model == "smoke-fixture"
    assert result.profile_name == "fixture-planner-happy_path"
    assert result.quality_degraded is False
    assert gateway._PROVIDER_RUNTIME_STATE["ollama"]["open_until"] == 9999.0


def test_call_ai_gateway_smoke_fixture_style_fail_only_fails_on_first_attempt():
    gateway._reset_gateway_runtime_state()

    try:
        gateway.call_ai_gateway(
            object(),
            task_type="revise",
            workflow_step="style",
            prompt="fixture prompt",
            params={"fixture_attempt_no": 1},
            provider_mode="smoke_fixture",
            fixture_scenario="style_fail",
        )
        assert False, "expected first fixture style attempt to fail"
    except RuntimeError as exc:
        assert "fixture style failure" in str(exc)

    result = gateway.call_ai_gateway(
        object(),
        task_type="revise",
        workflow_step="style",
        prompt="fixture prompt",
        params={"fixture_attempt_no": 2},
        provider_mode="smoke_fixture",
        fixture_scenario="style_fail",
    )

    assert result.provider == "fixture"
    assert result.model == "smoke-fixture"
    assert result.profile_name == "fixture-style-style_fail"
