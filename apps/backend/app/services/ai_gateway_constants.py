"""AI 网关的常量、dataclass 与极简的环境变量读取工具。

承接来自 ai_gateway_service.py 的：
- `_env_timeout_ms`：唯一一个仅做 os.getenv 解析的极小工具
- `GatewayCallResult` dataclass
- 完整的 `PROVIDER_FALLBACK_MATRIX` 与衍生 `DEFAULT_PROFILES / STEP_TIMEOUT_MS`
- `PROVIDER_DEFAULTS` / `_MODEL_PRICING_USD_PER_1K`
- 熔断阈值与 fixture 标识常量
- `PROVIDER_RUNTIME_STEPS` 步骤序列

这些都是**纯数据 / 纯派生**，不触达 DB、不依赖运行时 state、不调用网络。
ai_gateway_service.py 顶部会把它们 import 回来，以保持测试 monkeypatch 的属性面。
"""

from __future__ import annotations

import os
from dataclasses import dataclass


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

PROVIDER_RUNTIME_STEPS = ("analyze", "planner", "write", "style", "check")

_MODEL_PRICING_USD_PER_1K = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "deepseek-chat": {"input": 0.00014, "output": 0.00028},
    "grok-2-latest": {"input": 0.002, "output": 0.01},
}
