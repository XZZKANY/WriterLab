from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from app.schemas.workflow import GuardOutput, OverrideStepRequest, ResumeWorkflowRequest, StyleNegativeMatch, WorkflowSceneRequest
from app.services.ai_gateway_service import GatewayCallResult
from app.services.workflow_service import (
    STEP_ORDER,
    _agent_meta,
    _build_memory_candidate,
    _finish_step,
    _run_scene_workflow,
    _store_workflow_result,
    _with_agent_meta,
    override_workflow_step,
    recover_expired_workflow_runs,
    resume_workflow_run,
)


class _ModelDump:
    def __init__(self, **payload):
        self._payload = payload
        for key, value in payload.items():
            setattr(self, key, value)

    def model_dump(self):
        return dict(self._payload)


class _EmptyQuery:
    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def first(self):
        return None

    def all(self):
        return []

    def count(self):
        return 0


class _RunQuery(_EmptyQuery):
    def __init__(self, runs):
        self._runs = runs

    def all(self):
        return list(self._runs)


class _FakeDB:
    def __init__(self, runs=None):
        self.runs = list(runs or [])
        self.added = []

    def add(self, item):
        self.added.append(item)

    def commit(self):
        return None

    def refresh(self, item):
        return None

    def delete(self, item):
        return None

    def query(self, model):
        if getattr(model, "__name__", "") == "WorkflowRun":
            return _RunQuery(self.runs)
        return _EmptyQuery()


