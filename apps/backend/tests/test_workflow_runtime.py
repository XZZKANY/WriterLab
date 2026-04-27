"""workflow_runtime 直测 — recover_expired_workflow_runs 与 _claim_next_workflow_run。

_workflow_runner_loop 是无限 while True + I/O，跳过直测；
recover_expired_workflow_runs 已被 workflow_service_suite 间接覆盖，
这里补更细粒度的分支用例。
"""

from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

from app.services.workflow_constants import LEASE_SECONDS, RUNNER_ID, _utcnow
from app.services.workflow_runtime import _claim_next_workflow_run, recover_expired_workflow_runs


# ── FakeDB ──────────────────────────────────────────────────────────────────


class _Query:
    def __init__(self, items):
        self._items = list(items)

    def filter(self, *a, **kw):
        return self

    def order_by(self, *a, **kw):
        return self

    def first(self):
        return self._items[0] if self._items else None

    def all(self):
        return list(self._items)


class FakeDB:
    def __init__(self, by_model=None):
        self._by_model = by_model or {}
        self.added = []
        self.committed = 0

    def query(self, model):
        name = getattr(model, "__name__", "")
        return _Query(self._by_model.get(name, []))

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed += 1

    def refresh(self, obj):
        pass


def _expired_run(**kw):
    defaults = dict(
        id=uuid4(), status="running", current_step="plan",
        needs_merge=False, output_payload=None,
        lease_expires_at=_utcnow() - timedelta(seconds=1),
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


# ── recover_expired_workflow_runs ────────────────────────────────────────────


def test_recover_no_expired_runs_returns_zero():
    db = FakeDB(by_model={"WorkflowRun": []})
    assert recover_expired_workflow_runs(db) == 0


def test_recover_expired_with_checkpoint_queues_resume(monkeypatch):
    from app.services import workflow_service as wf
    run = _expired_run()
    db = FakeDB(by_model={"WorkflowRun": [run]})
    monkeypatch.setattr(wf, "_stable_resume_checkpoint", lambda db, run_id: "analyze")
    states = []
    monkeypatch.setattr(wf, "_set_run_state", lambda db, run, status, **kw: states.append(status))
    assert recover_expired_workflow_runs(db) == 1
    assert states == ["queued_resume"]


def test_recover_expired_checkpoint_passes_next_step(monkeypatch):
    from app.services import workflow_service as wf
    run = _expired_run()
    db = FakeDB(by_model={"WorkflowRun": [run]})
    monkeypatch.setattr(wf, "_stable_resume_checkpoint", lambda db, run_id: "plan")
    resume_froms = []
    monkeypatch.setattr(wf, "_set_run_state", lambda db, run, status, resume_from_step=None, **kw: resume_froms.append(resume_from_step))
    recover_expired_workflow_runs(db)
    # next step after "plan" is "write"
    assert resume_froms == ["write"]


def test_recover_expired_no_checkpoint_marks_failed(monkeypatch):
    from app.services import workflow_service as wf
    run = _expired_run()
    db = FakeDB(by_model={"WorkflowRun": [run]})
    monkeypatch.setattr(wf, "_stable_resume_checkpoint", lambda db, run_id: None)
    states = []
    monkeypatch.setattr(wf, "_set_run_state", lambda db, run, status, **kw: states.append(status))
    recover_expired_workflow_runs(db)
    assert states == ["failed"]


def test_recover_expired_needs_merge_marks_failed_even_with_checkpoint(monkeypatch):
    from app.services import workflow_service as wf
    run = _expired_run(needs_merge=True)
    db = FakeDB(by_model={"WorkflowRun": [run]})
    monkeypatch.setattr(wf, "_stable_resume_checkpoint", lambda db, run_id: "analyze")
    states = []
    monkeypatch.setattr(wf, "_set_run_state", lambda db, run, status, **kw: states.append(status))
    recover_expired_workflow_runs(db)
    assert states == ["failed"]


def test_recover_multiple_expired_handles_all(monkeypatch):
    from app.services import workflow_service as wf
    runs = [_expired_run(), _expired_run(needs_merge=True), _expired_run()]
    db = FakeDB(by_model={"WorkflowRun": runs})
    monkeypatch.setattr(wf, "_stable_resume_checkpoint", lambda db, run_id: "analyze")
    states = []
    monkeypatch.setattr(wf, "_set_run_state", lambda db, run, status, **kw: states.append(status))
    count = recover_expired_workflow_runs(db)
    assert count == 2  # two without needs_merge
    assert states.count("queued_resume") == 2
    assert states.count("failed") == 1


# ── _claim_next_workflow_run ──────────────────────────────────────────────────


def test_claim_returns_none_when_queue_empty():
    db = FakeDB(by_model={"WorkflowRun": []})
    assert _claim_next_workflow_run(db) is None


def test_claim_sets_running_status_and_worker():
    run = SimpleNamespace(
        id=uuid4(), status="queued", worker_id=None,
        heartbeat_at=None, lease_expires_at=None, started_at=None,
    )
    db = FakeDB(by_model={"WorkflowRun": [run]})
    result = _claim_next_workflow_run(db)
    assert result is run
    assert run.status == "running"
    assert run.worker_id == RUNNER_ID
    assert run.heartbeat_at is not None
    assert run.lease_expires_at is not None
    assert db.committed >= 1


def test_claim_sets_started_at_if_not_set():
    run = SimpleNamespace(
        id=uuid4(), status="queued", worker_id=None,
        heartbeat_at=None, lease_expires_at=None, started_at=None,
    )
    _claim_next_workflow_run(FakeDB(by_model={"WorkflowRun": [run]}))
    assert run.started_at is not None


def test_claim_preserves_existing_started_at():
    existing = _utcnow() - timedelta(minutes=10)
    run = SimpleNamespace(
        id=uuid4(), status="queued_resume", worker_id=None,
        heartbeat_at=None, lease_expires_at=None, started_at=existing,
    )
    _claim_next_workflow_run(FakeDB(by_model={"WorkflowRun": [run]}))
    assert run.started_at == existing


def test_claim_lease_duration_matches_constant():
    run = SimpleNamespace(
        id=uuid4(), status="queued", worker_id=None,
        heartbeat_at=None, lease_expires_at=None, started_at=None,
    )
    _claim_next_workflow_run(FakeDB(by_model={"WorkflowRun": [run]}))
    delta = run.lease_expires_at - run.heartbeat_at
    assert abs(delta - timedelta(seconds=LEASE_SECONDS)).total_seconds() < 1
