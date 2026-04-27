"""ai_gateway_state 直测。

T-6.B4.3.b 拆出的 D 块：state init + record_*。所有函数都通过 lazy import 访问主模块的
state dict；测试 mutate / monkeypatch 必须在两边一致生效。
"""

from app.services import ai_gateway_service as gateway
from app.services.ai_gateway_state import (
    _profile_runtime_state,
    _provider_runtime_state,
    _record_failure,
    _record_request,
    _record_success,
)


def setup_function():
    gateway._reset_gateway_runtime_state()


# ---------- _profile_runtime_state ----------

def test_profile_runtime_state_lazy_creates_default_when_unknown():
    profile = {"provider": "openai", "name": "p", "model": "m"}
    state = _profile_runtime_state(profile)
    assert state["spent_usd"] == 0.0
    assert "month" in state
    # 写回主模块 dict（同一对象）
    key = gateway._runtime_profile_key(profile)
    assert gateway._PROFILE_RUNTIME_STATE[key] is state


def test_profile_runtime_state_resets_when_month_changes():
    profile = {"provider": "openai", "name": "p", "model": "m"}
    key = gateway._runtime_profile_key(profile)
    # 先写入旧月份
    gateway._PROFILE_RUNTIME_STATE[key] = {"month": "1999-01", "spent_usd": 9.99}
    state = _profile_runtime_state(profile)
    assert state["month"] != "1999-01"
    assert state["spent_usd"] == 0.0


def test_profile_runtime_state_returns_existing_when_month_matches():
    profile = {"provider": "openai", "name": "p", "model": "m"}
    key = gateway._runtime_profile_key(profile)
    gateway._PROFILE_RUNTIME_STATE[key] = {"month": gateway._utc_month_key(), "spent_usd": 3.14}
    state = _profile_runtime_state(profile)
    assert state["spent_usd"] == 3.14


# ---------- _provider_runtime_state ----------

def test_provider_runtime_state_lazy_creates_default():
    state = _provider_runtime_state("openai")
    assert state == {"consecutive_failures": 0, "open_until": 0.0, "last_error": None}
    # 写回主模块 dict
    assert gateway._PROVIDER_RUNTIME_STATE["openai"] is state


def test_provider_runtime_state_returns_existing():
    gateway._PROVIDER_RUNTIME_STATE["openai"] = {
        "consecutive_failures": 5,
        "open_until": 12345.6,
        "last_error": "boom",
    }
    state = _provider_runtime_state("openai")
    assert state["consecutive_failures"] == 5


# ---------- _record_request ----------

def test_record_request_appends_timestamp(monkeypatch):
    monkeypatch.setattr(gateway.time, "time", lambda: 100.0)
    profile = {"provider": "openai", "name": "p", "model": "m"}
    _record_request(profile)
    key = gateway._runtime_profile_key(profile)
    assert list(gateway._REQUEST_WINDOWS[key]) == [100.0]


def test_record_request_evicts_old_timestamps(monkeypatch):
    profile = {"provider": "openai", "name": "p", "model": "m"}
    key = gateway._runtime_profile_key(profile)
    gateway._REQUEST_WINDOWS[key].append(0.0)  # 应被驱逐（>60s 前）
    gateway._REQUEST_WINDOWS[key].append(50.0)  # 应被驱逐
    monkeypatch.setattr(gateway.time, "time", lambda: 200.0)
    _record_request(profile)
    # 驱逐 0.0 与 50.0；剩下 200.0
    assert list(gateway._REQUEST_WINDOWS[key]) == [200.0]


# ---------- _record_success ----------

def test_record_success_clears_provider_failure_counters():
    gateway._PROVIDER_RUNTIME_STATE["openai"] = {
        "consecutive_failures": 5,
        "open_until": 9999.0,
        "last_error": "boom",
    }
    _record_success({"provider": "openai", "name": "p", "model": "m"}, cost_estimate=None)
    state = gateway._PROVIDER_RUNTIME_STATE["openai"]
    assert state["consecutive_failures"] == 0
    assert state["open_until"] == 0.0
    assert state["last_error"] is None


def test_record_success_accumulates_cost_when_provided():
    profile = {"provider": "openai", "name": "p", "model": "m"}
    _record_success(profile, cost_estimate=0.001)
    key = gateway._runtime_profile_key(profile)
    assert gateway._PROFILE_RUNTIME_STATE[key]["spent_usd"] == 0.001
    # 第二次累加
    _record_success(profile, cost_estimate=0.002)
    assert gateway._PROFILE_RUNTIME_STATE[key]["spent_usd"] == 0.003


def test_record_success_does_not_record_cost_when_estimate_is_none_or_zero():
    profile = {"provider": "openai", "name": "p", "model": "m"}
    _record_success(profile, cost_estimate=None)
    key = gateway._runtime_profile_key(profile)
    # cost_estimate=None → 不创建 profile state
    assert key not in gateway._PROFILE_RUNTIME_STATE


# ---------- _record_failure ----------

def test_record_failure_increments_consecutive_failures():
    profile = {"provider": "openai", "name": "p", "model": "m"}
    _record_failure(profile, error_message="boom1")
    state = gateway._PROVIDER_RUNTIME_STATE["openai"]
    assert state["consecutive_failures"] == 1
    assert state["last_error"] == "boom1"
    _record_failure(profile, error_message="boom2")
    assert gateway._PROVIDER_RUNTIME_STATE["openai"]["consecutive_failures"] == 2
    assert gateway._PROVIDER_RUNTIME_STATE["openai"]["last_error"] == "boom2"


def test_record_failure_opens_circuit_at_threshold(monkeypatch):
    monkeypatch.setattr(gateway.time, "time", lambda: 1000.0)
    profile = {"provider": "openai", "name": "p", "model": "m"}
    for _ in range(gateway.CIRCUIT_BREAKER_THRESHOLD):
        _record_failure(profile, error_message="x")
    state = gateway._PROVIDER_RUNTIME_STATE["openai"]
    assert state["consecutive_failures"] == gateway.CIRCUIT_BREAKER_THRESHOLD
    expected_open_until = 1000.0 + gateway.CIRCUIT_BREAKER_COOLDOWN_SECONDS
    assert state["open_until"] == expected_open_until


def test_record_failure_below_threshold_does_not_open_circuit():
    profile = {"provider": "openai", "name": "p", "model": "m"}
    _record_failure(profile, error_message="x")
    # threshold 一般是 3，这里只 1 次失败
    assert gateway._PROVIDER_RUNTIME_STATE["openai"]["open_until"] == 0.0
