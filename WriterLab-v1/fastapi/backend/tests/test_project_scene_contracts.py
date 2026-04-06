from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.projects import router as projects_router
from app.api.scenes import router as scenes_router
from app.db.session import get_db


def test_project_overview_returns_books_chapters_scenes_summary(monkeypatch):
    app = FastAPI()
    app.include_router(projects_router)

    project_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    book_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    chapter_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    scene_id = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
    now = datetime.utcnow()

    fake_project = SimpleNamespace(
        id=project_id,
        name="\u9879\u76ee\u6982\u89c8\u70df\u96fe\u6d4b\u8bd5",
        description="\u7528\u4e8e\u9501\u5b9a\u9879\u76ee\u6982\u89c8\u63a5\u53e3\u5951\u7ea6",
        genre="\u60ac\u7591",
        default_language="zh-CN",
        created_at=now,
        updated_at=now,
    )
    fake_book = SimpleNamespace(
        id=book_id,
        project_id=project_id,
        title="\u7b2c\u4e00\u5377",
        summary="\u9879\u76ee\u6982\u89c8\u4e2d\u7684\u56fe\u4e66",
        status="active",
        created_at=now,
        updated_at=now,
    )
    fake_chapter = SimpleNamespace(
        id=chapter_id,
        book_id=book_id,
        chapter_no=1,
        title="\u7b2c\u4e00\u7ae0",
        summary="\u9879\u76ee\u6982\u89c8\u4e2d\u7684\u7ae0\u8282",
        status="active",
        created_at=now,
        updated_at=now,
    )
    fake_scene = SimpleNamespace(
        id=scene_id,
        chapter_id=chapter_id,
        scene_no=1,
        title="\u7b2c\u4e00\u573a",
        pov_character_id=None,
        location_id=None,
        time_label=None,
        goal=None,
        conflict=None,
        outcome=None,
        must_include=None,
        must_avoid=None,
        status="draft",
        draft_text=None,
        scene_version=1,
        created_at=now,
        updated_at=now,
    )

    class _FakeQuery:
        def __init__(self, result):
            self._result = result

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            if self._result is None:
                return []
            return [self._result]

        def first(self):
            return self._result

    class _FakeDB:
        def query(self, model):
            model_name = getattr(model, "__name__", "")
            if model_name == "Project":
                return _FakeQuery(fake_project)
            if model_name == "Book":
                return _FakeQuery(fake_book)
            if model_name == "Chapter":
                return _FakeQuery(fake_chapter)
            if model_name == "Scene":
                return _FakeQuery(fake_scene)
            return _FakeQuery(None)

    app.dependency_overrides[get_db] = lambda: _FakeDB()
    client = TestClient(app)
    response = client.get(f"/api/projects/{project_id}/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["id"] == str(project_id)
    assert payload["project"]["name"] == "\u9879\u76ee\u6982\u89c8\u70df\u96fe\u6d4b\u8bd5"
    assert payload["books"][0]["id"] == str(book_id)
    assert payload["books"][0]["title"] == "\u7b2c\u4e00\u5377"
    assert payload["chapters_by_book"][str(book_id)][0]["id"] == str(chapter_id)
    assert payload["chapters_by_book"][str(book_id)][0]["chapter_no"] == 1
    assert payload["scenes_by_chapter"][str(chapter_id)][0]["id"] == str(scene_id)
    assert payload["scenes_by_chapter"][str(chapter_id)][0]["scene_no"] == 1
    assert payload["counts"] == {"books": 1, "chapters": 1, "scenes": 1}


def test_delete_missing_project_returns_404(monkeypatch):
    app = FastAPI()
    app.include_router(projects_router)

    missing_project_id = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")

    class _FakeDB:
        pass

    app.dependency_overrides[get_db] = lambda: _FakeDB()
    monkeypatch.setattr("app.api.projects.delete_project_query", lambda db, project_id: False)

    client = TestClient(app)
    response = client.delete(f"/api/projects/{missing_project_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}


def test_scene_update_rejects_stale_scene_version(monkeypatch):
    app = FastAPI()
    app.include_router(scenes_router)

    scene_id = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    fake_scene = SimpleNamespace(
        id=scene_id,
        chapter_id=UUID("11111111-1111-1111-1111-111111111111"),
        scene_no=1,
        title="\u7248\u672c\u51b2\u7a81\u573a\u666f",
        pov_character_id=None,
        location_id=None,
        time_label=None,
        goal=None,
        conflict=None,
        outcome=None,
        must_include=None,
        must_avoid=None,
        status="draft",
        draft_text="\u521d\u59cb\u6587\u672c",
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
            raise AssertionError("\u7248\u672c\u51b2\u7a81\u65f6\u4e0d\u5e94\u63d0\u4ea4\u6570\u636e\u5e93")

        def refresh(self, obj):
            raise AssertionError("\u7248\u672c\u51b2\u7a81\u65f6\u4e0d\u5e94\u5237\u65b0\u5bf9\u8c61")

    app.dependency_overrides[get_db] = lambda: _FakeDB()
    monkeypatch.setattr("app.api.scenes.create_scene_version", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.api.scenes.mark_scene_status", lambda *args, **kwargs: None)

    client = TestClient(app)
    response = client.patch(
        f"/api/scenes/{scene_id}",
        json={
            "draft_text": "\u66f4\u65b0\u540e\u7684\u6587\u672c",
            "expected_scene_version": 1,
            "version_source": "manual",
            "version_label": "\u624b\u52a8\u66f4\u65b0",
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Scene version mismatch"}
