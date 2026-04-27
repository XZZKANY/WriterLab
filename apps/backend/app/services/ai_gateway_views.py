"""AI 网关运行时状态的只读视图与展示辅助。

承接来自 ai_gateway_service.py 的 F 块：
- `_peek_profile_runtime_state` / `_peek_provider_runtime_state`：把模块级 state dict
  里的当前值打成只读副本（不写）
- `_runtime_open_until_iso`：把熔断 `open_until` 时间戳格式化为 ISO 字符串
- `_remaining_cooldown_seconds`：剩余冷却秒数（基于 `time.time`）
- `_known_provider_names`：把 PROVIDER_DEFAULTS / PROVIDER_FALLBACK_MATRIX / 当前
  profile 列表里出现过的 provider 合集排序

**关于 state dict 引用**：两个 `_peek_*` 函数读 `_PROVIDER_RUNTIME_STATE` 与
`_PROFILE_RUNTIME_STATE`，这两个 dict 必须留在 `ai_gateway_service`（测试直接 mutate
同一对象）。这里通过函数体内 lazy import 拿到主模块的 dict 引用——避免与主模块形成
循环 import 的加载顺序问题，同时与现有测试 patch 模式（mutate dict / monkeypatch.setattr
替换 attribute 绑定）完全兼容。
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Iterable

from app.services.ai_gateway_constants import PROVIDER_DEFAULTS, PROVIDER_FALLBACK_MATRIX
from app.services.ai_gateway_costing import _runtime_profile_key, _utc_month_key


def _peek_profile_runtime_state(profile: dict) -> dict:
    # lazy import：避免与 ai_gateway_service 形成 import 顺序敏感的循环依赖
    from app.services.ai_gateway_service import _PROFILE_RUNTIME_STATE

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
    from app.services.ai_gateway_service import _PROVIDER_RUNTIME_STATE

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
