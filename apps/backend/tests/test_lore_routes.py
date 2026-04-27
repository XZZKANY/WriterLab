"""characters / locations / lore_entries 三套同构 CRUD 路由的契约测试。

`tests/test_lore_domain_contracts.py` 覆盖了主路径；这里专门补 404 错误路径
与 response shape，让 happy + sad 两条都被守住。
"""

from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import characters as characters_module
from app.api import locations as locations_module
from app.api import lore_entries as lore_entries_module
from app.api.characters import router as characters_router
from app.api.locations import router as locations_router
from app.api.lore_entries import router as lore_entries_router
from app.db.session import get_db


def _app(*routers):
    app = FastAPI()
    for r in routers:
        app.include_router(r)
    return app


# ---------- characters ----------

def test_get_character_returns_404_when_missing(monkeypatch):
    monkeypatch.setattr(characters_module, "get_character_query", lambda db, cid: None)
    app = _app(characters_router)
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).get("/api/characters/11111111-1111-1111-1111-111111111111")
    assert response.status_code == 404
    assert response.json() == {"detail": "Character not found"}


def test_patch_character_returns_404_when_missing(monkeypatch):
    monkeypatch.setattr(characters_module, "get_character_query", lambda db, cid: None)
    app = _app(characters_router)
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).patch(
        "/api/characters/11111111-1111-1111-1111-111111111111",
        json={"name": "新名"},
    )
    assert response.status_code == 404


def test_delete_character_returns_404_when_missing(monkeypatch):
    monkeypatch.setattr(characters_module, "get_character_query", lambda db, cid: None)
    app = _app(characters_router)
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).delete("/api/characters/11111111-1111-1111-1111-111111111111")
    assert response.status_code == 404


def test_delete_character_returns_response_shape_when_succeeds(monkeypatch):
    char_id = UUID("11111111-1111-1111-1111-111111111111")
    fake_character = SimpleNamespace(id=char_id)
    monkeypatch.setattr(characters_module, "get_character_query", lambda db, cid: fake_character)
    monkeypatch.setattr(characters_module, "delete_character_query", lambda db, c: None)
    app = _app(characters_router)
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).delete(f"/api/characters/{char_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["deleted"] is True
    assert body["character_id"] == str(char_id)


def test_list_characters_filters_by_project_query_param(monkeypatch):
    project_id = UUID("11111111-1111-1111-1111-111111111111")
    captured = {}

    def fake_list(db, pid):
        captured["project_id"] = pid
        return []

    monkeypatch.setattr(characters_module, "list_characters_by_project", fake_list)
    app = _app(characters_router)
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).get(f"/api/characters?project_id={project_id}")
    assert response.status_code == 200
    assert response.json() == []
    assert captured["project_id"] == project_id


# ---------- locations ----------

def test_get_location_returns_404_when_missing(monkeypatch):
    monkeypatch.setattr(locations_module, "get_location_query", lambda db, lid: None)
    app = _app(locations_router)
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).get("/api/locations/11111111-1111-1111-1111-111111111111")
    assert response.status_code == 404
    assert response.json() == {"detail": "Location not found"}


def test_patch_location_returns_404_when_missing(monkeypatch):
    monkeypatch.setattr(locations_module, "get_location_query", lambda db, lid: None)
    app = _app(locations_router)
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).patch(
        "/api/locations/11111111-1111-1111-1111-111111111111",
        json={"name": "新地名"},
    )
    assert response.status_code == 404


def test_delete_location_returns_response_shape_when_succeeds(monkeypatch):
    loc_id = UUID("11111111-1111-1111-1111-111111111111")
    monkeypatch.setattr(
        locations_module, "get_location_query", lambda db, lid: SimpleNamespace(id=loc_id),
    )
    monkeypatch.setattr(locations_module, "delete_location_query", lambda db, l: None)
    app = _app(locations_router)
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).delete(f"/api/locations/{loc_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["deleted"] is True
    assert body["location_id"] == str(loc_id)


# ---------- lore_entries ----------

def test_get_lore_entry_returns_404_when_missing(monkeypatch):
    monkeypatch.setattr(lore_entries_module, "get_lore_entry_query", lambda db, eid: None)
    app = _app(lore_entries_router)
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).get("/api/lore-entries/11111111-1111-1111-1111-111111111111")
    assert response.status_code == 404
    assert response.json() == {"detail": "Lore entry not found"}


def test_patch_lore_entry_returns_404_when_missing(monkeypatch):
    monkeypatch.setattr(lore_entries_module, "get_lore_entry_query", lambda db, eid: None)
    app = _app(lore_entries_router)
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).patch(
        "/api/lore-entries/11111111-1111-1111-1111-111111111111",
        json={"title": "新标题"},
    )
    assert response.status_code == 404


def test_delete_lore_entry_returns_response_shape_when_succeeds(monkeypatch):
    entry_id = UUID("11111111-1111-1111-1111-111111111111")
    monkeypatch.setattr(
        lore_entries_module, "get_lore_entry_query", lambda db, eid: SimpleNamespace(id=entry_id),
    )
    monkeypatch.setattr(lore_entries_module, "delete_lore_entry_query", lambda db, e: None)
    app = _app(lore_entries_router)
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).delete(f"/api/lore-entries/{entry_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["deleted"] is True
    assert body["lore_entry_id"] == str(entry_id)


def test_list_lore_entries_returns_query_results(monkeypatch):
    project_id = UUID("11111111-1111-1111-1111-111111111111")
    entry = SimpleNamespace(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        project_id=project_id,
        category="cat",
        title="标题",
        content="正文",
        priority=50,
        canonical=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    monkeypatch.setattr(
        lore_entries_module, "list_lore_entries_by_project", lambda db, pid: [entry]
    )
    app = _app(lore_entries_router)
    app.dependency_overrides[get_db] = lambda: object()
    response = TestClient(app).get(f"/api/lore-entries?project_id={project_id}")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["title"] == "标题"
    assert items[0]["priority"] == 50
    assert items[0]["canonical"] is True
