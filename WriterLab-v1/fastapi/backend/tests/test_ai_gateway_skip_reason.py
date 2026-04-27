"""ai_gateway_skip_reason 直测。

T-6.B4.2 拆出的 4 个决策函数：rate_limit / budget / circuit / skip_reason。
所有这些都通过 lazy import 访问主模块的 state dict 与 D 块函数。
"""

from app.services import ai_gateway_service as gateway
from app.services.ai_gateway_skip_reason import (
    _budget_reason,
    _circuit_reason,
    _rate_limit_reason,
    _skip_reason,
)


# ---------- _rate_limit_reason ----------

def test_rate_limit_reason_returns_none_when_no_rpm_configured():
    profile = {"provider": "openai", "name": "p", "model": "m"}
    assert _rate_limit_reason(profile) is None


def test_rate_limit_reason_returns_none_when_window_below_limit(monkeypatch):
    gateway._reset_gateway_runtime_state()
    monkeypatch.setattr(gateway.time, "time", lambda: 30.0)
    profile = {"provider": "openai", "name": "p", "model": "m", "requests_per_minute": 5}
    # 只装 1 个时间戳，远低于 5 RPM
    key = gateway._runtime_profile_key(profile)
    gateway._REQUEST_WINDOWS[key].append(0.0)
    assert _rate_limit_reason(profile) is None


def test_rate_limit_reason_blocks_when_window_full(monkeypatch):
    gateway._reset_gateway_runtime_state()
    monkeypatch.setattr(gateway.time, "time", lambda: 30.0)
    profile = {"provider": "openai", "name": "p", "model": "m", "requests_per_minute": 2}
    key = gateway._runtime_profile_key(profile)
    # 装 2 个时间戳（30 秒前），还在 60s 滑动窗口内
    gateway._REQUEST_WINDOWS[key].append(0.0)
    gateway._REQUEST_WINDOWS[key].append(15.0)
    reason = _rate_limit_reason(profile)
    assert reason is not None
    assert "requests_per_minute=2" in reason


def test_rate_limit_reason_evicts_old_timestamps(monkeypatch):
    gateway._reset_gateway_runtime_state()
    # 当前时间 t=200；窗口 60s ⇒ 只有 t>=140 的戳才算数
    monkeypatch.setattr(gateway.time, "time", lambda: 200.0)
    profile = {"provider": "openai", "name": "p", "model": "m", "requests_per_minute": 1}
    key = gateway._runtime_profile_key(profile)
    gateway._REQUEST_WINDOWS[key].append(0.0)  # 应被驱逐
    gateway._REQUEST_WINDOWS[key].append(50.0)  # 应被驱逐
    # 没有有效戳 → 不应触发限流
    assert _rate_limit_reason(profile) is None


# ---------- _budget_reason ----------

def test_budget_reason_returns_none_when_no_budget():
    gateway._reset_gateway_runtime_state()
    profile = {"provider": "openai", "name": "p", "model": "m"}
    assert _budget_reason(profile) is None


def test_budget_reason_returns_none_when_under_budget():
    gateway._reset_gateway_runtime_state()
    profile = {
        "provider": "openai",
        "name": "p",
        "model": "m",
        "monthly_budget_usd": 10.0,
    }
    key = gateway._runtime_profile_key(profile)
    gateway._PROFILE_RUNTIME_STATE[key] = {
        "month": gateway._utc_month_key(),
        "spent_usd": 3.0,
    }
    assert _budget_reason(profile) is None


def test_budget_reason_blocks_when_at_or_above_budget():
    gateway._reset_gateway_runtime_state()
    profile = {
        "provider": "openai",
        "name": "p",
        "model": "m",
        "monthly_budget_usd": 10.0,
    }
    key = gateway._runtime_profile_key(profile)
    gateway._PROFILE_RUNTIME_STATE[key] = {
        "month": gateway._utc_month_key(),
        "spent_usd": 10.0,
    }
    reason = _budget_reason(profile)
    assert reason is not None
    assert "monthly_budget_usd=10" in reason


