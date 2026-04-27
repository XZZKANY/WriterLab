from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.models.scene import Scene
from app.models.workflow_run import WorkflowRun
from app.schemas.workflow import GuardOutput, StyleOutput, WorkflowSceneRequest
from app.services.workflow_constants import RUN_TERMINAL_STATUSES, _run_fixture_scenario
from app.services.workflow_extractors import (
    _build_planner_output,
    _extract_effective_snapshot,
    _extract_final_text,
    _extract_memory_id,
    _extract_planner_output,
    _extract_version_id,
    _fixture_guard_output,
    _should_reuse_step,
    _workflow_output,
)
from app.services.workflow_prompts import _planner_prompt, _style_prompt


"""workflow_service 的主执行编排器。

承接 `_run_scene_workflow` 主流程，但继续依赖 `workflow_service` 作为稳定 facade /
monkeypatch 表面：tests 会 patch `app.services.workflow_service.<name>` 上的大量协作者，
所以本模块内部对这些协作者的调用统一通过函数体内 lazy import 回主模块解析最新绑定。
"""


def _run_scene_workflow(db: Session, *, scene: Scene, payload: WorkflowSceneRequest, run: WorkflowRun) -> WorkflowRun:
    from app.services import workflow_service as workflow

    failures: list[dict[str, Any]] = []
    fixture_scenario = _run_fixture_scenario(run) or payload.fixture_scenario
    bundle = workflow.build_scene_context(scene, db, branch_id=payload.branch_id)
    run.context_compile_snapshot = jsonable_encoder(bundle.get("context_compile_snapshot"))
    db.add(run)
    db.commit()
    db.refresh(run)
    step_map = workflow._latest_workflow_steps(db, run.id)
    planner_output = _extract_planner_output(step_map.get("plan"))
    final_text = _extract_final_text(step_map)
    guard_output: GuardOutput | None = None
    version_id = _extract_version_id(step_map)
    memory_id = _extract_memory_id(step_map)
    resume_from_step = run.resume_from_step
    workflow._set_run_state(db, run=run, status="running", current_step=resume_from_step or run.current_step or "bootstrap")
    try:
        if not _should_reuse_step(step_map.get("analyze"), resume_from_step, "analyze"):
            analyze_step = workflow._create_step(db, run=run, step_key="analyze", input_snapshot={"scene_id": str(scene.id), "scene_version": scene.scene_version})
            try:
                if (scene.draft_text or "").strip():
                    analysis_result, _, analysis_call = workflow.analyze_scene(
                        scene,
                        db,
                        provider_mode=run.provider_mode,
                        fixture_scenario=fixture_scenario,
                        return_gateway_result=True,
                    )
                    workflow._finish_step(db, run=run, step=analyze_step, status="completed", machine_output_snapshot=analysis_result.model_dump(), effective_output_snapshot=analysis_result.model_dump(), gateway_result=analysis_call)
                else:
                    workflow._finish_step(db, run=run, step=analyze_step, status="skipped", machine_output_snapshot={"reason": "scene has no draft"}, effective_output_snapshot={"reason": "scene has no draft"})
            except Exception as exc:
                failures.append({"step": "analyze", "error": str(exc)})
                workflow._finish_step(db, run=run, step=analyze_step, status="failed", machine_output_snapshot={"error_summary": str(exc)}, effective_output_snapshot={"error_summary": str(exc)}, error_message=str(exc))
        workflow._heartbeat_run(db, run)
        step_map = workflow._latest_workflow_steps(db, run.id)
        if not _should_reuse_step(step_map.get("plan"), resume_from_step, "plan"):
            planner_step = workflow._create_step(db, run=run, step_key="plan", input_snapshot={"prompt": _planner_prompt(scene, bundle, payload.guidance), "context_bundle": bundle, "params": {"temperature": 0.3}, "scene_version": scene.scene_version, "previous_step_refs": {}})
            planner_call = None
            try:
                with workflow._vram_lock(db, resource_key="writerlab-gpu", lock_reason="plan"):
                    planner_call = workflow.call_ai_gateway(
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
                    workflow._finish_step(
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
                    return workflow._set_run_state(
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
                workflow._finish_step(db, run=run, step=planner_step, status="completed", machine_output_snapshot=planner_machine, effective_output_snapshot=planner_effective, gateway_result=planner_call)
            except Exception as exc:
                failures.append({"step": "plan", "error": str(exc)})
                if run.provider_mode == "smoke_fixture":
                    planner_step.provider_mode = run.provider_mode
                    planner_step.provider = "fixture"
                    planner_step.model = "smoke-fixture"
                    planner_step.profile_name = f"fixture-planner-{fixture_scenario}"
                workflow._finish_step(
                    db,
                    run=run,
                    step=planner_step,
                    status="failed",
                    machine_output_snapshot={"error_summary": str(exc)},
                    effective_output_snapshot={"error_summary": str(exc)},
                    error_message=str(exc),
                    gateway_result=planner_call,
                )
                return workflow._set_run_state(
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
        workflow._heartbeat_run(db, run)
        step_map = workflow._latest_workflow_steps(db, run.id)
        if not _should_reuse_step(step_map.get("write"), resume_from_step, "write"):
            write_step = workflow._create_step(db, run=run, step_key="write", input_snapshot={"prompt": "write_scene", "context_bundle": bundle, "params": {"length": payload.length}, "scene_version": scene.scene_version, "previous_step_refs": {"plan": str(step_map.get("plan").id) if step_map.get("plan") else None}})
            try:
                write_result, _, write_call = workflow.write_scene(
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
                workflow._finish_step(db, run=run, step=write_step, status="completed", machine_output_snapshot=write_result.model_dump(), effective_output_snapshot=write_result.model_dump(), gateway_result=write_call)
            except Exception as exc:
                workflow._finish_step(db, run=run, step=write_step, status="failed", machine_output_snapshot={"error_summary": str(exc)}, effective_output_snapshot={"error_summary": str(exc)}, error_message=str(exc))
                return workflow._set_run_state(db, run=run, status="failed", current_step="write", error_message=str(exc), output_payload={"step_failures": [{"step": "write", "error": str(exc)}]}, completed=True)
        else:
            final_text = _extract_final_text(step_map)
        workflow._heartbeat_run(db, run)
        step_map = workflow._latest_workflow_steps(db, run.id)
        if not _should_reuse_step(step_map.get("style"), resume_from_step, "style"):
            style_step = workflow._create_step(db, run=run, step_key="style", input_snapshot={"prompt": _style_prompt(scene, final_text, bundle), "context_bundle": bundle, "params": {"temperature": 0.4}, "scene_version": scene.scene_version, "previous_step_refs": {"write": str(step_map.get("write").id) if step_map.get("write") else None}})
            style_call = None
            try:
                with workflow._vram_lock(db, resource_key="writerlab-gpu", lock_reason="style"):
                    style_call = workflow.call_ai_gateway(
                        db,
                        task_type="revise",
                        workflow_step="style",
                        prompt=_style_prompt(scene, final_text, bundle),
                        params={"temperature": 0.4, "fixture_attempt_no": style_step.attempt_no},
                        provider_mode=run.provider_mode,
                        fixture_scenario=fixture_scenario,
                    )
                styled_text = style_call.text.strip() or final_text
                negative_rules = workflow.resolve_style_negative_rules(
                    db,
                    scene=scene,
                    project_id=run.project_id or workflow._resolve_project_id(scene, db),
                    branch_id=payload.branch_id,
                )
                negative_matches = workflow.match_style_negative_rules(styled_text, negative_rules)
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
                    workflow._finish_step(db, run=run, step=style_step, status="waiting_user_review", machine_output_snapshot=style_output, effective_output_snapshot=style_output, error_message="Hard negative style rule matched", gateway_result=style_call, guardrail_blocked=True, fallback_used=style_call.fallback_used)
                else:
                    final_text = effective_text
                    workflow._finish_step(db, run=run, step=style_step, status="completed", machine_output_snapshot=style_output, effective_output_snapshot=style_output, gateway_result=style_call, fallback_used=style_call.fallback_used)
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
                workflow._finish_step(
                    db,
                    run=run,
                    step=style_step,
                    status="failed",
                    machine_output_snapshot={"error_summary": str(exc)},
                    effective_output_snapshot={"error_summary": str(exc)},
                    error_message=str(exc),
                    gateway_result=style_call,
                )
                return workflow._set_run_state(
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
            final_text = _extract_final_text(workflow._latest_workflow_steps(db, run.id))
        workflow._heartbeat_run(db, run)
        step_map = workflow._latest_workflow_steps(db, run.id)
        if not _should_reuse_step(step_map.get("check"), resume_from_step, "check"):
            check_step = workflow._create_step(db, run=run, step_key="check", input_snapshot={"draft_length": len(final_text), "scene_version": scene.scene_version})
            try:
                issues, check_call = workflow.scan_scene_consistency(
                    db,
                    scene=scene,
                    draft_text=final_text,
                    workflow_run_id=run.id,
                    provider_mode=run.provider_mode,
                    fixture_scenario=fixture_scenario,
                    return_gateway_result=True,
                )
                workflow._finish_step(db, run=run, step=check_step, status="completed", machine_output_snapshot={"issue_count": len(issues), "issues": [issue.message for issue in issues]}, effective_output_snapshot={"issue_count": len(issues), "issues": [issue.message for issue in issues]}, gateway_result=check_call)
            except Exception as exc:
                failures.append({"step": "check", "error": str(exc)})
                workflow._finish_step(db, run=run, step=check_step, status="failed", machine_output_snapshot={"error_summary": str(exc)}, effective_output_snapshot={"error_summary": str(exc)}, error_message=str(exc))
        workflow._heartbeat_run(db, run)
        step_map = workflow._latest_workflow_steps(db, run.id)
        if not _should_reuse_step(step_map.get("guard"), resume_from_step, "guard"):
            guard_step = workflow._create_step(db, run=run, step_key="guard", input_snapshot={"draft_length": len(final_text), "scene_version": scene.scene_version})
            guard_output = _fixture_guard_output(final_text, fixture_scenario=fixture_scenario) or workflow.build_guard_output(final_text)
            workflow._finish_step(db, run=run, step=guard_step, status="completed" if guard_output.safe_to_apply else "waiting_user_review", machine_output_snapshot=guard_output.model_dump(), effective_output_snapshot=guard_output.model_dump(), error_message=guard_output.violations[0].reason if guard_output.violations else None, guardrail_blocked=not guard_output.safe_to_apply)
        else:
            guard_output = GuardOutput(**_extract_effective_snapshot(step_map.get("guard"))) if step_map.get("guard") else None
        workflow._heartbeat_run(db, run)
        step_map = workflow._latest_workflow_steps(db, run.id)
        if not _should_reuse_step(step_map.get("store"), resume_from_step, "store"):
            store_step = workflow._create_step(db, run=run, step_key="store", input_snapshot={"auto_apply": payload.auto_apply, "scene_version": scene.scene_version, "previous_step_refs": {"guard": str(step_map.get("guard").id) if step_map.get("guard") else None}})
            if guard_output and guard_output.safe_to_apply:
                version_id, run.needs_merge = workflow._store_workflow_result(db, run=run, scene=scene, payload=payload, store_step=store_step, final_text=final_text)
            else:
                workflow._finish_step(db, run=run, step=store_step, status="waiting_user_review", machine_output_snapshot={"stored": False, "guard_output": guard_output.model_dump() if guard_output else None}, effective_output_snapshot={"stored": False, "safe_to_apply": False, "needs_user_review": True, "violations": [item.model_dump() for item in (guard_output.violations if guard_output else [])]}, error_message="Guardrail requires manual review", guardrail_blocked=True)
                version_id = None
        else:
            version_id = _extract_version_id(step_map)
        workflow._heartbeat_run(db, run)
        step_map = workflow._latest_workflow_steps(db, run.id)
        if not _should_reuse_step(step_map.get("memory"), resume_from_step, "memory"):
            memory_step = workflow._create_step(db, run=run, step_key="memory", input_snapshot={"version_id": version_id, "scene_version": scene.scene_version})
            if not version_id or not final_text.strip():
                workflow._finish_step(db, run=run, step=memory_step, status="skipped", machine_output_snapshot={"memory_created": False}, effective_output_snapshot={"memory_created": False})
                memory_id = None
            else:
                memory = workflow._create_memory_candidate(db, scene=scene, payload=payload, project_id=workflow._resolve_project_id(scene, db), final_text=final_text)
                memory_id = str(memory.id) if memory else None
                workflow._finish_step(db, run=run, step=memory_step, status="completed", machine_output_snapshot={"memory_created": bool(memory_id), "memory_id": memory_id}, effective_output_snapshot={"memory_created": bool(memory_id), "memory_id": memory_id})
        else:
            memory_id = _extract_memory_id(step_map)
        step_map = workflow._latest_workflow_steps(db, run.id)
        final_status = "waiting_user_review" if run.needs_merge or any(step.status == "waiting_user_review" for step in step_map.values()) else ("partial_success" if failures else "completed")
        return workflow._set_run_state(db, run=run, status=final_status, current_step="done" if final_status != "waiting_user_review" else run.current_step, output_payload=_workflow_output(run, planner_output=planner_output, final_text=final_text, version_id=version_id, memory_id=memory_id, guard_output=guard_output, failures=failures), error_message="; ".join(f"{item['step']}: {item['error']}" for item in failures) if failures else None, completed=final_status in RUN_TERMINAL_STATUSES, needs_merge=run.needs_merge, quality_degraded=run.quality_degraded, resume_from_step=None if final_status in RUN_TERMINAL_STATUSES else run.resume_from_step)
    except Exception as exc:
        return workflow._set_run_state(db, run=run, status="failed", current_step=run.current_step, error_message=str(exc), output_payload={"step_failures": failures, "error_summary": str(exc), "final_text": final_text or None}, completed=True, quality_degraded=run.quality_degraded)
