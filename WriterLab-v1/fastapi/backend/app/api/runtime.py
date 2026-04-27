import asyncio

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.api.health import build_health_payload
from app.db.session import get_db
from app.schemas.runtime import (
    ProviderRuntimeStateResponse,
    RuntimeSelfCheckResponse,
    SmokeReportDetail,
    SmokeReportLatestResponse,
    SmokeRegressionResponse,
    SmokeReportSummary,
)
from app.services.ai_gateway_service import (
    get_provider_matrix,
    get_provider_runtime_state,
    summarize_provider_runtime_state,
)
from app.services.knowledge_service import vector_backend_label, vector_backend_status
from app.services.runtime_events import get_runtime_events
from app.services.runtime_status_service import get_runtime_status_snapshot
from app.services.smoke_report_service import (
    get_latest_smoke_reports,
    get_smoke_report_detail,
    get_smoke_report_regression,
    list_smoke_report_summaries,
)

router = APIRouter(tags=["runtime"])


@router.get("/api/runtime/provider-state", response_model=ProviderRuntimeStateResponse)
def runtime_provider_state(db: Session = Depends(get_db)):
    return get_provider_runtime_state(db)


@router.get("/api/runtime/smoke-reports", response_model=list[SmokeReportSummary])
def runtime_smoke_reports():
    return list_smoke_report_summaries()


@router.get("/api/runtime/smoke-reports/latest", response_model=SmokeReportLatestResponse)
def runtime_latest_smoke_reports():
    return get_latest_smoke_reports()


@router.get("/api/runtime/smoke-reports/{filename}/regression", response_model=SmokeRegressionResponse)
def runtime_smoke_report_regression(filename: str):
    return get_smoke_report_regression(filename)


@router.get("/api/runtime/smoke-reports/{filename}", response_model=SmokeReportDetail)
def runtime_smoke_report_detail(filename: str):
    return get_smoke_report_detail(filename)


@router.get("/api/runtime/self-check", response_model=RuntimeSelfCheckResponse)
def runtime_self_check(db: Session = Depends(get_db)):
    health = build_health_payload(db)
    knowledge_status = vector_backend_status(db)
    provider_matrix = get_provider_matrix()
    provider_runtime_state = get_provider_runtime_state(db)
    provider_runtime_summary = summarize_provider_runtime_state(provider_runtime_state)
    runtime_status = get_runtime_status_snapshot()
    return {
        "backend_root": {
            "ok": True,
            "message": "WriterLab backend is running",
            "endpoint": "/",
        },
        "health": health,
        "knowledge": {
            "vector_backend": vector_backend_label(db),
            "retrieval_mode": knowledge_status.get("mode") or ("pgvector" if knowledge_status.get("pgvector_ready") else "fallback"),
            "retrieval_reason": knowledge_status.get("reason") or "Knowledge backend status available",
            "pgvector_ready": bool(knowledge_status.get("pgvector_ready")),
        },
        "provider_matrix": {
            "ok": bool(provider_matrix.rules),
            "rule_count": len(provider_matrix.rules),
            "steps": [rule.step for rule in provider_matrix.rules],
        },
        "provider_runtime": provider_runtime_summary.model_dump(),
        "workflow_runtime": {
            "workflow_runner_started": bool(runtime_status.get("workflow_runner_started")),
            "recovery_scan_completed": bool(runtime_status.get("recovery_scan_completed")),
            "recovered_runs": int(runtime_status.get("recovered_runs") or 0),
            "last_startup_stage": str(runtime_status.get("last_startup_stage") or "unknown"),
            "startup_error": runtime_status.get("startup_error"),
        },
        "recommended_checks": {
            "backend": [
                "powershell -ExecutionPolicy Bypass -File D:\\WritierLab\\WriterLab-v1\\scripts\\check-backend.ps1",
            ],
            "frontend": [
                "powershell -ExecutionPolicy Bypass -File D:\\WritierLab\\WriterLab-v1\\scripts\\check-frontend.ps1",
            ],
            "notes": [
                "Frontend build may hit Windows spawn EPERM in restricted shells; treat it as an environment limitation unless TypeScript compilation also fails.",
            ],
        },
    }


@router.websocket("/api/runtime/events")
async def runtime_events_socket(websocket: WebSocket):
    await websocket.accept()
    cursor = 0
    try:
        while True:
            events, cursor = get_runtime_events(cursor)
            for event in events:
                await websocket.send_json(event)
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        return
