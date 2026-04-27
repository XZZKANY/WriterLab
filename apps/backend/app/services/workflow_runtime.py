from __future__ import annotations

import time
from datetime import timedelta

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.scene import Scene
from app.models.workflow_run import WorkflowRun
from app.schemas.workflow import WorkflowSceneRequest
from app.services.workflow_constants import LEASE_SECONDS, RUNNER_ID, RUNNER_POLL_SECONDS, _next_step_key, _utcnow


"""workflow_service 的 runner / recovery 内核。

承接后台 runner 与启动期 recovery 的内部实现，但继续依赖 `workflow_service` 作为
稳定 facade / monkeypatch 表面：测试会 patch `app.services.workflow_service._set_run_state`
和 `_stable_resume_checkpoint` 等符号，所以本模块内部对这些 helper 的调用统一通过
函数体内 lazy import 回主模块解析最新绑定。
"""


def recover_expired_workflow_runs(db: Session) -> int:
    from app.services import workflow_service as workflow

    recovered = 0
    for run in db.query(WorkflowRun).filter(WorkflowRun.status == "running", WorkflowRun.lease_expires_at.is_not(None), WorkflowRun.lease_expires_at < _utcnow()).all():
        checkpoint = workflow._stable_resume_checkpoint(db, run.id)
        if checkpoint and not run.needs_merge:
            workflow._set_run_state(db, run=run, status="queued_resume", current_step="queued", resume_from_step=_next_step_key(checkpoint))
            recovered += 1
        else:
            workflow._set_run_state(db, run=run, status="failed", current_step=run.current_step, error_message="lease_expired", output_payload={**(run.output_payload or {}), "error_summary": "lease_expired"}, completed=True)
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
    from app.services import workflow_service as workflow

    while True:
        db = SessionLocal()
        try:
            run = workflow._claim_next_workflow_run(db)
            if run is None:
                time.sleep(RUNNER_POLL_SECONDS)
                continue
            scene = db.query(Scene).filter(Scene.id == run.scene_id).first()
            if not scene:
                workflow._set_run_state(db, run=run, status="failed", error_message="Scene not found", completed=True)
                continue
            payload = WorkflowSceneRequest(**{key: value for key, value in (run.input_payload or {}).items() if key in WorkflowSceneRequest.model_fields})
            workflow._run_scene_workflow(db, scene=scene, payload=payload, run=run)
        except Exception:
            time.sleep(RUNNER_POLL_SECONDS)
        finally:
            db.close()
