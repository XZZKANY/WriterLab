from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.characters import router as characters_router
from app.api.locations import router as locations_router
from app.api.lore_entries import router as lore_entries_router
from app.db.session import get_db


class _SingleResultQuery:
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

class _ModelDB:
    def __init__(self, model_name, result):
        self._model_name = model_name
        self._result = result
        self.deleted = []

    def query(self, model):
        name = getattr(model, "__name__", "")
        if name == self._model_name:
            return _SingleResultQuery(self._result)
        return _SingleResultQuery(None)

    def commit(self):
        return None

    def refresh(self, _obj):
        return None

    def delete(self, obj):
        self.deleted.append(obj)


def _build_client(router, db):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def _make_character(character_id: UUID, project_id: UUID):
    now = datetime.utcnow()
    return SimpleNamespace(
        id=character_id,
        project_id=project_id,
        name="沈砚",
        aliases="阿砚",
        appearance="黑发，眼神冷静",
        personality="克制",
        background="出身旧都",
        motivation="查明真相",
        speaking_style="简短",
        status="draft",
        secrets="真实身份未公开",
        created_at=now,
        updated_at=now,
    )


def _make_location(location_id: UUID, project_id: UUID):
    now = datetime.utcnow()
    return SimpleNamespace(
        id=location_id,
        project_id=project_id,
        name="旧都档案馆",
        description="尘封手稿和旧地图堆满地下一层。",
        created_at=now,
        updated_at=now,
    )


def _make_lore_entry(entry_id: UUID, project_id: UUID):
    now = datetime.utcnow()
    return SimpleNamespace(
        id=entry_id,
        project_id=project_id,
        category="world_rule",
        title="雾潮规则",
        content="每逢雨夜，旧都边界会提前一小时起雾。",
        priority=50,
        canonical=True,
        created_at=now,
        updated_at=now,
    )


def test_list_characters_forwards_project_filter(monkeypatch):
    project_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    character_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    fake_character = _make_character(character_id, project_id)
    captured = {"project_id": None}

    def fake_list_characters(_db, incoming_project_id):
        captured["project_id"] = incoming_project_id
        return [fake_character]

    monkeypatch.setattr("app.api.characters.list_characters_by_project", fake_list_characters)
    client = _build_client(characters_router, object())

    response = client.get(f"/api/characters?project_id={project_id}")

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(character_id)
    assert captured["project_id"] == project_id

def test_list_lore_entries_forwards_project_filter(monkeypatch):
    project_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    entry_id = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
    fake_entry = _make_lore_entry(entry_id, project_id)
    captured = {"project_id": None}

    def fake_list_entries(_db, incoming_project_id):
        captured["project_id"] = incoming_project_id
        return [fake_entry]

    monkeypatch.setattr("app.api.lore_entries.list_lore_entries_by_project", fake_list_entries)
    client = _build_client(lore_entries_router, object())

    response = client.get(f"/api/lore-entries?project_id={project_id}")

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(entry_id)
    assert captured["project_id"] == project_id


def test_get_location_returns_detail_record():
    project_id = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
    location_id = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    fake_location = _make_location(location_id, project_id)
    client = _build_client(locations_router, _ModelDB("Location", fake_location))

    response = client.get(f"/api/locations/{location_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(location_id)
    assert payload["name"] == "旧都档案馆"


def test_update_location_returns_updated_record():
    project_id = UUID("11111111-1111-1111-1111-111111111111")
    location_id = UUID("22222222-2222-2222-2222-222222222222")
    fake_location = _make_location(location_id, project_id)
    client = _build_client(locations_router, _ModelDB("Location", fake_location))

    response = client.patch(
        f"/api/locations/{location_id}",
        json={"name": "新档案馆", "description": "地下室重新整理完毕。"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "新档案馆"
    assert payload["description"] == "地下室重新整理完毕。"


def test_delete_location_contract_exists():
    project_id = UUID("33333333-3333-3333-3333-333333333333")
    location_id = UUID("44444444-4444-4444-4444-444444444444")
    fake_location = _make_location(location_id, project_id)
    client = _build_client(locations_router, _ModelDB("Location", fake_location))

    response = client.delete(f"/api/locations/{location_id}")

    assert response.status_code == 200
    assert response.json()["deleted"] is True


def test_get_character_contract_exists():
    project_id = UUID("55555555-5555-5555-5555-555555555555")
    character_id = UUID("66666666-6666-6666-6666-666666666666")
    fake_character = _make_character(character_id, project_id)
    client = _build_client(characters_router, _ModelDB("Character", fake_character))

    response = client.get(f"/api/characters/{character_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(character_id)


def test_update_character_contract_exists():
    project_id = UUID("77777777-7777-7777-7777-777777777777")
    character_id = UUID("88888888-8888-8888-8888-888888888888")
    fake_character = _make_character(character_id, project_id)
    client = _build_client(characters_router, _ModelDB("Character", fake_character))

    response = client.patch(
        f"/api/characters/{character_id}",
        json={"personality": "更果断", "status": "active"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["personality"] == "更果断"
    assert payload["status"] == "active"


def test_delete_character_contract_exists():
    project_id = UUID("99999999-9999-9999-9999-999999999999")
    character_id = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    fake_character = _make_character(character_id, project_id)
    client = _build_client(characters_router, _ModelDB("Character", fake_character))

    response = client.delete(f"/api/characters/{character_id}")

    assert response.status_code == 200
    assert response.json()["deleted"] is True


def test_get_lore_entry_contract_exists():
    project_id = UUID("12121212-1212-1212-1212-121212121212")
    entry_id = UUID("34343434-3434-3434-3434-343434343434")
    fake_entry = _make_lore_entry(entry_id, project_id)
    client = _build_client(lore_entries_router, _ModelDB("LoreEntry", fake_entry))

    response = client.get(f"/api/lore-entries/{entry_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(entry_id)


def test_update_lore_entry_contract_exists():
    project_id = UUID("56565656-5656-5656-5656-565656565656")
    entry_id = UUID("78787878-7878-7878-7878-787878787878")
    fake_entry = _make_lore_entry(entry_id, project_id)
    client = _build_client(lore_entries_router, _ModelDB("LoreEntry", fake_entry))

    response = client.patch(
        f"/api/lore-entries/{entry_id}",
        json={"title": "雾潮规则（修订）", "content": "边界起雾会持续到午夜。"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "雾潮规则（修订）"
    assert payload["content"] == "边界起雾会持续到午夜。"


def test_delete_lore_entry_contract_exists():
    project_id = UUID("90909090-9090-9090-9090-909090909090")
    entry_id = UUID("abababab-abab-abab-abab-abababababab")
    fake_entry = _make_lore_entry(entry_id, project_id)
    client = _build_client(lore_entries_router, _ModelDB("LoreEntry", fake_entry))

    response = client.delete(f"/api/lore-entries/{entry_id}")

    assert response.status_code == 200
    assert response.json()["deleted"] is True
