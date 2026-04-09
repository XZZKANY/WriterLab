from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.branches import router as branches_router
from app.api.scenes import router as scenes_router
from app.db.session import get_db


def _build_scene_version(**overrides):
    base = {
        "id": UUID("11111111-1111-1111-1111-111111111111"),
        "scene_id": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        "content": "版本正文",
        "source": "manual",
        "label": "手动保存",
        "created_at": datetime(2026, 4, 7, 22, 0, 0),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _build_branch(**overrides):
    base = {
        "id": UUID("22222222-2222-2222-2222-222222222222"),
        "project_id": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        "name": "真相支线",
        "description": "分支描述",
        "parent_branch_id": None,
        "source_scene_id": UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        "source_version_id": UUID("33333333-3333-3333-3333-333333333333"),
        "latest_version_id": UUID("44444444-4444-4444-4444-444444444444"),
        "status": "active",
        "metadata_json": {"tone": "tense"},
        "created_at": datetime(2026, 4, 7, 22, 0, 0),
        "updated_at": datetime(2026, 4, 7, 22, 5, 0),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class _FakeQuery:
    def __init__(self, first_result=None, all_results=None):
        self._first_result = first_result
        self._all_results = all_results

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._first_result

    def all(self):
        return list(self._all_results or [])


class _FakeDB:
    def __init__(self, *, first_map=None, all_map=None):
        self.first_map = first_map or {}
        self.all_map = all_map or {}

    def query(self, model):
        name = getattr(model, "__name__", "")
        return _FakeQuery(first_result=self.first_map.get(name), all_results=self.all_map.get(name))


def test_get_scene_versions_returns_latest_first(monkeypatch):
    app = FastAPI()
    app.include_router(scenes_router)

    scene_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    latest = _build_scene_version(id=UUID("55555555-5555-5555-5555-555555555555"), scene_id=scene_id, label="最新版本")
    previous = _build_scene_version(id=UUID("66666666-6666-6666-6666-666666666666"), scene_id=scene_id, label="较早版本")
    fake_scene = SimpleNamespace(id=scene_id)

    app.dependency_overrides[get_db] = lambda: _FakeDB()
    monkeypatch.setattr("app.api.scenes.get_scene_record", lambda db, target_scene_id: fake_scene if target_scene_id == scene_id else None)
    monkeypatch.setattr("app.api.scenes.list_scene_version_records", lambda db, target_scene_id: [latest, previous] if target_scene_id == scene_id else [])

    response = TestClient(app).get(f"/api/scenes/{scene_id}/versions")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(latest.id), str(previous.id)]


def test_restore_scene_version_returns_current_text(monkeypatch):
    app = FastAPI()
    app.include_router(scenes_router)

    scene_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    version_id = UUID("77777777-7777-7777-7777-777777777777")
    fake_scene = SimpleNamespace(id=scene_id, draft_text="恢复前正文")
    fake_version = _build_scene_version(id=version_id, scene_id=scene_id, content="恢复后正文", source="restore", label="恢复版本")

    def _fake_restore_scene_version(db, scene, version):
        scene.draft_text = version.content
        return version

    app.dependency_overrides[get_db] = lambda: _FakeDB()
    monkeypatch.setattr("app.api.scenes.get_scene_record", lambda db, target_scene_id: fake_scene if target_scene_id == scene_id else None)
    monkeypatch.setattr("app.api.scenes.get_scene_version_record", lambda db, target_scene_id, target_version_id: fake_version if target_scene_id == scene_id and target_version_id == version_id else None)
    monkeypatch.setattr("app.api.scenes.restore_scene_version", _fake_restore_scene_version)

    response = TestClient(app).post(f"/api/scenes/{scene_id}/versions/{version_id}/restore")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "version_id": str(version_id),
        "restored_to_scene_id": str(scene_id),
        "current_text": "恢复后正文",
    }


def test_list_branches_returns_serialized_payload(monkeypatch):
    app = FastAPI()
    app.include_router(branches_router)

    project_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    chapter_id = UUID("88888888-8888-8888-8888-888888888888")
    branch = _build_branch(project_id=project_id)
    fake_project = SimpleNamespace(id=project_id)

    app.dependency_overrides[get_db] = lambda: _FakeDB(first_map={"Project": fake_project})
    monkeypatch.setattr("app.api.branches.list_story_branches", lambda db, project_id=None, source_scene_id=None: [branch])
    monkeypatch.setattr("app.api.branches.get_branch_source_chapter_id", lambda db, row: chapter_id)
    monkeypatch.setattr("app.api.branches._version_label", lambda db, version_id: "最新版本标签" if version_id == branch.latest_version_id else "来源版本标签")

    response = TestClient(app).get(f"/api/branches?project_id={project_id}")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == str(branch.id)
    assert payload[0]["project_id"] == str(project_id)
    assert payload[0]["source_chapter_id"] == str(chapter_id)
    assert payload[0]["latest_version_label"] == "最新版本标签"


def test_get_branch_diff_returns_diff_payload(monkeypatch):
    app = FastAPI()
    app.include_router(branches_router)

    chapter_id = UUID("88888888-8888-8888-8888-888888888888")
    branch = _build_branch()
    diff_rows = [{"type": "context", "text": "同一行"}, {"type": "add", "text": "新增行"}]

    app.dependency_overrides[get_db] = lambda: _FakeDB(first_map={"StoryBranch": branch})
    monkeypatch.setattr("app.api.branches.get_branch_diff", lambda db, row: ("原文", "支线正文", diff_rows))
    monkeypatch.setattr("app.api.branches.get_branch_source_chapter_id", lambda db, row: chapter_id)
    monkeypatch.setattr("app.api.branches._version_label", lambda db, version_id: "版本标签")

    response = TestClient(app).get(f"/api/branches/{branch.id}/diff")

    assert response.status_code == 200
    assert response.json()["branch_id"] == str(branch.id)
    assert response.json()["source_chapter_id"] == str(chapter_id)
    assert response.json()["diff_rows"] == diff_rows


def test_adopt_branch_returns_current_text(monkeypatch):
    app = FastAPI()
    app.include_router(branches_router)

    branch = _build_branch()
    scene_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    version_id = UUID("99999999-9999-9999-9999-999999999999")
    adopted_scene = SimpleNamespace(id=scene_id, draft_text="采纳后的正文")
    adopted_version = SimpleNamespace(id=version_id)

    app.dependency_overrides[get_db] = lambda: _FakeDB(first_map={"StoryBranch": branch})
    monkeypatch.setattr("app.api.branches.adopt_story_branch", lambda db, row: (adopted_scene, adopted_version))

    response = TestClient(app).post(f"/api/branches/{branch.id}/adopt")

    assert response.status_code == 200
    assert response.json()["branch_id"] == str(branch.id)
    assert response.json()["scene_id"] == str(scene_id)
    assert response.json()["version_id"] == str(version_id)
    assert response.json()["adopted_version_id"] == str(version_id)
    assert response.json()["current_text"] == "采纳后的正文"
