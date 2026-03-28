from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    genre: str | None = None
    default_language: str = "zh-CN"


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    genre: str | None
    default_language: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True