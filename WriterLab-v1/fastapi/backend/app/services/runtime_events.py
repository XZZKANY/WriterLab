from __future__ import annotations

import threading
from datetime import datetime
from typing import Any


_EVENT_LOCK = threading.Lock()
_EVENTS: list[dict[str, Any]] = []
_MAX_EVENTS = 500


def publish_runtime_event(payload: dict[str, Any]) -> None:
    event = {
        "event": payload.get("event", "runtime"),
        "run_id": payload.get("run_id"),
        "step": payload.get("step"),
        "provider": payload.get("provider"),
        "model": payload.get("model"),
        "source": payload.get("source", "workflow"),
        "queue_depth": payload.get("queue_depth", 0),
        "can_cancel": bool(payload.get("can_cancel", False)),
        "message": payload.get("message"),
        "created_at": datetime.utcnow().isoformat(),
    }
    with _EVENT_LOCK:
        _EVENTS.append(event)
        if len(_EVENTS) > _MAX_EVENTS:
            del _EVENTS[:-_MAX_EVENTS]


def get_runtime_events(after_index: int = 0) -> tuple[list[dict[str, Any]], int]:
    with _EVENT_LOCK:
        next_index = len(_EVENTS)
        if after_index < 0:
            after_index = 0
        return _EVENTS[after_index:next_index], next_index
