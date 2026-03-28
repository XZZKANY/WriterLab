from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


VersionSource = Literal["manual", "write", "revise", "restore", "workflow"]


class SceneVersionResponse(BaseModel):
    id: UUID
    scene_id: UUID
    content: str
    source: VersionSource
    label: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class RestoreVersionResponse(BaseModel):
    success: bool
    version_id: UUID
    restored_to_scene_id: UUID
    current_text: str
