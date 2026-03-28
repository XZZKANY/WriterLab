"""baseline core tables

Revision ID: 20260327_0001
Revises:
Create Date: 2026-03-27 00:00:01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260327_0001"
down_revision = None
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _has_table("projects"):
        op.create_table(
            "projects",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("genre", sa.String(length=100), nullable=True),
            sa.Column("default_language", sa.String(length=20), nullable=False, server_default="zh-CN"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    if not _has_table("books"):
        op.create_table(
            "books",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    if not _has_table("chapters"):
        op.create_table(
            "chapters",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("book_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("books.id"), nullable=False),
            sa.Column("chapter_no", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    if not _has_table("characters"):
        op.create_table(
            "characters",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("aliases", sa.Text(), nullable=True),
            sa.Column("appearance", sa.Text(), nullable=True),
            sa.Column("personality", sa.Text(), nullable=True),
            sa.Column("background", sa.Text(), nullable=True),
            sa.Column("motivation", sa.Text(), nullable=True),
            sa.Column("speaking_style", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=100), nullable=True),
            sa.Column("secrets", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    if not _has_table("locations"):
        op.create_table(
            "locations",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    if not _has_table("lore_entries"):
        op.create_table(
            "lore_entries",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("category", sa.String(length=100), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="50"),
            sa.Column("canonical", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    if not _has_table("scenes"):
        op.create_table(
            "scenes",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("chapter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chapters.id"), nullable=False),
            sa.Column("scene_no", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("pov_character_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("time_label", sa.String(length=100), nullable=True),
            sa.Column("goal", sa.Text(), nullable=True),
            sa.Column("conflict", sa.Text(), nullable=True),
            sa.Column("outcome", sa.Text(), nullable=True),
            sa.Column("must_include", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("must_avoid", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
            sa.Column("draft_text", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    if not _has_table("model_profiles"):
        op.create_table(
            "model_profiles",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("provider", sa.String(length=50), nullable=False),
            sa.Column("model", sa.String(length=200), nullable=False),
            sa.Column("task_type", sa.String(length=50), nullable=False),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("temperature", sa.Integer(), nullable=True),
            sa.Column("max_tokens", sa.Integer(), nullable=True),
            sa.Column("timeout_ms", sa.Integer(), nullable=True),
            sa.Column("fallback_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("model_profiles.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("name", name="uq_model_profiles_name"),
        )

    if not _has_table("ai_runs"):
        op.create_table(
            "ai_runs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("scene_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scenes.id"), nullable=True),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True),
            sa.Column("run_type", sa.String(length=100), nullable=False),
            sa.Column("task_type", sa.String(length=50), nullable=True),
            sa.Column("provider", sa.String(length=50), nullable=True),
            sa.Column("model", sa.String(length=200), nullable=False),
            sa.Column("prompt_version", sa.String(length=100), nullable=True),
            sa.Column("fallback_used", sa.Boolean(), nullable=True),
            sa.Column("input_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("raw_response", sa.Text(), nullable=True),
            sa.Column("parsed_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("token_usage", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("latency_ms", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    if not _has_table("knowledge_documents"):
        op.create_table(
            "knowledge_documents",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("type", sa.String(length=50), nullable=False, server_default="misc"),
            sa.Column("raw_content", sa.Text(), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("source", sa.String(length=100), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="ready"),
            sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    if not _has_table("knowledge_chunks"):
        op.create_table(
            "knowledge_chunks",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("knowledge_documents.id"), nullable=False),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    if not _has_table("scene_versions"):
        op.create_table(
            "scene_versions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("scene_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scenes.id"), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("source", sa.String(length=50), nullable=False),
            sa.Column("label", sa.String(length=200), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    if not _has_table("scene_analyses"):
        op.create_table(
            "scene_analyses",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True),
            sa.Column("scene_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scenes.id"), nullable=False),
            sa.Column("version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scene_versions.id"), nullable=True),
            sa.Column("analysis_type", sa.String(length=50), nullable=False, server_default="scene"),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="success"),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("raw_result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("ai_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_runs.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    if not _has_table("scene_analysis_items"):
        op.create_table(
            "scene_analysis_items",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("analysis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scene_analyses.id"), nullable=False),
            sa.Column("item_type", sa.String(length=50), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=True),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("severity", sa.String(length=20), nullable=True),
            sa.Column("is_selected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    for table_name in [
        "scene_analysis_items",
        "scene_analyses",
        "scene_versions",
        "knowledge_chunks",
        "knowledge_documents",
        "ai_runs",
        "model_profiles",
        "scenes",
        "lore_entries",
        "locations",
        "characters",
        "chapters",
        "books",
        "projects",
    ]:
        if table_name in tables:
            op.drop_table(table_name)
