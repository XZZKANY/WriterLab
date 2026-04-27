"""app/api/ai.py 路由契约：scene AI 三件套 + workflow 控制端点的 404 / 错误路径。

`tests/api/api_routes_suite.py` 已覆盖 workflow 编排的 happy 路径；这里专门补：
- analyze / write / revise 三个 endpoint 在 scene 不存在时 **不返回 4xx，而是 200 + success=False**
  （这是约定：scene-level AI 端点把所有错误都包成响应体，由前端统一显示）
- list_scene_analyses 透传 service 列表
- update_analysis_selection 在 analysis 不存在时返回 404
- get_workflow_run / cancel / resume / override 在 workflow 不存在时返回 404
"""

from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import ai as ai_module
from app.api.ai import router as ai_router
from app.db.session import get_db
from app.services.ai_errors import AIErrorType, AIServiceError


def _app():
    app = FastAPI()
    app.include_router(ai_router)
    return app


def _scene_id() -> UUID:
    return UUID("11111111-1111-1111-1111-111111111111")


def _workflow_id() -> UUID:
    return UUID("22222222-2222-2222-2222-222222222222")


def _analysis_id() -> UUID:
    return UUID("33333333-3333-3333-3333-333333333333")


# ---------- POST /api/ai/analyze-scene ----------

def test_analyze_scene_returns_success_false_when_scene_missing(monkeypatch):
    monkeypatch.setattr(ai_module, "get_scene_record", lambda db, sid: None)
    app = _app()
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).post(
        "/api/ai/analyze-scene", json={"scene_id": str(_scene_id())},
    )
    # 注意：是 200 OK + success=False，不是 404
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["message"] == "Scene not found"
    assert body["error_type"] == AIErrorType.VALIDATION
    assert body["run_id"] is None


def test_analyze_scene_returns_success_false_on_ai_service_error(monkeypatch):
    fake_scene = object()
    monkeypatch.setattr(ai_module, "get_scene_record", lambda db, sid: fake_scene)

    def boom(scene, db):
        raise AIServiceError(
            error_type=AIErrorType.MODEL_OUTPUT,
            message="upstream timeout",
            run_id=UUID("44444444-4444-4444-4444-444444444444"),
        )

    monkeypatch.setattr(ai_module, "analyze_scene", boom)
    app = _app()
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).post(
        "/api/ai/analyze-scene", json={"scene_id": str(_scene_id())},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["error_type"] == AIErrorType.MODEL_OUTPUT
    assert body["message"] == "upstream timeout"
    assert body["run_id"] == "44444444-4444-4444-4444-444444444444"


# ---------- POST /api/ai/write-scene ----------

def test_write_scene_returns_success_false_when_scene_missing(monkeypatch):
    monkeypatch.setattr(ai_module, "get_scene_record", lambda db, sid: None)
    app = _app()
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).post(
        "/api/ai/write-scene",
        json={"scene_id": str(_scene_id()), "length": "medium", "guidance": []},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["message"] == "Scene not found"


def test_write_scene_returns_success_false_on_ai_service_error(monkeypatch):
    monkeypatch.setattr(ai_module, "get_scene_record", lambda db, sid: object())

    def boom(scene, db, length, guidance, analysis_id):
        raise AIServiceError(
            error_type=AIErrorType.NETWORK,
            message="upstream offline",
            run_id=None,
        )

    monkeypatch.setattr(ai_module, "write_scene", boom)
    app = _app()
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).post(
        "/api/ai/write-scene", json={"scene_id": str(_scene_id())},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["error_type"] == AIErrorType.NETWORK


# ---------- POST /api/ai/revise-scene ----------

def test_revise_scene_returns_success_false_when_scene_missing(monkeypatch):
    monkeypatch.setattr(ai_module, "get_scene_record", lambda db, sid: None)
    app = _app()
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).post(
        "/api/ai/revise-scene",
        json={"scene_id": str(_scene_id()), "mode": "trim"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False


# ---------- GET /api/ai/scenes/{id}/analyses ----------

def test_list_scene_analyses_returns_empty_list_when_no_records(monkeypatch):
    monkeypatch.setattr(ai_module, "list_scene_analyses", lambda db, sid: [])
    app = _app()
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).get(f"/api/ai/scenes/{_scene_id()}/analyses")
    assert response.status_code == 200
    assert response.json() == []


# ---------- POST /api/ai/analyses/{id}/selection ----------

def test_update_analysis_selection_returns_404_when_missing(monkeypatch):
    monkeypatch.setattr(ai_module, "get_scene_analysis", lambda db, aid: None)
    app = _app()
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).post(
        f"/api/ai/analyses/{_analysis_id()}/selection",
        json={"selected_item_ids": []},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Analysis not found"}


# ---------- workflow control endpoints 404 paths ----------

def test_run_scene_workflow_returns_404_when_scene_missing(monkeypatch):
    monkeypatch.setattr(ai_module, "get_scene_record", lambda db, sid: None)
    app = _app()
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).post(
        "/api/ai/workflows/scene",
        json={"scene_id": str(_scene_id())},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Scene not found"}


def test_run_scene_workflow_sync_returns_404_when_scene_missing(monkeypatch):
    monkeypatch.setattr(ai_module, "get_scene_record", lambda db, sid: None)
    app = _app()
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).post(
        "/api/ai/workflows/scene/run-sync",
        json={"scene_id": str(_scene_id())},
    )
    assert response.status_code == 404


