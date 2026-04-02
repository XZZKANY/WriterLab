from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.scene_repository import get_scene as get_scene_record
from app.schemas.consistency import ConsistencyScanRequest, ConsistencyScanResponse
from app.services.consistency_service import scan_scene_consistency

router = APIRouter(prefix="/api/consistency", tags=["consistency"])


@router.post("/scan", response_model=ConsistencyScanResponse)
def scan_consistency(payload: ConsistencyScanRequest, db: Session = Depends(get_db)):
    scene = get_scene_record(db, payload.scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    issues = scan_scene_consistency(
        db,
        scene=scene,
        draft_text=payload.draft_text,
        workflow_run_id=payload.workflow_run_id,
    )
    summary = "未发现明显的一致性问题。" if not issues else f"发现 {len(issues)} 条一致性问题。"
    return ConsistencyScanResponse(issues=issues, summary=summary)
