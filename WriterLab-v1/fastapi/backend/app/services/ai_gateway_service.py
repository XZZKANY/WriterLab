import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.models.model_profile import ModelProfile
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
    profile_name: str
    attempts: list[dict]
    token_usage: dict | None = None
    cost_estimate: float | None = None


DEFAULT_PROFILES = {
    "analyze": [
        {"name": "default-analyze-primary", "provider": "deepseek", "model": os.getenv("DEEPSEEK_ANALYZE_MODEL", os.getenv("DEEPSEEK_MODEL", "deepseek-chat")), "priority": 10},
        {"name": "default-analyze-fallback", "provider": "ollama", "model": os.getenv("OLLAMA_ANALYZE_MODEL", os.getenv("OLLAMA_MODEL", "qwen2.5:3b")), "priority": 20},
    ],
    "planner": [
        {"name": "default-planner-primary", "provider": "deepseek", "model": os.getenv("DEEPSEEK_PLANNER_MODEL", os.getenv("DEEPSEEK_MODEL", "deepseek-chat")), "priority": 10},
        {"name": "default-planner-fallback", "provider": "ollama", "model": os.getenv("OLLAMA_ANALYZE_MODEL", os.getenv("OLLAMA_MODEL", "qwen2.5:3b")), "priority": 20},
    ],
    "write": [
        {"name": "default-write-primary", "provider": "openai", "model": os.getenv("OPENAI_WRITE_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini")), "priority": 10},
        {"name": "default-write-fallback", "provider": "ollama", "model": os.getenv("OLLAMA_WRITE_MODEL", os.getenv("OLLAMA_MODEL", "qwen2.5:3b")), "priority": 20},
    ],
    "style": [
        {"name": "default-style-primary", "provider": "xai", "model": os.getenv("XAI_STYLE_MODEL", os.getenv("XAI_MODEL", "grok-2-latest")), "priority": 10},
        {"name": "default-style-fallback", "provider": "ollama", "model": os.getenv("OLLAMA_REVISE_MODEL", os.getenv("OLLAMA_MODEL", "qwen2.5:3b")), "priority": 20},
    ],
    "revise": [
        {"name": "default-revise-primary", "provider": "xai", "model": os.getenv("XAI_REVISE_MODEL", os.getenv("XAI_MODEL", "grok-2-latest")), "priority": 10},
        {"name": "default-revise-fallback", "provider": "ollama", "model": os.getenv("OLLAMA_REVISE_MODEL", os.getenv("OLLAMA_MODEL", "qwen2.5:3b")), "priority": 20},
    ],
    "check": [
        {"name": "default-check-primary", "provider": "ollama", "model": os.getenv("OLLAMA_CHECK_MODEL", os.getenv("OLLAMA_MODEL", "qwen2.5:3b")), "priority": 10},
    ],
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

STEP_TIMEOUT_MS = {
    "analyze": _env_timeout_ms("WRITERLAB_TIMEOUT_ANALYZE_MS", 45000),
    "planner": _env_timeout_ms("WRITERLAB_TIMEOUT_PLANNER_MS", 45000),
    "write": _env_timeout_ms("WRITERLAB_TIMEOUT_WRITE_MS", 120000),
    "style": _env_timeout_ms("WRITERLAB_TIMEOUT_STYLE_MS", 75000),
    "check": _env_timeout_ms("WRITERLAB_TIMEOUT_CHECK_MS", 40000),
    "revise": _env_timeout_ms("WRITERLAB_TIMEOUT_REVISE_MS", 75000),
}

CIRCUIT_BREAKER_THRESHOLD = 3
CIRCUIT_BREAKER_COOLDOWN_SECONDS = 90

_REQUEST_WINDOWS: dict[str, deque[float]] = defaultdict(deque)
_PROFILE_RUNTIME_STATE: dict[str, dict] = {}
_PROVIDER_RUNTIME_STATE: dict[str, dict] = {}

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
    return DEFAULT_PROFILES.get(workflow_step or task_type, DEFAULT_PROFILES.get(task_type, []))


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


def call_ai_gateway(
    db: Session,
    *,
    task_type: str,
    prompt: str,
    params: dict | None = None,
    workflow_step: str | None = None,
    timeout_ms: int | None = None,
) -> GatewayCallResult:
    profiles = _resolve_profiles(db, task_type, workflow_step=workflow_step)
    if not profiles:
        raise RuntimeError(f"No model profile configured for task_type={task_type}")

    attempts: list[dict] = []
    started_at = time.time()

    for index, profile in enumerate(profiles):
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
                }
            )
            continue

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
                }
            )
            return GatewayCallResult(
                text=text,
                provider=profile["provider"],
                model=profile["model"],
                task_type=workflow_step or task_type,
                latency_ms=int((time.time() - started_at) * 1000),
                fallback_used=index > 0,
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
                }
            )

    last_error = attempts[-1]["error_message"] if attempts else "unknown gateway error"
    raise RuntimeError(last_error)
