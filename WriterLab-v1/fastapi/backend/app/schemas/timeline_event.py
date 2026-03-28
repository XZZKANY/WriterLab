from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TimelineEventCreate(BaseModel):
    project_id: UUID
    chapter_id: UUID | None = None
    scene_id: UUID | None = None
    title: str
    event_type: str = "incident"
    description: str
    participants: list[str] = Field(default_factory=list)
    event_time_label: str | None = None
    canonical: bool = True
    metadata_json: dict | None = None


class TimelineEventResponse(BaseModel):
    id: UUID
    project_id: UUID
    chapter_id: UUID | None
    scene_id: UUID | None
    title: str
    event_type: str
    description: str
    participants: list[str] | None
    event_time_label: str | None
    canonical: bool
    metadata_json: dict | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
