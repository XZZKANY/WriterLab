from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    schema_ready: bool
    workflow_runner_started: bool
    recovery_scan_completed: bool
    pgvector_ready: bool
    provider_matrix_loaded: bool
    provider_runtime_ready: bool
    version: str
    last_startup_stage: str
    startup_error: str | None = None
    recovered_runs: int = 0


class RuntimeCheckStatus(BaseModel):
    ok: bool
    message: str
    endpoint: str | None = None


class RuntimeKnowledgeStatus(BaseModel):
    vector_backend: str
    retrieval_mode: str
    retrieval_reason: str
    pgvector_ready: bool


class RuntimeProviderMatrixStatus(BaseModel):
    ok: bool
    rule_count: int = 0
    steps: list[str] = Field(default_factory=list)


class ProviderRuntimeProviderState(BaseModel):
    provider: str
    enabled: bool
    enabled_reason: str | None = None
    consecutive_failures: int = 0
    open_until: str | None = None
    remaining_cooldown_seconds: int = 0
    last_error: str | None = None


class ProviderRuntimeProfileState(BaseModel):
    profile_name: str
    provider: str
    model: str
    task_type: str | None = None
    workflow_step: str | None = None
    requests_per_minute: int | None = None
    monthly_budget_usd: float | None = None
    spent_usd: float = 0.0
    enabled: bool
    skip_reason: str | None = None


class ProviderRuntimeStepState(BaseModel):
    step: str
    ready: bool
    candidate_profiles: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)


class ProviderRuntimeSummary(BaseModel):
    ok: bool
    blocked_steps: list[str] = Field(default_factory=list)
    providers_with_open_circuit: list[str] = Field(default_factory=list)
    providers_disabled: list[str] = Field(default_factory=list)
    providers_rate_limited: list[str] = Field(default_factory=list)
    providers_budget_blocked: list[str] = Field(default_factory=list)


class ProviderRuntimeStateResponse(BaseModel):
    providers: list[ProviderRuntimeProviderState] = Field(default_factory=list)
    profiles: list[ProviderRuntimeProfileState] = Field(default_factory=list)
    steps: list[ProviderRuntimeStepState] = Field(default_factory=list)


class RuntimeWorkflowStatus(BaseModel):
    workflow_runner_started: bool
    recovery_scan_completed: bool
    recovered_runs: int = 0
    last_startup_stage: str
    startup_error: str | None = None


class RuntimeSelfCheckResponse(BaseModel):
    backend_root: RuntimeCheckStatus
    health: HealthResponse
    knowledge: RuntimeKnowledgeStatus
    provider_matrix: RuntimeProviderMatrixStatus
    provider_runtime: ProviderRuntimeSummary
    workflow_runtime: RuntimeWorkflowStatus
    recommended_checks: dict[str, list[str]] = Field(default_factory=dict)


class SmokeAssertion(BaseModel):
    name: str
    ok: bool
    detail: str | None = None


class SmokeReportSummary(BaseModel):
    report_type: Literal["backend_full_smoke", "frontend_live_smoke"]
    filename: str
    created_at: str
    provider_mode: str | None = None
    failure_stage: str | None = None
    success: bool
    scenario_count: int = 0


class BackendSmokeScenarioReport(BaseModel):
    name: str
    fixture_scenario: str | None = None
    expected_status: str | None = None
    actual_status: str | None = None
    resume_checkpoint: str | None = None
    step_statuses: list[dict[str, Any]] = Field(default_factory=list)
    event_summary: dict[str, Any] = Field(default_factory=dict)
    assertions: list[SmokeAssertion] = Field(default_factory=list)


class FrontendSmokeReportSummary(BaseModel):
    filename: str
    created_at: str
    success: bool
    status_code: int | None = None
    url: str | None = None
    markers: dict[str, bool] = Field(default_factory=dict)


class SmokeReportDetail(BaseModel):
    report_type: Literal["backend_full_smoke", "frontend_live_smoke"]
    filename: str
    created_at: str
    provider_mode: str | None = None
    failure_stage: str | None = None
    success: bool
    scenario_count: int = 0
    requested_provider_mode: str | None = None
    effective_provider_mode: str | None = None
    provider_preflight: dict[str, Any] | None = None
    blocking_reasons: list[str] = Field(default_factory=list)
    scenarios: list[BackendSmokeScenarioReport] = Field(default_factory=list)
    frontend_summary: FrontendSmokeReportSummary | None = None
    report: dict[str, Any] = Field(default_factory=dict)


class SmokeReportLatestResponse(BaseModel):
    backend_full_smoke: SmokeReportSummary | None = None
    frontend_live_smoke: SmokeReportSummary | None = None


class SmokeBaselineSummary(BaseModel):
    report_type: Literal["backend_full_smoke", "frontend_live_smoke"]
    filename: str
    created_at: str
    provider_mode: str | None = None
    failure_stage: str | None = None
    success: bool
    scenario_count: int = 0


class SmokeRegressionFinding(BaseModel):
    scope: Literal["report", "scenario", "assertion", "event", "step", "marker"]
    key: str
    message: str
    baseline_value: Any | None = None
    current_value: Any | None = None


class SmokeRegressionResponse(BaseModel):
    report_type: Literal["backend_full_smoke", "frontend_live_smoke"]
    filename: str
    comparable: bool
    regression_free: bool
    current_report: SmokeReportSummary
    baseline_report: SmokeBaselineSummary | None = None
    findings: list[SmokeRegressionFinding] = Field(default_factory=list)