# ---------- _circuit_reason ----------

def test_circuit_reason_returns_none_when_circuit_closed(monkeypatch):
    gateway._reset_gateway_runtime_state()
    monkeypatch.setattr(gateway.time, "time", lambda: 100.0)
    profile = {"provider": "openai", "name": "p", "model": "m"}
    assert _circuit_reason(profile) is None


def test_circuit_reason_blocks_when_circuit_open(monkeypatch):
    gateway._reset_gateway_runtime_state()
    monkeypatch.setattr(gateway.time, "time", lambda: 100.0)
    gateway._PROVIDER_RUNTIME_STATE["openai"] = {
        "consecutive_failures": 5,
        "open_until": 200.0,  # 100 秒后才解除
        "last_error": "boom",
    }
    profile = {"provider": "openai", "name": "p", "model": "m"}
    reason = _circuit_reason(profile)
    assert reason is not None
    assert "circuit open" in reason
    assert "openai" in reason


def test_circuit_reason_returns_none_after_open_until_passed(monkeypatch):
    gateway._reset_gateway_runtime_state()
    monkeypatch.setattr(gateway.time, "time", lambda: 500.0)
    gateway._PROVIDER_RUNTIME_STATE["openai"] = {
        "consecutive_failures": 5,
        "open_until": 200.0,  # 已过期
        "last_error": "old",
    }
    profile = {"provider": "openai", "name": "p", "model": "m"}
    assert _circuit_reason(profile) is None


# ---------- _skip_reason ----------

def test_skip_reason_returns_provider_disabled_first(monkeypatch):
    gateway._reset_gateway_runtime_state()
    monkeypatch.setenv("AI_PROVIDER_OLLAMA_ENABLED", "false")
    profile = {"provider": "ollama", "name": "p", "model": "m"}
    reason = _skip_reason(profile)
    assert reason is not None
    assert "AI_PROVIDER_OLLAMA_ENABLED" in reason


def test_skip_reason_returns_circuit_when_enabled_but_circuit_open(monkeypatch):
    gateway._reset_gateway_runtime_state()
    monkeypatch.setattr(gateway.time, "time", lambda: 100.0)
    gateway._PROVIDER_RUNTIME_STATE["openai"] = {
        "consecutive_failures": 5,
        "open_until": 200.0,
        "last_error": "boom",
    }
    profile = {"provider": "openai", "name": "p", "model": "m"}
    reason = _skip_reason(profile)
    assert reason is not None
    assert "circuit open" in reason


def test_skip_reason_returns_none_when_all_clear(monkeypatch):
    gateway._reset_gateway_runtime_state()
    monkeypatch.setattr(gateway.time, "time", lambda: 100.0)
    profile = {"provider": "openai", "name": "p", "model": "m"}
    assert _skip_reason(profile) is None


def test_skip_reason_priority_circuit_before_rate_limit_before_budget(monkeypatch):
    """同时触发熔断 + 限流 + 预算，应先返回熔断原因（订单：circuit > rate > budget）。"""
    gateway._reset_gateway_runtime_state()
    monkeypatch.setattr(gateway.time, "time", lambda: 100.0)
    profile = {
        "provider": "openai",
        "name": "p",
        "model": "m",
        "requests_per_minute": 1,
        "monthly_budget_usd": 1.0,
    }
    key = gateway._runtime_profile_key(profile)
    gateway._PROVIDER_RUNTIME_STATE["openai"] = {
        "consecutive_failures": 5,
        "open_until": 200.0,
        "last_error": "x",
    }
    gateway._REQUEST_WINDOWS[key].append(80.0)  # 触发限流
    gateway._PROFILE_RUNTIME_STATE[key] = {
        "month": gateway._utc_month_key(),
        "spent_usd": 999.0,
    }
    reason = _skip_reason(profile)
    assert reason is not None
    assert "circuit open" in reason  # 顺序：circuit 优先
