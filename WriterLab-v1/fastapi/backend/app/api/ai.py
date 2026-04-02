from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.scene_repository import get_scene as get_scene_record
from app.schemas.scene_analysis_store import SceneAnalysisStoredResponse, UpdateAnalysisSelectionRequest
from app.schemas.scene_analysis import AnalyzeSceneRequest, AnalyzeSceneResponse
from app.schemas.scene_revise import ReviseSceneRequest, ReviseSceneResponse
from app.schemas.scene_write import WriteSceneRequest, WriteSceneResponse
from app.schemas.workflow import (
    OverrideStepRequest,
    ProviderMatrixResponse,
    ResumeWorkflowRequest,
    WorkflowRunResponse,
    WorkflowSceneRequest,
)
from app.services.ai_errors import AIErrorType, AIServiceError
from app.services.scene_analysis_service import analyze_scene
from app.services.scene_analysis_store_service import (
    create_scene_analysis_record,
    get_scene_analysis,
    list_scene_analyses,
    set_selected_analysis_items,
    to_scene_analysis_response,
)
from app.services.scene_status_service import (
    SCENE_STATUS_ANALYZED,
    mark_scene_status,
)
from app.services.scene_revise_service import revise_scene
from app.services.scene_write_service import write_scene
from app.services.workflow_service import (
    cancel_workflow_run,
    execute_scene_workflow,
    get_workflow_run,
    list_workflow_steps,
    override_workflow_step,
    queue_scene_workflow,
    resume_workflow_run,
)
from app.services.ai_gateway_service import get_provider_matrix

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/provider-matrix", response_model=ProviderMatrixResponse)
def provider_matrix_api():
    return get_provider_matrix()


@router.post("/analyze-scene", response_model=AnalyzeSceneResponse)
def analyze_scene_api(payload: AnalyzeSceneRequest, db: Session = Depends(get_db)):
    scene = get_scene_record(db, payload.scene_id)
    if not scene:
        return AnalyzeSceneResponse(
            success=False,
            error_type=AIErrorType.VALIDATION,
            message="Scene not found",
            run_id=None,
        )

    try:
        result, run_id = analyze_scene(scene, db)
        analysis = create_scene_analysis_record(db, scene=scene, result=result, ai_run_id=run_id)
        mark_scene_status(scene, SCENE_STATUS_ANALYZED)
        db.add(scene)
        db.commit()
        return AnalyzeSceneResponse(success=True, data=result, run_id=run_id, analysis_id=analysis.id)
    except AIServiceError as exc:
        return AnalyzeSceneResponse(
            success=False,
            error_type=exc.error_type,
            message=exc.message,
            run_id=exc.run_id,
        )


@router.post("/write-scene", response_model=WriteSceneResponse)
def write_scene_api(payload: WriteSceneRequest, db: Session = Depends(get_db)):
    scene = get_scene_record(db, payload.scene_id)
    if not scene:
        return WriteSceneResponse(
            success=False,
            error_type=AIErrorType.VALIDATION,
            message="Scene not found",
            run_id=None,
        )

    try:
        result, run_id = write_scene(scene, db, payload.length, payload.guidance, payload.analysis_id)
        return WriteSceneResponse(success=True, data=result, run_id=run_id)
    except AIServiceError as exc:
        return WriteSceneResponse(
            success=False,
            error_type=exc.error_type,
            message=exc.message,
            run_id=exc.run_id,
        )


@router.post("/revise-scene", response_model=ReviseSceneResponse)
def revise_scene_api(payload: ReviseSceneRequest, db: Session = Depends(get_db)):
    scene = get_scene_record(db, payload.scene_id)
    if not scene:
        return ReviseSceneResponse(
            success=False,
            error_type=AIErrorType.VALIDATION,
            message="Scene not found",
            run_id=None,
        )

    try:
        result, run_id = revise_scene(scene, db, payload.mode)
        return ReviseSceneResponse(success=True, data=result, run_id=run_id)
    except AIServiceError as exc:
        return ReviseSceneResponse(
            success=False,
            error_type=exc.error_type,
            message=exc.message,
            run_id=exc.run_id,
        )


@router.get("/scenes/{scene_id}/analyses", response_model=list[SceneAnalysisStoredResponse])
def list_scene_analysis_api(scene_id: UUID, db: Session = Depends(get_db)):
    analyses = list_scene_analyses(db, scene_id)
    return [to_scene_analysis_response(db, analysis) for analysis in analyses]


@router.post("/analyses/{analysis_id}/selection", response_model=SceneAnalysisStoredResponse)
def update_analysis_selection_api(analysis_id: UUID, payload: UpdateAnalysisSelectionRequest, db: Session = Depends(get_db)):
    analysis = get_scene_analysis(db, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    set_selected_analysis_items(db, analysis_id, payload.selected_item_ids)
    refreshed = get_scene_analysis(db, analysis_id)
    return to_scene_analysis_response(db, refreshed)


@router.post("/workflows/scene", response_model=WorkflowRunResponse)
def run_scene_workflow(payload: WorkflowSceneRequest, db: Session = Depends(get_db)):
    scene = get_scene_record(db, payload.scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    run = queue_scene_workflow(db, scene=scene, payload=payload)
    run.steps = list_workflow_steps(db, run.id)
    return run


@router.post("/workflows/scene/run-sync", response_model=WorkflowRunResponse)
def run_scene_workflow_sync(payload: WorkflowSceneRequest, db: Session = Depends(get_db)):
    scene = get_scene_record(db, payload.scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    run = execute_scene_workflow(db, scene=scene, payload=payload)
    run.steps = list_workflow_steps(db, run.id)
    return run


@router.get("/workflows/{workflow_id}", response_model=WorkflowRunResponse)
def get_scene_workflow(workflow_id: UUID, db: Session = Depends(get_db)):
    run = get_workflow_run(db, workflow_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    run.steps = list_workflow_steps(db, workflow_id)
    return run


@router.post("/workflows/{workflow_id}/resume", response_model=WorkflowRunResponse)
def resume_scene_workflow(workflow_id: UUID, payload: ResumeWorkflowRequest, db: Session = Depends(get_db)):
    run = get_workflow_run(db, workflow_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    try:
        run = resume_workflow_run(db, run=run, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    run.steps = list_workflow_steps(db, workflow_id)
    return run


@router.post("/workflows/{workflow_id}/steps/{step_key}/override", response_model=WorkflowRunResponse)
def override_scene_workflow_step(workflow_id: UUID, step_key: str, payload: OverrideStepRequest, db: Session = Depends(get_db)):
    run = get_workflow_run(db, workflow_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    try:
        run = override_workflow_step(db, run=run, step_key=step_key, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    run.steps = list_workflow_steps(db, workflow_id)
    return run


@router.post("/workflows/{workflow_id}/cancel", response_model=WorkflowRunResponse)
def cancel_scene_workflow(workflow_id: UUID, db: Session = Depends(get_db)):
    run = get_workflow_run(db, workflow_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    run = cancel_workflow_run(db, run=run)
    run.steps = list_workflow_steps(db, workflow_id)
    return run
