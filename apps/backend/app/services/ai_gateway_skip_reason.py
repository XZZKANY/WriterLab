"""AI 网关 profile 跳过原因决策链（E 块）。

承接来自 ai_gateway_service.py 的 4 个函数：
- `_rate_limit_reason`：60 秒滑动窗口判 RPM 是否超额
- `_budget_reason`：当月累计花费是否超出 monthly_budget_usd
- `_circuit_reason`：provider 是否处于熔断冷却期
- `_skip_reason`：组合 `_provider_enabled / _circuit_reason / _rate_limit_reason / _budget_reason` 的决策链入口

**关于 state dict 与 D 块函数的引用**：上面三条 reason 都需要访问 `_REQUEST_WINDOWS`
或调用主模块的 `_profile_runtime_state / _provider_runtime_state`（D 块）。这些状态对象
按设计必须留在 ai_gateway_service。这里通过函数体内 lazy import 拿到主模块引用：
- `from app.services.ai_gateway_service import _REQUEST_WINDOWS, _profile_runtime_state, _provider_runtime_state`
- Python 的 `from X import Y` 每次执行都从 X 的 module dict 重新查 Y，所以 monkeypatch 与 dict mutation 在两边都能正确生效。

**关于循环依赖**：ai_gateway_service.py 必须先定义完三个 state dict 与 D 块的两个 lazy-init
函数 (`_profile_runtime_state` / `_provider_runtime_state`) 再 import 本模块，
否则首次加载本模块时会拿不到那些名字。在 ai_gateway_service.py 里把 `from
app.services.ai_gateway_skip_reason import ...` 放到 D 块函数定义之后即可。
"""

from __future__ import annotations

import time

from app.services.ai_gateway_costing import _provider_enabled, _runtime_profile_key


def _rate_limit_reason(profile: dict) -> str | None:
    rpm = profile.get("requests_per_minute")
    if not rpm:
        return None
    # lazy import 拿主模块的 _REQUEST_WINDOWS dict（mutation 在两边可见）
    from app.services.ai_gateway_service import _REQUEST_WINDOWS

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
    from app.services.ai_gateway_service import _profile_runtime_state

    state = _profile_runtime_state(profile)
    if float(state.get("spent_usd") or 0.0) >= float(budget):
        return f"profile {profile['name']} exceeded monthly_budget_usd={budget}"
    return None


def _circuit_reason(profile: dict) -> str | None:
    from app.services.ai_gateway_service import _provider_runtime_state

    state = _provider_runtime_state(profile["provider"])
    open_until = float(state.get("open_until") or 0.0)
    if open_until > time.time():
        remaining = max(int(open_until - time.time()), 1)
        return f"provider {profile['provider']} circuit open for {remaining}s"
    return None


def _skip_reason(profile: dict) -> str | None:
    enabled, enabled_reason = _provider_enabled(profile)
    if not enabled:
        return enabled_reason
    for resolver in (_circuit_reason, _rate_limit_reason, _budget_reason):
        reason = resolver(profile)
        if reason:
            return reason
    return None
