from __future__ import annotations

import os
import threading
from copy import deepcopy


_VERSION = os.getenv("WRITERLAB_VERSION", "writerlab-v1")
_LOCK = threading.Lock()
_DEFAULT_STATUS = {
    "version": _VERSION,
    "schema_ready": False,
    "recovery_scan_completed": False,
    "recovered_runs": 0,
    "workflow_runner_started": False,
    "last_startup_stage": "not_started",
    "startup_error": None,
}
_RUNTIME_STATUS = deepcopy(_DEFAULT_STATUS)


def reset_runtime_status() -> None:
    with _LOCK:
        _RUNTIME_STATUS.clear()
        _RUNTIME_STATUS.update(deepcopy(_DEFAULT_STATUS))


def mark_startup_stage(stage: str) -> None:
    with _LOCK:
        _RUNTIME_STATUS["last_startup_stage"] = stage
        if stage == "ready":
            _RUNTIME_STATUS["startup_error"] = None


def mark_schema_ready(is_ready: bool = True) -> None:
    with _LOCK:
        _RUNTIME_STATUS["schema_ready"] = bool(is_ready)


def mark_recovery_scan_completed(recovered_runs: int) -> None:
    with _LOCK:
        _RUNTIME_STATUS["recovery_scan_completed"] = True
        _RUNTIME_STATUS["recovered_runs"] = max(int(recovered_runs), 0)


def mark_workflow_runner_started(started: bool = True) -> None:
    with _LOCK:
        _RUNTIME_STATUS["workflow_runner_started"] = bool(started)


def mark_startup_error(stage: str, message: str) -> None:
    with _LOCK:
        _RUNTIME_STATUS["last_startup_stage"] = stage
        _RUNTIME_STATUS["startup_error"] = message


def get_runtime_status_snapshot() -> dict:
    with _LOCK:
        return deepcopy(_RUNTIME_STATUS)
