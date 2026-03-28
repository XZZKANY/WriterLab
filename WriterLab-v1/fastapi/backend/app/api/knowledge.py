from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project
from app.schemas.knowledge import (
    KnowledgeDocumentCreate,
    KnowledgeDocumentResponse,
    KnowledgeReindexRequest,
    KnowledgeReindexResponse,
    KnowledgeSearchResponse,
    KnowledgeRetrieveRequest,
    KnowledgeRetrieveResponse,
)
from app.schemas.style_memory import StyleMemoryConfirmRequest, StyleMemoryCreate, StyleMemoryResponse
from app.services.knowledge_service import (
    confirm_style_memory,
    create_knowledge_document,
    create_style_memory,
    list_style_memories,
    reindex_project_knowledge,
    retrieve_knowledge,
    retrieve_knowledge_with_status,
    vector_backend_label,
    vector_backend_status,
)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.post("/documents", response_model=KnowledgeDocumentResponse)
def create_document(payload: KnowledgeDocumentCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    document = create_knowledge_document(
        db,
        project_id=payload.project_id,
        title=payload.title,
        doc_type=payload.type,
        raw_content=payload.raw_content,
        source=payload.source,
    )
    return document


@router.post("/retrieve", response_model=KnowledgeRetrieveResponse)
def retrieve(payload: KnowledgeRetrieveRequest, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    hits = retrieve_knowledge(
        db,
        project_id=payload.project_id,
        query=payload.query,
        top_k=payload.top_k,
        source_kinds=payload.source_kinds,
    )
    return KnowledgeRetrieveResponse(query=payload.query, hits=hits)


@router.get("/search", response_model=KnowledgeSearchResponse)
def search(project_id: UUID, query: str, top_k: int = 5, scene_id: UUID | None = None, source_kinds: str | None = None, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    allowed = [item.strip() for item in (source_kinds or "").split(",") if item.strip()]
    hits, status = retrieve_knowledge_with_status(
        db,
        project_id=project_id,
        query=query,
        top_k=max(1, min(top_k, 10)),
        source_kinds=allowed,
    )
    return KnowledgeSearchResponse(
        project_id=project_id,
        scene_id=scene_id,
        query=query,
        hits=hits,
        retrieval_mode=status["mode"],
        retrieval_reason=status["reason"],
        pgvector_ready=status["pgvector_ready"],
    )


@router.post("/reindex", response_model=KnowledgeReindexResponse)
def reindex(payload: KnowledgeReindexRequest, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    documents_reindexed, chunks_rebuilt = reindex_project_knowledge(db, project_id=payload.project_id)
    status = vector_backend_status(db)
    return KnowledgeReindexResponse(
        project_id=payload.project_id,
        documents_reindexed=documents_reindexed,
        chunks_rebuilt=chunks_rebuilt,
        vector_backend=vector_backend_label(db),
        retrieval_reason=status["reason"],
        pgvector_ready=status["pgvector_ready"],
    )


@router.get("/style-memories", response_model=list[StyleMemoryResponse])
def get_style_memories(project_id: UUID, include_unconfirmed: bool = True, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return list_style_memories(db, project_id=project_id, include_unconfirmed=include_unconfirmed)


@router.post("/style-memories", response_model=StyleMemoryResponse)
def create_style_memory_api(payload: StyleMemoryCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return create_style_memory(
        db,
        project_id=payload.project_id,
        scene_id=payload.scene_id,
        memory_type=payload.memory_type,
        content=payload.content,
        source_excerpt=payload.source_excerpt,
        derived_rules=payload.derived_rules,
        user_confirmed=payload.user_confirmed,
        status=payload.status,
    )


@router.post("/style-memories/{memory_id}/confirm", response_model=StyleMemoryResponse)
def confirm_style_memory_api(memory_id: UUID, payload: StyleMemoryConfirmRequest, db: Session = Depends(get_db)):
    memory = confirm_style_memory(
        db,
        memory_id=memory_id,
        user_confirmed=payload.user_confirmed,
        status=payload.status,
    )
    if not memory:
        raise HTTPException(status_code=404, detail="Style memory not found")
    return memory
