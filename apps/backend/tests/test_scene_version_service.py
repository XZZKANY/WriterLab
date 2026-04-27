"""scene_version_service 直测。

主要验证 `create_scene_version` 的去重与 fallback 行为；`restore_scene_version`
的副作用（scene.draft_text 与 scene_version 自增）；`list_scene_versions` 的简单代理。
不依赖真实 DB，使用最小 Fake Session。
"""

from types import SimpleNamespace
from uuid import UUID

from app.services import scene_version_service as svc


class _FakeQuery:
    def __init__(self, items):
        self._items = list(items)

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._items[0] if self._items else None

    def limit(self, n):
        # 返回新的查询封装，模拟 .limit 之后的链式调用。
        return _FakeQuery(self._items[:n])

    def all(self):
        return list(self._items)


class _FakeDB:
    def __init__(self, latest=None, items=None):
        self.latest = latest
        self.items = items or []
        self.added: list = []
        self.committed = 0

    def query(self, model):
        return _FakeQuery(self.items if self.items else ([self.latest] if self.latest else []))

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed += 1

    def refresh(self, obj):
        # 模拟 SQLAlchemy 给 ORM 回写主键。
        if not getattr(obj, "id", None):
            obj.id = UUID("00000000-0000-0000-0000-000000000099")


def test_create_scene_version_returns_none_for_empty_content():
    db = _FakeDB()
    assert svc.create_scene_version(db, scene_id="s1", content="   ", source="manual") is None
    assert db.added == []
    assert db.committed == 0


def test_create_scene_version_returns_none_when_latest_matches():
    latest = SimpleNamespace(content="same", source="manual")
    db = _FakeDB(latest=latest)
    result = svc.create_scene_version(db, scene_id="s1", content="same", source="manual")
    assert result is None
    assert db.added == []


def test_create_scene_version_creates_new_when_no_history():
    db = _FakeDB()
    result = svc.create_scene_version(
        db, scene_id="s1", content="hello", source="manual", label="initial draft", scene_version=2
    )
    assert result is not None
    assert result.content == "hello"
    assert result.source == "manual"
    assert result.label == "initial draft"
    assert result.scene_version == 2
    assert len(db.added) == 1
    assert db.committed == 1


def test_create_scene_version_creates_new_when_content_changed():
    latest = SimpleNamespace(content="prev", source="manual")
    db = _FakeDB(latest=latest)
    result = svc.create_scene_version(db, scene_id="s1", content="next", source="manual")
    assert result is not None
    assert result.content == "next"


def test_create_scene_version_creates_new_when_source_changed():
    # 内容相同但 source 不同（manual vs workflow）也应当作新版本。
    latest = SimpleNamespace(content="text", source="manual")
    db = _FakeDB(latest=latest)
    result = svc.create_scene_version(db, scene_id="s1", content="text", source="workflow")
    assert result is not None
    assert result.source == "workflow"


def test_create_scene_version_defaults_scene_version_to_1():
    db = _FakeDB()
    result = svc.create_scene_version(db, scene_id="s1", content="text", source="manual")
    assert result.scene_version == 1


def test_list_scene_versions_proxies_query_with_limit():
    items = [SimpleNamespace(content=f"v{i}") for i in range(5)]
    db = _FakeDB(items=items)
    versions = svc.list_scene_versions(db, "s1", limit=3)
    assert [v.content for v in versions] == ["v0", "v1", "v2"]


def test_restore_scene_version_writes_back_draft_and_creates_version():
    scene = SimpleNamespace(id="s1", draft_text="old", scene_version=4)
    version = SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"), content="restored")
    db = _FakeDB()

    new_version = svc.restore_scene_version(db, scene=scene, version=version)

    assert scene.draft_text == "restored"
    assert scene.scene_version == 5  # 原 4 + 1
    assert new_version.source == "restore"
    assert "restore version" in new_version.label
    assert new_version.scene_version == 5
    # 至少 commit 两次：一次场景，一次新版本。
    assert db.committed >= 2


def test_restore_scene_version_handles_scene_with_zero_version():
    scene = SimpleNamespace(id="s1", draft_text="", scene_version=None)
    version = SimpleNamespace(id=UUID("22222222-2222-2222-2222-222222222222"), content="x")
    db = _FakeDB()

    new_version = svc.restore_scene_version(db, scene=scene, version=version)
    # None or 0 -> +1 都应得到 1
    assert scene.scene_version == 1
    assert new_version.scene_version == 1
