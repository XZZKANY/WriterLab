from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BookCreate(BaseModel):
    project_id: UUID
    title: str
    summary: str | None = None
    status: str = "draft"


class BookResponse(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    summary: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True