import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

import httpx
from sqlalchemy.orm import Session

from app.models.model_profile import ModelProfile
from app.schemas.runtime import (
    ProviderRuntimeProfileState,
    ProviderRuntimeProviderState,
    ProviderRuntimeStateResponse,
    ProviderRuntimeStepState,
    ProviderRuntimeSummary,
)
from app.schemas.workflow import ProviderFallbackRule, ProviderFallbackTarget, ProviderMatrixResponse
from app.services.ollama_service import ollama_generate
from app.services.provider_settings_service import resolve_provider_api_base, resolve_provider_api_key


def _env_timeout_ms(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return max(int(raw), 1000)
    except ValueError:
        return default


@dataclass
class GatewayCallResult:
    text: str
    provider: str
    model: str
    task_type: str
    latency_ms: int
    fallback_used: bool
    quality_degraded: bool
    profile_name: str
    attempts: list[dict]
    token_usage: dict | None = None
    cost_estimate: float | None = None


PROVIDER_FALLBACK_MATRIX = {
    "analyze": {
        "default_provider": "deepseek",
        "default_model": os.getenv("DEEPSEEK_ANALYZE_MODEL", os.getenv("DEEPSEEK_MODEL", "deepseek-chat")),
        "timeout_ms": _env_timeout_ms("WRITERLAB_TIMEOUT_ANALYZE_MS", 45000),
        "retry_count": 1,
        "fallback_targets": [
            {"provider": "ollama", "model": os.getenv("OLLAMA_ANALYZE_MODEL", os.getenv("OLLAMA_MODEL", "qwen2.5:3b"))},
        ],
        "fallback_to_ollama_when": "cloud failure, timeout, or provider unavailable",
        "quality_degraded_on_fallback": True,
    },
    "planner": {
        "default_provider": "deepseek",
        "default_model": os.getenv("DEEPSEEK_PLANNER_MODEL", os.getenv("DEEPSEEK_MODEL", "deepseek-chat")),
        "timeout_ms": _env_timeout_ms("WRITERLAB_TIMEOUT_PLANNER_MS", 45000),
        "retry_count": 1,
        "fallback_targets": [
            {"provider": "ollama", "model": os.getenv("OLLAMA_ANALYZE_MODEL", os.getenv("OLLAMA_MODEL", "qwen2.5:3b"))},
        ],
        "fallback_to_ollama_when": "planner provider fails or times out",
        "quality_degraded_on_fallback": True,
    },
    "write": {
        "default_provider": "openai",
        "default_model": os.getenv("OPENAI_WRITE_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
        "timeout_ms": _env_timeout_ms("WRITERLAB_TIMEOUT_WRITE_MS", 120000),
        "retry_count": 1,
        "fallback_targets": [
            {"provider": "ollama", "model": os.getenv("OLLAMA_WRITE_MODEL", os.getenv("OLLAMA_MODEL", "qwen2.5:3b"))},
        ],
        "fallback_to_ollama_when": "writer provider fails, times out, or is budget/rate limited",
        "quality_degraded_on_fallback": True,
    },
    "style": {
        "default_provider": "xai",
        "default_model": os.getenv("XAI_STYLE_MODEL", os.getenv("XAI_MODEL", "grok-2-latest")),
        "timeout_ms": _env_timeout_ms("WRITERLAB_TIMEOUT_STYLE_MS", 75000),
        "retry_count": 1,
        "fallback_targets": [
            {"provider": "ollama", "model": os.getenv("OLLAMA_REVISE_MODEL", os.getenv("OLLAMA_MODEL", "qwen2.5:3b"))},
        ],
        "fallback_to_ollama_when": "style provider fails or times out",
        "quality_degraded_on_fallback": True,
    },
    "revise": {
        "default_provider": "xai",
        "default_model": os.getenv("XAI_REVISE_MODEL", os.getenv("XAI_MODEL", "grok-2-latest")),
        "timeout_ms": _env_timeout_ms("WRITERLAB_TIMEOUT_REVISE_MS", 75000),
        "retry_count": 1,
        "fallback_targets": [
            {"provider": "ollama", "model": os.getenv("OLLAMA_REVISE_MODEL", os.getenv("OLLAMA_MODEL", "qwen2.5:3b"))},
        ],
        "fallback_to_ollama_when": "revise provider fails or times out",
        "quality_degraded_on_fallback": True,
    },
    "check": {
        "default_provider": "ollama",
        "default_model": os.getenv("OLLAMA_CHECK_MODEL", os.getenv("OLLAMA_MODEL", "qwen2.5:3b")),
        "timeout_ms": _env_timeout_ms("WRITERLAB_TIMEOUT_CHECK_MS", 40000),
        "retry_count": 0,
        "fallback_targets": [],
        "fallback_to_ollama_when": "local-first consistency check",
        "quality_degraded_on_fallback": False,
    },
}

DEFAULT_PROFILES = {
    key: [
        {
            "name": f"default-{key}-primary",
            "provider": rule["default_provider"],
            "model": rule["default_model"],
            "priority": 10,
        },
        *[
            {
                "name": f"default-{key}-fallback-{index + 1}",
                "provider": target["provider"],
                "model": target["model"],
                "priority": 20 + index,
            }
            for index, target in enumerate(rule.get("fallback_targets", []))
        ],
    ]
    for key, rule in PROVIDER_FALLBACK_MATRIX.items()
}

PROVIDER_DEFAULTS = {
    "openai": {
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "api_key_env": "OPENAI_API_KEY",
    },
    "deepseek": {
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "xai": {
        "base_url": os.getenv("XAI_BASE_URL", "https://api.x.ai/v1"),
        "api_key_env": "XAI_API_KEY",
    },
}

STEP_TIMEOUT_MS = {key: int(value["timeout_ms"]) for key, value in PROVIDER_FALLBACK_MATRIX.items()}
FIXTURE_PROVIDER = "fixture"
FIXTURE_MODEL = "smoke-fixture"
FIXTURE_VERSION = "v1"

CIRCUIT_BREAKER_THRESHOLD = 3
CIRCUIT_BREAKER_COOLDOWN_SECONDS = 90

_REQUEST_WINDOWS: dict[str, deque[float]] = defaultdict(deque)
_PROFILE_RUNTIME_STATE: dict[str, dict] = {}
_PROVIDER_RUNTIME_STATE: dict[str, dict] = {}
PROVIDER_RUNTIME_STEPS = ("analyze", "planner", "write", "style", "check")

_MODEL_PRICING_USD_PER_1K = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "deepseek-chat": {"input": 0.00014, "output": 0.00028},
    "grok-2-latest": {"input": 0.002, "output": 0.01},
}


def _resolve_profiles(db: Session, task_type: str, workflow_step: str | None = None) -> list[dict]:
    enabled_query = db.query(ModelProfile).filter(ModelProfile.is_enabled.is_(True))
    if workflow_step:
        db_profiles = (
            enabled_query.filter(ModelProfile.workflow_step == workflow_step)
            .order_by(ModelProfile.priority.asc(), ModelProfile.routing_weight.desc())
            .all()
        )
        if db_profiles:
            return [_profile_to_dict(profile) for profile in db_profiles]
        disabled_exists = (
            db.query(ModelProfile)
            .filter(ModelProfile.workflow_step == workflow_step)
            .first()
        )
        if disabled_exists:
            return []

    db_profiles = (
        enabled_query.filter(ModelProfile.task_type == task_type)
        .order_by(ModelProfile.priority.asc(), ModelProfile.routing_weight.desc())
        .all()
    )
    if db_profiles:
        return [_profile_to_dict(profile) for profile in db_profiles]
    disabled_exists = (
        db.query(ModelProfile)
        .filter(ModelProfile.task_type == task_type)
        .first()
    )
    if disabled_exists:
        return []
    matrix_key = workflow_step or task_type
    return DEFAULT_PROFILES.get(matrix_key, DEFAULT_PROFILES.get(task_type, []))


def _matrix_rule(task_type: str, workflow_step: str | None = None) -> dict:
    return PROVIDER_FALLBACK_MATRIX.get(workflow_step or task_type, PROVIDER_FALLBACK_MATRIX.get(task_type, {}))


def get_provider_matrix() -> ProviderMatrixResponse:
    rules = []
    for step, rule in PROVIDER_FALLBACK_MATRIX.items():
        rules.append(
            ProviderFallbackRule(
                step=step,
                default_provider=rule["default_provider"],
                default_model=rule["default_model"],
                timeout_ms=int(rule["timeout_ms"]),
                retry_count=int(rule["retry_count"]),
                fallback_targets=[ProviderFallbackTarget(**target) for target in rule.get("fallback_targets", [])],
                fallback_to_ollama_when=str(rule["fallback_to_ollama_when"]),
                quality_degraded_on_fallback=bool(rule.get("quality_degraded_on_fallback", False)),
            )
        )
    return ProviderMatrixResponse(rules=rules)


def _profile_to_dict(profile: ModelProfile) -> dict:
    return {
        "name": profile.name,
        "provider": profile.provider,
        "model": profile.model,
        "priority": profile.priority,
        "temperature": profile.temperature,
        "max_tokens": profile.max_tokens,
        "timeout_ms": profile.timeout_ms,
        "task_type": profile.task_type,
        "workflow_step": profile.workflow_step,
        "api_base": profile.api_base,
        "api_key_env": profile.api_key_env,
        "extra_headers": profile.extra_headers,
        "requests_per_minute": profile.requests_per_minute,
        "monthly_budget_usd": profile.monthly_budget_usd,
        "routing_weight": profile.routing_weight,
    }


def _runtime_profile_key(profile: dict) -> str:
    return f"{profile['provider']}::{profile['name']}::{profile['model']}"


def _utc_month_key() -> str:
    return datetime.utcnow().strftime("%Y-%m")


def _provider_enabled(profile: dict) -> tuple[bool, str | None]:
    provider = str(profile.get("provider") or "").upper()
    env_key = f"AI_PROVIDER_{provider}_ENABLED"
    raw = os.getenv(env_key)
    if raw is None:
        return True, None
    if str(raw).strip().lower() in {"0", "false", "off", "no", "disabled"}:
        return False, f"provider {profile['provider']} is disabled by {env_key}"
    return True, None


def _estimate_cost_usd(model: str, token_usage: dict | None) -> float | None:
    if not token_usage:
        return None
    pricing = _MODEL_PRICING_USD_PER_1K.get(model)
    if not pricing:
        return None
    prompt_tokens = float(token_usage.get("prompt_tokens") or token_usage.get("input_tokens") or 0)
    completion_tokens = float(token_usage.get("completion_tokens") or token_usage.get("output_tokens") or 0)
    return round(((prompt_tokens * pricing["input"]) + (completion_tokens * pricing["output"])) / 1000.0, 8)


def _profile_runtime_state(profile: dict) -> dict:
    key = _runtime_profile_key(profile)
    state = _PROFILE_RUNTIME_STATE.get(key)
    if state is None or state.get("month") != _utc_month_key():
        state = {
            "month": _utc_month_key(),
            "spent_usd": 0.0,
        }
        _PROFILE_RUNTIME_STATE[key] = state
    return state


def _provider_runtime_state(provider: str) -> dict:
    state = _PROVIDER_RUNTIME_STATE.get(provider)
    if state is None:
        state = {
            "consecutive_failures": 0,
            "open_until": 0.0,
            "last_error": None,
        }
        _PROVIDER_RUNTIME_STATE[provider] = state
    return state


def _rate_limit_reason(profile: dict) -> str | None:
    rpm = profile.get("requests_per_minute")
    if not rpm:
        return None
    key = _runtime_profile_key(profile)
    now = time.time()
    window = _REQUEST_WINDOWS[key]
    while window and (now - window[0]) > 60:
        window.popleft()
    if len(window) >= int(rpm):
        return f"profile {profile['name']} hit requests_per_minute={rpm}"
    return None


def _budget_reason(profile: dict) -> str | None:
    budget = profile.get("monthly_budget_usd")
    if budget is None:
        return None
    state = _profile_runtime_state(profile)
    if float(state.get("spent_usd") or 0.0) >= float(budget):
        return f"profile {profile['name']} exceeded monthly_budget_usd={budget}"
    return None


def _circuit_reason(profile: dict) -> str | None:
    state = _provider_runtime_state(profile["provider"])
    open_until = float(state.get("open_until") or 0.0)
    if open_until > time.time():
        remaining = max(int(open_until - time.time()), 1)
        return f"provider {profile['provider']} circuit open for {remaining}s"
    return None


def _record_request(profile: dict) -> None:
    key = _runtime_profile_key(profile)
    now = time.time()
    window = _REQUEST_WINDOWS[key]
    while window and (now - window[0]) > 60:
        window.popleft()
    window.append(now)


def _record_success(profile: dict, *, cost_estimate: float | None) -> None:
    provider_state = _provider_runtime_state(profile["provider"])
    provider_state["consecutive_failures"] = 0
    provider_state["open_until"] = 0.0
    provider_state["last_error"] = None
    if cost_estimate:
        state = _profile_runtime_state(profile)
        state["spent_usd"] = round(float(state.get("spent_usd") or 0.0) + float(cost_estimate), 8)


def _record_failure(profile: dict, *, error_message: str) -> None:
    provider_state = _provider_runtime_state(profile["provider"])
    provider_state["consecutive_failures"] = int(provider_state.get("consecutive_failures") or 0) + 1
    provider_state["last_error"] = error_message
    if provider_state["consecutive_failures"] >= CIRCUIT_BREAKER_THRESHOLD:
        provider_state["open_until"] = time.time() + CIRCUIT_BREAKER_COOLDOWN_SECONDS


def _skip_reason(profile: dict) -> str | None:
    enabled, enabled_reason = _provider_enabled(profile)
    if not enabled:
        return enabled_reason
    for resolver in (_circuit_reason, _rate_limit_reason, _budget_reason):
        reason = resolver(profile)
        if reason:
            return reason
    return None


def _reset_gateway_runtime_state() -> None:
    _REQUEST_WINDOWS.clear()
    _PROFILE_RUNTIME_STATE.clear()
    _PROVIDER_RUNTIME_STATE.clear()


def _peek_profile_runtime_state(profile: dict) -> dict:
    key = _runtime_profile_key(profile)
    state = _PROFILE_RUNTIME_STATE.get(key)
    if state is None or state.get("month") != _utc_month_key():
        return {
            "month": _utc_month_key(),
            "spent_usd": 0.0,
        }
    return {
        "month": state.get("month"),
        "spent_usd": float(state.get("spent_usd") or 0.0),
    }


def _peek_provider_runtime_state(provider: str) -> dict:
    state = _PROVIDER_RUNTIME_STATE.get(provider)
    if state is None:
        return {
            "consecutive_failures": 0,
            "open_until": 0.0,
            "last_error": None,
        }
    return {
        "consecutive_failures": int(state.get("consecutive_failures") or 0),
        "open_until": float(state.get("open_until") or 0.0),
        "last_error": state.get("last_error"),
    }


def _runtime_open_until_iso(open_until: float | int | None) -> str | None:
    value = float(open_until or 0.0)
    if value <= 0:
        return None
    return datetime.utcfromtimestamp(value).isoformat() + "Z"


def _remaining_cooldown_seconds(open_until: float | int | None) -> int:
    value = float(open_until or 0.0)
    if value <= time.time():
        return 0
    return max(int(value - time.time()), 1)


def _known_provider_names(profiles: Iterable[dict]) -> list[str]:
    providers = set(PROVIDER_DEFAULTS.keys())
    for rule in PROVIDER_FALLBACK_MATRIX.values():
        providers.add(str(rule["default_provider"]))
        for target in rule.get("fallback_targets", []):
            providers.add(str(target["provider"]))
    for profile in profiles:
        providers.add(str(profile.get("provider") or ""))
    return sorted(item for item in providers if item)


def _step_runtime_profiles(db: Session, step: str) -> list[dict]:
    if step == "analyze":
        return _resolve_profiles(db, "analyze")
    if step == "planner":
        return _resolve_profiles(db, "analyze", workflow_step="planner")
    if step == "write":
        return _resolve_profiles(db, "write")
    if step == "style":
        return _resolve_profiles(db, "revise", workflow_step="style")
    if step == "check":
        return _resolve_profiles(db, "analyze", workflow_step="check")
    return _resolve_profiles(db, step, workflow_step=step)


def get_provider_runtime_state(db: Session, *, steps: Iterable[str] | None = None) -> ProviderRuntimeStateResponse:
    target_steps = list(steps or PROVIDER_RUNTIME_STEPS)
    step_profiles: dict[str, list[dict]] = {step: _step_runtime_profiles(db, step) for step in target_steps}
    seen_profiles: dict[str, dict] = {}
    for profiles in step_profiles.values():
        for profile in profiles:
            seen_profiles[_runtime_profile_key(profile)] = profile

    providers = []
    for provider_name in _known_provider_names(seen_profiles.values()):
        enabled, enabled_reason = _provider_enabled({"provider": provider_name})
        runtime_state = _peek_provider_runtime_state(provider_name)
        providers.append(
            ProviderRuntimeProviderState(
                provider=provider_name,
                enabled=enabled,
                enabled_reason=enabled_reason,
                consecutive_failures=int(runtime_state.get("consecutive_failures") or 0),
                open_until=_runtime_open_until_iso(runtime_state.get("open_until")),
                remaining_cooldown_seconds=_remaining_cooldown_seconds(runtime_state.get("open_until")),
                last_error=runtime_state.get("last_error"),
            )
        )

    profiles = []
    for profile in sorted(seen_profiles.values(), key=lambda item: (str(item.get("workflow_step") or item.get("task_type") or ""), str(item.get("provider") or ""), str(item.get("name") or ""))):
        enabled, _ = _provider_enabled(profile)
        profile_state = _peek_profile_runtime_state(profile)
        profiles.append(
            ProviderRuntimeProfileState(
                profile_name=str(profile.get("name") or ""),
                provider=str(profile.get("provider") or ""),
                model=str(profile.get("model") or ""),
                task_type=profile.get("task_type"),
                workflow_step=profile.get("workflow_step"),
                requests_per_minute=int(profile["requests_per_minute"]) if profile.get("requests_per_minute") is not None else None,
                monthly_budget_usd=float(profile["monthly_budget_usd"]) if profile.get("monthly_budget_usd") is not None else None,
                spent_usd=float(profile_state.get("spent_usd") or 0.0),
                enabled=enabled,
                skip_reason=_skip_reason(profile),
            )
        )

    steps_payload = []
    for step in target_steps:
        profiles_for_step = step_profiles.get(step, [])
        candidate_profiles = [f"{profile['name']} ({profile['provider']}/{profile['model']})" for profile in profiles_for_step]
        blocking_reasons = [reason for reason in (_skip_reason(profile) for profile in profiles_for_step) if reason]
        ready = bool(profiles_for_step) and any(_skip_reason(profile) is None for profile in profiles_for_step)
        if not profiles_for_step:
            blocking_reasons = ["no configured provider profiles resolved for this step"]
        steps_payload.append(
            ProviderRuntimeStepState(
                step=step,
                ready=ready,
                candidate_profiles=candidate_profiles,
                blocking_reasons=blocking_reasons,
            )
        )

    return ProviderRuntimeStateResponse(
        providers=providers,
        profiles=profiles,
        steps=steps_payload,
    )


def summarize_provider_runtime_state(runtime_state: ProviderRuntimeStateResponse) -> ProviderRuntimeSummary:
    blocked_steps = [item.step for item in runtime_state.steps if not item.ready]
    providers_with_open_circuit = sorted(
        item.provider for item in runtime_state.providers if int(item.remaining_cooldown_seconds or 0) > 0
    )
    providers_disabled = sorted(
        item.provider for item in runtime_state.providers if not item.enabled
    )
    providers_rate_limited = sorted(
        {
            item.provider
            for item in runtime_state.profiles
            if item.skip_reason and "requests_per_minute" in item.skip_reason
        }
    )
    providers_budget_blocked = sorted(
        {
            item.provider
            for item in runtime_state.profiles
            if item.skip_reason and "monthly_budget_usd" in item.skip_reason
        }
    )
    return ProviderRuntimeSummary(
        ok=not blocked_steps,
        blocked_steps=blocked_steps,
        providers_with_open_circuit=providers_with_open_circuit,
        providers_disabled=providers_disabled,
        providers_rate_limited=providers_rate_limited,
        providers_budget_blocked=providers_budget_blocked,
    )


def _resolve_timeout_ms(profile: dict, task_type: str, workflow_step: str | None, timeout_ms: int | None) -> int:
    if timeout_ms is not None:
        return max(int(timeout_ms), 1000)
    if profile.get("timeout_ms") is not None:
        return max(int(profile["timeout_ms"]), 1000)
    if workflow_step and workflow_step in STEP_TIMEOUT_MS:
        return STEP_TIMEOUT_MS[workflow_step]
    if task_type in STEP_TIMEOUT_MS:
        return STEP_TIMEOUT_MS[task_type]
    return 120000


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text" and item.get("text"):
                parts.append(str(item["text"]))
        return "\n".join(parts).strip()
    return ""


def _openai_compatible_generate(profile: dict, prompt: str, params: dict | None, *, timeout_ms: int) -> tuple[str, dict | None]:
    provider = profile["provider"]
    defaults = PROVIDER_DEFAULTS.get(provider, {})
    base_url = (
        profile.get("api_base")
        or resolve_provider_api_base(provider)
        or defaults.get("base_url")
        or ""
    ).rstrip("/")
    api_key_env = profile.get("api_key_env") or defaults.get("api_key_env")
    api_key = resolve_provider_api_key(provider) or os.getenv(api_key_env or "")
    if not api_key:
        raise RuntimeError(f"Missing API key for provider={provider}")
    if not base_url:
        raise RuntimeError(f"Missing base_url for provider={provider}")

    timeout_seconds = max(float(timeout_ms) / 1000.0, 1.0)
    payload = {
        "model": profile["model"],
        "messages": [
            {"role": "system", "content": "You are a careful writing assistant."},
            {"role": "user", "content": prompt},
        ],
    }
    options = dict(params or {})
    if profile.get("temperature") is not None and "temperature" not in options:
        options["temperature"] = profile["temperature"]
    if profile.get("max_tokens") is not None and "max_tokens" not in options:
        options["max_tokens"] = profile["max_tokens"]
    payload.update(options)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        **(profile.get("extra_headers") or {}),
    }

    with httpx.Client(trust_env=False, timeout=timeout_seconds) as client:
        response = client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
    if response.status_code >= 400:
        raise RuntimeError(f"{provider} request failed: {response.status_code} {response.text}")

    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(f"{provider} returned invalid JSON") from exc

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"{provider} returned no choices")
    message = choices[0].get("message") or {}
    text = _extract_text(message.get("content"))
    if not text:
        raise RuntimeError(f"{provider} returned empty content")
    return text, data.get("usage")


