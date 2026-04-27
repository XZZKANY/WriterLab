from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.runtime import HealthResponse
from app.services.ai_gateway_service import get_provider_matrix, get_provider_runtime_state, summarize_provider_runtime_state
from app.services.knowledge_service import vector_backend_status
from app.services.runtime_status_service import get_runtime_status_snapshot

router = APIRouter(prefix="/api")


def build_health_payload(db: Session) -> dict:
    runtime_status = get_runtime_status_snapshot()
    vector_status = vector_backend_status(db)
    provider_rules = get_provider_matrix().rules
    provider_runtime = summarize_provider_runtime_state(get_provider_runtime_state(db))
    degraded = bool(runtime_status.get("startup_error"))
    return {
        "status": "degraded" if degraded else "ok",
        "service": "writerlab-backend",
        "schema_ready": bool(runtime_status.get("schema_ready")),
        "workflow_runner_started": bool(runtime_status.get("workflow_runner_started")),
        "recovery_scan_completed": bool(runtime_status.get("recovery_scan_completed")),
        "pgvector_ready": bool(vector_status.get("pgvector_ready")),
        "provider_matrix_loaded": bool(provider_rules),
        "provider_runtime_ready": provider_runtime.ok,
        "version": str(runtime_status.get("version") or "writerlab-v1"),
        "last_startup_stage": str(runtime_status.get("last_startup_stage") or "unknown"),
        "startup_error": runtime_status.get("startup_error"),
        "recovered_runs": int(runtime_status.get("recovered_runs") or 0),
    }


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    return build_health_payload(db)
