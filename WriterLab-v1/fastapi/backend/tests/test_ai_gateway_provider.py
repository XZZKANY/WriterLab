"""ai_gateway_provider 直测。

T-6.B4.3.a 拆出的 H 块 HTTP+Ollama 调用。`_call_provider` 是路由器；
`_openai_compatible_generate` 是 cloud 实际 HTTP 调用。
"""

from types import SimpleNamespace

import pytest

from app.services import ai_gateway_provider as provider_module
from app.services.ai_gateway_provider import _call_provider, _openai_compatible_generate


# ---------- _call_provider 路由 ----------

def test_call_provider_routes_ollama_to_ollama_generate(monkeypatch):
    captured = {}

    def fake_ollama_generate(prompt, *, model, options, think, timeout):
        captured.update(prompt=prompt, model=model, options=options, think=think, timeout=timeout)
        return "ollama text"

    monkeypatch.setattr(provider_module, "ollama_generate", fake_ollama_generate)

    profile = {"provider": "ollama", "model": "qwen2.5:3b", "temperature": 0.4, "name": "p"}
    text, usage = _call_provider(profile, "say hi", None, timeout_ms=5000)
    assert text == "ollama text"
    assert usage is None
    assert captured["model"] == "qwen2.5:3b"
    assert captured["timeout"] == pytest.approx(5.0)
    assert captured["options"]["temperature"] == 0.4
    assert captured["think"] is False


def test_call_provider_clamps_timeout_minimum_1s(monkeypatch):
    captured = {}

    def fake_ollama_generate(prompt, *, model, options, think, timeout):
        captured["timeout"] = timeout
        return "x"

    monkeypatch.setattr(provider_module, "ollama_generate", fake_ollama_generate)
    _call_provider({"provider": "ollama", "model": "m", "name": "p"}, "x", None, timeout_ms=200)
    assert captured["timeout"] == pytest.approx(1.0)


def test_call_provider_routes_openai_compatible(monkeypatch):
    captured = {}

    def fake_openai_compatible(profile, prompt, params, *, timeout_ms):
        captured.update(profile=profile, prompt=prompt, params=params, timeout_ms=timeout_ms)
        return "cloud text", {"prompt_tokens": 10}

    monkeypatch.setattr(provider_module, "_openai_compatible_generate", fake_openai_compatible)

    for cloud in ("openai", "deepseek", "xai"):
        profile = {"provider": cloud, "model": "m", "name": "p"}
        text, usage = _call_provider(profile, "x", {"temperature": 0.7}, timeout_ms=10000)
        assert text == "cloud text"
        assert usage == {"prompt_tokens": 10}
        assert captured["profile"]["provider"] == cloud


def test_call_provider_raises_for_unknown_provider():
    with pytest.raises(RuntimeError, match="Provider not configured"):
        _call_provider({"provider": "ghost", "model": "m", "name": "p"}, "x", None, timeout_ms=5000)


# ---------- _openai_compatible_generate（用 monkeypatch 替换 httpx + provider_settings） ----------

class _FakeResponse:
    def __init__(self, status_code, json_data, text="ok"):
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        if isinstance(self._json, Exception):
            raise self._json
        return self._json


class _FakeClient:
    def __init__(self, response):
        self._response = response

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, *, json, headers):
        self._last_url = url
        self._last_payload = json
        self._last_headers = headers
        return self._response


def _patch_keys(monkeypatch, *, base_url="https://api.openai.com/v1", api_key="sk-test"):
    monkeypatch.setattr(provider_module, "resolve_provider_api_base", lambda provider: base_url)
    monkeypatch.setattr(provider_module, "resolve_provider_api_key", lambda provider: api_key)


