"""AI 网关 provider 实际调用层（H 块）。

承接来自 ai_gateway_service.py 的 2 个函数：
- `_openai_compatible_generate`：通过 OpenAI 兼容 HTTP 协议（chat/completions）走 cloud provider
  （openai / deepseek / xai），从 profile 与 provider_settings_service 解析 API key 与 base_url
- `_call_provider`：根据 profile["provider"] 路由到 ollama_generate（local）或 _openai_compatible_generate（cloud）

**关于 monkeypatch 测试入口**：`_call_provider` 在 3 个测试中被
`monkeypatch.setattr(gateway, "_call_provider", fake)` 替换。
本模块拆出后，主模块通过 `from app.services.ai_gateway_provider import _call_provider`
拉回到 `app.services.ai_gateway_service` 的 module dict。`call_ai_gateway` 内部以
`_call_provider(...)` 形式调用，走 LOAD_GLOBAL 从主模块 dict 取最新绑定，所以
monkeypatch 替换主模块属性后，`call_ai_gateway` 调到的就是 fake。本模块的物理位置不影响该路径。
"""

from __future__ import annotations

import os

import httpx

from app.services.ai_gateway_constants import PROVIDER_DEFAULTS
from app.services.ai_gateway_costing import _extract_text
from app.services.ollama_service import ollama_generate
from app.services.provider_settings_service import resolve_provider_api_base, resolve_provider_api_key


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
