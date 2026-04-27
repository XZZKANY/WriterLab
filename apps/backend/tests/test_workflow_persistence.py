"""workflow_persistence 直测 — 不测通过 lazy import 调用多个协作者的复杂函数
（_create_run / _create_step / _finish_step），那些已经由 workflow_service_suite 通过
facade 间接覆盖。本文件聚焦 5 类内部逻辑可独立验证的函数。"""

from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

from app.services.workflow_constants import LEASE_SECONDS, RUNNER_ID
from app.services.workflow_persistence import (
    _attach_run_transient_fields,
    _attach_step_attempts,
    _create_memory_candidate,
    _heartbeat_run,
    _queue_depth,
    _resolve_project_id,
    _set_run_state,
)


# ── FakeDB ──────────────────────────────────────────────────────────────────


class _Query:
    def __init__(self, items, count=0):
        self._items = list(items)
        self._count = count

    def filter(self, *a, **kw):
        return self

    def order_by(self, *a, **kw):
        return self

    def count(self):
        return self._count

    def first(self):
        return self._items[0] if self._items else None

    def all(self):
        return list(self._items)


class FakeDB:
    def __init__(self, by_model=None, count_by_model=None):
        self._by_model = by_model or {}
        self._count_by_model = count_by_model or {}
        self.added = []
        self.committed = 0

    def query(self, model):
        name = getattr(model, "__name__", "")
        items = self._by_model.get(name, [])
        count = self._count_by_model.get(name, len(items))
        return _Query(items, count)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed += 1

    def refresh(self, obj):
        pass


