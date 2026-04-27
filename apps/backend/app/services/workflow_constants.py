"""工作流常量与纯工具函数。

承接来自 workflow_service.py 的：
- 步骤顺序与终态集合
- runner 标识与租约配置
- agent 元数据映射
- 纯小工具（不触达 DB / Session / 模型）
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime

from fastapi.encoders import jsonable_encoder

from app.services.ai_gateway_service import GatewayCallResult

# ---------- 步骤顺序与终态集合 ----------

STEP_ORDER = {
    "analyze": 10,
    "plan": 20,
    "write": 30,
    "style": 40,
    "check": 50,
    "guard": 60,
    "store": 70,
    "memory": 80,
}
STEP_SEQUENCE = [key for key, _ in sorted(STEP_ORDER.items(), key=lambda item: item[1])]
RUN_TERMINAL_STATUSES = {"completed", "partial_success", "failed", "cancelled"}
STEP_REUSABLE_STATUSES = {"completed", "skipped"}

# ---------- runner / 租约配置 ----------

LEASE_SECONDS = 45
RUNNER_POLL_SECONDS = 1.0
RUNNER_ID = f"workflow-runner-{os.getpid()}"
WORKFLOW_SCHEMA_VERSION = "workflow_step.v2"
VRAM_LOCK_TTL_SECONDS = int(os.getenv("WRITERLAB_VRAM_LOCK_TTL_SECONDS", "60"))

# ---------- 步骤 -> agent 元数据 ----------

STEP_AGENT_META = {
    "bootstrap": {"agent_key": "orchestrator", "agent_name": "Workflow Orchestrator", "agent_label": "Workflow Orchestrator"},
    "queued": {"agent_key": "orchestrator", "agent_name": "Workflow Orchestrator", "agent_label": "Workflow Orchestrator"},
    "analyze": {"agent_key": "planner", "agent_name": "Planner Agent", "agent_label": "Planner Agent"},
    "plan": {"agent_key": "planner", "agent_name": "Planner Agent", "agent_label": "Planner Agent"},
    "write": {"agent_key": "writer", "agent_name": "Writer Agent", "agent_label": "Writer Agent"},
    "style": {"agent_key": "style", "agent_name": "Style Agent", "agent_label": "Style Agent"},
    "check": {"agent_key": "consistency", "agent_name": "Consistency Agent", "agent_label": "Consistency Agent"},
    "guard": {"agent_key": "guardrail", "agent_name": "Guardrail Agent", "agent_label": "Guardrail Agent"},
    "store": {"agent_key": "store", "agent_name": "Store Agent", "agent_label": "Store Agent"},
    "memory": {"agent_key": "memory_curator", "agent_name": "Memory Curator Agent", "agent_label": "Memory Curator Agent"},
    "done": {"agent_key": "orchestrator", "agent_name": "Workflow Orchestrator", "agent_label": "Workflow Orchestrator"},
}


# ---------- 纯工具函数 ----------

def _utcnow() -> datetime:
    return datetime.utcnow()


def _hash_json(payload: dict | None) -> str | None:
    if payload is None:
        return None
    data = json.dumps(jsonable_encoder(payload), sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _agent_meta(step_key: str) -> dict[str, str]:
    return STEP_AGENT_META.get(step_key, STEP_AGENT_META["bootstrap"]).copy()


def _with_agent_meta(step_key: str, payload: dict | None = None) -> dict:
    data = payload.copy() if payload else {}
    data.update(_agent_meta(step_key))
    return data


def _resolve_gateway_tokens(result: GatewayCallResult | None) -> tuple[int | None, int | None]:
    usage = result.token_usage if result else None
    if not usage:
        return None, None
    prompt_tokens = usage.get("prompt_tokens") or usage.get("input_tokens")
    completion_tokens = usage.get("completion_tokens") or usage.get("output_tokens")
    return (
        int(prompt_tokens) if prompt_tokens is not None else None,
        int(completion_tokens) if completion_tokens is not None else None,
    )


def _next_step_key(step_key: str | None) -> str | None:
    if step_key not in STEP_ORDER:
        return STEP_SEQUENCE[0] if STEP_SEQUENCE else None
    for key in STEP_SEQUENCE:
        if STEP_ORDER[key] > STEP_ORDER[step_key]:
            return key
    return None


def _fixture_version_for_mode(provider_mode: str) -> str | None:
    # 延迟 import：避免在模块顶层形成循环依赖。直接走 ai_gateway_constants（常量的真实归属），
    # 不穿过 ai_gateway_service 的 re-export。
    from app.services.ai_gateway_constants import FIXTURE_VERSION

    return FIXTURE_VERSION if provider_mode == "smoke_fixture" else None


def _run_fixture_scenario(run) -> str | None:
    value = (run.input_payload or {}).get("fixture_scenario")
    return str(value) if value else None
