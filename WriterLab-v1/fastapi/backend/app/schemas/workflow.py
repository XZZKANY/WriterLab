from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowSceneRequest(BaseModel):
    scene_id: UUID
    branch_id: UUID | None = None
    length: str = "medium"
    guidance: list[str] = Field(default_factory=list)
    auto_apply: bool = False


class WorkflowStepResponse(BaseModel):
    id: UUID
    workflow_run_id: UUID
    step_key: str
    step_order: int
    status: str
    provider: str | None = None
    model: str | None = None
    input_payload: dict | None = None
    output_payload: dict | None = None
    error_message: str | None = None
    fallback_used: bool | None = None
    guardrail_blocked: bool | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    latency_ms: int | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowRunResponse(BaseModel):
    id: UUID
    project_id: UUID | None = None
    scene_id: UUID | None = None
    branch_id: UUID | None = None
    run_type: str
    status: str
    current_step: str | None = None
    input_payload: dict | None = None
    output_payload: dict | None = None
    error_message: str | None = None
    retry_count: int = 0
    queued_at: datetime | None = None
    heartbeat_at: datetime | None = None
    lease_expires_at: datetime | None = None
    cancel_requested_at: datetime | None = None
    cancelled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    steps: list[WorkflowStepResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True
