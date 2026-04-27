from __future__ import annotations

import threading

from sqlalchemy.orm import Session

from app.models.scene import Scene
from app.models.workflow_run import WorkflowRun
from app.models.workflow_step import WorkflowStep
from app.schemas.workflow import OverrideStepRequest, ResumeWorkflowRequest, WorkflowSceneRequest
from app.services.ai_gateway_service import call_ai_gateway
from app.services.ai_output_guardrails import build_guard_output
from app.services.consistency_service import scan_scene_consistency
from app.services.context_service import build_scene_context
from app.services.scene_analysis_service import analyze_scene
from app.services.scene_write_service import write_scene
from app.services.style_negative_service import match_style_negative_rules, resolve_style_negative_rules
# 把常量与纯小工具集中在 workflow_constants；通过 import 拉回本模块命名空间，
# 既保证调用点不变，又让 tests 通过 "app.services.workflow_service.<name>" 的字符串路径
# monkeypatch 仍然命中真正被调用的绑定。
from app.services.workflow_constants import (
    RUNNER_ID,
    RUN_TERMINAL_STATUSES,
    STEP_ORDER,
    _agent_meta,
    _next_step_key,
    _utcnow,
    _with_agent_meta,
)
from app.services.workflow_execution import _run_scene_workflow
from app.services.workflow_persistence import (
    _all_workflow_steps,
    _attach_run_transient_fields,
    _attach_step_attempts,
    _create_memory_candidate,
    _create_run,
    _create_step,
    _existing_dedup_response,
    _finish_step,
    _heartbeat_run,
    _invalidate_downstream_steps,
    _latest_step_for_key,
    _latest_workflow_steps,
    _publish_run_event,
    _record_dedup_response,
    _resolve_project_id,
    _set_run_state,
    _stable_resume_checkpoint,
    _store_workflow_result,
    _vram_lock,
)
from app.services.workflow_prompts import _build_memory_candidate
from app.services.workflow_runtime import (
    _workflow_runner_loop,
    recover_expired_workflow_runs,
)

__all__ = [
    "STEP_ORDER",
    "_agent_meta",
    "_build_memory_candidate",
    "_finish_step",
    "_run_scene_workflow",
    "_store_workflow_result",
    "_with_agent_meta",
    "override_workflow_step",
    "recover_expired_workflow_runs",
    "resume_workflow_run",
    "_existing_dedup_response",
    "_latest_step_for_key",
    "_create_step",
    "_invalidate_downstream_steps",
    "_next_step_key",
    "_record_dedup_response",
    "_stable_resume_checkpoint",
    "_set_run_state",
    "_publish_run_event",
    "_resolve_project_id",
    "_heartbeat_run",
    "_latest_workflow_steps",
    "_vram_lock",
    "_create_memory_candidate",
    "_attach_run_transient_fields",
    "_all_workflow_steps",
    "ensure_workflow_runner_started",
    "build_scene_context",
    "call_ai_gateway",
    "analyze_scene",
    "write_scene",
    "scan_scene_consistency",
    "build_guard_output",
    "resolve_style_negative_rules",
    "match_style_negative_rules",
]

_WORKFLOW_RUNNER_LOCK = threading.Lock()
_WORKFLOW_RUNNER_STARTED = False



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
