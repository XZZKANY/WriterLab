from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeDocumentCreate(BaseModel):
    project_id: UUID
    title: str
    type: Literal["character", "location", "lore", "rules", "timeline", "style", "misc"] = "misc"
    raw_content: str
    source: str | None = None


class KnowledgeDocumentResponse(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    type: str
    summary: str | None
    source: str | None
    status: str
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeChunkHit(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_title: str
    document_type: str
    memory_class: str | None = None
    source_label: str | None = None
    confirmed: bool | None = None
    score: float
    content: str
    source_kind: str | None = None
    citation: str | None = None
    metadata_json: dict | None = None


class KnowledgeRetrieveRequest(BaseModel):
    project_id: UUID
    scene_id: UUID | None = None
    query: str
    top_k: int = Field(default=3, ge=1, le=10)
    source_kinds: list[str] = Field(default_factory=list)


class KnowledgeRetrieveResponse(BaseModel):
    query: str
    hits: list[KnowledgeChunkHit] = Field(default_factory=list)


class KnowledgeSearchResponse(KnowledgeRetrieveResponse):
    project_id: UUID
    scene_id: UUID | None = None
    retrieval_mode: str = "fallback"
    retrieval_reason: str | None = None
    pgvector_ready: bool = False


class KnowledgeReindexRequest(BaseModel):
    project_id: UUID


class KnowledgeReindexResponse(BaseModel):
    project_id: UUID
    documents_reindexed: int
    chunks_rebuilt: int
    vector_backend: str = "fallback"
    retrieval_reason: str | None = None
    pgvector_ready: bool = False
