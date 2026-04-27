"""app/api/knowledge.py 路由契约：7 个 endpoint 的 404 路径与 response shape。

`tests/api/api_routes_suite.py` 已覆盖 search 的 happy 路径与 confirm 的成功路径；
这里专门补：
- POST /documents / /retrieve / /reindex / GET /style-memories / POST /style-memories
  在 project 不存在时统一返回 404
- search 在 project 不存在时返回 404
- POST /style-memories/{id}/confirm 在 memory 不存在时返回 404
- 各 endpoint 的 response shape（透传 service 返回值）
"""

from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import knowledge as knowledge_module
from app.api.knowledge import router as knowledge_router
from app.db.session import get_db


# ---------- helpers ----------

class _ProjectFoundQuery:
    """db.query(Project).filter(...).first() → 给定的 fake project。"""

    def __init__(self, value):
        self._value = value

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._value


class _ProjectFoundDB:
    """所有 query 都返回同一个 project（fake 占位）。"""

    def __init__(self, value):
        self._value = value

    def query(self, model):
        return _ProjectFoundQuery(self._value)


class _ProjectMissingDB:
    def query(self, model):
        return _ProjectFoundQuery(None)


def _app(*routers):
    app = FastAPI()
    for r in routers:
        app.include_router(r)
    return app


def _project_id() -> UUID:
    return UUID("11111111-1111-1111-1111-111111111111")


# ---------- POST /api/knowledge/documents ----------

def test_create_document_returns_404_when_project_missing():
    app = _app(knowledge_router)
    app.dependency_overrides[get_db] = lambda: _ProjectMissingDB()
    response = TestClient(app).post(
        "/api/knowledge/documents",
        json={
            "project_id": str(_project_id()),
            "title": "T",
            "type": "lore",
            "raw_content": "正文",
        },
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}


