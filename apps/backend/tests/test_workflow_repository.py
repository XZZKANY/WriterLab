"""workflow_repository 直测：2 个简单 query 代理。"""

from types import SimpleNamespace
from uuid import UUID

from app.repositories import workflow_repository as repo


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


def test_get_workflow_run_returns_first():
    run = SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"))
    db = _RoutingDB(by_model={"WorkflowRun": [run]})
    assert repo.get_workflow_run(db, "id") is run


def test_get_workflow_run_returns_none_when_missing():
    assert repo.get_workflow_run(_RoutingDB(), "missing") is None


def test_list_workflow_steps_returns_all_in_order():
    steps = [SimpleNamespace(id=i) for i in range(5)]
    db = _RoutingDB(by_model={"WorkflowStep": steps})
    assert repo.list_workflow_steps(db, "workflow-id") == steps


def test_list_workflow_steps_returns_empty_when_no_steps():
    assert repo.list_workflow_steps(_RoutingDB(), "workflow-id") == []
