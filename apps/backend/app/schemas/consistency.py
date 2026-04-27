from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConsistencyScanRequest(BaseModel):
    scene_id: UUID
    draft_text: str | None = None
    workflow_run_id: UUID | None = None


class ConsistencyIssueResponse(BaseModel):
    id: UUID
    project_id: UUID | None = None
    scene_id: UUID | None = None
    workflow_run_id: UUID | None = None
    issue_type: str
    severity: str
    source: str | None = None
    fix_suggestion: str | None = None
    message: str
    evidence_json: dict | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConsistencyScanResponse(BaseModel):
    issues: list[ConsistencyIssueResponse] = Field(default_factory=list)
    summary: str
