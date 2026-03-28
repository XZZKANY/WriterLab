from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timedelta
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.scene import Scene
from app.models.story_branch import StoryBranch
from app.models.style_memory import StyleMemory
from app.models.workflow_run import WorkflowRun
from app.models.workflow_step import WorkflowStep
from app.schemas.workflow import WorkflowSceneRequest
from app.services.ai_gateway_service import call_ai_gateway
from app.services.ai_output_guardrails import validate_prose_for_auto_apply, validate_style_output
from app.services.consistency_service import scan_scene_consistency
from app.services.context_service import build_scene_context
from app.services.knowledge_service import create_style_memory
from app.services.scene_analysis_service import analyze_scene
from app.services.scene_version_service import create_scene_version
from app.services.scene_write_service import write_scene

STEP_TIMEOUT_MS = {
    "analyze": 45000,
    "plan": 45000,
    "write": 120000,
    "style": 75000,
    "check": 40000,
    "guard": 10000,
    "memory": 15000,
}
STEP_ORDER = {
    "analyze": 10,
    "plan": 20,
    "write": 30,
    "style": 40,
    "check": 50,
    "guard": 60,
    "store": 70,
    "memory": 80,
}
TERMINAL_STATUSES = {"completed", "partial_success", "failed", "cancelled"}
LEASE_SECONDS = 45
RUNNER_POLL_SECONDS = 1.0
RUNNER_ID = f"workflow-runner-{os.getpid()}"

_WORKFLOW_RUNNER_LOCK = threading.Lock()
_WORKFLOW_RUNNER_STARTED = False

STEP_AGENT_META = {
    "bootstrap": {"agent_key": "orchestrator", "agent_name": "Workflow Orchestrator", "agent_label": "流程调度 Agent"},
    "queued": {"agent_key": "orchestrator", "agent_name": "Workflow Orchestrator", "agent_label": "流程调度 Agent"},
    "analyze": {"agent_key": "planner", "agent_name": "Planner Agent", "agent_label": "规划 Agent"},
    "plan": {"agent_key": "planner", "agent_name": "Planner Agent", "agent_label": "规划 Agent"},
    "write": {"agent_key": "writer", "agent_name": "Writer Agent", "agent_label": "写作 Agent"},
    "style": {"agent_key": "style", "agent_name": "Style Agent", "agent_label": "文风 Agent"},
    "check": {"agent_key": "consistency", "agent_name": "Consistency Agent", "agent_label": "一致性 Agent"},
    "guard": {"agent_key": "guardrail", "agent_name": "Guardrail Agent", "agent_label": "守门 Agent"},
    "store": {"agent_key": "store", "agent_name": "Store Agent", "agent_label": "存储 Agent"},
    "memory": {"agent_key": "memory_curator", "agent_name": "Memory Curator Agent", "agent_label": "记忆整理 Agent"},
    "done": {"agent_key": "orchestrator", "agent_name": "Workflow Orchestrator", "agent_label": "流程调度 Agent"},
}


def _utcnow() -> datetime:
    return datetime.utcnow()


def _agent_meta(step_key: str) -> dict[str, str]:
    return STEP_AGENT_META.get(step_key, STEP_AGENT_META["bootstrap"]).copy()


def _with_agent_meta(step_key: str, payload: dict | None = None) -> dict:
    data = payload.copy() if payload else {}
    data.update(_agent_meta(step_key))
    return data


def _resolve_project_id(scene: Scene, db: Session):
    chapter = db.query(Chapter).filter(Chapter.id == scene.chapter_id).first()
    if not chapter:
        return None
    book = db.query(Book).filter(Book.id == chapter.book_id).first()
    return book.project_id if book else None


