from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class StoryBranchCreate(BaseModel):
    project_id: UUID | None = None
    name: str
    description: str | None = None
    parent_branch_id: UUID | None = None
    source_scene_id: UUID | None = None
    source_version_id: UUID | None = None
    latest_version_id: UUID | None = None
    metadata_json: dict | None = None


class StoryBranchResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    description: str | None
    parent_branch_id: UUID | None
    source_scene_id: UUID | None
    source_chapter_id: UUID | None = None
    source_version_id: UUID | None
    latest_version_id: UUID | None
    latest_version_label: str | None = None
    status: str
    metadata_json: dict | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BranchDiffResponse(BaseModel):
    branch_id: UUID
    branch_name: str | None = None
    source_scene_id: UUID | None = None
    source_chapter_id: UUID | None = None
    source_version_id: UUID | None
    latest_version_id: UUID | None
    source_version_label: str | None = None
    latest_version_label: str | None = None
    base_text: str
    source_text: str
    branch_text: str
    diff_rows: list[dict]


class BranchAdoptResponse(BaseModel):
    branch_id: UUID
    scene_id: UUID
    version_id: UUID | None
    adopted_version_id: UUID | None = None
    current_text: str
    adopted_at: datetime