def test_get_scene_workflow_returns_404_when_missing(monkeypatch):
    monkeypatch.setattr(ai_module, "get_workflow_run", lambda db, wid: None)
    app = _app()
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).get(f"/api/ai/workflows/{_workflow_id()}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Workflow run not found"}


def test_resume_scene_workflow_returns_404_when_missing(monkeypatch):
    monkeypatch.setattr(ai_module, "get_workflow_run", lambda db, wid: None)
    app = _app()
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).post(
        f"/api/ai/workflows/{_workflow_id()}/resume",
        json={"idempotency_key": "k", "expected_step_version": 1},
    )
    assert response.status_code == 404


def test_resume_scene_workflow_returns_409_on_value_error(monkeypatch):
    monkeypatch.setattr(ai_module, "get_workflow_run", lambda db, wid: object())

    def raise_value_error(db, run, payload):
        raise ValueError("workflow already complete")

    monkeypatch.setattr(ai_module, "resume_workflow_run", raise_value_error)
    app = _app()
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).post(
        f"/api/ai/workflows/{_workflow_id()}/resume",
        json={"idempotency_key": "k", "expected_step_version": 1},
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "workflow already complete"}


def test_override_workflow_step_returns_404_when_missing(monkeypatch):
    monkeypatch.setattr(ai_module, "get_workflow_run", lambda db, wid: None)
    app = _app()
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).post(
        f"/api/ai/workflows/{_workflow_id()}/steps/plan/override",
        json={
            "idempotency_key": "k",
            "expected_step_version": 1,
            "derived_from_version": 0,
            "edited_reason": "test",
            "effective_output_snapshot": {},
        },
    )
    assert response.status_code == 404


def test_override_workflow_step_returns_409_on_value_error(monkeypatch):
    monkeypatch.setattr(ai_module, "get_workflow_run", lambda db, wid: object())

    def raise_value_error(db, *, run, step_key, payload):
        raise ValueError("invalid step")

    monkeypatch.setattr(ai_module, "override_workflow_step", raise_value_error)
    app = _app()
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).post(
        f"/api/ai/workflows/{_workflow_id()}/steps/plan/override",
        json={
            "idempotency_key": "k",
            "expected_step_version": 1,
            "derived_from_version": 0,
            "edited_reason": "test",
            "effective_output_snapshot": {},
        },
    )
    assert response.status_code == 409


def test_cancel_scene_workflow_returns_404_when_missing(monkeypatch):
    monkeypatch.setattr(ai_module, "get_workflow_run", lambda db, wid: None)
    app = _app()
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).post(f"/api/ai/workflows/{_workflow_id()}/cancel")
    assert response.status_code == 404
