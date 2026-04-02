from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SceneCreate(BaseModel):
    chapter_id: UUID
    scene_no: int
    title: str
    pov_character_id: UUID | None = None
    location_id: UUID | None = None
    time_label: str | None = None
    goal: str | None = None
    conflict: str | None = None
    outcome: str | None = None
    must_include: list[str] | None = None
    must_avoid: list[str] | None = None
    status: str = "draft"
    draft_text: str | None = None


class SceneUpdate(BaseModel):
    title: str | None = None
    pov_character_id: UUID | None = None
    location_id: UUID | None = None
    time_label: str | None = None
    goal: str | None = None
    conflict: str | None = None
    outcome: str | None = None
    must_include: list[str] | None = None
    must_avoid: list[str] | None = None
    status: str | None = None
    draft_text: str | None = None
    expected_scene_version: int | None = None
    version_source: str | None = None
    version_label: str | None = None


class SceneResponse(BaseModel):
    id: UUID
    chapter_id: UUID
    scene_no: int
    title: str
    pov_character_id: UUID | None
    location_id: UUID | None
    time_label: str | None
    goal: str | None
    conflict: str | None
    outcome: str | None
    must_include: list[str] | None
    must_avoid: list[str] | None
    status: str
    draft_text: str | None
    scene_version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