def _planner_prompt(scene: Scene, bundle: dict, guidance: list[str]) -> str:
    return (
        "你是小说创作流水线中的剧情规划助手。请输出简洁、可执行的中文要点列表，不要写解释，不要输出 JSON。\n"
        f"场景摘要：{bundle['scene_summary']}\n"
        f"近期场景：{bundle.get('recent_scenes', [])}\n"
        f"设定约束：{[item.title for item in bundle['lore_constraints']]}\n"
        f"时间线锚点：{[item.title for item in bundle['timeline_events']]}\n"
        f"风格记忆：{[item.content for item in bundle['style_memories']]}\n"
        f"知识命中：{[item.content for item in bundle['knowledge_hits']]}\n"
        f"用户指导：{guidance}\n"
        f"必须包含：{scene.must_include or []}\n"
        f"必须避免：{scene.must_avoid or []}\n"
        "请按“场景目标 / 推进顺序 / 情绪转折 / 风险提醒”组织要点。"
    )


def _style_prompt(scene: Scene, draft_text: str, bundle: dict) -> str:
    return (
        "你是小说场景润色助手。请只返回润色后的中文正文，不要标题，不要列表，不要解释，不要总结，不要批注，不要改写说明。\n"
        "必须保留原文事实、时间顺序、人物关系、视角和语言。\n"
        "如果原稿已经可用，只做最小必要修改。\n"
        "不要把正文改成点评、摘要、提纲、译者注或分析报告。\n"
        "长度应尽量接近原稿，除非在消除明显重复。\n"
        f"场景摘要：{bundle['scene_summary']}\n"
        f"近期场景：{bundle.get('recent_scenes', [])}\n"
        f"风格记忆：{[item.content for item in bundle['style_memories']]}\n"
        f"必须包含：{scene.must_include or []}\n"
        f"必须避免：{scene.must_avoid or []}\n"
        f"原稿：\n{draft_text}"
    )


def _step_timeout_ms(step_key: str) -> int:
    return STEP_TIMEOUT_MS.get(step_key, 20000)