def _fake_run(**overrides):
    now = datetime.utcnow()
    payload = {
        "id": uuid4(),
        "project_id": uuid4(),
        "input_payload": {"scene_version": 1},
        "provider_mode": "live",
        "fixture_version": None,
        "output_payload": None,
        "status": "completed",
        "current_step": "done",
        "retry_count": 0,
        "resume_from_step": None,
        "needs_merge": False,
        "quality_degraded": False,
        "worker_id": None,
        "heartbeat_at": None,
        "lease_expires_at": None,
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def _fake_step(step_key: str, **overrides):
    payload = {
        "id": uuid4(),
        "step_key": step_key,
        "step_order": STEP_ORDER.get(step_key, 0),
        "status": "running",
        "version": 1,
        "attempt_no": 1,
        "started_at": datetime.utcnow() - timedelta(seconds=1),
        "provider_mode": "live",
        "provider": None,
        "model": None,
        "profile_name": None,
        "output_payload": None,
        "machine_output_snapshot": None,
        "effective_output_snapshot": None,
        "fallback_used": False,
        "fallback_count": 0,
        "latency_ms": None,
        "edited_reason": None,
        "invalidated_by_step": None,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_agent_meta_maps_guard_and_memory_steps():
    guard = _agent_meta("guard")
    memory = _agent_meta("memory")

    assert guard["agent_key"] == "guardrail"
    assert guard["agent_name"] == "Guardrail Agent"
    assert memory["agent_key"] == "memory_curator"
    assert memory["agent_name"] == "Memory Curator Agent"


def test_with_agent_meta_keeps_payload_and_adds_labels():
    payload = _with_agent_meta("write", {"draft_length": 1200})

    assert payload["draft_length"] == 1200
    assert payload["agent_key"] == "writer"
    assert payload["agent_name"] == "Writer Agent"


def test_build_memory_candidate_prefers_guidance_rules():
    scene = SimpleNamespace(title="Dock Scene")
    payload = SimpleNamespace(guidance=["Keep the pacing tight.", "Avoid sermon-like exposition."])

    content, rules = _build_memory_candidate(scene, payload, "Accepted draft")

    assert "Keep the pacing tight." in content
    assert rules[:2] == ["Keep the pacing tight.", "Avoid sermon-like exposition."]


def test_build_memory_candidate_has_safe_fallback_without_guidance():
    scene = SimpleNamespace(title="Dock Scene")
    payload = SimpleNamespace(guidance=[])

    content, rules = _build_memory_candidate(scene, payload, "Accepted draft")

    assert "Dock Scene" in content
    assert any("Avoid overexplaining motivations" in rule for rule in rules)


def test_override_workflow_step_invalidates_downstream_and_queues_resume(monkeypatch):
    db = _FakeDB()
    run = _fake_run(provider_mode="smoke_fixture", fixture_version="v1")
    latest = _fake_step("plan", version=3, attempt_no=3, machine_output_snapshot={"raw_plan": "old"}, provider_mode="smoke_fixture", provider="fixture", model="smoke-fixture", profile_name="fixture-plan-happy_path")
    override_step = _fake_step("plan", version=4, attempt_no=4)
    captured = {}

    monkeypatch.setattr("app.services.workflow_service._existing_dedup_response", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.workflow_service._latest_step_for_key", lambda *args, **kwargs: latest)
    monkeypatch.setattr("app.services.workflow_service._create_step", lambda *args, **kwargs: override_step)
    monkeypatch.setattr(
        "app.services.workflow_service._finish_step",
        lambda *args, **kwargs: captured.setdefault("finish", kwargs) or override_step,
    )
    monkeypatch.setattr(
        "app.services.workflow_service._invalidate_downstream_steps",
        lambda *args, **kwargs: captured.setdefault("invalidate", kwargs),
    )
    monkeypatch.setattr("app.services.workflow_service._next_step_key", lambda step_key: "write")
    monkeypatch.setattr("app.services.workflow_service._record_dedup_response", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.workflow_service.ensure_workflow_runner_started", lambda: None)

    payload = OverrideStepRequest(
        idempotency_key="override-1",
        expected_step_version=3,
        derived_from_version=3,
        edited_reason="Human corrected the outline",
        effective_output_snapshot={"summary": "new plan"},
    )

    override_workflow_step(db, run=run, step_key="plan", payload=payload)

    assert run.status == "queued_resume"
    assert run.current_step == "queued"
    assert run.resume_from_step == "write"
    assert captured["finish"]["user_edited"] is True
    assert captured["finish"]["effective_output_snapshot"] == {"summary": "new plan"}
    assert captured["invalidate"]["source_step"] is override_step
    assert override_step.provider_mode == "smoke_fixture"
    assert override_step.provider == "fixture"
    assert override_step.model == "smoke-fixture"
    assert override_step.profile_name == "fixture-plan-happy_path"


def test_resume_workflow_run_queues_from_checkpoint(monkeypatch):
    db = _FakeDB()
    run = _fake_run(status="failed", current_step="style", retry_count=1, provider_mode="smoke_fixture", fixture_version="v1")
    checkpoint_step = _fake_step("plan", version=2)

    monkeypatch.setattr("app.services.workflow_service._existing_dedup_response", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.workflow_service._stable_resume_checkpoint", lambda *args, **kwargs: "plan")
    monkeypatch.setattr("app.services.workflow_service._latest_step_for_key", lambda *args, **kwargs: checkpoint_step)
    monkeypatch.setattr("app.services.workflow_service._next_step_key", lambda step_key: "write")
    monkeypatch.setattr("app.services.workflow_service._record_dedup_response", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.workflow_service.ensure_workflow_runner_started", lambda: None)

    def _fake_set_run_state(db, *, run, status, current_step=None, resume_from_step=None, **kwargs):
        run.status = status
        run.current_step = current_step
        run.resume_from_step = resume_from_step
        return run

    monkeypatch.setattr("app.services.workflow_service._set_run_state", _fake_set_run_state)

    payload = ResumeWorkflowRequest(idempotency_key="resume-1", expected_step_version=2, resume_from_step=None)
    resume_workflow_run(db, run=run, payload=payload)

    assert run.retry_count == 2
    assert run.status == "queued_resume"
    assert run.current_step == "queued"
    assert run.resume_from_step == "write"
    assert run.provider_mode == "smoke_fixture"
    assert run.fixture_version == "v1"


def test_store_workflow_result_waits_for_review_on_scene_version_conflict(monkeypatch):
    db = _FakeDB()
    run = _fake_run(input_payload={"scene_version": 2})
    scene = SimpleNamespace(id=uuid4(), scene_version=3, draft_text="old draft")
    store_step = _fake_step("store")
    captured = {}

    monkeypatch.setattr(
        "app.services.workflow_service._finish_step",
        lambda *args, **kwargs: captured.setdefault("finish", kwargs),
    )

    payload = WorkflowSceneRequest(scene_id=uuid4(), branch_id=None, length="medium", guidance=[], auto_apply=True)
    version_id, needs_merge = _store_workflow_result(db, run=run, scene=scene, payload=payload, store_step=store_step, final_text="new text")

    assert version_id is None
    assert needs_merge is True
    assert captured["finish"]["status"] == "waiting_user_review"
    assert captured["finish"]["effective_output_snapshot"]["needs_merge"] is True


def test_finish_step_persists_gateway_attempts_and_quality_degraded(monkeypatch):
    db = _FakeDB()
    run = _fake_run(quality_degraded=False, provider_mode="smoke_fixture", fixture_version="v1")
    step = _fake_step("style")
    gateway_result = GatewayCallResult(
        text="styled prose",
        provider="ollama",
        model="qwen2.5:3b",
        task_type="revise",
        latency_ms=321,
        fallback_used=True,
        quality_degraded=True,
        profile_name="style-fallback",
        attempts=[{"status": "error"}, {"status": "success"}],
        token_usage={"prompt_tokens": 12, "completion_tokens": 34},
        cost_estimate=0.01,
    )

    monkeypatch.setattr("app.services.workflow_service._publish_run_event", lambda *args, **kwargs: None)

    _finish_step(
        db,
        run=run,
        step=step,
        status="completed",
        machine_output_snapshot={"styled_text": "machine"},
        effective_output_snapshot={"styled_text": "effective"},
        gateway_result=gateway_result,
    )

    assert step.provider == "ollama"
    assert step.model == "qwen2.5:3b"
    assert step.provider_mode == "smoke_fixture"
    assert step.profile_name == "style-fallback"
    assert step.fallback_count == 1
    assert step.output_payload["quality_degraded"] is True
    assert len(step.output_payload["attempts"]) == 2
    assert run.quality_degraded is True


def test_recover_expired_workflow_runs_marks_resume_when_checkpoint_exists(monkeypatch):
    run = _fake_run(
        status="running",
        current_step="style",
        lease_expires_at=datetime.utcnow() - timedelta(seconds=5),
        needs_merge=False,
    )
    db = _FakeDB([run])

    monkeypatch.setattr("app.services.workflow_service._stable_resume_checkpoint", lambda *args, **kwargs: "plan")
    monkeypatch.setattr("app.services.workflow_service._next_step_key", lambda step_key: "write")

    def _fake_set_run_state(db, *, run, status, current_step=None, resume_from_step=None, **kwargs):
        run.status = status
        run.current_step = current_step
        run.resume_from_step = resume_from_step
        return run

    monkeypatch.setattr("app.services.workflow_service._set_run_state", _fake_set_run_state)

    recovered = recover_expired_workflow_runs(db)

    assert recovered == 1
    assert run.status == "queued_resume"
    assert run.resume_from_step == "write"


def test_recover_expired_workflow_runs_marks_failed_without_checkpoint(monkeypatch):
    run = _fake_run(
        status="running",
        current_step="style",
        lease_expires_at=datetime.utcnow() - timedelta(seconds=5),
        needs_merge=False,
        output_payload={},
    )
    db = _FakeDB([run])

    monkeypatch.setattr("app.services.workflow_service._stable_resume_checkpoint", lambda *args, **kwargs: None)

    def _fake_set_run_state(db, *, run, status, current_step=None, error_message=None, output_payload=None, **kwargs):
        run.status = status
        run.current_step = current_step
        run.error_message = error_message
        run.output_payload = output_payload
        return run

    monkeypatch.setattr("app.services.workflow_service._set_run_state", _fake_set_run_state)

    recovered = recover_expired_workflow_runs(db)

    assert recovered == 0
    assert run.status == "failed"
    assert run.error_message == "lease_expired"
    assert run.output_payload["error_summary"] == "lease_expired"


def test_run_scene_workflow_routes_hard_negative_to_waiting_user_review(monkeypatch):
    run, step_map = _execute_style_workflow(
        monkeypatch,
        [
            StyleNegativeMatch(
                rule_id="hard-1",
                label="sermon",
                severity="hard",
                match_mode="exact",
                matched_text="sermon",
                reason="Matched exact style negative rule",
                source="project",
            )
        ],
    )

    style_step = step_map["style"]
    assert style_step.status == "waiting_user_review"
    assert run.status == "waiting_user_review"
    assert style_step.effective_output_snapshot["hard_negative_hits"] == ["sermon"]
    assert style_step.effective_output_snapshot["rewrite_suggestions"]


def test_run_scene_workflow_keeps_soft_negative_as_completed(monkeypatch):
    run, step_map = _execute_style_workflow(
        monkeypatch,
        [
            StyleNegativeMatch(
                rule_id="soft-1",
                label="too-purple",
                severity="soft",
                match_mode="tag",
                matched_text="too-purple",
                reason="Matched tag style negative rule",
                source="project",
            )
        ],
    )

    style_step = step_map["style"]
    assert style_step.status == "completed"
    assert run.status == "completed"
    assert style_step.effective_output_snapshot["soft_negative_hits"] == ["too-purple"]
    assert style_step.effective_output_snapshot["negative_matches"][0]["label"] == "too-purple"


def _execute_style_workflow(monkeypatch, negative_matches, *, provider_mode="live", fixture_scenario="happy_path"):
    db = _FakeDB()
    scene = SimpleNamespace(
        id=uuid4(),
        chapter_id=uuid4(),
        title="Night Dock",
        goal="Escape",
        conflict="Storm",
        outcome="Temporary shelter",
        must_include=[],
        must_avoid=[],
        draft_text="Rain hit the roof.",
        scene_version=1,
    )
    payload = WorkflowSceneRequest(scene_id=scene.id, branch_id=None, length="medium", guidance=[], auto_apply=False, provider_mode=provider_mode, fixture_scenario=fixture_scenario)
    run = _fake_run(status="queued", current_step="queued", quality_degraded=False, input_payload={"scene_version": 1, "fixture_scenario": fixture_scenario}, provider_mode=provider_mode, fixture_version="v1" if provider_mode == "smoke_fixture" else None)
    step_map = {}

    monkeypatch.setattr(
        "app.services.workflow_service.build_scene_context",
        lambda *args, **kwargs: {
            "context_compile_snapshot": {"summary_reason": "none", "candidates": [], "clipped_sources": []},
            "recent_scenes": [],
            "lore_constraints": [],
            "style_memories": [],
        },
    )
    monkeypatch.setattr("app.services.workflow_service._resolve_project_id", lambda *args, **kwargs: run.project_id)
    monkeypatch.setattr("app.services.workflow_service._heartbeat_run", lambda db, run: run)
    monkeypatch.setattr("app.services.workflow_service._latest_workflow_steps", lambda *args, **kwargs: dict(step_map))

    def _fake_create_step(db, *, run, step_key, input_snapshot, parent_step_id=None):
        step = _fake_step(step_key, input_payload=input_snapshot, parent_step_id=parent_step_id)
        step_map[step_key] = step
        return step

    def _fake_finish_step(
        db,
        *,
        run,
        step,
        status,
        machine_output_snapshot=None,
        effective_output_snapshot=None,
        error_message=None,
        gateway_result=None,
        user_edited=False,
        edited_reason=None,
        guardrail_blocked=None,
        fallback_used=None,
    ):
        step.status = status
        step.machine_output_snapshot = machine_output_snapshot
        step.effective_output_snapshot = effective_output_snapshot if effective_output_snapshot is not None else machine_output_snapshot
        step.output_payload = step.effective_output_snapshot
        step.error_message = error_message
        step.provider_mode = run.provider_mode
        step.provider = gateway_result.provider if gateway_result else step.provider
        step.model = gateway_result.model if gateway_result else step.model
        step.profile_name = gateway_result.profile_name if gateway_result else step.profile_name
        step.fallback_used = fallback_used if fallback_used is not None else (gateway_result.fallback_used if gateway_result else False)
        step.fallback_count = max(len(gateway_result.attempts) - 1, 0) if gateway_result else 0
        step.edited_reason = edited_reason
        step_map[step.step_key] = step
        return step

    def _fake_set_run_state(
        db,
        *,
        run,
        status,
        current_step=None,
        error_message=None,
        output_payload=None,
        completed=False,
        needs_merge=None,
        quality_degraded=None,
        resume_from_step=None,
    ):
        run.status = status
        if current_step is not None:
            run.current_step = current_step
        if error_message is not None:
            run.error_message = error_message
        if output_payload is not None:
            run.output_payload = output_payload
        if needs_merge is not None:
            run.needs_merge = needs_merge
        if quality_degraded is not None:
            run.quality_degraded = quality_degraded
        if resume_from_step is not None:
            run.resume_from_step = resume_from_step
        return run

    @contextmanager
    def _noop_lock(*args, **kwargs):
        yield None

    def _fake_call_ai_gateway(
        db,
        *,
        task_type,
        workflow_step=None,
        prompt=None,
        params=None,
        provider_mode="live",
        fixture_scenario="happy_path",
    ):
        fixture_provider = "fixture" if provider_mode == "smoke_fixture" else None
        fixture_model = "smoke-fixture" if provider_mode == "smoke_fixture" else None
        fixture_attempt_no = int((params or {}).get("fixture_attempt_no") or 1)
        if workflow_step == "planner" and fixture_scenario == "malformed_planner":
            plan_text = "[fixture-malformed-planner]"
        else:
            plan_text = "plan summary"
        if workflow_step == "style":
            if fixture_scenario == "style_fail" and fixture_attempt_no <= 1:
                raise RuntimeError("fixture style failure")
            return GatewayCallResult(
                text="Summary: revised scene.\n\nRewrite notes: tighten the imagery and explain the emotional stakes." if fixture_scenario == "guard_block" else "styled prose with flourish",
                provider=fixture_provider or "xai",
                model=fixture_model or "grok-2-latest",
                task_type=task_type,
                latency_ms=222,
                fallback_used=False,
                quality_degraded=False,
                profile_name=f"fixture-style-{fixture_scenario}" if provider_mode == "smoke_fixture" else "style-primary",
                attempts=[{"status": "success"}],
                token_usage={"prompt_tokens": 11, "completion_tokens": 22},
                cost_estimate=0.01,
            )
        return GatewayCallResult(
            text=plan_text,
            provider=fixture_provider or "deepseek",
            model=fixture_model or "deepseek-chat",
            task_type=task_type,
            latency_ms=111,
            fallback_used=False,
            quality_degraded=False,
            profile_name=f"fixture-planner-{fixture_scenario}" if provider_mode == "smoke_fixture" else "planner-primary",
            attempts=[{"status": "success"}],
            token_usage={"prompt_tokens": 5, "completion_tokens": 7},
            cost_estimate=0.001,
        )

    monkeypatch.setattr("app.services.workflow_service._create_step", _fake_create_step)
    monkeypatch.setattr("app.services.workflow_service._finish_step", _fake_finish_step)
    monkeypatch.setattr("app.services.workflow_service._set_run_state", _fake_set_run_state)
    monkeypatch.setattr("app.services.workflow_service._vram_lock", _noop_lock)
    monkeypatch.setattr("app.services.workflow_service.call_ai_gateway", _fake_call_ai_gateway)
    monkeypatch.setattr("app.services.workflow_service.analyze_scene", lambda *args, **kwargs: (_ModelDump(summary="analysis"), None, GatewayCallResult(text='{"summary":"analysis","scene_goal_detected":"goal","emotional_flow":[],"problems":[],"suggestions":[]}', provider="fixture" if provider_mode == "smoke_fixture" else "deepseek", model="smoke-fixture" if provider_mode == "smoke_fixture" else "deepseek-chat", task_type="analyze", latency_ms=0, fallback_used=False, quality_degraded=False, profile_name="fixture-analyze-happy_path" if provider_mode == "smoke_fixture" else "analyze-primary", attempts=[{"status": "success"}], token_usage={"prompt_tokens": 0, "completion_tokens": 0}, cost_estimate=0.0)))
    monkeypatch.setattr("app.services.workflow_service.write_scene", lambda *args, **kwargs: (_ModelDump(draft_text="base draft"), None, GatewayCallResult(text="base draft", provider="fixture" if provider_mode == "smoke_fixture" else "openai", model="smoke-fixture" if provider_mode == "smoke_fixture" else "gpt-4o-mini", task_type="write", latency_ms=0, fallback_used=False, quality_degraded=False, profile_name="fixture-write-happy_path" if provider_mode == "smoke_fixture" else "write-primary", attempts=[{"status": "success"}], token_usage={"prompt_tokens": 0, "completion_tokens": 0}, cost_estimate=0.0)))
    monkeypatch.setattr("app.services.workflow_service.scan_scene_consistency", lambda *args, **kwargs: (([SimpleNamespace(message="Fixture check issue")] if fixture_scenario == "check_issue" else []), GatewayCallResult(text='[{"type":"timeline_conflict","message":"Fixture check issue"}]' if fixture_scenario == "check_issue" else "[]", provider="fixture" if provider_mode == "smoke_fixture" else "ollama", model="smoke-fixture" if provider_mode == "smoke_fixture" else "qwen2.5:3b", task_type="check", latency_ms=0, fallback_used=False, quality_degraded=False, profile_name=f"fixture-check-{fixture_scenario}" if provider_mode == "smoke_fixture" else "check-primary", attempts=[{"status": "success"}], token_usage={"prompt_tokens": 0, "completion_tokens": 0}, cost_estimate=0.0)))
    monkeypatch.setattr("app.services.workflow_service.build_guard_output", lambda text: GuardOutput(safe_to_apply=True))
    monkeypatch.setattr("app.services.workflow_service._store_workflow_result", lambda *args, **kwargs: (None, False))
    monkeypatch.setattr("app.services.workflow_service._create_memory_candidate", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.workflow_service.resolve_style_negative_rules", lambda *args, **kwargs: [])
    monkeypatch.setattr("app.services.workflow_service.match_style_negative_rules", lambda *args, **kwargs: list(negative_matches))

    _run_scene_workflow(db, scene=scene, payload=payload, run=run)
    return run, step_map


def test_run_scene_workflow_smoke_fixture_records_provider_metadata(monkeypatch):
    run, step_map = _execute_style_workflow(monkeypatch, [], provider_mode="smoke_fixture")

    assert run.provider_mode == "smoke_fixture"
    assert run.fixture_version == "v1"
    assert step_map["analyze"].provider_mode == "smoke_fixture"
    assert step_map["analyze"].provider == "fixture"
    assert step_map["write"].model == "smoke-fixture"
    assert step_map["check"].profile_name == "fixture-check-happy_path"


def test_run_scene_workflow_smoke_fixture_planner_wait_review(monkeypatch):
    run, step_map = _execute_style_workflow(monkeypatch, [], provider_mode="smoke_fixture", fixture_scenario="planner_wait_review")

    assert run.status == "waiting_user_review"
    assert run.resume_from_step == "write"
    assert step_map["plan"].status == "waiting_user_review"
    assert step_map["plan"].provider_mode == "smoke_fixture"


def test_run_scene_workflow_smoke_fixture_guard_block(monkeypatch):
    run, step_map = _execute_style_workflow(monkeypatch, [], provider_mode="smoke_fixture", fixture_scenario="guard_block")

    assert run.status == "waiting_user_review"
    assert step_map["guard"].status == "waiting_user_review"
    assert step_map["guard"].effective_output_snapshot["safe_to_apply"] is False
    assert step_map["store"].status == "waiting_user_review"


def test_run_scene_workflow_smoke_fixture_malformed_planner(monkeypatch):
    run, step_map = _execute_style_workflow(monkeypatch, [], provider_mode="smoke_fixture", fixture_scenario="malformed_planner")

    assert run.status == "failed"
    assert step_map["plan"].status == "failed"
    assert "planner output is not valid plan text" in (run.error_message or "")
