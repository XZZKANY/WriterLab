from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.projects import router as projects_router
from app.api.scenes import router as scenes_router
from app.db.session import get_db


def test_project_overview_endpoint_returns_dashboard_contract(monkeypatch):
    app = FastAPI()
    app.include_router(projects_router)

    project_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    now = datetime.utcnow()
    fake_project = SimpleNamespace(
        id=project_id,
        name="项目概览烟雾测试",
        description="用于锁定项目概览接口契约",
        genre="悬疑",
        default_language="zh-CN",
        created_at=now,
        updated_at=now,
    )

    class _FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return fake_project

    class _FakeDB:
        def query(self, model):
            return _FakeQuery()

    app.dependency_overrides[get_db] = lambda: _FakeDB()

    client = TestClient(app)
    response = client.get(f"/api/projects/{project_id}/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == str(project_id)
    assert payload["project_name"] == "项目概览烟雾测试"
    assert payload["default_language"] == "zh-CN"


def test_delete_missing_project_returns_404(monkeypatch):
    app = FastAPI()
    app.include_router(projects_router)

    missing_project_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

    class _FakeDB:
        pass

    app.dependency_overrides[get_db] = lambda: _FakeDB()
    monkeypatch.setattr("app.api.projects.delete_project_query", lambda db, project_id: False)

    client = TestClient(app)
    response = client.delete(f"/api/projects/{missing_project_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_update_scene_version_mismatch_returns_409(monkeypatch):
    app = FastAPI()
    app.include_router(scenes_router)

    scene_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    fake_scene = SimpleNamespace(
        id=scene_id,
        chapter_id=UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
        scene_no=1,
        title="版本冲突场景",
        pov_character_id=None,
        location_id=None,
        time_label=None,
        goal=None,
        conflict=None,
        outcome=None,
        must_include=None,
        must_avoid=None,
        status="draft",
        draft_text="初始文本",
        scene_version=2,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    class _FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return fake_scene

    class _FakeDB:
        def query(self, model):
            return _FakeQuery()

        def commit(self):
            raise AssertionError("版本冲突时不应提交数据库")

        def refresh(self, obj):
            raise AssertionError("版本冲突时不应刷新对象")

    app.dependency_overrides[get_db] = lambda: _FakeDB()
    monkeypatch.setattr("app.api.scenes.create_scene_version", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.api.scenes.mark_scene_status", lambda *args, **kwargs: None)

    client = TestClient(app)
    response = client.patch(
        f"/api/scenes/{scene_id}",
        json={
            "draft_text": "更新后的文本",
            "expected_scene_version": 1,
            "version_source": "manual",
            "version_label": "手动更新",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Scene version mismatch"
