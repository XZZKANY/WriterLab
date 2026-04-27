"""POST /api/vn/export 与 POST /api/consistency/scan 路由契约。

vn 是无状态导出（输入 draft_text → 输出 dialogue lines + markdown + image prompts）；
consistency 调用 service 后包装 summary。
"""

from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import consistency as consistency_module
from app.api.consistency import router as consistency_router
from app.api.vn import router as vn_router
from app.db.session import get_db


def _app(*routers):
    app = FastAPI()
    for r in routers:
        app.include_router(r)
    return app


# ---------- POST /api/vn/export ----------

def test_vn_export_returns_dialogue_lines_and_image_prompts():
    response = TestClient(_app(vn_router)).post(
        "/api/vn/export",
        json={
            "draft_text": "Ava(smile): Welcome home.\nThe room glows with warm lantern light.",
            "scene_title": "Homecoming",
            "include_image_prompts": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Homecoming"
    assert len(body["lines"]) == 2
    assert body["lines"][0]["kind"] == "dialogue"
    assert body["lines"][0]["character"] == "Ava"
    assert body["lines"][0]["expression"] == "smile"
    assert body["lines"][1]["kind"] == "narration"
    assert "Homecoming" in body["image_prompts"][0]
    assert "markdown_script" in body


def test_vn_export_skips_image_prompts_when_flag_false():
    response = TestClient(_app(vn_router)).post(
        "/api/vn/export",
        json={
            "draft_text": "Ava: Hello.",
            "scene_title": "X",
            "include_image_prompts": False,
        },
    )
    assert response.status_code == 200
    assert response.json()["image_prompts"] == []


def test_vn_export_handles_empty_draft_text():
    response = TestClient(_app(vn_router)).post(
        "/api/vn/export",
        json={"draft_text": "", "scene_title": None, "include_image_prompts": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["lines"] == []
    assert body["image_prompts"] == []


# ---------- POST /api/consistency/scan ----------

def test_consistency_scan_returns_404_when_scene_missing(monkeypatch):
    monkeypatch.setattr(consistency_module, "get_scene_record", lambda db, sid: None)
    app = _app(consistency_router)
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).post(
        "/api/consistency/scan",
        json={
            "scene_id": "11111111-1111-1111-1111-111111111111",
            "draft_text": "正文",
        },
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Scene not found"}


def test_consistency_scan_returns_summary_with_no_issues(monkeypatch):
    monkeypatch.setattr(
        consistency_module, "get_scene_record",
        lambda db, sid: SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111")),
    )
    monkeypatch.setattr(
        consistency_module, "scan_scene_consistency",
        lambda db, scene, draft_text, workflow_run_id=None: [],
    )
    app = _app(consistency_router)
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).post(
        "/api/consistency/scan",
        json={
            "scene_id": "11111111-1111-1111-1111-111111111111",
            "draft_text": "正文",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["issues"] == []
    assert "未发现明显" in body["summary"]


def test_consistency_scan_returns_summary_with_issue_count(monkeypatch):
    monkeypatch.setattr(
        consistency_module, "get_scene_record",
        lambda db, sid: SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111")),
    )
    now = __import__("datetime").datetime.utcnow()
    fake_issue = SimpleNamespace(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        project_id=None,
        scene_id=UUID("11111111-1111-1111-1111-111111111111"),
        workflow_run_id=None,
        issue_type="must_include_missing",
        severity="medium",
        source="规则检查",
        message="缺少必写项：信封",
        evidence_json=None,
        fix_suggestion="把信封补回当前段落。",
        status="open",
        created_at=now,
        updated_at=now,
    )
    monkeypatch.setattr(
        consistency_module, "scan_scene_consistency",
        lambda db, scene, draft_text, workflow_run_id=None: [fake_issue, fake_issue],
    )
    app = _app(consistency_router)
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).post(
        "/api/consistency/scan",
        json={
            "scene_id": "11111111-1111-1111-1111-111111111111",
            "draft_text": "正文",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["issues"]) == 2
    assert "2 条" in body["summary"]
