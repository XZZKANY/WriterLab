from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


ReviseMode = Literal["trim", "literary", "unify"]


class ReviseSceneRequest(BaseModel):
    scene_id: UUID
    mode: ReviseMode


class ReviseSceneResult(BaseModel):
    revised_text: str
    notes: list[str] = Field(default_factory=list)
    changed: bool = True
    version_created: bool = False
    version_source: str | None = None
    version_id: UUID | None = None
    message: str | None = None
    reason: str | None = None


class ReviseSceneResponse(BaseModel):
    success: bool
    data: ReviseSceneResult | None = None
    run_id: UUID | None = None
    error_type: str | None = None
    message: str | None = None
