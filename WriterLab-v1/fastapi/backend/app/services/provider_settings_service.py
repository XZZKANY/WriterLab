from __future__ import annotations

import json
from pathlib import Path


_SUPPORTED_PROVIDERS = ("openai", "deepseek", "xai")
_SETTINGS_PATH = Path(__file__).resolve().parents[2] / ".runtime" / "provider_settings.json"
_DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "xai": "https://api.x.ai/v1",
}


def _ensure_runtime_dir() -> None:
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)


def _mask_api_key(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * max(len(value) - 8, 4)}{value[-4:]}"


def _normalize_provider_payload(provider: str, payload: dict | None) -> dict:
    payload = payload or {}
    api_key = str(payload.get("api_key") or "").strip()
    api_base = str(payload.get("api_base") or _DEFAULT_BASE_URLS.get(provider) or "").strip()
    return {
        "provider": provider,
        "api_key": api_key,
        "api_base": api_base,
    }


def load_provider_settings() -> dict[str, dict]:
    if not _SETTINGS_PATH.exists():
        return {provider: _normalize_provider_payload(provider, None) for provider in _SUPPORTED_PROVIDERS}
    try:
        data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {provider: _normalize_provider_payload(provider, None) for provider in _SUPPORTED_PROVIDERS}
    return {
        provider: _normalize_provider_payload(provider, data.get(provider))
        for provider in _SUPPORTED_PROVIDERS
    }


def save_provider_settings(payload: dict[str, dict]) -> dict[str, dict]:
    current = load_provider_settings()
    next_payload: dict[str, dict] = {}
    for provider in _SUPPORTED_PROVIDERS:
        entry = payload.get(provider, {})
        current_entry = current[provider]
        api_key = entry.get("api_key")
        api_base = entry.get("api_base")
        normalized = {
            "provider": provider,
            "api_key": current_entry["api_key"] if api_key is None else str(api_key).strip(),
            "api_base": current_entry["api_base"] if api_base is None else str(api_base).strip(),
        }
        if not normalized["api_base"]:
            normalized["api_base"] = _DEFAULT_BASE_URLS[provider]
        next_payload[provider] = normalized

    _ensure_runtime_dir()
    _SETTINGS_PATH.write_text(
        json.dumps(
            {
                provider: {
                    "api_key": next_payload[provider]["api_key"],
                    "api_base": next_payload[provider]["api_base"],
                }
                for provider in _SUPPORTED_PROVIDERS
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return next_payload


def get_provider_settings_response() -> list[dict]:
    settings = load_provider_settings()
    response: list[dict] = []
    for provider in _SUPPORTED_PROVIDERS:
        item = settings[provider]
        api_key = item["api_key"]
        response.append(
            {
                "provider": provider,
                "api_base": item["api_base"],
                "has_api_key": bool(api_key),
                "api_key_masked": _mask_api_key(api_key) if api_key else None,
            }
        )
    return response


def resolve_provider_api_key(provider: str) -> str | None:
    provider = str(provider or "").strip().lower()
    if provider not in _SUPPORTED_PROVIDERS:
        return None
    return load_provider_settings().get(provider, {}).get("api_key") or None


def resolve_provider_api_base(provider: str) -> str | None:
    provider = str(provider or "").strip().lower()
    if provider not in _SUPPORTED_PROVIDERS:
        return None
    return load_provider_settings().get(provider, {}).get("api_base") or _DEFAULT_BASE_URLS.get(provider)
