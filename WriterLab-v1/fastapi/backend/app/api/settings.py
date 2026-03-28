from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter

from app.services.provider_settings_service import (
    get_provider_settings_response,
    save_provider_settings,
)


router = APIRouter(prefix="/api/settings", tags=["settings"])


class ProviderSettingsItemRequest(BaseModel):
    api_key: str | None = Field(default=None)
    api_base: str | None = Field(default=None)


class ProviderSettingsUpdateRequest(BaseModel):
    openai: ProviderSettingsItemRequest | None = None
    deepseek: ProviderSettingsItemRequest | None = None
    xai: ProviderSettingsItemRequest | None = None


@router.get("/providers")
def get_provider_settings():
    return {"providers": get_provider_settings_response()}


@router.put("/providers")
def update_provider_settings(payload: ProviderSettingsUpdateRequest):
    saved = save_provider_settings(payload.model_dump())
    return {
        "message": "API 配置已保存",
        "providers": get_provider_settings_response(),
        "saved_providers": [provider for provider, item in saved.items() if item.get("api_key")],
    }
