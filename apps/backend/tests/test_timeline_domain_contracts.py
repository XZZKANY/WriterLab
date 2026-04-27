from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.timeline_events import router as timeline_router
from app.db.session import get_db


def _build_timeline_event(**overrides):
    base = {
        "id": UUID("11111111-1111-1111-1111-111111111111"),
        "project_id": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        "chapter_id": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        "scene_id": UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        "title": "时间线事件",
        "event_type": "incident",
        "description": "时间线事件描述",
        "participants": ["林岚"],
        "event_time_label": "第 1 天",
        "canonical": True,
        "metadata_json": {"source": "manual"},
        "created_at": datetime(2026, 4, 7, 10, 0, 0),
        "updated_at": datetime(2026, 4, 7, 10, 0, 0),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class _FakeQuery:
    def __init__(self, rows=None, single=None):
        self._rows = rows or []
        self._single = single

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._rows)

    def first(self):
        return self._single


class _FakeDB:
    def __init__(self, rows=None, single=None):
        self._rows = rows or []
        self._single = single

    def query(self, model):
        return _FakeQuery(rows=self._rows, single=self._single)

    def add(self, row):
        return None

    def commit(self):
        return None

    def refresh(self, row):
        return None


def test_list_timeline_events_filters_by_project_id(monkeypatch):
    app = FastAPI()
    app.include_router(timeline_router)

    project_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    other_project_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    other_row = _build_timeline_event(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        project_id=other_project_id,
        title="无关事件",
        event_type="note",
        description="应被过滤掉",
        participants=[],
        event_time_label=None,
        canonical=False,
        metadata_json=None,
        chapter_id=None,
        scene_id=None,
    )
    expected_row = _build_timeline_event(project_id=project_id)
    app.dependency_overrides[get_db] = lambda: _FakeDB(rows=[expected_row, other_row])

    captured = {}

    def _fake_list_timeline_events(db, project_id, chapter_id=None, scene_id=None):
        captured["project_id"] = project_id
        captured["chapter_id"] = chapter_id
        captured["scene_id"] = scene_id
        return [row for row in [expected_row, other_row] if row.project_id == project_id]

    monkeypatch.setattr("app.api.timeline_events.list_timeline_events", _fake_list_timeline_events)

    client = TestClient(app)
    response = client.get(f"/api/timeline-events?project_id={project_id}")

    assert response.status_code == 200
    assert captured == {"project_id": project_id, "chapter_id": None, "scene_id": None}
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == str(expected_row.id)
    assert payload[0]["project_id"] == str(project_id)
    assert payload[0]["title"] == "时间线事件"


def test_create_timeline_event_returns_created_payload(monkeypatch):
    app = FastAPI()
    app.include_router(timeline_router)

    project_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    created_row = _build_timeline_event(project_id=project_id)
    app.dependency_overrides[get_db] = lambda: _FakeDB(single=created_row)

    captured = {}

    def _fake_create_timeline_event(db, payload):
        captured["payload"] = payload
        return created_row

    monkeypatch.setattr("app.api.timeline_events.create_timeline_event", _fake_create_timeline_event)

    client = TestClient(app)
    response = client.post(
        "/api/timeline-events",
        json={
            "project_id": str(project_id),
            "chapter_id": str(created_row.chapter_id),
            "scene_id": str(created_row.scene_id),
            "title": "时间线事件",
            "event_type": "incident",
            "description": "时间线事件描述",
            "participants": ["林岚"],
            "event_time_label": "第 1 天",
            "canonical": True,
            "metadata_json": {"source": "manual"},
        },
    )

    assert response.status_code == 200
    assert captured["payload"].project_id == project_id
    payload = response.json()
    assert payload["id"] == str(created_row.id)
    assert payload["project_id"] == str(project_id)
    assert payload["title"] == "时间线事件"
    assert payload["description"] == "时间线事件描述"

def test_get_missing_timeline_event_returns_404(monkeypatch):
    app = FastAPI()
    app.include_router(timeline_router)

    missing_event_id = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
    app.dependency_overrides[get_db] = lambda: _FakeDB()
    monkeypatch.setattr("app.api.timeline_events.get_timeline_event", lambda db, event_id: None)

    client = TestClient(app)
    response = client.get(f"/api/timeline-events/{missing_event_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Timeline event not found"}


def test_update_missing_timeline_event_returns_404(monkeypatch):
    app = FastAPI()
    app.include_router(timeline_router)

    missing_event_id = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
    app.dependency_overrides[get_db] = lambda: _FakeDB()
    monkeypatch.setattr("app.api.timeline_events.get_timeline_event", lambda db, event_id: None)

    client = TestClient(app)
    response = client.patch(
        f"/api/timeline-events/{missing_event_id}",
        json={
            "title": "更新后的时间线事件",
            "description": "更新后的描述",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Timeline event not found"}


def test_delete_missing_timeline_event_returns_404(monkeypatch):
    app = FastAPI()
    app.include_router(timeline_router)

    missing_event_id = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    app.dependency_overrides[get_db] = lambda: _FakeDB()
    monkeypatch.setattr("app.api.timeline_events.get_timeline_event", lambda db, event_id: None)

    client = TestClient(app)
    response = client.delete(f"/api/timeline-events/{missing_event_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Timeline event not found"}
