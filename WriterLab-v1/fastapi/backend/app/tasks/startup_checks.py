import logging

from sqlalchemy import inspect

from app.db.session import SessionLocal, engine
from app.services.runtime.runtime_status_service import (
    mark_recovery_scan_completed,
    mark_schema_ready,
    mark_startup_error,
    mark_startup_stage,
    mark_workflow_runner_started,
    reset_runtime_status,
)
from app.services.workflow.workflow_service import (
    ensure_workflow_runner_started,
    is_workflow_runner_started,
    recover_expired_workflow_runs,
)
from app.tasks.schema_upgrades import apply_schema_upgrades

logger = logging.getLogger(__name__)


def assert_schema_is_migrated() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "alembic_version" not in tables:
        raise RuntimeError(
            "Database schema is not managed yet. Run Alembic migrations before starting the API."
        )


def run_startup_sequence() -> None:
    reset_runtime_status()
    mark_startup_stage("schema_validation")
    try:
        assert_schema_is_migrated()
        mark_schema_ready(True)
        logger.info("Schema validation completed.")
    except Exception as exc:  # pragma: no cover - startup control flow
        mark_startup_error("schema_validation", str(exc))
        logger.exception("Schema validation failed during startup.")
        raise RuntimeError(
            "Schema validation failed. Run Alembic migrations before starting the API."
        ) from exc

    mark_startup_stage("schema_upgrade")
    try:
        apply_schema_upgrades(engine)
        logger.info("Schema upgrades applied.")
    except Exception as exc:  # pragma: no cover - startup control flow
        mark_startup_error("schema_upgrade", str(exc))
        logger.exception("Schema upgrade failed during startup.")
        raise RuntimeError("Schema upgrade failed during startup.") from exc

    db = SessionLocal()
    try:
        mark_startup_stage("workflow_recovery")
        recovered_runs = recover_expired_workflow_runs(db)
        mark_recovery_scan_completed(recovered_runs)
        logger.info("Workflow recovery scan completed. recovered_runs=%s", recovered_runs)
    except Exception as exc:  # pragma: no cover - startup control flow
        mark_startup_error("workflow_recovery", str(exc))
        logger.exception("Workflow recovery scan failed during startup.")
        raise RuntimeError("Workflow recovery startup scan failed.") from exc
    finally:
        db.close()

    mark_startup_stage("workflow_runner")
    try:
        ensure_workflow_runner_started()
        mark_workflow_runner_started(is_workflow_runner_started())
        logger.info("Workflow runner started.")
    except Exception as exc:  # pragma: no cover - startup control flow
        mark_startup_error("workflow_runner", str(exc))
        logger.exception("Workflow runner failed to start.")
        raise RuntimeError("Workflow runner startup failed.") from exc

    mark_startup_stage("ready")