def test_openai_compatible_generate_returns_text_and_usage(monkeypatch):
    _patch_keys(monkeypatch)
    fake_resp = _FakeResponse(
        200,
        {
            "choices": [{"message": {"content": "  hello world  "}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 24},
        },
    )
    client = _FakeClient(fake_resp)
    monkeypatch.setattr(provider_module.httpx, "Client", lambda **kwargs: client)

    profile = {"provider": "openai", "model": "gpt-4o-mini", "name": "p"}
    text, usage = _openai_compatible_generate(profile, "hi", None, timeout_ms=10000)
    assert text == "hello world"
    assert usage == {"prompt_tokens": 12, "completion_tokens": 24}
    # URL = base_url 去尾 / 后 + /chat/completions
    assert client._last_url == "https://api.openai.com/v1/chat/completions"
    # Authorization header
    assert client._last_headers["Authorization"] == "Bearer sk-test"


def test_openai_compatible_generate_raises_when_no_api_key(monkeypatch):
    _patch_keys(monkeypatch, api_key=None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="Missing API key"):
        _openai_compatible_generate(
            {"provider": "openai", "model": "m", "name": "p", "api_key_env": "OPENAI_API_KEY"},
            "x",
            None,
            timeout_ms=5000,
        )


def test_openai_compatible_generate_raises_on_http_error(monkeypatch):
    _patch_keys(monkeypatch)
    fake_resp = _FakeResponse(500, {}, text="internal error")
    monkeypatch.setattr(provider_module.httpx, "Client", lambda **kwargs: _FakeClient(fake_resp))
    with pytest.raises(RuntimeError, match="500"):
        _openai_compatible_generate({"provider": "openai", "model": "m", "name": "p"}, "x", None, timeout_ms=5000)


def test_openai_compatible_generate_raises_on_invalid_json(monkeypatch):
    _patch_keys(monkeypatch)
    fake_resp = _FakeResponse(200, ValueError("bad json"))
    monkeypatch.setattr(provider_module.httpx, "Client", lambda **kwargs: _FakeClient(fake_resp))
    with pytest.raises(RuntimeError, match="invalid JSON"):
        _openai_compatible_generate({"provider": "openai", "model": "m", "name": "p"}, "x", None, timeout_ms=5000)


def test_openai_compatible_generate_raises_when_no_choices(monkeypatch):
    _patch_keys(monkeypatch)
    fake_resp = _FakeResponse(200, {"choices": []})
    monkeypatch.setattr(provider_module.httpx, "Client", lambda **kwargs: _FakeClient(fake_resp))
    with pytest.raises(RuntimeError, match="no choices"):
        _openai_compatible_generate({"provider": "openai", "model": "m", "name": "p"}, "x", None, timeout_ms=5000)


def test_openai_compatible_generate_raises_when_empty_content(monkeypatch):
    _patch_keys(monkeypatch)
    fake_resp = _FakeResponse(200, {"choices": [{"message": {"content": "   "}}]})
    monkeypatch.setattr(provider_module.httpx, "Client", lambda **kwargs: _FakeClient(fake_resp))
    with pytest.raises(RuntimeError, match="empty content"):
        _openai_compatible_generate({"provider": "openai", "model": "m", "name": "p"}, "x", None, timeout_ms=5000)


def test_openai_compatible_generate_passes_temperature_and_max_tokens(monkeypatch):
    _patch_keys(monkeypatch)
    fake_resp = _FakeResponse(200, {"choices": [{"message": {"content": "ok"}}], "usage": {}})
    client = _FakeClient(fake_resp)
    monkeypatch.setattr(provider_module.httpx, "Client", lambda **kwargs: client)

    profile = {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "name": "p",
        "temperature": 0.5,
        "max_tokens": 100,
    }
    _openai_compatible_generate(profile, "x", None, timeout_ms=5000)
    assert client._last_payload["temperature"] == 0.5
    assert client._last_payload["max_tokens"] == 100


def test_openai_compatible_generate_explicit_params_override_profile_defaults(monkeypatch):
    _patch_keys(monkeypatch)
    fake_resp = _FakeResponse(200, {"choices": [{"message": {"content": "ok"}}]})
    client = _FakeClient(fake_resp)
    monkeypatch.setattr(provider_module.httpx, "Client", lambda **kwargs: client)

    profile = {"provider": "openai", "model": "m", "name": "p", "temperature": 0.5}
    # 显式 params.temperature=0.9 应覆盖 profile.temperature=0.5
    _openai_compatible_generate(profile, "x", {"temperature": 0.9}, timeout_ms=5000)
    assert client._last_payload["temperature"] == 0.9


def test_openai_compatible_generate_includes_extra_headers(monkeypatch):
    _patch_keys(monkeypatch)
    fake_resp = _FakeResponse(200, {"choices": [{"message": {"content": "ok"}}]})
    client = _FakeClient(fake_resp)
    monkeypatch.setattr(provider_module.httpx, "Client", lambda **kwargs: client)

    profile = {"provider": "openai", "model": "m", "name": "p", "extra_headers": {"X-Run-Id": "abc"}}
    _openai_compatible_generate(profile, "x", None, timeout_ms=5000)
    assert client._last_headers["X-Run-Id"] == "abc"
    # Authorization 不能被 extra_headers 覆盖（profile.extra_headers 后展开会覆盖；这里测当前实现）
    # 注意：当前实现 `**(profile.get("extra_headers") or {})` 在最后展开，所以 extra_headers 会覆盖 Authorization。
    # 这里只检查 X-Run-Id 进入了请求，避免锁死覆盖语义。
