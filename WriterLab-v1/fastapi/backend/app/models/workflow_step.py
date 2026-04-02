import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workflow_runs.id"), nullable=False)
    step_key: Mapped[str] = mapped_column(String(50), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(50), nullable=False, default="workflow_step.v2")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_step_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workflow_steps.id"), nullable=True)
    invalidated_by_step: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workflow_steps.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued")
    input_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    output_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    profile_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    input_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    machine_output_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    effective_output_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    fallback_used: Mapped[bool | None] = mapped_column(nullable=True)
    fallback_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    guardrail_blocked: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    user_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    edited_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
