from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CharacterCreate(BaseModel):
    project_id: UUID
    name: str
    aliases: str | None = None
    appearance: str | None = None
    personality: str | None = None
    background: str | None = None
    motivation: str | None = None
    speaking_style: str | None = None
    status: str | None = None
    secrets: str | None = None


class CharacterUpdate(BaseModel):
    name: str | None = None
    aliases: str | None = None
    appearance: str | None = None
    personality: str | None = None
    background: str | None = None
    motivation: str | None = None
    speaking_style: str | None = None
    status: str | None = None
    secrets: str | None = None


class CharacterResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    aliases: str | None
    appearance: str | None
    personality: str | None
    background: str | None
    motivation: str | None
    speaking_style: str | None
    status: str | None
    secrets: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CharacterDeleteResponse(BaseModel):
    deleted: bool
    character_id: UUID
