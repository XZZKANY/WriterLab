from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class LocationCreate(BaseModel):
    project_id: UUID
    name: str
    description: str | None = None

class LocationUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

class LocationResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True