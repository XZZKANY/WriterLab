from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StyleMemoryCreate(BaseModel):
    project_id: UUID
    scene_id: UUID | None = None
    memory_type: str = "style_rule"
    content: str
    source_excerpt: str | None = None
    derived_rules: list[str] = Field(default_factory=list)
    user_confirmed: bool = False
    status: str = "suggested"
    scope_type: str = "project"
    scope_id: UUID | None = None
    active: bool = True
    expires_at: datetime | None = None


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
    scope_type: str = "project"
    scope_id: UUID | None = None
    active: bool = True
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StyleMemoryConfirmRequest(BaseModel):
    user_confirmed: bool = True
    status: str | None = "confirmed"
