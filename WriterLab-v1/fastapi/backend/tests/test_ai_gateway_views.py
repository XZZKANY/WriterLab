"""ai_gateway_views 直测。

T-6.B4.1 拆出的 5 个只读视图函数：3 个零 state 辅助 +
2 个通过 lazy import 读 ai_gateway_service state dict 的 peek 函数。
"""

from app.services import ai_gateway_service as gateway
from app.services.ai_gateway_views import (
    _known_provider_names,
    _peek_profile_runtime_state,
    _peek_provider_runtime_state,
    _remaining_cooldown_seconds,
    _runtime_open_until_iso,
)


# ---------- _runtime_open_until_iso ----------

def test_runtime_open_until_iso_returns_none_for_zero_or_negative():
    assert _runtime_open_until_iso(0) is None
    assert _runtime_open_until_iso(0.0) is None
    assert _runtime_open_until_iso(-1) is None
    assert _runtime_open_until_iso(None) is None


def test_runtime_open_until_iso_formats_unix_timestamp():
    out = _runtime_open_until_iso(1700000000)
    assert out is not None
    assert out.endswith("Z")
    # 1700000000 → 2023-11-14T22:13:20Z
    assert "2023-11-14" in out


# ---------- _remaining_cooldown_seconds ----------

def test_remaining_cooldown_seconds_returns_zero_when_in_past():
    assert _remaining_cooldown_seconds(0) == 0
    assert _remaining_cooldown_seconds(None) == 0
    assert _remaining_cooldown_seconds(1) == 0  # 1970 时间戳


def test_remaining_cooldown_seconds_returns_at_least_1_when_in_future(monkeypatch):
    # monkeypatch.setattr(gateway.time, "time", lambda: 100.0)  ← 这是测主模块的 time，
    # 我们这里直接用未来 timestamp 即可；views 内部用自己的 time module。
    import time

    future = time.time() + 10
    out = _remaining_cooldown_seconds(future)
    assert out >= 1


# ---------- _known_provider_names ----------

def test_known_provider_names_includes_default_providers():
    out = _known_provider_names([])
    # PROVIDER_DEFAULTS 至少有 openai/deepseek/xai
    assert "openai" in out
    assert "deepseek" in out
    assert "xai" in out


def test_known_provider_names_includes_extra_profile_providers():
    custom_profile = {"provider": "custom-vendor"}
    out = _known_provider_names([custom_profile])
    assert "custom-vendor" in out


def test_known_provider_names_excludes_blank_provider_strings():
    out = _known_provider_names([{"provider": ""}, {"provider": None}])
    assert "" not in out
    # None 会被 str(None) → "None"，但因为不是空才被加入；这是已实现行为
    # 测试不锁这部分细节，重点是不漏掉 default providers
    assert "openai" in out


def test_known_provider_names_returns_sorted_unique():
    out = _known_provider_names([{"provider": "openai"}])
    assert out == sorted(out)
    assert len(out) == len(set(out))


# ---------- _peek_provider_runtime_state ----------

def test_peek_provider_runtime_state_default_when_unknown():
    gateway._reset_gateway_runtime_state()
    snapshot = _peek_provider_runtime_state("openai")
    assert snapshot == {
        "consecutive_failures": 0,
        "open_until": 0.0,
        "last_error": None,
    }


def test_peek_provider_runtime_state_reads_main_module_dict():
    gateway._reset_gateway_runtime_state()
    # 直接 mutate 主模块的 state dict（测试一直这样做）
    gateway._PROVIDER_RUNTIME_STATE["openai"] = {
        "consecutive_failures": 5,
        "open_until": 12345.6,
        "last_error": "boom",
    }
    snapshot = _peek_provider_runtime_state("openai")
    assert snapshot["consecutive_failures"] == 5
    assert snapshot["open_until"] == 12345.6
    assert snapshot["last_error"] == "boom"


def test_peek_provider_runtime_state_returns_independent_copy():
    """peek 必须返回新字典，外部修改不污染内部 state。"""
    gateway._reset_gateway_runtime_state()
    gateway._PROVIDER_RUNTIME_STATE["x"] = {
        "consecutive_failures": 1,
        "open_until": 0.0,
        "last_error": None,
    }
    snap = _peek_provider_runtime_state("x")
    snap["consecutive_failures"] = 999
    fresh = _peek_provider_runtime_state("x")
    assert fresh["consecutive_failures"] == 1


# ---------- _peek_profile_runtime_state ----------

def test_peek_profile_runtime_state_default_when_unknown():
    gateway._reset_gateway_runtime_state()
    profile = {"provider": "openai", "name": "default-write-primary", "model": "gpt-4o-mini"}
    snapshot = _peek_profile_runtime_state(profile)
    assert "month" in snapshot
    assert snapshot["spent_usd"] == 0.0


def test_peek_profile_runtime_state_reads_main_module_dict():
    gateway._reset_gateway_runtime_state()
    profile = {"provider": "openai", "name": "default-write-primary", "model": "gpt-4o-mini"}
    key = gateway._runtime_profile_key(profile)
    gateway._PROFILE_RUNTIME_STATE[key] = {
        "month": gateway._utc_month_key(),
        "spent_usd": 3.14,
    }
    snapshot = _peek_profile_runtime_state(profile)
    assert snapshot["spent_usd"] == 3.14


def test_peek_profile_runtime_state_returns_default_when_month_stale():
    gateway._reset_gateway_runtime_state()
    profile = {"provider": "openai", "name": "x", "model": "y"}
    key = gateway._runtime_profile_key(profile)
    # 故意写入旧月份
    gateway._PROFILE_RUNTIME_STATE[key] = {
        "month": "1999-01",
        "spent_usd": 99.0,
    }
    snap = _peek_profile_runtime_state(profile)
    # 月份过期 → fallback default（spent_usd=0）
    assert snap["spent_usd"] == 0.0
    assert snap["month"] != "1999-01"
