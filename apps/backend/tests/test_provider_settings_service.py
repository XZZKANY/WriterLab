"""provider_settings_service 直测。

该模块负责把云端 provider 的 API key/base 持久化到 backend/.runtime/provider_settings.json，
被 settings 路由与 ai_gateway 共用。重点验证：
- API key 掩码（_mask_api_key）
- 默认 api_base 当 payload 缺失时的回填
- save_* 后再 load_* 的往返一致性
- API key 留空时表示"保留旧密钥"，传入新值则覆盖
- 损坏 JSON 文件容忍降级
- resolve_* 对未知 provider 的回退
"""

import json

import pytest

from app.services import provider_settings_service as ps


@pytest.fixture(autouse=True)
def _isolated_settings_path(tmp_path, monkeypatch):
    """每个用例使用独立的 .runtime 目录，避免污染真实 backend/.runtime/。"""
    target = tmp_path / "provider_settings.json"
    monkeypatch.setattr(ps, "_SETTINGS_PATH", target)
    yield target


def test_default_settings_returned_when_file_missing():
    settings = ps.load_provider_settings()
    assert set(settings.keys()) == {"openai", "deepseek", "xai"}
    for provider, entry in settings.items():
        assert entry["api_key"] == ""
        assert entry["api_base"] == ps._DEFAULT_BASE_URLS[provider]


def test_corrupt_json_file_falls_back_to_defaults(_isolated_settings_path):
    _isolated_settings_path.parent.mkdir(parents=True, exist_ok=True)
    _isolated_settings_path.write_text("{not json", encoding="utf-8")
    settings = ps.load_provider_settings()
    for provider, entry in settings.items():
        assert entry["api_key"] == ""
        assert entry["api_base"] == ps._DEFAULT_BASE_URLS[provider]


def test_save_then_load_round_trip(_isolated_settings_path):
    saved = ps.save_provider_settings(
        {
            "openai": {"api_key": "sk-aaaaaaaaaaaa", "api_base": "https://custom.openai.example/v1"},
            "deepseek": {"api_key": "ds-1234567890", "api_base": "https://api.deepseek.com/v1"},
            "xai": {"api_key": "", "api_base": ""},  # 留空 base 应回到默认
        }
    )
    assert saved["openai"]["api_key"] == "sk-aaaaaaaaaaaa"
    assert saved["openai"]["api_base"] == "https://custom.openai.example/v1"
    assert saved["xai"]["api_base"] == ps._DEFAULT_BASE_URLS["xai"]

    # 持久化后磁盘应有内容；再加载应一致。
    on_disk = json.loads(_isolated_settings_path.read_text(encoding="utf-8"))
    assert on_disk["openai"]["api_key"] == "sk-aaaaaaaaaaaa"
    reloaded = ps.load_provider_settings()
    assert reloaded["deepseek"]["api_key"] == "ds-1234567890"


def test_save_with_api_key_none_keeps_existing_value():
    ps.save_provider_settings({"openai": {"api_key": "sk-keep-me", "api_base": ""}})
    # 第二次只动 api_base；api_key=None 表示保留。
    saved = ps.save_provider_settings({"openai": {"api_key": None, "api_base": "https://new.example/v1"}})
    assert saved["openai"]["api_key"] == "sk-keep-me"
    assert saved["openai"]["api_base"] == "https://new.example/v1"


def test_save_with_empty_api_base_falls_back_to_default():
    saved = ps.save_provider_settings({"deepseek": {"api_key": "k", "api_base": "   "}})
    assert saved["deepseek"]["api_base"] == ps._DEFAULT_BASE_URLS["deepseek"]


def test_get_provider_settings_response_marks_has_key_and_masks():
    ps.save_provider_settings({"openai": {"api_key": "sk-abcd1234efgh5678", "api_base": ""}})
    response = ps.get_provider_settings_response()
    openai_entry = next(item for item in response if item["provider"] == "openai")
    assert openai_entry["has_api_key"] is True
    masked = openai_entry["api_key_masked"]
    assert masked is not None
    assert masked.startswith("sk-a")
    assert masked.endswith("5678")
    assert "*" in masked
    # 没设过的 provider 不暴露 has_api_key=True。
    deepseek_entry = next(item for item in response if item["provider"] == "deepseek")
    assert deepseek_entry["has_api_key"] is False
    assert deepseek_entry["api_key_masked"] is None


def test_mask_api_key_short_value_masks_entirely():
    assert ps._mask_api_key("abcd") == "****"
    assert ps._mask_api_key("12345678") == "********"


def test_mask_api_key_keeps_first_and_last_four():
    masked = ps._mask_api_key("sk-abcdefghijklmnopqr")
    assert masked.startswith("sk-a")
    assert masked.endswith("nopqr"[-4:])
    # 中间至少 4 个 *
    assert masked.count("*") >= 4


def test_resolve_provider_api_key_returns_none_for_unknown_provider():
    assert ps.resolve_provider_api_key("unknown") is None
    assert ps.resolve_provider_api_key("") is None


def test_resolve_provider_api_key_returns_saved_value():
    ps.save_provider_settings({"deepseek": {"api_key": "ds-secret", "api_base": ""}})
    assert ps.resolve_provider_api_key("deepseek") == "ds-secret"
    # 大小写应被规整为小写；意外的空白也应去掉。
    assert ps.resolve_provider_api_key("  DEEPSEEK ") == "ds-secret"


def test_resolve_provider_api_base_falls_back_to_default():
    # 不传任何 settings 时应回到 _DEFAULT_BASE_URLS。
    assert ps.resolve_provider_api_base("openai") == ps._DEFAULT_BASE_URLS["openai"]
    assert ps.resolve_provider_api_base("xai") == ps._DEFAULT_BASE_URLS["xai"]
    assert ps.resolve_provider_api_base("unknown") is None


def test_resolve_provider_api_base_returns_overridden_value():
    ps.save_provider_settings({"openai": {"api_key": "k", "api_base": "https://proxy.local/v1"}})
    assert ps.resolve_provider_api_base("openai") == "https://proxy.local/v1"
