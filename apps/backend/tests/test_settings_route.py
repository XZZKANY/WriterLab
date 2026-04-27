"""GET / PUT /api/settings/providers 路由契约。

后端 API 与 frontend lib/api/settings.ts 对齐的关键路径。
监控点：
- 响应 shape：{providers: [...]}
- PUT 后返回 message + providers + saved_providers
- saved_providers 只包含真实存了 api_key 的 provider
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import settings as settings_module
from app.api.settings import router as settings_router


def _patch_settings(monkeypatch, *, response_items=None, save_result=None):
    response_items = response_items or [
        {"provider": "openai", "api_base": "https://api.openai.com/v1", "has_api_key": False, "api_key_masked": None},
    ]
    save_result = save_result or {
        "openai": {"api_key": "", "api_base": "https://api.openai.com/v1"},
        "deepseek": {"api_key": "", "api_base": "https://api.deepseek.com/v1"},
        "xai": {"api_key": "", "api_base": "https://api.x.ai/v1"},
    }
    monkeypatch.setattr(settings_module, "get_provider_settings_response", lambda: list(response_items))
    monkeypatch.setattr(settings_module, "save_provider_settings", lambda payload: dict(save_result))


def _make_app():
    app = FastAPI()
    app.include_router(settings_router)
    return TestClient(app)


def test_get_provider_settings_returns_providers_shape(monkeypatch):
    _patch_settings(
        monkeypatch,
        response_items=[
            {"provider": "openai", "api_base": "x", "has_api_key": True, "api_key_masked": "sk-x***x"},
            {"provider": "deepseek", "api_base": "y", "has_api_key": False, "api_key_masked": None},
        ],
    )
    response = _make_app().get("/api/settings/providers")
    assert response.status_code == 200
    body = response.json()
    assert "providers" in body
    assert len(body["providers"]) == 2
    assert body["providers"][0]["provider"] == "openai"
    assert body["providers"][0]["has_api_key"] is True


def test_put_provider_settings_returns_message_providers_saved(monkeypatch):
    _patch_settings(
        monkeypatch,
        save_result={
            "openai": {"api_key": "sk-new", "api_base": "https://api.openai.com/v1"},
            "deepseek": {"api_key": "", "api_base": "https://api.deepseek.com/v1"},
            "xai": {"api_key": "", "api_base": "https://api.x.ai/v1"},
        },
    )
    response = _make_app().put(
        "/api/settings/providers",
        json={
            "openai": {"api_key": "sk-new", "api_base": None},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "API 配置已保存"
    assert "providers" in body
    # saved_providers 只包含真有 api_key 的 provider
    assert body["saved_providers"] == ["openai"]


def test_put_provider_settings_with_empty_payload_yields_empty_saved_list(monkeypatch):
    """所有 provider 都没存 api_key（save_result 全是 ""）→ saved_providers 应为空列表。"""
    _patch_settings(monkeypatch)
    response = _make_app().put("/api/settings/providers", json={})
    assert response.status_code == 200
    assert response.json()["saved_providers"] == []


def test_put_provider_settings_accepts_partial_provider_payload(monkeypatch):
    """payload 只传 openai 也应能接受（其它字段在 schema 是 Optional）。"""
    _patch_settings(monkeypatch)
    response = _make_app().put(
        "/api/settings/providers",
        json={"openai": {"api_key": "sk-x"}},
    )
    assert response.status_code == 200


def test_put_provider_settings_rejects_unknown_provider_field(monkeypatch):
    """payload 顶层字段只允许 openai / deepseek / xai；其它字段不会被识别但也不应崩。"""
    _patch_settings(monkeypatch)
    response = _make_app().put(
        "/api/settings/providers",
        json={"unknown_provider": {"api_key": "x"}},
    )
    # Pydantic 默认 ignore 额外字段；返回 200 即可
    assert response.status_code == 200
