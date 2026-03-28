from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class LoreEntryCreate(BaseModel):
    project_id: UUID
    category: str
    title: str
    content: str
    priority: int = 50
    canonical: bool = True


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

    class Config:
        from_attributes = True