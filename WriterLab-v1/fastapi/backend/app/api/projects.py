from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project
from app.repositories.project_repository import (
    delete_project as delete_project_query,
    get_project_overview as get_project_overview_query,
    list_projects as list_projects_query,
)
from app.schemas.project import (
    ProjectCreate,
    ProjectDeleteResponse,
    ProjectOverviewResponse,
    ProjectResponse,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(
        name=payload.name,
        description=payload.description,
        genre=payload.genre,
        default_language=payload.default_language,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    return list_projects_query(db)


@router.get("/{project_id}/overview", response_model=ProjectOverviewResponse)
def get_project_overview(project_id: UUID, db: Session = Depends(get_db)):
    payload = get_project_overview_query(db, project_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return payload


@router.delete("/{project_id}", response_model=ProjectDeleteResponse)
def delete_project(project_id: UUID, db: Session = Depends(get_db)):
    if not delete_project_query(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return {"deleted": True, "project_id": project_id}
