from __future__ import annotations

from contextlib import contextmanager
from datetime import timedelta
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.scene import Scene
from app.models.story_branch import StoryBranch
from app.models.style_memory import StyleMemory
from app.models.vram_lock import VRAMLock
from app.models.workflow_request_dedup import WorkflowRequestDedup
from app.models.workflow_run import WorkflowRun
from app.models.workflow_step import WorkflowStep
from app.schemas.workflow import WorkflowSceneRequest
from app.services.ai_gateway_service import GatewayCallResult
from app.services.knowledge_service import create_style_memory
from app.services.runtime_events import publish_runtime_event
from app.services.scene_version_service import create_scene_version
from app.services.workflow_constants import (
    LEASE_SECONDS,
    RUNNER_ID,
    RUN_TERMINAL_STATUSES,
    STEP_ORDER,
    STEP_REUSABLE_STATUSES,
    STEP_SEQUENCE,
    VRAM_LOCK_TTL_SECONDS,
    WORKFLOW_SCHEMA_VERSION,
    _fixture_version_for_mode,
    _hash_json,
    _resolve_gateway_tokens,
    _run_fixture_scenario,
    _utcnow,
    _with_agent_meta,
)
from app.services.workflow_prompts import _build_memory_candidate


"""workflow_service 的 DB / persistence helper 层。

本模块承接 run/step 持久化、resume checkpoint、去重记录、VRAM lock、store/memory side-effect。

关键兼容约束：tests 会对 `app.services.workflow_service.<name>` 做 monkeypatch，
所以本模块内部凡是调用这些 helper 时，都尽量通过函数体内 lazy import 回主模块拿最新绑定，
避免绑定死在子模块局部命名空间，导致 patch 不生效。
"""


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


def _create_memory_candidate(db: Session, *, scene: Scene, payload: WorkflowSceneRequest, project_id, final_text: str) -> StyleMemory | None:
    if not project_id or not final_text.strip():
        return None
    content, rules = _build_memory_candidate(scene, payload, final_text)
    existing = db.query(StyleMemory).filter(StyleMemory.project_id == project_id, StyleMemory.scene_id == scene.id, StyleMemory.memory_type == "workflow_style_candidate", StyleMemory.content == content).order_by(StyleMemory.updated_at.desc(), StyleMemory.created_at.desc()).first()
    if existing:
        return existing
    return create_style_memory(db, project_id=project_id, scene_id=scene.id, memory_type="workflow_style_candidate", content=content, source_excerpt=final_text[:240], derived_rules=rules, user_confirmed=False, status="suggested", scope_type="scene", scope_id=scene.id)


def _attach_run_transient_fields(db: Session, run: WorkflowRun | None) -> WorkflowRun | None:
    if run is None:
        return None
    from app.services import workflow_service as workflow

    run.resume_checkpoint = workflow._stable_resume_checkpoint(db, run.id)
    run.fixture_scenario = _run_fixture_scenario(run)
    return run


def _create_run(db: Session, *, scene: Scene, payload: WorkflowSceneRequest, status: str = "queued") -> WorkflowRun:
    from app.services import workflow_service as workflow

    now = _utcnow()
    run = WorkflowRun(
        project_id=workflow._resolve_project_id(scene, db),
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
    workflow._publish_run_event(db, run=run, event="workflow_queued", message=run.status)
    return workflow._attach_run_transient_fields(db, run)


def _set_run_state(db: Session, *, run: WorkflowRun, status: str, current_step: str | None = None, error_message: str | None = None, output_payload: dict | None = None, completed: bool = False, needs_merge: bool | None = None, quality_degraded: bool | None = None, resume_from_step: str | None = None) -> WorkflowRun:
    from app.services import workflow_service as workflow

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
    workflow._publish_run_event(db, run=run, event=f"workflow_{status}", message=error_message or status)
    if status == "waiting_user_review":
        workflow._publish_run_event(db, run=run, event="workflow_waiting_review", message=error_message or status)
    return workflow._attach_run_transient_fields(db, run)


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
    from app.services import workflow_service as workflow

    latest: dict[str, WorkflowStep] = {}
    for step in workflow._all_workflow_steps(db, workflow_id):
        if step.status == "invalidated":
            continue
        latest[step.step_key] = step
    return latest


def _stable_resume_checkpoint(db: Session, workflow_id: UUID) -> str | None:
    from app.services import workflow_service as workflow

    step_map = workflow._latest_workflow_steps(db, workflow_id)
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
    from app.services import workflow_service as workflow

    latest = workflow._latest_step_for_key(db, run.id, step_key)
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
    workflow._set_run_state(db, run=run, status="running", current_step=step_key)
    workflow._publish_run_event(db, run=run, event="step_started", step=step_key, message=f"{step_key} started")
    return step


def _finish_step(db: Session, *, run: WorkflowRun, step: WorkflowStep, status: str, machine_output_snapshot: dict | None = None, effective_output_snapshot: dict | None = None, error_message: str | None = None, gateway_result: GatewayCallResult | None = None, user_edited: bool = False, edited_reason: str | None = None, guardrail_blocked: bool | None = None, fallback_used: bool | None = None) -> WorkflowStep:
    from app.services import workflow_service as workflow

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
    workflow._attach_step_attempts(step)
    workflow._publish_run_event(db, run=run, event=f"step_{status}", step=step.step_key, provider=step.provider, model=step.model, message=error_message or status)
    return step


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
    from app.services import workflow_service as workflow

    for step in workflow._latest_workflow_steps(db, run.id).values():
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
    from app.services import workflow_service as workflow

    if not payload.auto_apply or not final_text.strip():
        workflow._finish_step(db, run=run, step=store_step, status="skipped", machine_output_snapshot={"stored": False, "reason": "auto_apply disabled"}, effective_output_snapshot={"stored": False, "reason": "auto_apply disabled"})
        return None, False
    expected_scene_version = int((run.input_payload or {}).get("scene_version") or scene.scene_version or 1)
    db.refresh(scene)
    if scene.scene_version != expected_scene_version:
        workflow._finish_step(db, run=run, step=store_step, status="waiting_user_review", machine_output_snapshot={"stored": False, "needs_merge": True}, effective_output_snapshot={"stored": False, "needs_merge": True, "version_id": None}, error_message="Scene version changed during workflow execution")
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
    workflow._finish_step(db, run=run, step=store_step, status="completed", machine_output_snapshot={"stored": True, "version_id": str(version.id) if version else None}, effective_output_snapshot={"stored": True, "auto_applied": bool(version), "safe_to_apply": True, "version_id": str(version.id) if version else None})
    return str(version.id) if version else None, False
