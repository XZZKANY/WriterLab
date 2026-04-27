"""lore_repository 直测。

3 套同构 CRUD（character / location / lore_entry）。重点：
- update_* 用 model_dump(exclude_unset=True) —— 只覆盖显式传入的字段
- delete_* 调用 db.delete + db.commit 并返回 True
- list_*_by_project / get_* 走简单查询代理
"""

from types import SimpleNamespace
from uuid import UUID

from app.repositories import lore_repository as repo


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
    def __init__(self, by_model: dict | None = None):
        self._by_model = by_model or {}
        self.deleted: list = []
        self.commits = 0

    def query(self, model):
        name = getattr(model, "__name__", "")
        return _Query(self._by_model.get(name, []))

    def delete(self, obj):
        self.deleted.append(obj)

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        pass


# ---------- list / get ----------

def test_list_characters_by_project():
    char = SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"))
    db = _RoutingDB(by_model={"Character": [char]})
    assert repo.list_characters_by_project(db, "p") == [char]


def test_list_locations_by_project():
    loc = SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"))
    db = _RoutingDB(by_model={"Location": [loc]})
    assert repo.list_locations_by_project(db, "p") == [loc]


def test_list_lore_entries_by_project():
    entry = SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"))
    db = _RoutingDB(by_model={"LoreEntry": [entry]})
    assert repo.list_lore_entries_by_project(db, "p") == [entry]


def test_get_character_returns_first():
    char = SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"))
    db = _RoutingDB(by_model={"Character": [char]})
    assert repo.get_character(db, "id") is char


def test_get_character_returns_none_when_missing():
    db = _RoutingDB()
    assert repo.get_character(db, "missing") is None


# ---------- update_* ----------

class _Payload:
    """模拟 Pydantic 模型：用 _data 控制 model_dump(exclude_unset=True) 返回。"""

    def __init__(self, data):
        self._data = dict(data)

    def model_dump(self, *, exclude_unset=False):
        # 只在 exclude_unset=True 时返回我们存的数据；其他默认行为
        if exclude_unset:
            return dict(self._data)
        return dict(self._data)


def test_update_character_only_overwrites_explicit_fields():
    char = SimpleNamespace(
        name="原名",
        aliases="原别名",
        appearance="原外观",
    )
    db = _RoutingDB()
    payload = _Payload({"name": "新名", "appearance": "新外观"})
    out = repo.update_character(db, char, payload)
    assert out is char
    assert char.name == "新名"
    assert char.aliases == "原别名"  # 未在 payload 内 → 不动
    assert char.appearance == "新外观"
    assert db.commits == 1


def test_update_character_with_empty_payload_is_noop():
    char = SimpleNamespace(name="x", aliases="y")
    db = _RoutingDB()
    payload = _Payload({})
    repo.update_character(db, char, payload)
    assert char.name == "x"
    assert char.aliases == "y"


def test_update_location_writes_only_provided():
    loc = SimpleNamespace(name="原名", description="原描述")
    db = _RoutingDB()
    payload = _Payload({"description": "新描述"})
    repo.update_location(db, loc, payload)
    assert loc.name == "原名"
    assert loc.description == "新描述"
    assert db.commits == 1


def test_update_lore_entry_writes_only_provided():
    entry = SimpleNamespace(title="原标题", content="原正文", priority=50, canonical=True)
    db = _RoutingDB()
    payload = _Payload({"priority": 80, "canonical": False})
    repo.update_lore_entry(db, entry, payload)
    assert entry.title == "原标题"
    assert entry.content == "原正文"
    assert entry.priority == 80
    assert entry.canonical is False


# ---------- delete_* ----------

def test_delete_character_calls_db_delete_and_commits():
    char = SimpleNamespace(id="x")
    db = _RoutingDB()
    assert repo.delete_character(db, char) is True
    assert db.deleted == [char]
    assert db.commits == 1


def test_delete_location_calls_db_delete_and_commits():
    loc = SimpleNamespace(id="x")
    db = _RoutingDB()
    assert repo.delete_location(db, loc) is True
    assert db.deleted == [loc]
    assert db.commits == 1


def test_delete_lore_entry_calls_db_delete_and_commits():
    entry = SimpleNamespace(id="x")
    db = _RoutingDB()
    assert repo.delete_lore_entry(db, entry) is True
    assert db.deleted == [entry]
    assert db.commits == 1