def _create_run(db: Session, *, scene: Scene, payload: WorkflowSceneRequest, status: str = "queued") -> WorkflowRun:
    queued_at = _utcnow()
    run = WorkflowRun(
        project_id=_resolve_project_id(scene, db),
        scene_id=scene.id,
        branch_id=payload.branch_id,
        run_type="scene_pipeline",
        status=status,
        current_step="queued" if status == "queued" else "bootstrap",
        input_payload=jsonable_encoder(payload.model_dump()),
        queued_at=queued_at,
        started_at=queued_at if status != "queued" else None,
        heartbeat_at=queued_at if status != "queued" else None,
        lease_expires_at=(queued_at + timedelta(seconds=LEASE_SECONDS)) if status != "queued" else None,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _set_run_state(
    db: Session,
    *,
    run: WorkflowRun,
    status: str,
    current_step: str | None = None,
    error_message: str | None = None,
    output_payload: dict | None = None,
    started: bool = False,
    completed: bool = False,
) -> WorkflowRun:
    now = _utcnow()
    run.status = status
    if current_step is not None:
        run.current_step = current_step
    run.error_message = error_message
    if output_payload is not None:
        run.output_payload = jsonable_encoder(output_payload)
    if started and run.started_at is None:
        run.started_at = now
    if status in {"running", "queued"}:
        run.heartbeat_at = now
        run.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
    if completed:
        run.completed_at = now
        if status == "cancelled" and run.cancelled_at is None:
            run.cancelled_at = now
        run.lease_expires_at = None
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _heartbeat_run(db: Session, run: WorkflowRun) -> WorkflowRun:
    run.heartbeat_at = _utcnow()
    run.lease_expires_at = run.heartbeat_at + timedelta(seconds=LEASE_SECONDS)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _create_step(db: Session, *, run: WorkflowRun, step_key: str, step_order: int, input_payload: dict | None = None) -> WorkflowStep:
    started_at = _utcnow()
    step = WorkflowStep(
        workflow_run_id=run.id,
        step_key=step_key,
        step_order=step_order,
        status="running",
        input_payload=jsonable_encoder(_with_agent_meta(step_key, input_payload or {})),
        started_at=started_at,
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    _set_run_state(db, run=run, status="running", current_step=step_key, started=True)
    return step


def _finish_step(
    db: Session,
    *,
    step: WorkflowStep,
    status: str,
    output_payload: dict | None = None,
    error_message: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    latency_ms: int | None = None,
    duration_ms: int | None = None,
    fallback_used: bool | None = None,
    guardrail_blocked: bool | None = None,
) -> WorkflowStep:
    completed_at = _utcnow()
    step.status = status
    step.output_payload = jsonable_encoder(_with_agent_meta(step.step_key, output_payload)) if output_payload is not None else _with_agent_meta(step.step_key)
    step.error_message = error_message
    step.provider = provider
    step.model = model
    step.fallback_used = fallback_used
    step.guardrail_blocked = guardrail_blocked
    step.completed_at = completed_at
    if duration_ms is None:
        if step.started_at is not None:
            duration_ms = max(int((completed_at - step.started_at).total_seconds() * 1000), 0)
        else:
            duration_ms = latency_ms
    step.duration_ms = duration_ms
    step.latency_ms = latency_ms if latency_ms is not None else duration_ms
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


def _serialize_gateway_call(result) -> dict:
    return {
        "provider": result.provider,
        "model": result.model,
        "latency_ms": result.latency_ms,
        "fallback_used": result.fallback_used,
        "profile_name": result.profile_name,
        "attempts": result.attempts,
        "token_usage": result.token_usage,
        "cost_estimate": result.cost_estimate,
    }


def _mark_optional_step_failure(
    db: Session,
    *,
    step: WorkflowStep,
    step_key: str,
    exc: Exception,
    failures: list[dict],
    guardrail_blocked: bool = False,
) -> None:
    message = str(exc)
    _finish_step(
        db,
        step=step,
        status="failed",
        output_payload=_with_agent_meta(
            step_key,
            {"error_summary": message, "guardrail_blocked": guardrail_blocked},
        ),
        error_message=message,
        guardrail_blocked=guardrail_blocked,
    )
    failures.append({"step": step_key, "error": message, "guardrail_blocked": guardrail_blocked})


def _store_workflow_result(
    db: Session,
    *,
    scene: Scene,
    payload: WorkflowSceneRequest,
    final_text: str,
) -> str | None:
    if not payload.auto_apply or not final_text.strip():
        return None

    scene.draft_text = final_text
    db.add(scene)
    db.commit()
    db.refresh(scene)

    version = create_scene_version(db, scene_id=scene.id, content=final_text, source="workflow", label="workflow result")
    if payload.branch_id and version is not None:
        branch = db.query(StoryBranch).filter(StoryBranch.id == payload.branch_id).first()
        if branch:
            branch.latest_version_id = version.id
            db.add(branch)
            db.commit()

    return str(version.id) if version is not None else None


def _build_memory_candidate(scene: Scene, payload: WorkflowSceneRequest, final_text: str) -> tuple[str, list[str]]:
    guidance_rules = [item.strip() for item in payload.guidance if item and item.strip()]
    if guidance_rules:
        content = "本次采纳文本体现的写作偏好：" + "；".join(guidance_rules[:4])
        rules = guidance_rules[:6]
    else:
        content = f"场景《{scene.title or '未命名场景'}》的采纳结果延续了当前项目的叙述节奏，并保持中文小说正文表达。"
        rules = [
            "保持中文小说正文表达，不输出解释性总结",
            "沿用当前项目的叙述节奏和镜头推进",
        ]
    return content, rules


def _create_memory_candidate(
    db: Session,
    *,
    scene: Scene,
    payload: WorkflowSceneRequest,
    project_id,
    final_text: str,
) -> StyleMemory | None:
    if not project_id or not final_text.strip():
        return None

    content, rules = _build_memory_candidate(scene, payload, final_text)
    source_excerpt = final_text.strip()[:240]
    existing = (
        db.query(StyleMemory)
        .filter(
            StyleMemory.project_id == project_id,
            StyleMemory.scene_id == scene.id,
            StyleMemory.memory_type == "workflow_style_candidate",
            StyleMemory.content == content,
        )
        .order_by(StyleMemory.updated_at.desc(), StyleMemory.created_at.desc())
        .first()
    )
    if existing:
        return existing

    return create_style_memory(
        db,
        project_id=project_id,
        scene_id=scene.id,
        memory_type="workflow_style_candidate",
        content=content,
        source_excerpt=source_excerpt,
        derived_rules=rules,
        user_confirmed=False,
        status="suggested",
    )


def _latest_workflow_steps(db: Session, workflow_id: UUID) -> dict[str, WorkflowStep]:
    steps = (
        db.query(WorkflowStep)
        .filter(WorkflowStep.workflow_run_id == workflow_id)
        .order_by(WorkflowStep.created_at.asc(), WorkflowStep.step_order.asc())
        .all()
    )
    latest: dict[str, WorkflowStep] = {}
    for step in steps:
        latest[step.step_key] = step
    return latest


def _extract_planner_text(step: WorkflowStep | None) -> str:
    if not step or step.status != "success":
        return ""
    value = (step.output_payload or {}).get("plan")
    return str(value).strip() if isinstance(value, str) else ""


def _extract_final_text(step_map: dict[str, WorkflowStep]) -> str:
    style_step = step_map.get("style")
    if style_step and style_step.status == "success":
        value = (style_step.output_payload or {}).get("styled_text")
        if isinstance(value, str) and value.strip():
            return value.strip()

    write_step = step_map.get("write")
    if write_step and write_step.status == "success":
        payload = write_step.output_payload or {}
        for key in ("draft_text", "partial_text", "revised_text"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _extract_version_id(step_map: dict[str, WorkflowStep]) -> str | None:
    store_step = step_map.get("store")
    if not store_step or store_step.status != "success":
        return None
    value = (store_step.output_payload or {}).get("version_id")
    return str(value) if value else None


def _extract_memory_id(step_map: dict[str, WorkflowStep]) -> str | None:
    memory_step = step_map.get("memory")
    if not memory_step or memory_step.status != "success":
        return None
    value = (memory_step.output_payload or {}).get("memory_id")
    return str(value) if value else None


def _should_skip_step(step: WorkflowStep | None) -> bool:
    return step is not None and step.status in {"success", "skipped"}


def _cancel_requested(run: WorkflowRun) -> bool:
    return run.cancel_requested_at is not None


def _cancel_run(db: Session, run: WorkflowRun, *, message: str = "Workflow cancelled by user") -> WorkflowRun:
    return _set_run_state(
        db,
        run=run,
        status="cancelled",
        current_step="cancelled",
        error_message=message,
        output_payload={
            **(run.output_payload or {}),
            "error_summary": message,
            "cancelled": True,
        },
        completed=True,
    )


def _maybe_cancel_before_step(db: Session, run: WorkflowRun) -> bool:
    db.refresh(run)
    if _cancel_requested(run):
        _cancel_run(db, run)
        return True
    return False


def _run_scene_workflow(db: Session, *, scene: Scene, payload: WorkflowSceneRequest, run: WorkflowRun) -> WorkflowRun:
    planner_text = ""
    final_text = ""
    issues = []
    failures: list[dict] = []
    safe_to_apply = False
    memory_id: str | None = None
    project_id = _resolve_project_id(scene, db)

    existing_steps = _latest_workflow_steps(db, run.id)
    planner_text = _extract_planner_text(existing_steps)
    final_text = _extract_final_text(existing_steps)
    reused_version_id = _extract_version_id(existing_steps)
    memory_id = _extract_memory_id(existing_steps)
    force_check_retry = bool(
        run.retry_count
        and (
            existing_steps.get("style") is not None
            and not _should_skip_step(existing_steps.get("style"))
        )
    )
    force_guard_retry = bool(
        run.retry_count
        and (
            force_check_retry
            or (existing_steps.get("guard") is not None and existing_steps.get("guard").status != "success")
        )
    )
    force_store_retry = bool(
        run.retry_count
        and (
            force_guard_retry
            or (existing_steps.get("check") is not None and existing_steps.get("check").status != "success")
            or (existing_steps.get("store") is not None and existing_steps.get("store").status != "success")
        )
    )
    force_memory_retry = bool(
        run.retry_count
        and (
            force_store_retry
            or (existing_steps.get("memory") is not None and existing_steps.get("memory").status != "success")
        )
    )

    _set_run_state(db, run=run, status="running", current_step=run.current_step or "bootstrap", started=True)

    try:
        bundle = build_scene_context(scene, db)

        if _maybe_cancel_before_step(db, run):
            return get_workflow_run(db, run.id)

        analyze_prior = existing_steps.get("analyze")
        if not _should_skip_step(analyze_prior):
            analyze_step = _create_step(db, run=run, step_key="analyze", step_order=STEP_ORDER["analyze"], input_payload={"scene_id": str(scene.id)})
            if (scene.draft_text or "").strip():
                try:
                    analysis_result, _ = analyze_scene(scene, db)
                    _finish_step(db, step=analyze_step, status="success", output_payload=analysis_result.model_dump())
                except Exception as exc:
                    _mark_optional_step_failure(db, step=analyze_step, step_key="analyze", exc=exc, failures=failures)
            else:
                _finish_step(db, step=analyze_step, status="skipped", output_payload={"reason": "scene has no draft yet"})

        _heartbeat_run(db, run)
        if _maybe_cancel_before_step(db, run):
            return get_workflow_run(db, run.id)

        planner_prior = existing_steps.get("plan")
        if not _should_skip_step(planner_prior):
            planner_step = _create_step(db, run=run, step_key="plan", step_order=STEP_ORDER["plan"], input_payload={"guidance": payload.guidance})
            try:
                planner_call = call_ai_gateway(
                    db,
                    task_type="analyze",
                    workflow_step="planner",
                    prompt=_planner_prompt(scene, bundle, payload.guidance),
                    params={"temperature": 0.3},
                    timeout_ms=_step_timeout_ms("plan"),
                )
                planner_text = planner_call.text.strip()
                _finish_step(
                    db,
                    step=planner_step,
                    status="success",
                    output_payload={"plan": planner_text, **_serialize_gateway_call(planner_call)},
                    provider=planner_call.provider,
                    model=planner_call.model,
                    latency_ms=planner_call.latency_ms,
                    fallback_used=planner_call.fallback_used,
                )
            except Exception as exc:
                _mark_optional_step_failure(db, step=planner_step, step_key="plan", exc=exc, failures=failures)
        else:
            planner_text = _extract_planner_text(existing_steps)

        _heartbeat_run(db, run)
        if _maybe_cancel_before_step(db, run):
            return get_workflow_run(db, run.id)

        write_prior = existing_steps.get("write")
        if not _should_skip_step(write_prior):
            write_step = _create_step(
                db,
                run=run,
                step_key="write",
                step_order=STEP_ORDER["write"],
                input_payload={"length": payload.length, "guidance": payload.guidance},
            )
            try:
                write_result, _ = write_scene(scene, db, payload.length, payload.guidance)
                final_text = write_result.draft_text or ""
                write_output = write_result.model_dump()
                write_output["partial_text"] = final_text or None
                _finish_step(db, step=write_step, status="success", output_payload=write_output)
            except Exception as exc:
                message = str(exc)
                _finish_step(
                    db,
                    step=write_step,
                    status="failed",
                    output_payload={"error_summary": message, "partial_text": final_text or None},
                    error_message=message,
                )
                failures.append({"step": "write", "error": message})
                _set_run_state(
                    db,
                    run=run,
                    status="failed",
                    current_step="write",
                    error_message=message,
                    output_payload={"partial_text": final_text or None, "error_summary": message, "step_failures": failures},
                    completed=True,
                )
                return get_workflow_run(db, run.id)
        else:
            final_text = _extract_final_text(existing_steps)

        _heartbeat_run(db, run)
        if _maybe_cancel_before_step(db, run):
            return get_workflow_run(db, run.id)

        style_prior = existing_steps.get("style")
        if not _should_skip_step(style_prior):
            style_step = _create_step(db, run=run, step_key="style", step_order=STEP_ORDER["style"], input_payload={"length": len(final_text)})
            try:
                style_call = call_ai_gateway(
                    db,
                    task_type="revise",
                    workflow_step="style",
                    prompt=_style_prompt(scene, final_text, bundle),
                    params={"temperature": 0.4},
                    timeout_ms=_step_timeout_ms("style"),
                )
                styled_text = style_call.text.strip() or final_text
                style_guard = validate_style_output(final_text, styled_text)
                if not style_guard.ok:
                    _finish_step(
                        db,
                        step=style_step,
                        status="failed",
                        output_payload={
                            "error_summary": style_guard.reason,
                            "guardrail_blocked": True,
                            "rejected_text_preview": styled_text[:600],
                            **_serialize_gateway_call(style_call),
                        },
                        error_message=style_guard.reason,
                        provider=style_call.provider,
                        model=style_call.model,
                        latency_ms=style_call.latency_ms,
                        fallback_used=style_call.fallback_used,
                        guardrail_blocked=True,
                    )
                    failures.append({"step": "style", "error": style_guard.reason, "guardrail_blocked": True})
                else:
                    final_text = styled_text
                    _finish_step(
                        db,
                        step=style_step,
                        status="success",
                        output_payload={"styled_text": final_text, **_serialize_gateway_call(style_call)},
                        provider=style_call.provider,
                        model=style_call.model,
                        latency_ms=style_call.latency_ms,
                        fallback_used=style_call.fallback_used,
                    )
            except Exception as exc:
                _mark_optional_step_failure(db, step=style_step, step_key="style", exc=exc, failures=failures)
        else:
            final_text = _extract_final_text(_latest_workflow_steps(db, run.id))

        _heartbeat_run(db, run)
        if _maybe_cancel_before_step(db, run):
            return get_workflow_run(db, run.id)

        check_prior = existing_steps.get("check")
        if force_check_retry or not _should_skip_step(check_prior):
            check_step = _create_step(db, run=run, step_key="check", step_order=STEP_ORDER["check"], input_payload={"draft_length": len(final_text)})
            try:
                issues = scan_scene_consistency(db, scene=scene, draft_text=final_text, workflow_run_id=run.id)
                _finish_step(
                    db,
                    step=check_step,
                    status="success",
                    output_payload={
                        "issue_count": len(issues),
                        "issues": [issue.message for issue in issues],
                    },
                )
            except Exception as exc:
                _mark_optional_step_failure(db, step=check_step, step_key="check", exc=exc, failures=failures)

        _heartbeat_run(db, run)
        if _maybe_cancel_before_step(db, run):
            return get_workflow_run(db, run.id)

        guard_prior = existing_steps.get("guard")
        if force_guard_retry or not _should_skip_step(guard_prior):
            guard_step = _create_step(
                db,
                run=run,
                step_key="guard",
                step_order=STEP_ORDER["guard"],
                input_payload={"draft_length": len(final_text), "auto_apply_requested": payload.auto_apply},
            )
            guard = validate_prose_for_auto_apply(final_text)
            safe_to_apply = bool(guard.ok)
            if safe_to_apply:
                _finish_step(
                    db,
                    step=guard_step,
                    status="success",
                    output_payload={
                        "safe_to_apply": True,
                        "guardrail_blocked": False,
                        "error_summary": None,
                    },
                    guardrail_blocked=False,
                )
            else:
                _finish_step(
                    db,
                    step=guard_step,
                    status="failed",
                    output_payload={
                        "safe_to_apply": False,
                        "guardrail_blocked": True,
                        "error_summary": guard.reason,
                        "rejected_text_preview": final_text[:600] or None,
                    },
                    error_message=guard.reason,
                    guardrail_blocked=True,
                )
                failures.append({"step": "guard", "error": guard.reason, "guardrail_blocked": True})
        else:
            prior_guard_output = guard_prior.output_payload or {}
            safe_to_apply = bool(prior_guard_output.get("safe_to_apply"))

        _heartbeat_run(db, run)
        if _maybe_cancel_before_step(db, run):
            return get_workflow_run(db, run.id)

        store_prior = existing_steps.get("store")
        version_id = reused_version_id
        if force_store_retry or not _should_skip_step(store_prior):
            store_step = _create_step(db, run=run, step_key="store", step_order=STEP_ORDER["store"], input_payload={"auto_apply": payload.auto_apply})
            if payload.auto_apply and not safe_to_apply:
                _finish_step(
                    db,
                    step=store_step,
                    status="skipped",
                    output_payload={
                        "stored": False,
                        "version_id": None,
                        "guardrail_blocked": True,
                        "safe_to_apply": False,
                        "error_summary": "Guardrail blocked auto-apply for this draft",
                    },
                    guardrail_blocked=True,
                )
            else:
                version_id = _store_workflow_result(db, scene=scene, payload=payload, final_text=final_text)
                _finish_step(
                    db,
                    step=store_step,
                    status="success",
                    output_payload={
                        "stored": bool(payload.auto_apply and final_text.strip()),
                        "auto_applied": bool(version_id),
                        "safe_to_apply": safe_to_apply or not payload.auto_apply,
                        "version_id": version_id,
                    },
                )

        _heartbeat_run(db, run)
        if _maybe_cancel_before_step(db, run):
            return get_workflow_run(db, run.id)

        memory_prior = existing_steps.get("memory")
        if force_memory_retry or not _should_skip_step(memory_prior):
            memory_step = _create_step(
                db,
                run=run,
                step_key="memory",
                step_order=STEP_ORDER["memory"],
                input_payload={"auto_applied": bool(version_id), "guidance_count": len(payload.guidance)},
            )
            if not version_id or not final_text.strip():
                _finish_step(
                    db,
                    step=memory_step,
                    status="skipped",
                    output_payload={
                        "memory_created": False,
                        "reason": "No adopted result available for memory curation",
                    },
                )
            else:
                try:
                    memory = _create_memory_candidate(
                        db,
                        scene=scene,
                        payload=payload,
                        project_id=project_id,
                        final_text=final_text,
                    )
                    memory_id = str(memory.id) if memory else None
                    _finish_step(
                        db,
                        step=memory_step,
                        status="success",
                        output_payload={
                            "memory_created": bool(memory_id),
                            "memory_id": memory_id,
                            "memory_status": getattr(memory, "status", None) if memory else None,
                            "memory_confirmed": getattr(memory, "user_confirmed", False) if memory else False,
                        },
                    )
                except Exception as exc:
                    _mark_optional_step_failure(db, step=memory_step, step_key="memory", exc=exc, failures=failures)

        run_status = "partial_success" if failures else "completed"
        error_summary = "; ".join(f"{item['step']}: {item['error']}" for item in failures) if failures else None
        _set_run_state(
            db,
            run=run,
            status=run_status,
            current_step="done",
            error_message=error_summary,
            output_payload={
                "planner_text": planner_text or None,
                "final_text": final_text or None,
                "partial_text": (final_text or None) if failures else None,
                "issue_count": len(issues),
                "auto_applied": bool(version_id),
                "safe_to_apply": safe_to_apply or not payload.auto_apply,
                "version_id": version_id,
                "memory_id": memory_id,
                "agent_pipeline": [meta["agent_name"] for meta in STEP_AGENT_META.values() if meta["agent_key"] != "orchestrator"],
                "step_failures": failures,
                "error_summary": error_summary,
            },
            completed=True,
        )
        return get_workflow_run(db, run.id)
    except Exception as exc:
        message = str(exc)
        _set_run_state(
            db,
            run=run,
            status="failed",
            current_step=run.current_step,
            error_message=message,
            output_payload={
                "planner_text": planner_text or None,
                "final_text": final_text or None,
                "partial_text": final_text or None,
                "step_failures": failures,
                "error_summary": message,
            },
            completed=True,
        )
        return get_workflow_run(db, run.id)


def _claim_next_workflow_run(db: Session) -> WorkflowRun | None:
    now = _utcnow()

    queued_to_cancel = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.status == "queued", WorkflowRun.cancel_requested_at.is_not(None))
        .order_by(WorkflowRun.queued_at.asc(), WorkflowRun.created_at.asc())
        .first()
    )
    if queued_to_cancel:
        return _cancel_run(db, queued_to_cancel)

    candidate = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.status == "queued")
        .order_by(WorkflowRun.retry_count.asc(), WorkflowRun.queued_at.asc(), WorkflowRun.created_at.asc())
        .first()
    )
    if candidate is None:
        candidate = (
            db.query(WorkflowRun)
            .filter(
                WorkflowRun.status == "running",
                WorkflowRun.lease_expires_at.is_not(None),
                WorkflowRun.lease_expires_at < now,
                WorkflowRun.cancelled_at.is_(None),
            )
            .order_by(WorkflowRun.updated_at.asc())
            .first()
        )
        if candidate:
            candidate.status = "queued"
            candidate.current_step = "queued"
            candidate.queued_at = now
            db.add(candidate)
            db.commit()
            db.refresh(candidate)

    if candidate is None:
        return None

    candidate.status = "running"
    candidate.current_step = candidate.current_step or "bootstrap"
    candidate.started_at = candidate.started_at or now
    candidate.heartbeat_at = now
    candidate.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def _workflow_runner_loop() -> None:
    while True:
        db = SessionLocal()
        try:
            run = _claim_next_workflow_run(db)
            if run is None:
                time.sleep(RUNNER_POLL_SECONDS)
                continue
            if run.status == "cancelled":
                continue
            scene = db.query(Scene).filter(Scene.id == run.scene_id).first()
            if not scene:
                _set_run_state(db, run=run, status="failed", error_message="Scene not found", completed=True)
                continue
            payload = WorkflowSceneRequest(**(run.input_payload or {}))
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
        worker = threading.Thread(target=_workflow_runner_loop, name=RUNNER_ID, daemon=True)
        worker.start()
        _WORKFLOW_RUNNER_STARTED = True


