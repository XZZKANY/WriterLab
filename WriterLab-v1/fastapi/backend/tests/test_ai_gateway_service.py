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
