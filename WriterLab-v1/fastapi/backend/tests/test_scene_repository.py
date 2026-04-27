"""scene_repository 直测：4 个简单 query 代理。"""

from types import SimpleNamespace
from uuid import UUID

from app.repositories import scene_repository as repo


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

    def query(self, model):
        name = getattr(model, "__name__", "")
        return _Query(self._by_model.get(name, []))


def test_get_scene_returns_first():
    scene = SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"))
    db = _RoutingDB(by_model={"Scene": [scene]})
    assert repo.get_scene(db, "id") is scene


def test_get_scene_returns_none_when_missing():
    assert repo.get_scene(_RoutingDB(), "missing") is None


def test_get_scene_version_returns_first():
    version = SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"))
    db = _RoutingDB(by_model={"SceneVersion": [version]})
    assert repo.get_scene_version(db, "scene-id", "version-id") is version


def test_get_scene_version_returns_none_when_missing():
    assert repo.get_scene_version(_RoutingDB(), "s", "v") is None


def test_list_scenes_by_chapter_returns_all():
    scenes = [SimpleNamespace(id=i) for i in range(3)]
    db = _RoutingDB(by_model={"Scene": scenes})
    assert repo.list_scenes_by_chapter(db, "chapter-id") == scenes


def test_list_scenes_by_chapter_handles_empty():
    assert repo.list_scenes_by_chapter(_RoutingDB(), "chapter-id") == []


def test_list_scene_versions_returns_all():
    versions = [SimpleNamespace(id=i) for i in range(3)]
    db = _RoutingDB(by_model={"SceneVersion": versions})
    assert repo.list_scene_versions(db, "scene-id") == versions


def test_list_scene_versions_handles_empty():
    assert repo.list_scene_versions(_RoutingDB(), "scene-id") == []
