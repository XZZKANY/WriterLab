from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ChapterCreate(BaseModel):
    book_id: UUID
    chapter_no: int
    title: str
    summary: str | None = None
    status: str = "draft"


class ChapterResponse(BaseModel):
    id: UUID
    book_id: UUID
    chapter_no: int
    title: str
    summary: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        