def queue_scene_workflow(db: Session, *, scene: Scene, payload: WorkflowSceneRequest) -> WorkflowRun:
    run = _create_run(db, scene=scene, payload=payload, status="queued")
    ensure_workflow_runner_started()
    return run


def execute_scene_workflow(db: Session, *, scene: Scene, payload: WorkflowSceneRequest) -> WorkflowRun:
    run = _create_run(db, scene=scene, payload=payload, status="running")
    return _run_scene_workflow(db, scene=scene, payload=payload, run=run)


def retry_workflow_run(db: Session, *, run: WorkflowRun) -> WorkflowRun:
    if run.status not in {"failed", "partial_success", "cancelled"}:
        return run
    now = _utcnow()
    run.status = "queued"
    run.current_step = "queued"
    run.error_message = None
    run.queued_at = now
    run.completed_at = None
    run.cancel_requested_at = None
    run.cancelled_at = None
    run.heartbeat_at = None
    run.lease_expires_at = None
    run.retry_count = (run.retry_count or 0) + 1
    db.add(run)
    db.commit()
    db.refresh(run)
    ensure_workflow_runner_started()
    return run


def cancel_workflow_run(db: Session, *, run: WorkflowRun) -> WorkflowRun:
    if run.status in TERMINAL_STATUSES:
        return run
    if run.status == "queued":
        run.cancel_requested_at = _utcnow()
        db.add(run)
        db.commit()
        db.refresh(run)
        return _cancel_run(db, run)
    run.cancel_requested_at = _utcnow()
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def get_workflow_run(db: Session, workflow_id):
    return db.query(WorkflowRun).filter(WorkflowRun.id == workflow_id).first()


def list_workflow_steps(db: Session, workflow_id) -> list[WorkflowStep]:
    return (
        db.query(WorkflowStep)
        .filter(WorkflowStep.workflow_run_id == workflow_id)
        .order_by(WorkflowStep.step_order.asc(), WorkflowStep.created_at.asc())
        .all()
    )
