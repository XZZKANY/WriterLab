"""build_health_payload 与 GET /api/health 的契约测试。

build_health_payload 组装多个 service 的返回值；用 monkeypatch 替换上游
service 函数，验证：status 字段、各 ready / loaded 标志位、degraded 切换、
版本号 fallback 等。
"""

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import health as health_module
from app.api.health import build_health_payload, router as health_router
from app.db.session import get_db


def _stub_provider_runtime(ok=True):
    return SimpleNamespace(ok=ok)


def _stub_provider_matrix(rules=None):
    # 区分 None（默认占位）与 []（显式空，用于测 provider_matrix_loaded=False 分支）
    if rules is None:
        rules = [SimpleNamespace(step="write")]
    return SimpleNamespace(rules=rules)


def _patch_services(monkeypatch, *, runtime_status, vector_status, matrix_rules=None, runtime_ok=True):
    monkeypatch.setattr(health_module, "get_runtime_status_snapshot", lambda: runtime_status)
    monkeypatch.setattr(health_module, "vector_backend_status", lambda db: vector_status)
    monkeypatch.setattr(health_module, "get_provider_matrix", lambda: _stub_provider_matrix(matrix_rules))
    monkeypatch.setattr(health_module, "get_provider_runtime_state", lambda db: object())
    monkeypatch.setattr(health_module, "summarize_provider_runtime_state", lambda state: _stub_provider_runtime(ok=runtime_ok))


# ---------- build_health_payload ----------

def test_build_health_payload_returns_ok_when_all_green(monkeypatch):
    _patch_services(
        monkeypatch,
        runtime_status={
            "schema_ready": True,
            "workflow_runner_started": True,
            "recovery_scan_completed": True,
            "version": "writerlab-v1",
            "last_startup_stage": "ready",
            "startup_error": None,
            "recovered_runs": 0,
        },
        vector_status={"pgvector_ready": True},
    )
    payload = build_health_payload(db=object())
    assert payload["status"] == "ok"
    assert payload["service"] == "writerlab-backend"
    assert payload["schema_ready"] is True
    assert payload["workflow_runner_started"] is True
    assert payload["recovery_scan_completed"] is True
    assert payload["pgvector_ready"] is True
    assert payload["provider_matrix_loaded"] is True
    assert payload["provider_runtime_ready"] is True
    assert payload["version"] == "writerlab-v1"
    assert payload["last_startup_stage"] == "ready"
    assert payload["startup_error"] is None
    assert payload["recovered_runs"] == 0


def test_build_health_payload_returns_degraded_when_startup_error_present(monkeypatch):
    _patch_services(
        monkeypatch,
        runtime_status={
            "schema_ready": False,
            "startup_error": "alembic migration failed",
            "last_startup_stage": "schema_validation",
        },
        vector_status={"pgvector_ready": False},
    )
    payload = build_health_payload(db=object())
    assert payload["status"] == "degraded"
    assert payload["startup_error"] == "alembic migration failed"
    assert payload["last_startup_stage"] == "schema_validation"
    assert payload["schema_ready"] is False
    assert payload["pgvector_ready"] is False


def test_build_health_payload_provider_matrix_loaded_false_when_no_rules(monkeypatch):
    _patch_services(
        monkeypatch,
        runtime_status={"schema_ready": True},
        vector_status={"pgvector_ready": True},
        matrix_rules=[],  # 空 rule 列表
    )
    payload = build_health_payload(db=object())
    assert payload["provider_matrix_loaded"] is False


def test_build_health_payload_provider_runtime_ready_false_when_summary_not_ok(monkeypatch):
    _patch_services(
        monkeypatch,
        runtime_status={"schema_ready": True},
        vector_status={"pgvector_ready": True},
        runtime_ok=False,
    )
    payload = build_health_payload(db=object())
    assert payload["provider_runtime_ready"] is False


def test_build_health_payload_uses_default_version_when_missing(monkeypatch):
    _patch_services(
        monkeypatch,
        runtime_status={},  # 完全空
        vector_status={"pgvector_ready": False},
    )
    payload = build_health_payload(db=object())
    assert payload["version"] == "writerlab-v1"
    assert payload["last_startup_stage"] == "unknown"
    assert payload["recovered_runs"] == 0
    assert payload["schema_ready"] is False


def test_build_health_payload_clamps_recovered_runs_to_int(monkeypatch):
    _patch_services(
        monkeypatch,
        runtime_status={"recovered_runs": "5"},  # 字符串
        vector_status={"pgvector_ready": True},
    )
    payload = build_health_payload(db=object())
    assert payload["recovered_runs"] == 5


# ---------- GET /api/health（路由级契约） ----------

def test_health_route_returns_200_with_known_fields(monkeypatch):
    _patch_services(
        monkeypatch,
        runtime_status={"schema_ready": True, "version": "writerlab-v1"},
        vector_status={"pgvector_ready": True},
    )

    app = FastAPI()
    app.include_router(health_router)
    app.dependency_overrides[get_db] = lambda: object()

    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    # 关键字段全部出现
    for key in [
        "status",
        "service",
        "schema_ready",
        "workflow_runner_started",
        "recovery_scan_completed",
        "pgvector_ready",
        "provider_matrix_loaded",
        "provider_runtime_ready",
        "version",
        "last_startup_stage",
        "recovered_runs",
    ]:
        assert key in body, f"GET /api/health 响应缺少字段: {key}"
    assert body["service"] == "writerlab-backend"
