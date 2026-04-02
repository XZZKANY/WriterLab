from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.scene import Scene
from app.models.story_branch import StoryBranch
from app.models.style_memory import StyleMemory
from app.models.vram_lock import VRAMLock
from app.models.workflow_request_dedup import WorkflowRequestDedup
from app.models.workflow_run import WorkflowRun
from app.models.workflow_step import WorkflowStep
from app.schemas.workflow import GuardOutput, OverrideStepRequest, PlannerOutput, ResumeWorkflowRequest, StyleOutput, Violation, WorkflowSceneRequest
from app.services.ai.ai_gateway_service import FIXTURE_VERSION, GatewayCallResult, call_ai_gateway
from app.services.ai_output_guardrails import build_guard_output
from app.services.consistency.consistency_service import scan_scene_consistency
from app.services.context.context_service import build_scene_context
from app.services.knowledge.knowledge_service import create_style_memory
from app.services.runtime_events import publish_runtime_event
from app.services.scene_analysis_service import analyze_scene
from app.services.scene_version_service import create_scene_version
from app.services.scene_write_service import write_scene
from app.services.style_negative_service import match_style_negative_rules, resolve_style_negative_rules

STEP_ORDER = {"analyze": 10, "plan": 20, "write": 30, "style": 40, "check": 50, "guard": 60, "store": 70, "memory": 80}
STEP_SEQUENCE = [key for key, _ in sorted(STEP_ORDER.items(), key=lambda item: item[1])]
RUN_TERMINAL_STATUSES = {"completed", "partial_success", "failed", "cancelled"}
STEP_REUSABLE_STATUSES = {"completed", "skipped"}
LEASE_SECONDS = 45
RUNNER_POLL_SECONDS = 1.0
RUNNER_ID = f"workflow-runner-{os.getpid()}"
WORKFLOW_SCHEMA_VERSION = "workflow_step.v2"
VRAM_LOCK_TTL_SECONDS = int(os.getenv("WRITERLAB_VRAM_LOCK_TTL_SECONDS", "60"))

_WORKFLOW_RUNNER_LOCK = threading.Lock()
_WORKFLOW_RUNNER_STARTED = False

STEP_AGENT_META = {
    "bootstrap": {"agent_key": "orchestrator", "agent_name": "Workflow Orchestrator", "agent_label": "Workflow Orchestrator"},
    "queued": {"agent_key": "orchestrator", "agent_name": "Workflow Orchestrator", "agent_label": "Workflow Orchestrator"},
    "analyze": {"agent_key": "planner", "agent_name": "Planner Agent", "agent_label": "Planner Agent"},
    "plan": {"agent_key": "planner", "agent_name": "Planner Agent", "agent_label": "Planner Agent"},
    "write": {"agent_key": "writer", "agent_name": "Writer Agent", "agent_label": "Writer Agent"},
    "style": {"agent_key": "style", "agent_name": "Style Agent", "agent_label": "Style Agent"},
    "check": {"agent_key": "consistency", "agent_name": "Consistency Agent", "agent_label": "Consistency Agent"},
    "guard": {"agent_key": "guardrail", "agent_name": "Guardrail Agent", "agent_label": "Guardrail Agent"},
    "store": {"agent_key": "store", "agent_name": "Store Agent", "agent_label": "Store Agent"},
    "memory": {"agent_key": "memory_curator", "agent_name": "Memory Curator Agent", "agent_label": "Memory Curator Agent"},
    "done": {"agent_key": "orchestrator", "agent_name": "Workflow Orchestrator", "agent_label": "Workflow Orchestrator"},
}


def _utcnow() -> datetime:
    return datetime.utcnow()


