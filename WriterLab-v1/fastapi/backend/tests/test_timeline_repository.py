"""timeline_repository 直测：list / get / create / update / delete。"""

from types import SimpleNamespace
from uuid import UUID

from app.repositories import timeline_repository as repo


class _Query:
    def __init__(self, items):
        self._items = list(items)

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._items[0] if self._items else None

    def all(self):
        return list(self._items)


class _RoutingDB:
    def __init__(self, items=None):
        self._items = items or []
        self.added: list = []
        self.deleted: list = []
        self.commits = 0

    def query(self, model):
        return _Query(self._items)

    def add(self, obj):
        self.added.append(obj)

    def delete(self, obj):
        self.deleted.append(obj)

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        pass


class _Payload:
    def __init__(self, data):
        self._data = dict(data)

    def model_dump(self, *, exclude_unset=False):
        return dict(self._data)


def test_list_timeline_events_filters_only_by_project_when_no_chapter_or_scene():
    event = SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"))
    db = _RoutingDB(items=[event])
    out = repo.list_timeline_events(db, project_id="p")
    assert out == [event]


def test_list_timeline_events_accepts_optional_chapter_and_scene_filters():
    event = SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"))
    db = _RoutingDB(items=[event])
    out = repo.list_timeline_events(db, project_id="p", chapter_id="c", scene_id="s")
    assert out == [event]


def test_get_timeline_event_returns_first():
    event = SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"))
    db = _RoutingDB(items=[event])
    assert repo.get_timeline_event(db, "id") is event


def test_get_timeline_event_returns_none_when_missing():
    assert repo.get_timeline_event(_RoutingDB(), "missing") is None


def test_create_timeline_event_constructs_row_from_payload():
    """create 期望 payload.model_dump() 返回所有非 None 字段，再通过 TimelineEvent(**data) 构造 ORM 行。"""
    db = _RoutingDB()
    payload = _Payload({
        "project_id": UUID("11111111-1111-1111-1111-111111111111"),
        "title": "事件 A",
        "event_type": "scene",
        "description": "描述",
        "canonical": True,
    })
    row = repo.create_timeline_event(db, payload)
    assert row is not None
    assert row.title == "事件 A"
    assert row.event_type == "scene"
    assert row.canonical is True
    assert len(db.added) == 1
    assert db.commits == 1


def test_update_timeline_event_only_writes_explicit_fields():
    row = SimpleNamespace(title="原标题", description="原描述", canonical=True)
    db = _RoutingDB()
    payload = _Payload({"description": "新描述"})
    out = repo.update_timeline_event(db, row, payload)
    assert out is row
    assert row.title == "原标题"  # 未传 → 不动
    assert row.description == "新描述"
    assert row.canonical is True
    assert db.commits == 1


def test_update_timeline_event_empty_payload_is_noop():
    row = SimpleNamespace(title="x")
    db = _RoutingDB()
    repo.update_timeline_event(db, row, _Payload({}))
    assert row.title == "x"
    assert db.commits == 1  # 仍触发 commit


def test_delete_timeline_event_calls_db_delete_and_commits():
    row = SimpleNamespace(id="x")
    db = _RoutingDB()
    assert repo.delete_timeline_event(db, row) is None
    assert db.deleted == [row]
    assert db.commits == 1
