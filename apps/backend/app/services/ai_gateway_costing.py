"""AI 网关的纯计算工具：成本估算、超时解析、profile key、消息体抽取。

承接来自 ai_gateway_service.py 的：
- `_runtime_profile_key`：profile 在 state 字典中的复合 key
- `_utc_month_key`：当前 UTC 月份字符串（用于月度预算窗口）
- `_provider_enabled`：解析 `AI_PROVIDER_<X>_ENABLED` 环境变量
- `_estimate_cost_usd`：基于 _MODEL_PRICING_USD_PER_1K 的价格估算
- `_resolve_timeout_ms`：从多个候选位置中拣选 effective timeout
- `_extract_text`：把 OpenAI 兼容协议的 message.content 拍平成字符串

这些函数都是**纯函数**，不触达 DB、不读写共享 state、不调用网络。
ai_gateway_service.py 顶部会 import 回来，保持测试 monkeypatch 的属性面。
"""

from __future__ import annotations

import os
from datetime import datetime

from app.services.ai_gateway_constants import _MODEL_PRICING_USD_PER_1K, STEP_TIMEOUT_MS


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
