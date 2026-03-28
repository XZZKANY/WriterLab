from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project
from app.models.scene_version import SceneVersion
from app.models.story_branch import StoryBranch
from app.schemas.branch import BranchAdoptResponse, BranchDiffResponse, StoryBranchCreate, StoryBranchResponse
from app.services.branch_service import (
    adopt_story_branch,
    create_story_branch,
    get_branch_diff,
    get_branch_source_chapter_id,
    list_story_branches,
)

router = APIRouter(prefix="/api/branches", tags=["branches"])


def _version_label(db: Session, version_id):
    if version_id is None:
        return None
    version = db.query(SceneVersion).filter(SceneVersion.id == version_id).first()
    if not version:
        return None
    return version.label or version.source


def _serialize_branch(db: Session, branch: StoryBranch) -> StoryBranchResponse:
    return StoryBranchResponse(
        id=branch.id,
        project_id=branch.project_id,
        name=branch.name,
        description=branch.description,
        parent_branch_id=branch.parent_branch_id,
        source_scene_id=branch.source_scene_id,
        source_chapter_id=get_branch_source_chapter_id(db, branch),
        source_version_id=branch.source_version_id,
        latest_version_id=branch.latest_version_id,
        latest_version_label=_version_label(db, branch.latest_version_id),
        status=branch.status,
        metadata_json=branch.metadata_json,
        created_at=branch.created_at,
        updated_at=branch.updated_at,
    )


@router.post("", response_model=StoryBranchResponse)
def create_branch(payload: StoryBranchCreate, db: Session = Depends(get_db)):
    try:
        branch = create_story_branch(db, payload)
        return _serialize_branch(db, branch)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[StoryBranchResponse])
def list_branches(project_id: UUID | None = None, scene_id: UUID | None = None, db: Session = Depends(get_db)):
    if project_id is None and scene_id is None:
        raise HTTPException(status_code=400, detail="project_id or scene_id is required")
    if project_id is not None:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
    return [_serialize_branch(db, branch) for branch in list_story_branches(db, project_id=project_id, source_scene_id=scene_id)]


@router.get("/{branch_id}/diff", response_model=BranchDiffResponse)
def get_branch_diff_api(branch_id: UUID, db: Session = Depends(get_db)):
    branch = db.query(StoryBranch).filter(StoryBranch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    source_text, branch_text, diff_rows = get_branch_diff(db, branch)
    return BranchDiffResponse(
        branch_id=branch.id,
        branch_name=branch.name,
        source_scene_id=branch.source_scene_id,
        source_chapter_id=get_branch_source_chapter_id(db, branch),
        source_version_id=branch.source_version_id,
        latest_version_id=branch.latest_version_id,
        source_version_label=_version_label(db, branch.source_version_id),
        latest_version_label=_version_label(db, branch.latest_version_id),
        base_text=source_text,
        source_text=source_text,
        branch_text=branch_text,
        diff_rows=diff_rows,
    )


@router.post("/{branch_id}/adopt", response_model=BranchAdoptResponse)
def adopt_branch_api(branch_id: UUID, db: Session = Depends(get_db)):
    branch = db.query(StoryBranch).filter(StoryBranch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    try:
        scene, version = adopt_story_branch(db, branch)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return BranchAdoptResponse(
        branch_id=branch.id,
        scene_id=scene.id,
        version_id=version.id if version else None,
        adopted_version_id=version.id if version else None,
        current_text=scene.draft_text or "",
        adopted_at=datetime.utcnow(),
    )
