"""ollama_service 直测。

`ollama_generate` 是本地 Ollama 调用入口；用 monkeypatch 把 httpx.Client
替换成 fake，覆盖：payload 拼接、状态码 / JSON / 空内容错误、超时与模型名 fallback。
不需要真实 Ollama 服务运行。
"""

import json

import httpx
import pytest

from app.services import ollama_service


class _FakeResponse:
    def __init__(self, status_code: int, body, text: str | None = None):
        self.status_code = status_code
        self._body = body
        self.text = text if text is not None else (json.dumps(body) if isinstance(body, dict) else str(body))

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


class _FakeClient:
    """httpx.Client 的最小替身：记录 post 调用并返回预设响应。"""

    def __init__(self, response, raise_on_post: Exception | None = None):
        self._response = response
        self._raise = raise_on_post
        self.last_url: str | None = None
        self.last_json: dict | None = None
        self.timeout = None
        self.trust_env = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, *, json):
        self.last_url = url
        self.last_json = json
        if self._raise is not None:
            raise self._raise
        return self._response


def _patch_client(monkeypatch, response=None, raise_on_post=None):
    client = _FakeClient(response, raise_on_post=raise_on_post)

    def fake_client_factory(*, trust_env, timeout):
        client.trust_env = trust_env
        client.timeout = timeout
        return client

    monkeypatch.setattr(ollama_service.httpx, "Client", fake_client_factory)
    return client


# ---------- happy path ----------

def test_ollama_generate_returns_response_content(monkeypatch):
    client = _patch_client(monkeypatch, response=_FakeResponse(200, {"response": "hello world"}))
    out = ollama_service.ollama_generate("say hi")
    assert out == "hello world"
    # 默认走 OLLAMA_URL / OLLAMA_MODEL / OLLAMA_TIMEOUT
    assert client.last_url == ollama_service.OLLAMA_URL
    assert client.last_json["model"] == ollama_service.OLLAMA_MODEL
    assert client.last_json["prompt"] == "say hi"
    assert client.last_json["stream"] is False
    assert client.last_json["think"] is False
    # 默认 num_ctx=512 注入到 options
    assert client.last_json["options"]["num_ctx"] == 512


def test_ollama_generate_overrides_model_and_timeout(monkeypatch):
    client = _patch_client(monkeypatch, response=_FakeResponse(200, {"response": "ok"}))
    ollama_service.ollama_generate("x", model="qwen2.5:7b", timeout=12.0)
    assert client.last_json["model"] == "qwen2.5:7b"
    assert client.timeout == 12.0


def test_ollama_generate_passes_through_think_flag(monkeypatch):
    client = _patch_client(monkeypatch, response=_FakeResponse(200, {"response": "ok"}))
    ollama_service.ollama_generate("x", think=True)
    assert client.last_json["think"] is True


def test_ollama_generate_merges_options_with_default_num_ctx(monkeypatch):
    client = _patch_client(monkeypatch, response=_FakeResponse(200, {"response": "ok"}))
    ollama_service.ollama_generate("x", options={"temperature": 0.4, "top_p": 0.95})
    assert client.last_json["options"]["temperature"] == 0.4
    assert client.last_json["options"]["top_p"] == 0.95
    # 默认 num_ctx 仍存在
    assert client.last_json["options"]["num_ctx"] == 512


def test_ollama_generate_options_can_override_default_num_ctx(monkeypatch):
    """options 后展开会覆盖默认 num_ctx —— 当前实现的预期行为。"""
    client = _patch_client(monkeypatch, response=_FakeResponse(200, {"response": "ok"}))
    ollama_service.ollama_generate("x", options={"num_ctx": 4096})
    assert client.last_json["options"]["num_ctx"] == 4096


def test_ollama_generate_uses_trust_env_false(monkeypatch):
    """关键：本地调用必须绕过 HTTP 代理（避免 localhost 被代理转发后 502）。"""
    client = _patch_client(monkeypatch, response=_FakeResponse(200, {"response": "ok"}))
    ollama_service.ollama_generate("x")
    assert client.trust_env is False


# ---------- error paths ----------

def test_ollama_generate_raises_when_http_error(monkeypatch):
    _patch_client(monkeypatch, raise_on_post=httpx.ConnectError("connection refused"))
    with pytest.raises(RuntimeError, match="Ollama 调用失败"):
        ollama_service.ollama_generate("x")


def test_ollama_generate_raises_on_non_200_status(monkeypatch):
    _patch_client(monkeypatch, response=_FakeResponse(500, {"err": "boom"}, text="internal"))
    with pytest.raises(RuntimeError, match="状态码 500"):
        ollama_service.ollama_generate("x")


def test_ollama_generate_raises_on_invalid_json(monkeypatch):
    _patch_client(monkeypatch, response=_FakeResponse(200, ValueError("bad json"), text="<html>"))
    with pytest.raises(RuntimeError, match="非 JSON"):
        ollama_service.ollama_generate("x")


def test_ollama_generate_raises_when_response_field_missing(monkeypatch):
    _patch_client(monkeypatch, response=_FakeResponse(200, {"other_field": "x"}))
    with pytest.raises(RuntimeError, match="返回内容为空"):
        ollama_service.ollama_generate("x")


def test_ollama_generate_raises_when_response_is_blank_string(monkeypatch):
    _patch_client(monkeypatch, response=_FakeResponse(200, {"response": "   "}))
    with pytest.raises(RuntimeError, match="返回内容为空"):
        ollama_service.ollama_generate("x")


def test_ollama_generate_raises_when_response_is_non_string(monkeypatch):
    """response 不是字符串（比如 list 或 dict）应被拒绝。"""
    _patch_client(monkeypatch, response=_FakeResponse(200, {"response": ["not", "a", "string"]}))
    with pytest.raises(RuntimeError, match="返回内容为空"):
        ollama_service.ollama_generate("x")