def _hash_json(payload: dict | None) -> str | None:
    if payload is None:
        return None
    data = json.dumps(jsonable_encoder(payload), sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _agent_meta(step_key: str) -> dict[str, str]:
    return STEP_AGENT_META.get(step_key, STEP_AGENT_META["bootstrap"]).copy()


def _with_agent_meta(step_key: str, payload: dict | None = None) -> dict:
    data = payload.copy() if payload else {}
    data.update(_agent_meta(step_key))
    return data


def _attach_step_attempts(step: WorkflowStep) -> WorkflowStep:
    attempts = []
    if isinstance(step.output_payload, dict):
        raw_attempts = step.output_payload.get("attempts")
        if isinstance(raw_attempts, list):
            attempts = raw_attempts
    setattr(step, "attempts", attempts)
    return step


def _resolve_project_id(scene: Scene, db: Session):
    chapter = db.query(Chapter).filter(Chapter.id == scene.chapter_id).first()
    if not chapter:
        return None
    book = db.query(Book).filter(Book.id == chapter.book_id).first()
    return book.project_id if book else None


def _queue_depth(db: Session) -> int:
    return db.query(WorkflowRun).filter(WorkflowRun.status.in_(["queued", "queued_resume"])).count()


def _publish_run_event(db: Session, *, run: WorkflowRun, event: str, step: str | None = None, provider: str | None = None, model: str | None = None, message: str | None = None) -> None:
    publish_runtime_event(
        {
            "event": event,
            "run_id": str(run.id),
            "step": step or run.current_step,
            "provider": provider,
            "model": model,
            "source": "workflow",
            "queue_depth": _queue_depth(db),
            "can_cancel": run.status not in RUN_TERMINAL_STATUSES,
            "message": message,
        }
    )


def _resolve_gateway_tokens(result: GatewayCallResult | None) -> tuple[int | None, int | None]:
    usage = result.token_usage if result else None
    if not usage:
        return None, None
    prompt_tokens = usage.get("prompt_tokens") or usage.get("input_tokens")
    completion_tokens = usage.get("completion_tokens") or usage.get("output_tokens")
    return int(prompt_tokens) if prompt_tokens is not None else None, int(completion_tokens) if completion_tokens is not None else None


def _next_step_key(step_key: str | None) -> str | None:
    if step_key not in STEP_ORDER:
        return STEP_SEQUENCE[0] if STEP_SEQUENCE else None
    for key in STEP_SEQUENCE:
        if STEP_ORDER[key] > STEP_ORDER[step_key]:
            return key
    return None


def _planner_prompt(scene: Scene, bundle: dict, guidance: list[str]) -> str:
    return "\n".join([f"Scene title: {scene.title}", f"Goal: {scene.goal or ''}", f"Conflict: {scene.conflict or ''}", f"Outcome target: {scene.outcome or ''}", f"Guidance: {guidance}", f"Recent scenes: {bundle.get('recent_scenes', [])}", f"Lore constraints: {[item.title for item in bundle.get('lore_constraints', [])]}", "Produce a concise plan."])


def _style_prompt(scene: Scene, draft_text: str, bundle: dict) -> str:
    return "\n".join(["Rewrite the following scene prose while preserving continuity.", f"Scene title: {scene.title}", f"Must include: {scene.must_include or []}", f"Must avoid: {scene.must_avoid or []}", f"Style memory: {[item.content for item in bundle.get('style_memories', [])]}", "Return only scene prose.", draft_text])


def _build_memory_candidate(scene: Scene, payload: WorkflowSceneRequest, final_text: str) -> tuple[str, list[str]]:
    guidance_rules = [item.strip() for item in payload.guidance if item and item.strip()]
    if guidance_rules:
        return (f"Workflow style candidate for {scene.title or 'scene'}: " + " | ".join(guidance_rules[:4]), guidance_rules[:6])
    return (
        f"Workflow style candidate for {scene.title or 'scene'} based on accepted draft tone.",
        ["Use 中文小说正文 cadence instead of commentary.", "Avoid overexplaining motivations in narration."],
    )


def _create_memory_candidate(db: Session, *, scene: Scene, payload: WorkflowSceneRequest, project_id, final_text: str) -> StyleMemory | None:
    if not project_id or not final_text.strip():
        return None
    content, rules = _build_memory_candidate(scene, payload, final_text)
    existing = db.query(StyleMemory).filter(StyleMemory.project_id == project_id, StyleMemory.scene_id == scene.id, StyleMemory.memory_type == "workflow_style_candidate", StyleMemory.content == content).order_by(StyleMemory.updated_at.desc(), StyleMemory.created_at.desc()).first()
    if existing:
        return existing
    return create_style_memory(db, project_id=project_id, scene_id=scene.id, memory_type="workflow_style_candidate", content=content, source_excerpt=final_text[:240], derived_rules=rules, user_confirmed=False, status="suggested", scope_type="scene", scope_id=scene.id)


def _fixture_version_for_mode(provider_mode: str) -> str | None:
    return FIXTURE_VERSION if provider_mode == "smoke_fixture" else None


def _run_fixture_scenario(run: WorkflowRun) -> str | None:
    value = (run.input_payload or {}).get("fixture_scenario")
    return str(value) if value else None


def _attach_run_transient_fields(db: Session, run: WorkflowRun | None) -> WorkflowRun | None:
    if run is None:
        return None
    run.resume_checkpoint = _stable_resume_checkpoint(db, run.id)
    run.fixture_scenario = _run_fixture_scenario(run)
    return run


def _create_run(db: Session, *, scene: Scene, payload: WorkflowSceneRequest, status: str = "queued") -> WorkflowRun:
    now = _utcnow()
    run = WorkflowRun(
        project_id=_resolve_project_id(scene, db),
        scene_id=scene.id,
        branch_id=payload.branch_id,
        run_type="scene_pipeline",
        status=status,
        current_step="queued" if status == "queued" else "bootstrap",
        provider_mode=payload.provider_mode,
        fixture_version=_fixture_version_for_mode(payload.provider_mode),
        input_payload=jsonable_encoder({**payload.model_dump(), "scene_version": scene.scene_version}),
        queued_at=now,
        heartbeat_at=None if status == "queued" else now,
        lease_expires_at=None if status == "queued" else now + timedelta(seconds=LEASE_SECONDS),
        started_at=None if status == "queued" else now,
        needs_merge=False,
        quality_degraded=False,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    _publish_run_event(db, run=run, event="workflow_queued", message=run.status)
    return _attach_run_transient_fields(db, run)


def _set_run_state(db: Session, *, run: WorkflowRun, status: str, current_step: str | None = None, error_message: str | None = None, output_payload: dict | None = None, completed: bool = False, needs_merge: bool | None = None, quality_degraded: bool | None = None, resume_from_step: str | None = None) -> WorkflowRun:
    now = _utcnow()
    run.status = status
    if current_step is not None:
        run.current_step = current_step
    if error_message is not None:
        run.error_message = error_message
    if output_payload is not None:
        run.output_payload = jsonable_encoder(output_payload)
    if needs_merge is not None:
        run.needs_merge = needs_merge
    if quality_degraded is not None:
        run.quality_degraded = quality_degraded
    if resume_from_step is not None:
        run.resume_from_step = resume_from_step
    if status in {"running", "queued", "queued_resume"}:
        run.worker_id = RUNNER_ID if status == "running" else None
        run.heartbeat_at = now if status == "running" else None
        run.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS) if status == "running" else None
        run.started_at = run.started_at or now
    if completed:
        run.completed_at = now
        run.worker_id = None
        run.heartbeat_at = None
        run.lease_expires_at = None
        if status == "cancelled" and run.cancelled_at is None:
            run.cancelled_at = now
    db.add(run)
    db.commit()
    db.refresh(run)
    _publish_run_event(db, run=run, event=f"workflow_{status}", message=error_message or status)
    if status == "waiting_user_review":
        _publish_run_event(db, run=run, event="workflow_waiting_review", message=error_message or status)
    return _attach_run_transient_fields(db, run)


def _heartbeat_run(db: Session, run: WorkflowRun) -> WorkflowRun:
    run.heartbeat_at = _utcnow()
    run.lease_expires_at = run.heartbeat_at + timedelta(seconds=LEASE_SECONDS)
    run.worker_id = RUNNER_ID
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _all_workflow_steps(db: Session, workflow_id: UUID) -> list[WorkflowStep]:
    return db.query(WorkflowStep).filter(WorkflowStep.workflow_run_id == workflow_id).order_by(WorkflowStep.step_order.asc(), WorkflowStep.attempt_no.asc(), WorkflowStep.created_at.asc()).all()


def _latest_step_for_key(db: Session, workflow_id: UUID, step_key: str) -> WorkflowStep | None:
    return db.query(WorkflowStep).filter(WorkflowStep.workflow_run_id == workflow_id, WorkflowStep.step_key == step_key).order_by(WorkflowStep.attempt_no.desc(), WorkflowStep.created_at.desc()).first()


def _latest_workflow_steps(db: Session, workflow_id: UUID) -> dict[str, WorkflowStep]:
    latest: dict[str, WorkflowStep] = {}
    for step in _all_workflow_steps(db, workflow_id):
        if step.status == "invalidated":
            continue
        latest[step.step_key] = step
    return latest


def _stable_resume_checkpoint(db: Session, workflow_id: UUID) -> str | None:
    step_map = _latest_workflow_steps(db, workflow_id)
    last_completed = None
    for key in STEP_SEQUENCE:
        step = step_map.get(key)
        if step is None:
            break
        if step.status in STEP_REUSABLE_STATUSES:
            last_completed = key
            continue
        break
    return last_completed


def _create_step(db: Session, *, run: WorkflowRun, step_key: str, input_snapshot: dict | None, parent_step_id: UUID | None = None) -> WorkflowStep:
    latest = _latest_step_for_key(db, run.id, step_key)
    payload = jsonable_encoder(_with_agent_meta(step_key, input_snapshot or {}))
    step = WorkflowStep(
        workflow_run_id=run.id,
        step_key=step_key,
        step_order=STEP_ORDER[step_key],
        schema_version=WORKFLOW_SCHEMA_VERSION,
        version=(latest.version + 1) if latest else 1,
        attempt_no=(latest.attempt_no + 1) if latest else 1,
        parent_step_id=parent_step_id or (latest.id if latest else None),
        status="running",
        provider_mode=run.provider_mode,
        input_payload=payload,
        input_hash=_hash_json(payload),
        started_at=_utcnow(),
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    _set_run_state(db, run=run, status="running", current_step=step_key)
    _publish_run_event(db, run=run, event="step_started", step=step_key, message=f"{step_key} started")
    return step


def _finish_step(db: Session, *, run: WorkflowRun, step: WorkflowStep, status: str, machine_output_snapshot: dict | None = None, effective_output_snapshot: dict | None = None, error_message: str | None = None, gateway_result: GatewayCallResult | None = None, user_edited: bool = False, edited_reason: str | None = None, guardrail_blocked: bool | None = None, fallback_used: bool | None = None) -> WorkflowStep:
    now = _utcnow()
    prompt_tokens, completion_tokens = _resolve_gateway_tokens(gateway_result)
    payload = effective_output_snapshot if effective_output_snapshot is not None else machine_output_snapshot
    attempts = jsonable_encoder(gateway_result.attempts) if gateway_result else []
    payload_with_meta = _with_agent_meta(step.step_key, payload or {}) if payload is not None else None
    if payload_with_meta is not None:
        payload_with_meta["attempts"] = attempts
        payload_with_meta["fallback_count"] = max((len(attempts) - 1), 0)
        payload_with_meta["quality_degraded"] = bool(gateway_result.quality_degraded) if gateway_result else False
    step.status = status
    step.provider_mode = run.provider_mode
    step.provider = gateway_result.provider if gateway_result else step.provider
    step.model = gateway_result.model if gateway_result else step.model
    step.profile_name = gateway_result.profile_name if gateway_result else step.profile_name
    step.output_payload = jsonable_encoder(payload_with_meta) if payload_with_meta is not None else None
    step.machine_output_snapshot = jsonable_encoder(machine_output_snapshot) if machine_output_snapshot is not None else None
    step.effective_output_snapshot = jsonable_encoder(effective_output_snapshot) if effective_output_snapshot is not None else step.machine_output_snapshot
    step.output_hash = _hash_json(step.effective_output_snapshot)
    step.error_message = error_message
    step.fallback_used = fallback_used if fallback_used is not None else (gateway_result.fallback_used if gateway_result else step.fallback_used)
    step.fallback_count = max((len(gateway_result.attempts) - 1), 0) if gateway_result else step.fallback_count
    step.guardrail_blocked = guardrail_blocked
    step.user_edited = user_edited
    step.edited_at = now if user_edited else None
    step.edited_reason = edited_reason
    step.prompt_tokens = prompt_tokens
    step.completion_tokens = completion_tokens
    step.finished_at = now
    step.latency_ms = gateway_result.latency_ms if gateway_result else step.latency_ms
    step.duration_ms = max(int((now - (step.started_at or now)).total_seconds() * 1000), 0)
    run.quality_degraded = run.quality_degraded or bool(gateway_result.quality_degraded if gateway_result else False)
    db.add(run)
    db.add(step)
    db.commit()
    db.refresh(step)
    _attach_step_attempts(step)
    _publish_run_event(db, run=run, event=f"step_{status}", step=step.step_key, provider=step.provider, model=step.model, message=error_message or status)
    return step


def _extract_effective_snapshot(step: WorkflowStep | None) -> dict[str, Any]:
    if not step:
        return {}
    return step.effective_output_snapshot or step.output_payload or {}


def _build_planner_output(raw_plan: str, *, scene: Scene, guidance: list[str]) -> PlannerOutput:
    normalized = (raw_plan or "").strip()
    if not normalized or normalized == "[fixture-malformed-planner]":
        raise ValueError("planner output is not valid plan text")
    return PlannerOutput(
        summary=normalized[:500] or "No summary",
        writing_goals=guidance[:5],
        constraints=list(scene.must_avoid or []),
        next_prompt_hints=list(scene.must_include or []),
        raw_plan=normalized,
    )


def _extract_planner_output(step: WorkflowStep | None) -> PlannerOutput | None:
    snapshot = _extract_effective_snapshot(step)
    if not snapshot:
        return None
    try:
        return PlannerOutput(**snapshot)
    except Exception:
        raw_plan = str(snapshot.get("raw_plan") or snapshot.get("plan") or "").strip()
        return PlannerOutput(summary=raw_plan[:500] or "No summary", raw_plan=raw_plan) if raw_plan else None


def _fixture_guard_output(final_text: str, *, fixture_scenario: str) -> GuardOutput | None:
    if fixture_scenario != "guard_block":
        return None
    return GuardOutput(
        safe_to_apply=False,
        needs_rewrite=True,
        needs_user_review=True,
        violations=[
            Violation(
                type="guard_violation",
                span=None,
                rule_id="guard.fixture_block",
                severity="high",
                reason="Fixture scenario forced a guard block for acceptance coverage.",
                suggestion="Review the deterministic guard-block scenario output before applying.",
            )
        ],
    )


def _extract_final_text(step_map: dict[str, WorkflowStep]) -> str:
    style_step = step_map.get("style")
    if style_step and style_step.status == "completed":
        value = _extract_effective_snapshot(style_step).get("styled_text")
        if isinstance(value, str) and value.strip():
            return value.strip()
    write_step = step_map.get("write")
    if write_step and write_step.status == "completed":
        value = _extract_effective_snapshot(write_step).get("draft_text")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_version_id(step_map: dict[str, WorkflowStep]) -> str | None:
    value = _extract_effective_snapshot(step_map.get("store")).get("version_id") if step_map.get("store") else None
    return str(value) if value else None


def _extract_memory_id(step_map: dict[str, WorkflowStep]) -> str | None:
    value = _extract_effective_snapshot(step_map.get("memory")).get("memory_id") if step_map.get("memory") else None
    return str(value) if value else None


def _should_reuse_step(step: WorkflowStep | None, resume_from_step: str | None, step_key: str) -> bool:
    if not step or step.status not in STEP_REUSABLE_STATUSES:
        return False
    return not resume_from_step or STEP_ORDER[step_key] < STEP_ORDER.get(resume_from_step, 0)


def _record_dedup_response(db: Session, *, run: WorkflowRun, endpoint: str, idempotency_key: str, request_payload: dict, response_payload: dict) -> None:
    row = db.query(WorkflowRequestDedup).filter(WorkflowRequestDedup.workflow_run_id == run.id, WorkflowRequestDedup.endpoint == endpoint, WorkflowRequestDedup.idempotency_key == idempotency_key).first()
    if row is None:
        row = WorkflowRequestDedup(workflow_run_id=run.id, endpoint=endpoint, idempotency_key=idempotency_key)
    row.request_payload = jsonable_encoder(request_payload)
    row.response_payload = jsonable_encoder(response_payload)
    db.add(row)
    db.commit()


def _existing_dedup_response(db: Session, *, run: WorkflowRun, endpoint: str, idempotency_key: str) -> dict | None:
    row = db.query(WorkflowRequestDedup).filter(WorkflowRequestDedup.workflow_run_id == run.id, WorkflowRequestDedup.endpoint == endpoint, WorkflowRequestDedup.idempotency_key == idempotency_key).first()
    return row.response_payload if row else None


def _invalidate_downstream_steps(db: Session, *, run: WorkflowRun, source_step: WorkflowStep) -> None:
    for step in _latest_workflow_steps(db, run.id).values():
        if step.step_order <= source_step.step_order or step.status in {"invalidated", "cancelled"}:
            continue
        step.status = "invalidated"
        step.invalidated_by_step = source_step.id
        step.finished_at = _utcnow()
        db.add(step)
    db.commit()


@contextmanager
def _vram_lock(db: Session, *, resource_key: str, lock_reason: str):
    now = _utcnow()
    lock = db.query(VRAMLock).filter(VRAMLock.resource_key == resource_key).first()
    if lock and lock.heartbeat_at and lock.heartbeat_at + timedelta(seconds=lock.ttl_seconds) < now:
        db.delete(lock)
        db.commit()
        lock = None
    if lock is None:
        lock = VRAMLock(resource_key=resource_key, lock_owner=RUNNER_ID, lock_reason=lock_reason, acquired_at=now, ttl_seconds=VRAM_LOCK_TTL_SECONDS, heartbeat_at=now)
        db.add(lock)
        db.commit()
        db.refresh(lock)
    try:
        yield lock
    finally:
        fresh = db.query(VRAMLock).filter(VRAMLock.resource_key == resource_key).first()
        if fresh and fresh.lock_owner == RUNNER_ID:
            db.delete(fresh)
            db.commit()


def _store_workflow_result(db: Session, *, run: WorkflowRun, scene: Scene, payload: WorkflowSceneRequest, store_step: WorkflowStep, final_text: str) -> tuple[str | None, bool]:
    if not payload.auto_apply or not final_text.strip():
        _finish_step(db, run=run, step=store_step, status="skipped", machine_output_snapshot={"stored": False, "reason": "auto_apply disabled"}, effective_output_snapshot={"stored": False, "reason": "auto_apply disabled"})
        return None, False
    expected_scene_version = int((run.input_payload or {}).get("scene_version") or scene.scene_version or 1)
    db.refresh(scene)
    if scene.scene_version != expected_scene_version:
        _finish_step(db, run=run, step=store_step, status="waiting_user_review", machine_output_snapshot={"stored": False, "needs_merge": True}, effective_output_snapshot={"stored": False, "needs_merge": True, "version_id": None}, error_message="Scene version changed during workflow execution")
        return None, True
    scene.draft_text = final_text
    scene.scene_version = (scene.scene_version or 0) + 1
    db.add(scene)
    db.commit()
    db.refresh(scene)
    version = create_scene_version(db, scene_id=scene.id, content=final_text, source="workflow", label="workflow result", scene_version=scene.scene_version, workflow_step_id=store_step.id)
    if payload.branch_id and version is not None:
        branch = db.query(StoryBranch).filter(StoryBranch.id == payload.branch_id).first()
        if branch:
            branch.latest_version_id = version.id
            db.add(branch)
            db.commit()
    _finish_step(db, run=run, step=store_step, status="completed", machine_output_snapshot={"stored": True, "version_id": str(version.id) if version else None}, effective_output_snapshot={"stored": True, "auto_applied": bool(version), "safe_to_apply": True, "version_id": str(version.id) if version else None})
    return str(version.id) if version else None, False


def _workflow_output(run: WorkflowRun, *, planner_output: PlannerOutput | None, final_text: str, version_id: str | None, memory_id: str | None, guard_output: GuardOutput | None, failures: list[dict]) -> dict[str, Any]:
    return {
        "planner_output": planner_output.model_dump() if planner_output else None,
        "final_text": final_text or None,
        "partial_text": (final_text or None) if failures else None,
        "auto_applied": bool(version_id),
        "safe_to_apply": guard_output.safe_to_apply if guard_output else False,
        "needs_rewrite": guard_output.needs_rewrite if guard_output else False,
        "needs_user_review": guard_output.needs_user_review if guard_output else False,
        "violations": [item.model_dump() for item in (guard_output.violations if guard_output else [])],
        "needs_merge": run.needs_merge,
        "quality_degraded": run.quality_degraded,
        "version_id": version_id,
        "memory_id": memory_id,
        "step_failures": failures,
    }


def _run_scene_workflow(db: Session, *, scene: Scene, payload: WorkflowSceneRequest, run: WorkflowRun) -> WorkflowRun:
    failures: list[dict[str, Any]] = []
    fixture_scenario = _run_fixture_scenario(run) or payload.fixture_scenario
    bundle = build_scene_context(scene, db, branch_id=payload.branch_id)
    run.context_compile_snapshot = jsonable_encoder(bundle.get("context_compile_snapshot"))
    db.add(run)
    db.commit()
    db.refresh(run)
    step_map = _latest_workflow_steps(db, run.id)
    planner_output = _extract_planner_output(step_map.get("plan"))
    final_text = _extract_final_text(step_map)
    guard_output: GuardOutput | None = None
    version_id = _extract_version_id(step_map)
    memory_id = _extract_memory_id(step_map)
    resume_from_step = run.resume_from_step
    _set_run_state(db, run=run, status="running", current_step=resume_from_step or run.current_step or "bootstrap")
    try:
        if not _should_reuse_step(step_map.get("analyze"), resume_from_step, "analyze"):
            analyze_step = _create_step(db, run=run, step_key="analyze", input_snapshot={"scene_id": str(scene.id), "scene_version": scene.scene_version})
            try:
                if (scene.draft_text or "").strip():
                    analysis_result, _, analysis_call = analyze_scene(
                        scene,
                        db,
                        provider_mode=run.provider_mode,
                        fixture_scenario=fixture_scenario,
                        return_gateway_result=True,
                    )
                    _finish_step(db, run=run, step=analyze_step, status="completed", machine_output_snapshot=analysis_result.model_dump(), effective_output_snapshot=analysis_result.model_dump(), gateway_result=analysis_call)
                else:
                    _finish_step(db, run=run, step=analyze_step, status="skipped", machine_output_snapshot={"reason": "scene has no draft"}, effective_output_snapshot={"reason": "scene has no draft"})
            except Exception as exc:
                failures.append({"step": "analyze", "error": str(exc)})
                _finish_step(db, run=run, step=analyze_step, status="failed", machine_output_snapshot={"error_summary": str(exc)}, effective_output_snapshot={"error_summary": str(exc)}, error_message=str(exc))
        _heartbeat_run(db, run)
        step_map = _latest_workflow_steps(db, run.id)
        if not _should_reuse_step(step_map.get("plan"), resume_from_step, "plan"):
            planner_step = _create_step(db, run=run, step_key="plan", input_snapshot={"prompt": _planner_prompt(scene, bundle, payload.guidance), "context_bundle": bundle, "params": {"temperature": 0.3}, "scene_version": scene.scene_version, "previous_step_refs": {}})
            planner_call = None
            try:
                with _vram_lock(db, resource_key="writerlab-gpu", lock_reason="plan"):
                    planner_call = call_ai_gateway(
                        db,
                        task_type="analyze",
                        workflow_step="planner",
                        prompt=_planner_prompt(scene, bundle, payload.guidance),
                        params={"temperature": 0.3},
                        provider_mode=run.provider_mode,
                        fixture_scenario=fixture_scenario,
                    )
                planner_output = _build_planner_output(planner_call.text, scene=scene, guidance=payload.guidance)
                planner_effective = planner_output.model_dump()
                planner_machine = {"raw_plan": planner_call.text.strip()}
                if run.provider_mode == "smoke_fixture" and fixture_scenario == "planner_wait_review":
                    _finish_step(
                        db,
                        run=run,
                        step=planner_step,
                        status="waiting_user_review",
                        machine_output_snapshot=planner_machine,
                        effective_output_snapshot=planner_effective,
                        gateway_result=planner_call,
                        error_message="Fixture planner scenario requires manual review",
                        guardrail_blocked=True,
                    )
                    return _set_run_state(
                        db,
                        run=run,
                        status="waiting_user_review",
                        current_step="plan",
                        output_payload=_workflow_output(run, planner_output=planner_output, final_text=final_text, version_id=version_id, memory_id=memory_id, guard_output=guard_output, failures=failures),
                        error_message="planner: fixture manual review",
                        needs_merge=run.needs_merge,
                        quality_degraded=run.quality_degraded,
                        resume_from_step="write",
                    )
                _finish_step(db, run=run, step=planner_step, status="completed", machine_output_snapshot=planner_machine, effective_output_snapshot=planner_effective, gateway_result=planner_call)
            except Exception as exc:
                failures.append({"step": "plan", "error": str(exc)})
                if run.provider_mode == "smoke_fixture":
                    planner_step.provider_mode = run.provider_mode
                    planner_step.provider = "fixture"
                    planner_step.model = "smoke-fixture"
                    planner_step.profile_name = f"fixture-planner-{fixture_scenario}"
                _finish_step(
                    db,
                    run=run,
                    step=planner_step,
                    status="failed",
                    machine_output_snapshot={"error_summary": str(exc)},
                    effective_output_snapshot={"error_summary": str(exc)},
                    error_message=str(exc),
                    gateway_result=planner_call,
                )
                return _set_run_state(
                    db,
                    run=run,
                    status="failed",
                    current_step="plan",
                    error_message=str(exc),
                    output_payload={"step_failures": failures, "error_summary": str(exc), "final_text": final_text or None},
                    completed=True,
                    quality_degraded=run.quality_degraded,
                )
        else:
            planner_output = _extract_planner_output(step_map.get("plan"))
        _heartbeat_run(db, run)
        step_map = _latest_workflow_steps(db, run.id)
        if not _should_reuse_step(step_map.get("write"), resume_from_step, "write"):
            write_step = _create_step(db, run=run, step_key="write", input_snapshot={"prompt": "write_scene", "context_bundle": bundle, "params": {"length": payload.length}, "scene_version": scene.scene_version, "previous_step_refs": {"plan": str(step_map.get("plan").id) if step_map.get("plan") else None}})
            try:
                write_result, _, write_call = write_scene(
                    scene,
                    db,
                    payload.length,
                    payload.guidance,
                    persist_version=False,
                    provider_mode=run.provider_mode,
                    fixture_scenario=fixture_scenario,
                    return_gateway_result=True,
                )
                final_text = write_result.draft_text
                _finish_step(db, run=run, step=write_step, status="completed", machine_output_snapshot=write_result.model_dump(), effective_output_snapshot=write_result.model_dump(), gateway_result=write_call)
            except Exception as exc:
                _finish_step(db, run=run, step=write_step, status="failed", machine_output_snapshot={"error_summary": str(exc)}, effective_output_snapshot={"error_summary": str(exc)}, error_message=str(exc))
                return _set_run_state(db, run=run, status="failed", current_step="write", error_message=str(exc), output_payload={"step_failures": [{"step": "write", "error": str(exc)}]}, completed=True)
        else:
            final_text = _extract_final_text(step_map)
        _heartbeat_run(db, run)
        step_map = _latest_workflow_steps(db, run.id)
        if not _should_reuse_step(step_map.get("style"), resume_from_step, "style"):
            style_step = _create_step(db, run=run, step_key="style", input_snapshot={"prompt": _style_prompt(scene, final_text, bundle), "context_bundle": bundle, "params": {"temperature": 0.4}, "scene_version": scene.scene_version, "previous_step_refs": {"write": str(step_map.get("write").id) if step_map.get("write") else None}})
            style_call = None
            try:
                with _vram_lock(db, resource_key="writerlab-gpu", lock_reason="style"):
                    style_call = call_ai_gateway(
                        db,
                        task_type="revise",
                        workflow_step="style",
                        prompt=_style_prompt(scene, final_text, bundle),
                        params={"temperature": 0.4, "fixture_attempt_no": style_step.attempt_no},
                        provider_mode=run.provider_mode,
                        fixture_scenario=fixture_scenario,
                    )
                styled_text = style_call.text.strip() or final_text
                negative_rules = resolve_style_negative_rules(
                    db,
                    scene=scene,
                    project_id=run.project_id or _resolve_project_id(scene, db),
                    branch_id=payload.branch_id,
                )
                negative_matches = match_style_negative_rules(styled_text, negative_rules)
                hard_matches = [item for item in negative_matches if item.severity == "hard"]
                soft_matches = [item for item in negative_matches if item.severity == "soft"]
                effective_text = final_text if hard_matches else styled_text
                rewrite_suggestions = [f"{item.label}: {item.reason}" for item in hard_matches]
                rewrite_suggestions.extend(f"{item.label}: tone down or rewrite this style pattern." for item in soft_matches)
                style_output = StyleOutput(
                    machine_output={"styled_text": styled_text},
                    effective_output={"styled_text": effective_text},
                    hard_negative_hits=[item.label for item in hard_matches],
                    soft_negative_hits=[item.label for item in soft_matches],
                    negative_matches=[item.model_dump() for item in negative_matches],
                    rewrite_suggestions=rewrite_suggestions,
                ).model_dump()
                style_output["styled_text"] = effective_text
                if hard_matches:
                    failures.append({"step": "style", "error": "hard negative style hit"})
                    _finish_step(db, run=run, step=style_step, status="waiting_user_review", machine_output_snapshot=style_output, effective_output_snapshot=style_output, error_message="Hard negative style rule matched", gateway_result=style_call, guardrail_blocked=True, fallback_used=style_call.fallback_used)
                else:
                    final_text = effective_text
                    _finish_step(db, run=run, step=style_step, status="completed", machine_output_snapshot=style_output, effective_output_snapshot=style_output, gateway_result=style_call, fallback_used=style_call.fallback_used)
                    run.quality_degraded = run.quality_degraded or style_call.quality_degraded
                    db.add(run)
                    db.commit()
            except Exception as exc:
                failures.append({"step": "style", "error": str(exc)})
                if run.provider_mode == "smoke_fixture":
                    style_step.provider_mode = run.provider_mode
                    style_step.provider = "fixture"
                    style_step.model = "smoke-fixture"
                    style_step.profile_name = f"fixture-style-{fixture_scenario}"
                _finish_step(
                    db,
                    run=run,
                    step=style_step,
                    status="failed",
                    machine_output_snapshot={"error_summary": str(exc)},
                    effective_output_snapshot={"error_summary": str(exc)},
                    error_message=str(exc),
                    gateway_result=style_call,
                )
                return _set_run_state(
                    db,
                    run=run,
                    status="failed",
                    current_step="style",
                    error_message=str(exc),
                    output_payload={"step_failures": failures, "error_summary": str(exc), "final_text": final_text or None},
                    completed=True,
                    quality_degraded=run.quality_degraded,
                )
        else:
            final_text = _extract_final_text(_latest_workflow_steps(db, run.id))
        _heartbeat_run(db, run)
        step_map = _latest_workflow_steps(db, run.id)
        if not _should_reuse_step(step_map.get("check"), resume_from_step, "check"):
            check_step = _create_step(db, run=run, step_key="check", input_snapshot={"draft_length": len(final_text), "scene_version": scene.scene_version})
            try:
                issues, check_call = scan_scene_consistency(
                    db,
                    scene=scene,
                    draft_text=final_text,
                    workflow_run_id=run.id,
                    provider_mode=run.provider_mode,
                    fixture_scenario=fixture_scenario,
                    return_gateway_result=True,
                )
                _finish_step(db, run=run, step=check_step, status="completed", machine_output_snapshot={"issue_count": len(issues), "issues": [issue.message for issue in issues]}, effective_output_snapshot={"issue_count": len(issues), "issues": [issue.message for issue in issues]}, gateway_result=check_call)
            except Exception as exc:
                failures.append({"step": "check", "error": str(exc)})
                _finish_step(db, run=run, step=check_step, status="failed", machine_output_snapshot={"error_summary": str(exc)}, effective_output_snapshot={"error_summary": str(exc)}, error_message=str(exc))
        _heartbeat_run(db, run)
        step_map = _latest_workflow_steps(db, run.id)
        if not _should_reuse_step(step_map.get("guard"), resume_from_step, "guard"):
            guard_step = _create_step(db, run=run, step_key="guard", input_snapshot={"draft_length": len(final_text), "scene_version": scene.scene_version})
            guard_output = _fixture_guard_output(final_text, fixture_scenario=fixture_scenario) or build_guard_output(final_text)
            _finish_step(db, run=run, step=guard_step, status="completed" if guard_output.safe_to_apply else "waiting_user_review", machine_output_snapshot=guard_output.model_dump(), effective_output_snapshot=guard_output.model_dump(), error_message=guard_output.violations[0].reason if guard_output.violations else None, guardrail_blocked=not guard_output.safe_to_apply)
        else:
            guard_output = GuardOutput(**_extract_effective_snapshot(step_map.get("guard"))) if step_map.get("guard") else None
        _heartbeat_run(db, run)
        step_map = _latest_workflow_steps(db, run.id)
        if not _should_reuse_step(step_map.get("store"), resume_from_step, "store"):
            store_step = _create_step(db, run=run, step_key="store", input_snapshot={"auto_apply": payload.auto_apply, "scene_version": scene.scene_version, "previous_step_refs": {"guard": str(step_map.get("guard").id) if step_map.get("guard") else None}})
            if guard_output and guard_output.safe_to_apply:
                version_id, run.needs_merge = _store_workflow_result(db, run=run, scene=scene, payload=payload, store_step=store_step, final_text=final_text)
            else:
                _finish_step(db, run=run, step=store_step, status="waiting_user_review", machine_output_snapshot={"stored": False, "guard_output": guard_output.model_dump() if guard_output else None}, effective_output_snapshot={"stored": False, "safe_to_apply": False, "needs_user_review": True, "violations": [item.model_dump() for item in (guard_output.violations if guard_output else [])]}, error_message="Guardrail requires manual review", guardrail_blocked=True)
                version_id = None
        else:
            version_id = _extract_version_id(step_map)
        _heartbeat_run(db, run)
        step_map = _latest_workflow_steps(db, run.id)
        if not _should_reuse_step(step_map.get("memory"), resume_from_step, "memory"):
            memory_step = _create_step(db, run=run, step_key="memory", input_snapshot={"version_id": version_id, "scene_version": scene.scene_version})
            if not version_id or not final_text.strip():
                _finish_step(db, run=run, step=memory_step, status="skipped", machine_output_snapshot={"memory_created": False}, effective_output_snapshot={"memory_created": False})
                memory_id = None
            else:
                memory = _create_memory_candidate(db, scene=scene, payload=payload, project_id=_resolve_project_id(scene, db), final_text=final_text)
                memory_id = str(memory.id) if memory else None
                _finish_step(db, run=run, step=memory_step, status="completed", machine_output_snapshot={"memory_created": bool(memory_id), "memory_id": memory_id}, effective_output_snapshot={"memory_created": bool(memory_id), "memory_id": memory_id})
        else:
            memory_id = _extract_memory_id(step_map)
        step_map = _latest_workflow_steps(db, run.id)
        final_status = "waiting_user_review" if run.needs_merge or any(step.status == "waiting_user_review" for step in step_map.values()) else ("partial_success" if failures else "completed")
        return _set_run_state(db, run=run, status=final_status, current_step="done" if final_status != "waiting_user_review" else run.current_step, output_payload=_workflow_output(run, planner_output=planner_output, final_text=final_text, version_id=version_id, memory_id=memory_id, guard_output=guard_output, failures=failures), error_message="; ".join(f"{item['step']}: {item['error']}" for item in failures) if failures else None, completed=final_status in RUN_TERMINAL_STATUSES, needs_merge=run.needs_merge, quality_degraded=run.quality_degraded, resume_from_step=None if final_status in RUN_TERMINAL_STATUSES else run.resume_from_step)
    except Exception as exc:
        return _set_run_state(db, run=run, status="failed", current_step=run.current_step, error_message=str(exc), output_payload={"step_failures": failures, "error_summary": str(exc), "final_text": final_text or None}, completed=True, quality_degraded=run.quality_degraded)


def recover_expired_workflow_runs(db: Session) -> int:
    recovered = 0
    for run in db.query(WorkflowRun).filter(WorkflowRun.status == "running", WorkflowRun.lease_expires_at.is_not(None), WorkflowRun.lease_expires_at < _utcnow()).all():
        checkpoint = _stable_resume_checkpoint(db, run.id)
        if checkpoint and not run.needs_merge:
            _set_run_state(db, run=run, status="queued_resume", current_step="queued", resume_from_step=_next_step_key(checkpoint))
            recovered += 1
        else:
            _set_run_state(db, run=run, status="failed", current_step=run.current_step, error_message="lease_expired", output_payload={**(run.output_payload or {}), "error_summary": "lease_expired"}, completed=True)
    return recovered


def _claim_next_workflow_run(db: Session) -> WorkflowRun | None:
    run = db.query(WorkflowRun).filter(WorkflowRun.status.in_(["queued", "queued_resume"])).order_by(WorkflowRun.retry_count.asc(), WorkflowRun.queued_at.asc(), WorkflowRun.created_at.asc()).first()
    if run is None:
        return None
    run.status = "running"
    run.worker_id = RUNNER_ID
    run.heartbeat_at = _utcnow()
    run.lease_expires_at = run.heartbeat_at + timedelta(seconds=LEASE_SECONDS)
    run.started_at = run.started_at or run.heartbeat_at
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _workflow_runner_loop() -> None:
    while True:
        db = SessionLocal()
        try:
            run = _claim_next_workflow_run(db)
            if run is None:
                time.sleep(RUNNER_POLL_SECONDS)
                continue
            scene = db.query(Scene).filter(Scene.id == run.scene_id).first()
            if not scene:
                _set_run_state(db, run=run, status="failed", error_message="Scene not found", completed=True)
                continue
            payload = WorkflowSceneRequest(**{key: value for key, value in (run.input_payload or {}).items() if key in WorkflowSceneRequest.model_fields})
            _run_scene_workflow(db, scene=scene, payload=payload, run=run)
        except Exception:
            time.sleep(RUNNER_POLL_SECONDS)
        finally:
            db.close()


def ensure_workflow_runner_started() -> None:
    global _WORKFLOW_RUNNER_STARTED
    with _WORKFLOW_RUNNER_LOCK:
        if _WORKFLOW_RUNNER_STARTED:
            return
        threading.Thread(target=_workflow_runner_loop, name=RUNNER_ID, daemon=True).start()
        _WORKFLOW_RUNNER_STARTED = True


def is_workflow_runner_started() -> bool:
    return _WORKFLOW_RUNNER_STARTED


def queue_scene_workflow(db: Session, *, scene: Scene, payload: WorkflowSceneRequest) -> WorkflowRun:
    run = _create_run(db, scene=scene, payload=payload, status="queued")
    ensure_workflow_runner_started()
    return _attach_run_transient_fields(db, run)


def execute_scene_workflow(db: Session, *, scene: Scene, payload: WorkflowSceneRequest) -> WorkflowRun:
    return _attach_run_transient_fields(db, _run_scene_workflow(db, scene=scene, payload=payload, run=_create_run(db, scene=scene, payload=payload, status="running")))


def resume_workflow_run(db: Session, *, run: WorkflowRun, payload: ResumeWorkflowRequest) -> WorkflowRun:
    if _existing_dedup_response(db, run=run, endpoint="resume", idempotency_key=payload.idempotency_key):
        refreshed = get_workflow_run(db, run.id)
        refreshed.steps = list_workflow_steps(db, run.id)
        return refreshed
    checkpoint = _stable_resume_checkpoint(db, run.id)
    checkpoint_step = _latest_step_for_key(db, run.id, checkpoint) if checkpoint else None
    if checkpoint_step and checkpoint_step.version != payload.expected_step_version:
        raise ValueError("Workflow resume version mismatch")
    resume_from = payload.resume_from_step or _next_step_key(checkpoint)
    if resume_from is None:
        return run
    run.retry_count = (run.retry_count or 0) + 1
    _set_run_state(db, run=run, status="queued_resume", current_step="queued", resume_from_step=resume_from)
    _record_dedup_response(db, run=run, endpoint="resume", idempotency_key=payload.idempotency_key, request_payload=payload.model_dump(), response_payload={"workflow_id": str(run.id), "status": run.status})
    _publish_run_event(db, run=run, event="workflow_resumed", step=resume_from, message=f"resume from {resume_from}")
    ensure_workflow_runner_started()
    return _attach_run_transient_fields(db, run)


def override_workflow_step(db: Session, *, run: WorkflowRun, step_key: str, payload: OverrideStepRequest) -> WorkflowRun:
    if step_key != "plan":
        raise ValueError("Only planner override is supported in v1")
    if _existing_dedup_response(db, run=run, endpoint=f"override:{step_key}", idempotency_key=payload.idempotency_key):
        refreshed = get_workflow_run(db, run.id)
        refreshed.steps = list_workflow_steps(db, run.id)
        return refreshed
    latest = _latest_step_for_key(db, run.id, step_key)
    if latest is None or latest.version != payload.expected_step_version or latest.version != payload.derived_from_version:
        raise ValueError("Workflow override version mismatch")
    override_step = _create_step(db, run=run, step_key=step_key, input_snapshot={"override": True, "scene_version": (run.input_payload or {}).get("scene_version"), "previous_step_refs": {"source_step_id": str(latest.id)}}, parent_step_id=latest.id)
    override_step.provider_mode = run.provider_mode
    override_step.provider = latest.provider
    override_step.model = latest.model
    override_step.profile_name = getattr(latest, "profile_name", None)
    _finish_step(db, run=run, step=override_step, status="completed", machine_output_snapshot=latest.machine_output_snapshot or latest.effective_output_snapshot, effective_output_snapshot=payload.effective_output_snapshot, user_edited=True, edited_reason=payload.edited_reason)
    _invalidate_downstream_steps(db, run=run, source_step=override_step)
    run.resume_from_step = _next_step_key(step_key)
    run.status = "queued_resume"
    run.current_step = "queued"
    db.add(run)
    db.commit()
    db.refresh(run)
    _record_dedup_response(db, run=run, endpoint=f"override:{step_key}", idempotency_key=payload.idempotency_key, request_payload=payload.model_dump(), response_payload={"workflow_id": str(run.id), "status": run.status, "resume_from_step": run.resume_from_step})
    _publish_run_event(db, run=run, event="workflow_resumed", step=run.resume_from_step, message=f"override resume from {run.resume_from_step}")
    ensure_workflow_runner_started()
    return _attach_run_transient_fields(db, run)


def cancel_workflow_run(db: Session, *, run: WorkflowRun) -> WorkflowRun:
    if run.status in RUN_TERMINAL_STATUSES:
        return run
    run.cancel_requested_at = _utcnow()
    if run.status in {"queued", "queued_resume"}:
        return _set_run_state(db, run=run, status="cancelled", current_step="cancelled", error_message="Workflow cancelled by user", output_payload={"cancelled": True}, completed=True)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def get_workflow_run(db: Session, workflow_id):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_id).first()
    return _attach_run_transient_fields(db, run)


def list_workflow_steps(db: Session, workflow_id) -> list[WorkflowStep]:
    return [_attach_step_attempts(step) for step in _all_workflow_steps(db, workflow_id)]
