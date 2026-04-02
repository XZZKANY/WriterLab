from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SceneAnalysisItemResponse(BaseModel):
    id: UUID
    analysis_id: UUID
    item_type: str
    title: str | None = None
    content: str
    severity: str | None = None
    is_selected: bool
    sort_order: int
    metadata_json: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class SceneAnalysisStoredResponse(BaseModel):
    id: UUID
    project_id: UUID | None = None
    scene_id: UUID
    version_id: UUID | None = None
    analysis_type: str
    status: str
    summary: str | None = None
    ai_run_id: UUID | None = None
    created_at: datetime
    items: list[SceneAnalysisItemResponse] = Field(default_factory=list)


class UpdateAnalysisSelectionRequest(BaseModel):
    selected_item_ids: list[UUID] = Field(default_factory=list)
