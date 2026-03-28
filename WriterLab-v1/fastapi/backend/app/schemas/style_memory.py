from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class StyleMemoryCreate(BaseModel):
    project_id: UUID
    scene_id: UUID | None = None
    memory_type: str = "style_rule"
    content: str
    source_excerpt: str | None = None
    derived_rules: list[str] = Field(default_factory=list)
    user_confirmed: bool = False
    status: str = "suggested"


class StyleMemoryResponse(BaseModel):
    id: UUID
    project_id: UUID
    scene_id: UUID | None
    memory_type: str
    content: str
    source_excerpt: str | None
    derived_rules: list[str] | None
    user_confirmed: bool
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StyleMemoryConfirmRequest(BaseModel):
    user_confirmed: bool = True
    status: str | None = "confirmed"
