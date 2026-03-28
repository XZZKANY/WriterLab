from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class WriteSceneRequest(BaseModel):
    scene_id: UUID
    length: Literal["short", "medium", "long"] = "medium"
    guidance: list[str] = Field(default_factory=list)
    analysis_id: UUID | None = None


class WriteSceneResult(BaseModel):
    draft_text: str
    notes: list[str] = Field(default_factory=list)
    analysis_id_used: UUID | None = None
    selected_guidance: list[str] = Field(default_factory=list)
    unselected_guidance_count: int = 0
    knowledge_hit_count: int = 0
    changed: bool = True
    version_created: bool = True
    version_source: str | None = "write"
    version_id: UUID | None = None
    message: str | None = None
    reason: str | None = None


class WriteSceneResponse(BaseModel):
    success: bool
    data: WriteSceneResult | None = None
    run_id: UUID | None = None
    error_type: str | None = None
    message: str | None = None
