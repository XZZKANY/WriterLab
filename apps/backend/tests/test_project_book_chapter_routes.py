"""项目层 3 个简单路由的契约测试：projects / books / chapters。

聚焦：HTTP 路径、参数解析（query string）、201/200 响应 shape、404 路径。
不验证 ORM 持久化（由 SQLAlchemy 自身覆盖），只验证路由层薄壳行为。
"""

from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import projects as projects_module
from app.api.projects import router as projects_router
from app.api.books import router as books_router
from app.api.chapters import router as chapters_router
from app.db.session import get_db


# ---------- 辅助 fake DB ----------

class _RecordingDB:
    """记录 add/commit/refresh；refresh 时给 ORM 实例填上 id + 时间戳。"""

    def __init__(self, *, fixed_id=None):
        self._fixed_id = fixed_id or UUID("11111111-1111-1111-1111-111111111111")
        self.added: list = []
        self.commits = 0

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        if not getattr(obj, "id", None):
            obj.id = self._fixed_id
        now = datetime.utcnow()
        if not getattr(obj, "created_at", None):
            obj.created_at = now
        if not getattr(obj, "updated_at", None):
            obj.updated_at = now


def _app(*routers):
    app = FastAPI()
    for r in routers:
        app.include_router(r)
    return app


# ---------- POST /api/projects ----------

def test_create_project_returns_response_shape():
    db = _RecordingDB()
    app = _app(projects_router)
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    response = client.post(
        "/api/projects",
        json={
            "name": "测试项目",
            "description": "测试描述",
            "genre": "悬疑",
            "default_language": "zh-CN",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "测试项目"
    assert body["description"] == "测试描述"
    assert body["genre"] == "悬疑"
    assert body["default_language"] == "zh-CN"
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body
    # 副作用：1 个 add + 1 个 commit
    assert len(db.added) == 1
    assert db.commits == 1


def test_create_project_accepts_minimum_payload():
    db = _RecordingDB()
    app = _app(projects_router)
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)
    response = client.post("/api/projects", json={"name": "x"})
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "x"


# ---------- GET /api/projects ----------

def test_list_projects_returns_query_results(monkeypatch):
    project = SimpleNamespace(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        name="P",
        description=None,
        genre=None,
        default_language="zh-CN",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    monkeypatch.setattr(projects_module, "list_projects_query", lambda db: [project])
    app = _app(projects_router)
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).get("/api/projects")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["name"] == "P"


# ---------- GET /api/projects/{id}/overview ----------

def test_get_project_overview_returns_404_when_missing(monkeypatch):
    monkeypatch.setattr(projects_module, "get_project_overview_query", lambda db, project_id: None)
    app = _app(projects_router)
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).get(
        "/api/projects/11111111-1111-1111-1111-111111111111/overview"
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}