def _call_provider(profile: dict, prompt: str, params: dict | None, *, timeout_ms: int) -> tuple[str, dict | None]:
    provider = profile["provider"]
    if provider == "ollama":
        options = dict(params or {})
        if profile.get("temperature") is not None and "temperature" not in options:
            options["temperature"] = profile["temperature"]
        return (
            ollama_generate(
                prompt,
                model=profile["model"],
                options=options or None,
                think=False,
                timeout=max(float(timeout_ms) / 1000.0, 1.0),
            ),
            None,
        )
    if provider in {"openai", "deepseek", "xai"}:
        return _openai_compatible_generate(profile, prompt, params, timeout_ms=timeout_ms)
    raise RuntimeError(f"Provider not configured: {provider}")


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


def call_ai_gateway(
    db: Session,
    *,
    task_type: str,
    prompt: str,
    params: dict | None = None,
    workflow_step: str | None = None,
    timeout_ms: int | None = None,
    provider_mode: str = "live",
    fixture_scenario: str = "happy_path",
) -> GatewayCallResult:
    if provider_mode == "smoke_fixture":
        return _fixture_gateway_result(
            task_type=task_type,
            workflow_step=workflow_step,
            fixture_scenario=fixture_scenario,
            params=params,
        )
    profiles = _resolve_profiles(db, task_type, workflow_step=workflow_step)
    if not profiles:
        raise RuntimeError(f"No model profile configured for task_type={task_type}")

    attempts: list[dict] = []
    started_at = time.time()
    matrix_rule = _matrix_rule(task_type, workflow_step)
    retry_count = int(matrix_rule.get("retry_count") or 0)

    for index, profile in enumerate(profiles):
        for retry_index in range(retry_count + 1):
            attempt_started = time.time()
            resolved_timeout_ms = _resolve_timeout_ms(profile, task_type, workflow_step, timeout_ms)
            skip_reason = _skip_reason(profile)
            if skip_reason:
                attempts.append(
                    {
                        "provider": profile["provider"],
                        "model": profile["model"],
                        "profile_name": profile["name"],
                        "status": "skipped",
                        "error_message": skip_reason,
                        "timeout_ms": resolved_timeout_ms,
                        "latency_ms": 0,
                        "retry_index": retry_index,
                    }
                )
                break

            try:
                _record_request(profile)
                text, token_usage = _call_provider(profile, prompt, params, timeout_ms=resolved_timeout_ms)
                cost_estimate = _estimate_cost_usd(profile["model"], token_usage)
                _record_success(profile, cost_estimate=cost_estimate)
                attempts.append(
                    {
                        "provider": profile["provider"],
                        "model": profile["model"],
                        "profile_name": profile["name"],
                        "status": "success",
                        "timeout_ms": resolved_timeout_ms,
                        "latency_ms": int((time.time() - attempt_started) * 1000),
                        "cost_estimate": cost_estimate,
                        "retry_index": retry_index,
                    }
                )
                return GatewayCallResult(
                    text=text,
                    provider=profile["provider"],
                    model=profile["model"],
                    task_type=workflow_step or task_type,
                    latency_ms=int((time.time() - started_at) * 1000),
                    fallback_used=index > 0,
                    quality_degraded=bool(index > 0 and matrix_rule.get("quality_degraded_on_fallback")),
                    profile_name=profile["name"],
                    attempts=attempts,
                    token_usage=token_usage,
                    cost_estimate=cost_estimate,
                )
            except Exception as exc:
                _record_failure(profile, error_message=str(exc))
                attempts.append(
                    {
                        "provider": profile["provider"],
                        "model": profile["model"],
                        "profile_name": profile["name"],
                        "status": "error",
                        "error_message": str(exc),
                        "timeout_ms": resolved_timeout_ms,
                        "latency_ms": int((time.time() - attempt_started) * 1000),
                        "provider_failures": _provider_runtime_state(profile["provider"]).get("consecutive_failures"),
                        "retry_index": retry_index,
                    }
                )
                if retry_index >= retry_count:
                    break

    last_error = attempts[-1]["error_message"] if attempts else "unknown gateway error"
    raise RuntimeError(last_error)