def _make_run(**kw):
    defaults = dict(
        status=None, current_step=None, error_message=None,
        output_payload=None, needs_merge=None, quality_degraded=None,
        resume_from_step=None, heartbeat_at=None, lease_expires_at=None,
        worker_id=None, started_at=None, completed_at=None, cancelled_at=None,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


# ── _attach_step_attempts ────────────────────────────────────────────────────


def test_attach_step_attempts_extracts_list():
    step = SimpleNamespace(output_payload={"attempts": [{"n": 1}, {"n": 2}]})
    assert _attach_step_attempts(step).attempts == [{"n": 1}, {"n": 2}]


def test_attach_step_attempts_empty_when_key_missing():
    step = SimpleNamespace(output_payload={"other": "stuff"})
    assert _attach_step_attempts(step).attempts == []


def test_attach_step_attempts_empty_when_payload_none():
    step = SimpleNamespace(output_payload=None)
    assert _attach_step_attempts(step).attempts == []


def test_attach_step_attempts_non_list_value_yields_empty():
    step = SimpleNamespace(output_payload={"attempts": "not-a-list"})
    assert _attach_step_attempts(step).attempts == []


# ── _resolve_project_id ──────────────────────────────────────────────────────


def test_resolve_project_id_chapter_not_found_returns_none():
    scene = SimpleNamespace(chapter_id=uuid4())
    assert _resolve_project_id(scene, FakeDB()) is None


def test_resolve_project_id_book_not_found_returns_none():
    chapter = SimpleNamespace(id=uuid4(), book_id=uuid4())
    scene = SimpleNamespace(chapter_id=chapter.id)
    db = FakeDB(by_model={"Chapter": [chapter]})
    assert _resolve_project_id(scene, db) is None


def test_resolve_project_id_returns_project_id():
    pid = uuid4()
    book = SimpleNamespace(id=uuid4(), project_id=pid)
    chapter = SimpleNamespace(id=uuid4(), book_id=book.id)
    scene = SimpleNamespace(chapter_id=chapter.id)
    db = FakeDB(by_model={"Chapter": [chapter], "Book": [book]})
    assert _resolve_project_id(scene, db) == pid


# ── _queue_depth ──────────────────────────────────────────────────────────────


def test_queue_depth_zero():
    db = FakeDB(count_by_model={"WorkflowRun": 0})
    assert _queue_depth(db) == 0


def test_queue_depth_non_zero():
    db = FakeDB(count_by_model={"WorkflowRun": 7})
    assert _queue_depth(db) == 7


# ── _heartbeat_run ────────────────────────────────────────────────────────────


def test_heartbeat_run_sets_timestamps_and_worker():
    run = SimpleNamespace(heartbeat_at=None, lease_expires_at=None, worker_id=None)
    _heartbeat_run(FakeDB(), run)
    assert run.heartbeat_at is not None
    assert run.worker_id == RUNNER_ID
    delta = run.lease_expires_at - run.heartbeat_at
    assert abs(delta - timedelta(seconds=LEASE_SECONDS)).total_seconds() < 1


def test_heartbeat_run_commits():
    run = SimpleNamespace(heartbeat_at=None, lease_expires_at=None, worker_id=None)
    db = FakeDB()
    _heartbeat_run(db, run)
    assert db.committed >= 1


# ── _set_run_state ────────────────────────────────────────────────────────────


def test_set_run_state_running_fills_heartbeat_and_lease(monkeypatch):
    from app.services import workflow_service as wf
    monkeypatch.setattr(wf, "_publish_run_event", lambda *a, **kw: None)
    monkeypatch.setattr(wf, "_attach_run_transient_fields", lambda db, run: run)
    run = _make_run()
    _set_run_state(FakeDB(), run=run, status="running", current_step="plan")
    assert run.status == "running"
    assert run.current_step == "plan"
    assert run.heartbeat_at is not None
    assert run.lease_expires_at is not None
    assert run.worker_id == RUNNER_ID


def test_set_run_state_queued_clears_worker(monkeypatch):
    from app.services import workflow_service as wf
    monkeypatch.setattr(wf, "_publish_run_event", lambda *a, **kw: None)
    monkeypatch.setattr(wf, "_attach_run_transient_fields", lambda db, run: run)
    run = _make_run(worker_id="old-worker")
    _set_run_state(FakeDB(), run=run, status="queued")
    assert run.worker_id is None


def test_set_run_state_completed_clears_worker_and_lease(monkeypatch):
    from app.services import workflow_service as wf
    monkeypatch.setattr(wf, "_publish_run_event", lambda *a, **kw: None)
    monkeypatch.setattr(wf, "_attach_run_transient_fields", lambda db, run: run)
    run = _make_run(worker_id="w", heartbeat_at="old", lease_expires_at="old")
    _set_run_state(FakeDB(), run=run, status="completed", completed=True)
    assert run.completed_at is not None
    assert run.worker_id is None
    assert run.heartbeat_at is None
    assert run.lease_expires_at is None


def test_set_run_state_cancelled_sets_cancelled_at(monkeypatch):
    from app.services import workflow_service as wf
    monkeypatch.setattr(wf, "_publish_run_event", lambda *a, **kw: None)
    monkeypatch.setattr(wf, "_attach_run_transient_fields", lambda db, run: run)
    run = _make_run()
    _set_run_state(FakeDB(), run=run, status="cancelled", completed=True)
    assert run.cancelled_at is not None


def test_set_run_state_waiting_user_review_emits_extra_event(monkeypatch):
    from app.services import workflow_service as wf
    events = []
    monkeypatch.setattr(wf, "_publish_run_event", lambda db, run, event, **kw: events.append(event))
    monkeypatch.setattr(wf, "_attach_run_transient_fields", lambda db, run: run)
    run = _make_run()
    _set_run_state(FakeDB(), run=run, status="waiting_user_review")
    assert "workflow_waiting_review" in events


def test_set_run_state_error_message_stored(monkeypatch):
    from app.services import workflow_service as wf
    monkeypatch.setattr(wf, "_publish_run_event", lambda *a, **kw: None)
    monkeypatch.setattr(wf, "_attach_run_transient_fields", lambda db, run: run)
    run = _make_run()
    _set_run_state(FakeDB(), run=run, status="failed", error_message="boom", completed=True)
    assert run.error_message == "boom"


# ── _attach_run_transient_fields ──────────────────────────────────────────────


def test_attach_run_transient_fields_none_returns_none():
    assert _attach_run_transient_fields(FakeDB(), None) is None


# ── _create_memory_candidate ──────────────────────────────────────────────────


def test_create_memory_candidate_no_project_id_returns_none():
    scene = SimpleNamespace(id=uuid4(), chapter_id=uuid4(), draft_text="text")
    payload = SimpleNamespace(model_dump=lambda: {}, guidance=None, branch_id=None, provider_mode=None, fixture_scenario=None)
    assert _create_memory_candidate(FakeDB(), scene=scene, payload=payload, project_id=None, final_text="text") is None


def test_create_memory_candidate_empty_text_returns_none():
    scene = SimpleNamespace(id=uuid4(), chapter_id=uuid4(), draft_text="text")
    payload = SimpleNamespace(model_dump=lambda: {}, guidance=None, branch_id=None, provider_mode=None, fixture_scenario=None)
    assert _create_memory_candidate(FakeDB(), scene=scene, payload=payload, project_id=uuid4(), final_text="   ") is None