def test_get_project_overview_returns_payload_when_found(monkeypatch):
    project_id = UUID("11111111-1111-1111-1111-111111111111")
    book_id = UUID("22222222-2222-2222-2222-222222222222")
    chapter_id = UUID("33333333-3333-3333-3333-333333333333")
    scene_id = UUID("44444444-4444-4444-4444-444444444444")

    project = SimpleNamespace(
        id=project_id, name="P", description=None, genre=None,
        default_language="zh-CN",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    book = SimpleNamespace(
        id=book_id, project_id=project_id, title="B", summary=None, status="draft",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    chapter = SimpleNamespace(
        id=chapter_id, book_id=book_id, chapter_no=1, title="C", summary=None, status="draft",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    scene = SimpleNamespace(
        id=scene_id, chapter_id=chapter_id, scene_no=1, title="S",
        pov_character_id=None, location_id=None, time_label=None,
        goal=None, conflict=None, outcome=None,
        must_include=None, must_avoid=None,
        status="draft", draft_text=None, scene_version=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    payload = {
        "project": project,
        "books": [book],
        "chapters_by_book": {str(book_id): [chapter]},
        "scenes_by_chapter": {str(chapter_id): [scene]},
        "counts": {"books": 1, "chapters": 1, "scenes": 1},
    }
    monkeypatch.setattr(projects_module, "get_project_overview_query", lambda db, pid: payload)

    app = _app(projects_router)
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).get(f"/api/projects/{project_id}/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["project"]["id"] == str(project_id)
    assert body["counts"] == {"books": 1, "chapters": 1, "scenes": 1}


# ---------- DELETE /api/projects/{id} ----------

def test_delete_project_returns_404_when_missing(monkeypatch):
    monkeypatch.setattr(projects_module, "delete_project_query", lambda db, project_id: False)
    app = _app(projects_router)
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).delete(
        "/api/projects/11111111-1111-1111-1111-111111111111"
    )
    assert response.status_code == 404


def test_delete_project_returns_deleted_true_when_succeeds(monkeypatch):
    project_id = UUID("11111111-1111-1111-1111-111111111111")
    monkeypatch.setattr(projects_module, "delete_project_query", lambda db, pid: True)
    app = _app(projects_router)
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).delete(f"/api/projects/{project_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["deleted"] is True
    assert body["project_id"] == str(project_id)


# ---------- POST/GET /api/books ----------

def test_create_book_returns_response_shape():
    db = _RecordingDB()
    app = _app(books_router)
    app.dependency_overrides[get_db] = lambda: db
    project_id = UUID("11111111-1111-1111-1111-111111111111")
    response = TestClient(app).post(
        "/api/books",
        json={
            "project_id": str(project_id),
            "title": "第一卷",
            "summary": "简介",
            "status": "draft",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["title"] == "第一卷"
    assert body["status"] == "draft"
    assert body["project_id"] == str(project_id)


def test_list_books_filters_by_project_query_param(monkeypatch):
    from app.api import books as books_module

    captured = {}

    def fake_list_books(db, project_id):
        captured["project_id"] = project_id
        return [
            SimpleNamespace(
                id=UUID("22222222-2222-2222-2222-222222222222"),
                project_id=project_id,
                title="B",
                summary=None,
                status="draft",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        ]

    monkeypatch.setattr(books_module, "list_books_by_project", fake_list_books)
    app = _app(books_router)
    app.dependency_overrides[get_db] = lambda: object()
    project_id = UUID("11111111-1111-1111-1111-111111111111")
    response = TestClient(app).get(f"/api/books?project_id={project_id}")
    assert response.status_code == 200
    assert len(response.json()) == 1
    # query 参数被正确解析为 UUID
    assert captured["project_id"] == project_id


def test_list_books_rejects_invalid_uuid():
    app = _app(books_router)
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).get("/api/books?project_id=not-a-uuid")
    assert response.status_code == 422


# ---------- POST/GET /api/chapters ----------

def test_create_chapter_returns_response_shape():
    db = _RecordingDB()
    app = _app(chapters_router)
    app.dependency_overrides[get_db] = lambda: db
    book_id = UUID("11111111-1111-1111-1111-111111111111")
    response = TestClient(app).post(
        "/api/chapters",
        json={
            "book_id": str(book_id),
            "chapter_no": 1,
            "title": "第 1 章",
            "summary": "简介",
            "status": "draft",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["title"] == "第 1 章"
    assert body["chapter_no"] == 1
    assert body["status"] == "draft"


def test_list_chapters_filters_by_book_query_param(monkeypatch):
    from app.api import chapters as chapters_module

    captured = {}

    def fake_list_chapters(db, book_id):
        captured["book_id"] = book_id
        return [
            SimpleNamespace(
                id=UUID("22222222-2222-2222-2222-222222222222"),
                book_id=book_id,
                chapter_no=1,
                title="C",
                summary=None,
                status="draft",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        ]

    monkeypatch.setattr(chapters_module, "list_chapters_by_book", fake_list_chapters)
    app = _app(chapters_router)
    app.dependency_overrides[get_db] = lambda: object()
    book_id = UUID("11111111-1111-1111-1111-111111111111")
    response = TestClient(app).get(f"/api/chapters?book_id={book_id}")
    assert response.status_code == 200
    assert captured["book_id"] == book_id
