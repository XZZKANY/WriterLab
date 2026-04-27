import os

import httpx


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "240"))


def ollama_generate(
    prompt: str,
    options: dict | None = None,
    model: str | None = None,
    think: bool = False,
    timeout: float | None = None,
) -> str:
    payload = {
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "think": think,
        "options": {
            "num_ctx": 512,
            **(options or {}),
        },
    }

    try:
        # Ollama runs locally; bypass system HTTP proxies to avoid localhost calls
        # being forwarded to a proxy and failing with 502.
        with httpx.Client(trust_env=False, timeout=timeout or OLLAMA_TIMEOUT) as client:
            response = client.post(OLLAMA_URL, json=payload)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Ollama 调用失败：{exc}") from exc

    if response.status_code != 200:
        raise RuntimeError(
            f"Ollama 调用失败，状态码 {response.status_code}，响应内容：{response.text}"
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(f"Ollama 返回了非 JSON 响应：{response.text}") from exc

    content = data.get("response")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(f"Ollama 返回内容为空：{data}")

    return content
