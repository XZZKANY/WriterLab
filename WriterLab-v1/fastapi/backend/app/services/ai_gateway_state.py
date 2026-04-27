"""AI 网关运行时 state 的 lazy-init 入口与写入函数（D 块）。

承接来自 ai_gateway_service.py 的 5 个函数：
- `_profile_runtime_state`：lazy 创建/返回某个 profile 的当月预算累计 dict
- `_provider_runtime_state`：lazy 创建/返回某个 provider 的熔断状态 dict
- `_record_request`：在 60 秒滑动窗口里追加当前请求时间戳（同时驱逐过期）
- `_record_success`：清零 provider 熔断计数 + 把成本累计到 profile 月度预算
- `_record_failure`：累加 provider 失败计数；达到熔断阈值时设置 open_until

**关于 state dict 引用与 monkeypatch**：三个 state dict
（`_REQUEST_WINDOWS / _PROFILE_RUNTIME_STATE / _PROVIDER_RUNTIME_STATE`）必须留在
`ai_gateway_service.py`，因为测试直接 mutate（`gateway._PROVIDER_RUNTIME_STATE["x"] = ...`）。
本模块通过函数体内 lazy import 拿到主模块的 dict 引用，与 B4.1/B4.2 中 views/skip_reason
模块的做法一致。

`_reset_gateway_runtime_state` 故意**不**搬到本模块——它必须直接 `clear()` 主模块的 dict
对象，且测试以 `gateway._reset_gateway_runtime_state()` 形式调用，留在主模块更稳。
"""

from __future__ import annotations

import time

from app.services.ai_gateway_constants import (
    CIRCUIT_BREAKER_COOLDOWN_SECONDS,
    CIRCUIT_BREAKER_THRESHOLD,
)
from app.services.ai_gateway_costing import _runtime_profile_key, _utc_month_key


def _profile_runtime_state(profile: dict) -> dict:
    from app.services.ai_gateway_service import _PROFILE_RUNTIME_STATE

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
    from app.services.ai_gateway_service import _PROVIDER_RUNTIME_STATE

    state = _PROVIDER_RUNTIME_STATE.get(provider)
    if state is None:
        state = {
            "consecutive_failures": 0,
            "open_until": 0.0,
            "last_error": None,
        }
        _PROVIDER_RUNTIME_STATE[provider] = state
    return state


def _record_request(profile: dict) -> None:
    from app.services.ai_gateway_service import _REQUEST_WINDOWS

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
