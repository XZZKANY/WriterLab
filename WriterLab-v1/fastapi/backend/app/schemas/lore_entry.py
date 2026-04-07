from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LoreEntryCreate(BaseModel):
    project_id: UUID
    category: str
    title: str
    content: str
    priority: int = 50
    canonical: bool = True


class LoreEntryUpdate(BaseModel):
    category: str | None = None
    title: str | None = None
    content: str | None = None
    priority: int | None = None
    canonical: bool | None = None


class LoreEntryResponse(BaseModel):
    id: UUID
    project_id: UUID
    category: str
    title: str
    content: str
    priority: int
    canonical: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoreEntryDeleteResponse(BaseModel):
    deleted: bool
    lore_entry_id: UUID
