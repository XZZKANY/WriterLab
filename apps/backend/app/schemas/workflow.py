from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


WORKFLOW_RUN_STATUSES = (
    "queued",
    "running",
    "waiting_user_review",
    "partial_success",
    "failed",
    "completed",
    "cancelled",
    "queued_resume",
)

WORKFLOW_STEP_STATUSES = (
    "queued",
    "running",
    "waiting_user_review",
    "completed",
    "failed",
    "invalidated",
    "skipped",
    "cancelled",
)


class Violation(BaseModel):
    type: str
    span: str | None = None
    rule_id: str
    severity: str
    reason: str
    suggestion: str | None = None


class PlannerOutput(BaseModel):
    schema_version: str = "planner_output.v1"
    summary: str
    writing_goals: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    next_prompt_hints: list[str] = Field(default_factory=list)
    raw_plan: str | None = None


class ContextCompileCandidate(BaseModel):
    source_id: str
    source_type: str
    scope: str
    title: str | None = None
    score: float
    similarity: float
    recency: float
    importance: float
    token_count: int = 0
    summary_applied: bool = False
    diversity_slot: str | None = None


class ContextCompileSnapshot(BaseModel):
    schema_version: str = "context_compile_snapshot.v1"
    project_id: UUID | None = None
    branch_id: UUID | None = None
    chapter_id: UUID | None = None
    scene_id: UUID | None = None
    hard_filters: list[str] = Field(default_factory=list)
    hard_filter_result: dict[str, bool | str | None] = Field(default_factory=dict)
    candidates: list[ContextCompileCandidate] = Field(default_factory=list)
    budget: dict[str, int | float] = Field(default_factory=dict)
    summary_triggered: bool = False
    summary_reason: str | None = None
    summary_output: list[dict[str, Any]] = Field(default_factory=list)
    clipped_sources: list[str] = Field(default_factory=list)
    deduped_sources: list[str] = Field(default_factory=list)
    source_diversity_applied: dict[str, int] = Field(default_factory=dict)
    scope_resolution: dict[str, str | None] = Field(default_factory=dict)


class WriterInput(BaseModel):
    schema_version: str = "writer_input.v1"
    project_id: UUID | None = None
    branch_id: UUID | None = None
    chapter_id: UUID | None = None
    scene_id: UUID
    scene_version: int
    planner_step_id: UUID | None = None
    planner_output: PlannerOutput | None = None
    context_snapshot: ContextCompileSnapshot | None = None
    user_guidance: list[str] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)


class StyleOutput(BaseModel):
    schema_version: str = "style_output.v1"
    machine_output: dict[str, Any] = Field(default_factory=dict)
    effective_output: dict[str, Any] = Field(default_factory=dict)
    hard_negative_hits: list[str] = Field(default_factory=list)
    soft_negative_hits: list[str] = Field(default_factory=list)
    negative_matches: list[dict[str, Any]] = Field(default_factory=list)
    rewrite_suggestions: list[str] = Field(default_factory=list)


class GuardOutput(BaseModel):
    schema_version: str = "guard_output.v1"
    safe_to_apply: bool
    needs_rewrite: bool = False
    needs_user_review: bool = False
    violations: list[Violation] = Field(default_factory=list)


class VRAMLockState(BaseModel):
    schema_version: str = "vram_lock_state.v1"
    resource_key: str
    lock_owner: str
    lock_reason: str
    acquired_at: datetime
    ttl_seconds: int
    heartbeat_at: datetime | None = None


class ProviderFallbackTarget(BaseModel):
    provider: str
    model: str


class ProviderFallbackRule(BaseModel):
    step: str
    default_provider: str
    default_model: str
    timeout_ms: int
    retry_count: int
    fallback_targets: list[ProviderFallbackTarget] = Field(default_factory=list)
    fallback_to_ollama_when: str
    quality_degraded_on_fallback: bool = False


class ProviderMatrixResponse(BaseModel):
    rules: list[ProviderFallbackRule] = Field(default_factory=list)


class StyleNegativeRule(BaseModel):
    id: UUID | None = None
    project_id: UUID | None = None
    branch_id: UUID | None = None
    scope_type: str = "project"
    scope_id: UUID | None = None
    label: str
    severity: str
    match_mode: str
    pattern: str
    active: bool = True
    expires_at: datetime | None = None


class StyleNegativeMatch(BaseModel):
    rule_id: str
    label: str
    severity: str
    match_mode: str
    matched_text: str | None = None
    reason: str
    source: str


class WorkflowStepDebugView(BaseModel):
    id: UUID
    step_key: str
    version: int
    attempt_no: int
    status: str
    invalidated_by_step: UUID | None = None
    machine_output_snapshot: dict | None = None
    effective_output_snapshot: dict | None = None
    edited_reason: str | None = None
    attempts: list[dict[str, Any]] = Field(default_factory=list)


class WorkflowSceneRequest(BaseModel):
    scene_id: UUID
    branch_id: UUID | None = None
    length: str = "medium"
    guidance: list[str] = Field(default_factory=list)
    auto_apply: bool = False
    provider_mode: str = "live"
    fixture_scenario: str = "happy_path"


class ResumeWorkflowRequest(BaseModel):
    idempotency_key: str
    expected_step_version: int
    resume_from_step: str | None = None


class OverrideStepRequest(BaseModel):
    idempotency_key: str
    expected_step_version: int
    derived_from_version: int
    edited_reason: str
    effective_output_snapshot: dict[str, Any]


class WorkflowStepResponse(BaseModel):
    id: UUID
    workflow_run_id: UUID
    step_key: str
    step_order: int
    schema_version: str
    version: int
    attempt_no: int
    parent_step_id: UUID | None = None
    invalidated_by_step: UUID | None = None
    status: str
    input_hash: str | None = None
    output_hash: str | None = None
    provider_mode: str | None = None
    provider: str | None = None
    model: str | None = None
    profile_name: str | None = None
    input_payload: dict | None = None
    output_payload: dict | None = None
    machine_output_snapshot: dict | None = None
    effective_output_snapshot: dict | None = None
    attempts: list[dict[str, Any]] = Field(default_factory=list)
    error_message: str | None = None
    fallback_used: bool | None = None
    fallback_count: int = 0
    guardrail_blocked: bool | None = None
    user_edited: bool = False
    edited_at: datetime | None = None
    edited_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    latency_ms: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowRunResponse(BaseModel):
    id: UUID
    project_id: UUID | None = None
    scene_id: UUID | None = None
    branch_id: UUID | None = None
    run_type: str
    status: str
    current_step: str | None = None
    provider_mode: str = "live"
    fixture_version: str | None = None
    fixture_scenario: str | None = None
    input_payload: dict | None = None
    output_payload: dict | None = None
    error_message: str | None = None
    retry_count: int = 0
    worker_id: str | None = None
    queued_at: datetime | None = None
    heartbeat_at: datetime | None = None
    lease_expires_at: datetime | None = None
    cancel_requested_at: datetime | None = None
    cancelled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    needs_merge: bool = False
    quality_degraded: bool = False
    resume_from_step: str | None = None
    context_compile_snapshot: ContextCompileSnapshot | None = None
    resume_checkpoint: str | None = None
    created_at: datetime
    updated_at: datetime
    steps: list[WorkflowStepResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
