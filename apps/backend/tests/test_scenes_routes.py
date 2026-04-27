"""app/api/scenes.py 路由契约：覆盖 PATCH 的乐观锁 / 版本副作用 + 各 GET 的 404 路径。

`tests/test_acceptance_api_contracts.py` 已覆盖 GET /context；`test_story_version_branch_contracts.py`
覆盖 versions / restore happy；这里专门补：
- PATCH 在 expected_scene_version 不匹配时返回 409
- PATCH 只改非 draft_text 字段时不会刷新 scene_version
- PATCH 改 draft_text 时 scene_version + 1 且自动建 SceneVersion 行
- PATCH 改 draft_text 时不显式传 status 会自动回到 "draft"
- GET /context, /bundle, /versions 在 scene 不存在时统一 404
- POST /restore scene 存在但 version 不存在 → 404 "Scene version not found"
"""

from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import scenes as scenes_module
from app.api.scenes import router as scenes_router
from app.db.session import get_db


def _app():
    app = FastAPI()
    app.include_router(scenes_router)
    return app


def _scene_id() -> UUID:
    return UUID("11111111-1111-1111-1111-111111111111")


def _make_scene(*, scene_version=1, draft_text="原文"):
    """Pydantic SceneResponse 必填字段全部铺好。"""
    now = datetime.utcnow()
    return SimpleNamespace(
        id=_scene_id(),
        chapter_id=UUID("22222222-2222-2222-2222-222222222222"),
        scene_no=1,
        title="标题",
        pov_character_id=None,
        location_id=None,
        time_label=None,
        goal=None,
        conflict=None,
        outcome=None,
        must_include=None,
        must_avoid=None,
        status="draft",
        draft_text=draft_text,
        scene_version=scene_version,
        created_at=now,
        updated_at=now,
    )


class _RecordingDB:
    def __init__(self):
        self.commits = 0

    def add(self, _):
        pass

    def commit(self):
        self.commits += 1

    def refresh(self, _):
        pass


# ---------- PATCH /api/scenes/{id} ----------

def test_patch_scene_returns_404_when_missing(monkeypatch):
    monkeypatch.setattr(scenes_module, "get_scene_record", lambda db, sid: None)
    app = _app()
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).patch(
        f"/api/scenes/{_scene_id()}", json={"title": "新标题"}
    )
    assert response.status_code == 404


def test_patch_scene_returns_409_on_version_mismatch(monkeypatch):
    scene = _make_scene(scene_version=5)
    monkeypatch.setattr(scenes_module, "get_scene_record", lambda db, sid: scene)
    app = _app()
    app.dependency_overrides[get_db] = lambda: _RecordingDB()
    response = TestClient(app).patch(
        f"/api/scenes/{_scene_id()}",
        json={"title": "新标题", "expected_scene_version": 3},
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Scene version mismatch"}


def test_patch_scene_metadata_only_does_not_create_version(monkeypatch):
    scene = _make_scene(scene_version=2, draft_text="原文")
    created_versions = []
    monkeypatch.setattr(scenes_module, "get_scene_record", lambda db, sid: scene)
    monkeypatch.setattr(
        scenes_module, "create_scene_version",
        lambda db, **kwargs: created_versions.append(kwargs),
    )
    app = _app()
    app.dependency_overrides[get_db] = lambda: _RecordingDB()
    response = TestClient(app).patch(
        f"/api/scenes/{_scene_id()}", json={"title": "新标题"}
    )
    assert response.status_code == 200
    assert scene.title == "新标题"
    assert scene.scene_version == 2  # 未改动
    assert created_versions == []  # 没刷新版本


def test_patch_scene_draft_text_change_creates_version_and_resets_status(monkeypatch):
    scene = _make_scene(scene_version=2, draft_text="原文")
    scene.status = "completed"  # 提前设非 draft
    created_versions = []
    monkeypatch.setattr(scenes_module, "get_scene_record", lambda db, sid: scene)
    monkeypatch.setattr(
        scenes_module, "create_scene_version",
        lambda db, **kwargs: created_versions.append(kwargs) or SimpleNamespace(id="v"),
    )
    monkeypatch.setattr(scenes_module, "mark_scene_status", lambda s, st: setattr(s, "status", st))
    app = _app()
    app.dependency_overrides[get_db] = lambda: _RecordingDB()
    response = TestClient(app).patch(
        f"/api/scenes/{_scene_id()}",
        json={
            "draft_text": "新文",
            "version_source": "ai-write",
            "version_label": "ai-1",
        },
    )
    assert response.status_code == 200
    assert scene.draft_text == "新文"
    assert scene.scene_version == 3  # +1
    assert scene.status == "draft"  # 自动回到 draft
    assert len(created_versions) == 1
    assert created_versions[0]["source"] == "ai-write"
    assert created_versions[0]["label"] == "ai-1"


def test_patch_scene_draft_text_change_keeps_explicit_status(monkeypatch):
    scene = _make_scene(scene_version=1, draft_text="原文")
    scene.status = "completed"
    created_versions = []
    monkeypatch.setattr(scenes_module, "get_scene_record", lambda db, sid: scene)
    monkeypatch.setattr(
        scenes_module, "create_scene_version",
        lambda db, **kwargs: created_versions.append(kwargs) or SimpleNamespace(id="v"),
    )
    monkeypatch.setattr(scenes_module, "mark_scene_status", lambda s, st: setattr(s, "status", st))
    app = _app()
    app.dependency_overrides[get_db] = lambda: _RecordingDB()
    response = TestClient(app).patch(
        f"/api/scenes/{_scene_id()}",
        json={"draft_text": "新文", "status": "completed"},
    )
    assert response.status_code == 200
    # 显式传 status 时不会被 mark_scene_status 覆盖回 draft
    assert scene.status == "completed"
    assert scene.scene_version == 2


# ---------- GET /api/scenes/{id}/context|bundle|versions ----------

def test_get_scene_context_returns_404_when_missing(monkeypatch):
    monkeypatch.setattr(scenes_module, "get_scene_record", lambda db, sid: None)
    app = _app()
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).get(f"/api/scenes/{_scene_id()}/context")
    assert response.status_code == 404


def test_get_scene_bundle_returns_404_when_missing(monkeypatch):
    monkeypatch.setattr(scenes_module, "get_scene_record", lambda db, sid: None)
    app = _app()
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).get(f"/api/scenes/{_scene_id()}/bundle")
    assert response.status_code == 404


def test_get_scene_versions_returns_404_when_missing(monkeypatch):
    monkeypatch.setattr(scenes_module, "get_scene_record", lambda db, sid: None)
    app = _app()
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).get(f"/api/scenes/{_scene_id()}/versions")
    assert response.status_code == 404


# ---------- POST /api/scenes/{id}/versions/{vid}/restore ----------

def test_restore_version_returns_404_when_scene_missing(monkeypatch):
    monkeypatch.setattr(scenes_module, "get_scene_record", lambda db, sid: None)
    app = _app()
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).post(
        f"/api/scenes/{_scene_id()}/versions/22222222-2222-2222-2222-222222222222/restore"
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Scene not found"}


def test_restore_version_returns_404_when_version_missing(monkeypatch):
    scene = _make_scene()
    monkeypatch.setattr(scenes_module, "get_scene_record", lambda db, sid: scene)
    monkeypatch.setattr(scenes_module, "get_scene_version_record", lambda db, sid, vid: None)
    app = _app()
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).post(
        f"/api/scenes/{_scene_id()}/versions/22222222-2222-2222-2222-222222222222/restore"
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Scene version not found"}