def test_create_document_returns_response_shape(monkeypatch):
    pid = _project_id()
    doc_id = UUID("22222222-2222-2222-2222-222222222222")
    now = datetime.utcnow()
    fake_doc = SimpleNamespace(
        id=doc_id,
        project_id=pid,
        title="T",
        type="lore",
        summary=None,
        source=None,
        status="ready",
        chunk_count=3,
        created_at=now,
        updated_at=now,
    )
    monkeypatch.setattr(
        knowledge_module, "create_knowledge_document",
        lambda db, **kwargs: fake_doc,
    )
    app = _app(knowledge_router)
    app.dependency_overrides[get_db] = lambda: _ProjectFoundDB(SimpleNamespace(id=pid))
    response = TestClient(app).post(
        "/api/knowledge/documents",
        json={"project_id": str(pid), "title": "T", "raw_content": "正文"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(doc_id)
    assert body["title"] == "T"
    assert body["chunk_count"] == 3


# ---------- POST /api/knowledge/retrieve ----------

def test_retrieve_returns_404_when_project_missing():
    app = _app(knowledge_router)
    app.dependency_overrides[get_db] = lambda: _ProjectMissingDB()
    response = TestClient(app).post(
        "/api/knowledge/retrieve",
        json={"project_id": str(_project_id()), "query": "q"},
    )
    assert response.status_code == 404


def test_retrieve_returns_query_and_hits(monkeypatch):
    pid = _project_id()
    monkeypatch.setattr(
        knowledge_module, "retrieve_knowledge",
        lambda db, **kwargs: [],
    )
    app = _app(knowledge_router)
    app.dependency_overrides[get_db] = lambda: _ProjectFoundDB(SimpleNamespace(id=pid))
    response = TestClient(app).post(
        "/api/knowledge/retrieve",
        json={"project_id": str(pid), "query": "dragon", "top_k": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "dragon"
    assert body["hits"] == []


# ---------- GET /api/knowledge/search ----------

def test_search_returns_404_when_project_missing():
    app = _app(knowledge_router)
    app.dependency_overrides[get_db] = lambda: _ProjectMissingDB()
    response = TestClient(app).get(
        f"/api/knowledge/search?project_id={_project_id()}&query=q"
    )
    assert response.status_code == 404


def test_search_clamps_top_k_within_1_and_10(monkeypatch):
    pid = _project_id()
    captured = {}

    def fake_retrieve(db, *, project_id, query, top_k, source_kinds):
        captured["top_k"] = top_k
        return [], {"mode": "fallback", "reason": "ok", "pgvector_ready": False}

    monkeypatch.setattr(knowledge_module, "retrieve_knowledge_with_status", fake_retrieve)
    app = _app(knowledge_router)
    app.dependency_overrides[get_db] = lambda: _ProjectFoundDB(SimpleNamespace(id=pid))
    client = TestClient(app)

    # top_k 上限 10
    client.get(f"/api/knowledge/search?project_id={pid}&query=q&top_k=99")
    assert captured["top_k"] == 10

    # top_k 下限 1
    client.get(f"/api/knowledge/search?project_id={pid}&query=q&top_k=0")
    assert captured["top_k"] == 1


def test_search_parses_source_kinds_csv(monkeypatch):
    pid = _project_id()
    captured = {}

    def fake_retrieve(db, *, project_id, query, top_k, source_kinds):
        captured["source_kinds"] = source_kinds
        return [], {"mode": "fallback", "reason": "ok", "pgvector_ready": False}

    monkeypatch.setattr(knowledge_module, "retrieve_knowledge_with_status", fake_retrieve)
    app = _app(knowledge_router)
    app.dependency_overrides[get_db] = lambda: _ProjectFoundDB(SimpleNamespace(id=pid))
    TestClient(app).get(
        f"/api/knowledge/search?project_id={pid}&query=q&source_kinds=lore, character ,"
    )
    # 空白被 strip，空段被丢弃
    assert captured["source_kinds"] == ["lore", "character"]


# ---------- POST /api/knowledge/reindex ----------

def test_reindex_returns_404_when_project_missing():
    app = _app(knowledge_router)
    app.dependency_overrides[get_db] = lambda: _ProjectMissingDB()
    response = TestClient(app).post(
        "/api/knowledge/reindex",
        json={"project_id": str(_project_id())},
    )
    assert response.status_code == 404


def test_reindex_returns_counts_and_backend_label(monkeypatch):
    pid = _project_id()
    monkeypatch.setattr(
        knowledge_module, "reindex_project_knowledge",
        lambda db, *, project_id: (5, 12),
    )
    monkeypatch.setattr(knowledge_module, "vector_backend_label", lambda db: "pgvector")
    monkeypatch.setattr(
        knowledge_module, "vector_backend_status",
        lambda db: {"reason": "ok", "pgvector_ready": True},
    )
    app = _app(knowledge_router)
    app.dependency_overrides[get_db] = lambda: _ProjectFoundDB(SimpleNamespace(id=pid))
    response = TestClient(app).post(
        "/api/knowledge/reindex", json={"project_id": str(pid)},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["documents_reindexed"] == 5
    assert body["chunks_rebuilt"] == 12
    assert body["vector_backend"] == "pgvector"
    assert body["pgvector_ready"] is True


# ---------- GET /api/knowledge/style-memories ----------

def test_get_style_memories_returns_404_when_project_missing():
    app = _app(knowledge_router)
    app.dependency_overrides[get_db] = lambda: _ProjectMissingDB()
    response = TestClient(app).get(
        f"/api/knowledge/style-memories?project_id={_project_id()}"
    )
    assert response.status_code == 404


def test_get_style_memories_returns_list(monkeypatch):
    pid = _project_id()
    now = datetime.utcnow()
    fake_mem = SimpleNamespace(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        project_id=pid,
        scene_id=None,
        memory_type="style_rule",
        content="保持冷峻语气。",
        source_excerpt=None,
        derived_rules=[],
        user_confirmed=False,
        status="suggested",
        scope_type="project",
        scope_id=None,
        active=True,
        expires_at=None,
        created_at=now,
        updated_at=now,
    )
    monkeypatch.setattr(
        knowledge_module, "list_style_memories",
        lambda db, *, project_id, include_unconfirmed: [fake_mem],
    )
    app = _app(knowledge_router)
    app.dependency_overrides[get_db] = lambda: _ProjectFoundDB(SimpleNamespace(id=pid))
    response = TestClient(app).get(f"/api/knowledge/style-memories?project_id={pid}")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["content"] == "保持冷峻语气。"
    assert items[0]["status"] == "suggested"


# ---------- POST /api/knowledge/style-memories ----------

def test_create_style_memory_returns_404_when_project_missing():
    app = _app(knowledge_router)
    app.dependency_overrides[get_db] = lambda: _ProjectMissingDB()
    response = TestClient(app).post(
        "/api/knowledge/style-memories",
        json={"project_id": str(_project_id()), "content": "x"},
    )
    assert response.status_code == 404


def test_create_style_memory_returns_response_shape(monkeypatch):
    pid = _project_id()
    mem_id = UUID("22222222-2222-2222-2222-222222222222")
    now = datetime.utcnow()
    fake_mem = SimpleNamespace(
        id=mem_id,
        project_id=pid,
        scene_id=None,
        memory_type="style_rule",
        content="冷峻",
        source_excerpt=None,
        derived_rules=[],
        user_confirmed=False,
        status="suggested",
        scope_type="project",
        scope_id=None,
        active=True,
        expires_at=None,
        created_at=now,
        updated_at=now,
    )
    monkeypatch.setattr(
        knowledge_module, "create_style_memory",
        lambda db, **kwargs: fake_mem,
    )
    app = _app(knowledge_router)
    app.dependency_overrides[get_db] = lambda: _ProjectFoundDB(SimpleNamespace(id=pid))
    response = TestClient(app).post(
        "/api/knowledge/style-memories",
        json={"project_id": str(pid), "content": "冷峻"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(mem_id)
    assert body["content"] == "冷峻"


# ---------- POST /api/knowledge/style-memories/{id}/confirm ----------

def test_confirm_style_memory_returns_404_when_missing(monkeypatch):
    monkeypatch.setattr(knowledge_module, "confirm_style_memory", lambda db, **kwargs: None)
    app = _app(knowledge_router)
    # 这条路径不查 Project，所以 db 占位即可
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).post(
        "/api/knowledge/style-memories/22222222-2222-2222-2222-222222222222/confirm",
        json={"user_confirmed": True, "status": "confirmed"},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Style memory not found"}
