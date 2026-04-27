import time
from collections import defaultdict, deque
from typing import Iterable

from sqlalchemy.orm import Session

from app.schemas.runtime import (
    ProviderRuntimeProfileState,
    ProviderRuntimeProviderState,
    ProviderRuntimeStateResponse,
    ProviderRuntimeStepState,
    ProviderRuntimeSummary,
)
# 常量与 dataclass 集中在 ai_gateway_constants；通过 import 拉回本模块命名空间，
# 既保持调用点不变，也让测试通过 "app.services.ai_gateway_service.<name>" 属性访问与
# monkeypatch 继续生效。三个模块级 state 字典则**必须留在本模块**——测试会直接对它们做赋值
# (gateway._PROVIDER_RUNTIME_STATE["x"] = ...)，分离到子模块会出现"不同模块持有不同对象"的 bug。
#
# 下面两个 import 块同时承担 **re-export 表面**：
# - 测试代码直接读取 `gateway.CIRCUIT_BREAKER_THRESHOLD` 等常量、调用 `gateway._utc_month_key()` 等
# - 已拆出的子模块（skip_reason / state / views 等）在 lazy import 时通过
#   `from app.services.ai_gateway_service import <name>` 取这些符号
# pyflakes 会把它们当 unused（主模块代码不直接调）；这是已知故意保留项。
# ruff: noqa: F401
from app.services.ai_gateway_constants import (
    CIRCUIT_BREAKER_COOLDOWN_SECONDS,
    CIRCUIT_BREAKER_THRESHOLD,
    DEFAULT_PROFILES,
    GatewayCallResult,
    PROVIDER_FALLBACK_MATRIX,
    PROVIDER_RUNTIME_STEPS,
)
from app.services.ai_gateway_costing import (
    _estimate_cost_usd,
    _provider_enabled,
    _resolve_timeout_ms,
    _runtime_profile_key,
    _utc_month_key,
)
from app.services.ai_gateway_fixtures import _fixture_gateway_result


# 三个模块级 state 字典必须留在本模块（测试直接 mutate；分离会让多个模块持有不同对象）。
_REQUEST_WINDOWS: dict[str, deque[float]] = defaultdict(deque)
_PROFILE_RUNTIME_STATE: dict[str, dict] = {}
_PROVIDER_RUNTIME_STATE: dict[str, dict] = {}

# state dict 定义之后再 import views——views 中两个 _peek_* 函数体内会 lazy import
# 上面的 dict，所以这一行的位置必须在 dict 定义**之后**才安全。
from app.services.ai_gateway_views import (  # noqa: E402  intentional below state dicts
    _known_provider_names,
    _peek_profile_runtime_state,
    _peek_provider_runtime_state,
    _remaining_cooldown_seconds,
    _runtime_open_until_iso,
)


# B 块（profile 解析 + 路由矩阵）拆到 ai_gateway_routing。
# 通过 import 拉回让 `monkeypatch.setattr(gateway, "_resolve_profiles", fake)` 与
# `monkeypatch.setattr(gateway, "_step_runtime_profiles", fake)` 命中主模块属性，
# 让 `call_ai_gateway` 与 `get_provider_runtime_state` 内部 LOAD_GLOBAL 走主模块绑定。
# `_step_runtime_profiles` 内部对 `_resolve_profiles` 的调用也走 lazy import 主模块。
from app.services.ai_gateway_routing import (
    _matrix_rule,
    _resolve_profiles,
    _step_runtime_profiles,
    get_provider_matrix,
)


# D 块（state init + record_*）拆到 ai_gateway_state；通过 import 拉回让
# `call_ai_gateway` 内部以 LOAD_GLOBAL 调用这些名字时拿到子模块函数。
# 注意：必须在三个 state dict 定义之后再 import，因为子模块内部 lazy import 这些 dict。
from app.services.ai_gateway_state import (  # noqa: E402  intentional below state dicts
    _profile_runtime_state,
    _provider_runtime_state,
    _record_failure,
    _record_request,
    _record_success,
)


def _reset_gateway_runtime_state() -> None:
    _REQUEST_WINDOWS.clear()
    _PROFILE_RUNTIME_STATE.clear()
    _PROVIDER_RUNTIME_STATE.clear()


# 必须在 D 块（_profile_runtime_state / _provider_runtime_state / state dict）已定义
# 之后再 import skip_reason，否则首次加载 skip_reason 时 lazy import 会抓不到名字。
from app.services.ai_gateway_skip_reason import _skip_reason  # noqa: E402  intentional below D block


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


# H 块（HTTP/Ollama 调用）拆到 ai_gateway_provider；通过 import 拉回让
# `monkeypatch.setattr(gateway, "_call_provider", fake)` 与 `call_ai_gateway` 内部的
# LOAD_GLOBAL 路径继续命中。
from app.services.ai_gateway_provider import _call_provider  # noqa: E402  intentional below summarize_provider_runtime_state


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
