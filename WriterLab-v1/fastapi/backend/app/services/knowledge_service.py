import hashlib
import math
import re
from collections import Counter
from typing import Iterable

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_document import KnowledgeDocument
from app.models.style_memory import StyleMemory
from app.schemas.knowledge import KnowledgeChunkHit

EMBED_DIM = 128
VECTOR_DIMENSION = 128


def _tokenize(text_value: str) -> list[str]:
    return re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+", (text_value or "").lower())


def embed_text(text_value: str) -> list[float]:
    counts = Counter(_tokenize(text_value))
    if not counts:
        return [0.0] * EMBED_DIM

    vector = [0.0] * EMBED_DIM
    for token, count in counts.items():
        index = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % EMBED_DIM
        vector[index] += float(count)

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    return float(sum(a * b for a, b in zip(left, right)))


def chunk_text(content: str, chunk_size: int = 320, overlap: int = 48) -> list[str]:
    cleaned = "\n".join(line.strip() for line in (content or "").splitlines() if line.strip()).strip()
    if not cleaned:
        return []

    paragraphs = re.split(r"\n{2,}", cleaned)
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)
        if len(paragraph) <= chunk_size:
            current = paragraph
            continue

        start = 0
        while start < len(paragraph):
            end = min(start + chunk_size, len(paragraph))
            chunks.append(paragraph[start:end])
            if end >= len(paragraph):
                break
            start = max(end - overlap, start + 1)
        current = ""

    if current:
        chunks.append(current)
    return chunks


def _normalize_source_kind(value: str | None) -> str:
    return (value or "misc").strip().lower() or "misc"


def _memory_class_for_document(doc_type: str | None) -> str:
    normalized = _normalize_source_kind(doc_type)
    if normalized == "timeline":
        return "timeline_event"
    if normalized == "style":
        return "style_memory"
    return "canonical_lore"


def _vector_literal(values: Iterable[float]) -> str:
    return "[" + ",".join(f"{float(value):.8f}" for value in values) + "]"


def vector_backend_status(db: Session) -> dict:
    try:
        extension_available = bool(
            db.execute(text("SELECT EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector')")).scalar()
        )
    except Exception as exc:
        return {
            "mode": "fallback",
            "reason": f"database introspection failed: {exc}",
            "pgvector_ready": False,
        }

    if not extension_available:
        return {
            "mode": "fallback",
            "reason": "pgvector extension files are not installed on this PostgreSQL instance",
            "pgvector_ready": False,
        }
    try:
        extension_installed = bool(
            db.execute(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")).scalar()
        )
        vector_type_present = bool(
            db.execute(text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'vector')")).scalar()
        )
    except Exception as exc:
        return {
            "mode": "fallback",
            "reason": f"database introspection failed: {exc}",
            "pgvector_ready": False,
        }
    if not extension_installed or not vector_type_present:
        return {
            "mode": "fallback",
            "reason": "pgvector is available on the server but not enabled in this database",
            "pgvector_ready": False,
        }
    try:
        column_present = bool(
            db.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'knowledge_chunks'
                          AND column_name = 'embedding_vector'
                    )
                    """
                )
            ).scalar()
        )
    except Exception as exc:
        return {
            "mode": "fallback",
            "reason": f"database introspection failed: {exc}",
            "pgvector_ready": False,
        }
    if not column_present:
        return {
            "mode": "fallback",
            "reason": "knowledge_chunks.embedding_vector is missing",
            "pgvector_ready": False,
        }
    return {
        "mode": "pgvector",
        "reason": "pgvector is active",
        "pgvector_ready": True,
    }


def _supports_pgvector(db: Session) -> bool:
    return bool(vector_backend_status(db).get("pgvector_ready"))


def vector_backend_label(db: Session) -> str:
    return str(vector_backend_status(db).get("mode") or "fallback")


def _build_chunk_metadata(document: KnowledgeDocument) -> dict:
    source_kind = _normalize_source_kind(document.type)
    return {
        "title": document.title,
        "type": document.type,
        "source": document.source,
        "source_label": document.source or document.title,
        "source_kind": source_kind,
        "memory_class": _memory_class_for_document(document.type),
        "confirmed": True,
    }


def _persist_embedding_vector(db: Session, *, chunk_id, embedding: list[float]) -> None:
    if not _supports_pgvector(db):
        return
    db.execute(
        text(
            """
            UPDATE knowledge_chunks
            SET embedding_vector = CAST(:embedding_vector AS vector)
            WHERE id = :chunk_id
            """
        ),
        {
            "chunk_id": str(chunk_id),
            "embedding_vector": _vector_literal(embedding),
        },
    )


def _rebuild_document_chunks(db: Session, document: KnowledgeDocument) -> int:
    db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == document.id).delete()
    chunks = chunk_text(document.raw_content)
    metadata_json = _build_chunk_metadata(document)

    for index, chunk in enumerate(chunks):
        embedding = embed_text(chunk)
        row = KnowledgeChunk(
            document_id=document.id,
            project_id=document.project_id,
            chunk_index=index,
            content=chunk,
            embedding=embedding,
            token_count=max(len(_tokenize(chunk)), 1),
            metadata_json=metadata_json,
        )
        db.add(row)
        db.flush()
        _persist_embedding_vector(db, chunk_id=row.id, embedding=embedding)

    document.status = "ready"
    document.chunk_count = len(chunks)
    db.add(document)
    db.flush()
    return len(chunks)


def create_knowledge_document(
    db: Session,
    *,
    project_id,
    title: str,
    doc_type: str,
    raw_content: str,
    source: str | None = None,
) -> KnowledgeDocument:
    document = KnowledgeDocument(
        project_id=project_id,
        title=title,
        type=doc_type,
        raw_content=raw_content,
        summary=(raw_content or "").strip()[:200] or None,
        source=source,
        status="processing",
        chunk_count=0,
        metadata_json={
            "memory_class": _memory_class_for_document(doc_type),
            "source_kind": _normalize_source_kind(doc_type),
            "source_label": source or title,
            "confirmed": True,
        },
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    _rebuild_document_chunks(db, document)
    db.commit()
    db.refresh(document)
    return document


def create_style_memory(
    db: Session,
    *,
    project_id,
    scene_id=None,
    memory_type: str,
    content: str,
    source_excerpt: str | None = None,
    derived_rules: list[str] | None = None,
    user_confirmed: bool = False,
    status: str = "suggested",
    scope_type: str = "project",
    scope_id=None,
    active: bool = True,
    expires_at=None,
) -> StyleMemory:
    memory = StyleMemory(
        project_id=project_id,
        scene_id=scene_id,
        memory_type=memory_type,
        content=content,
        source_excerpt=source_excerpt,
        derived_rules=derived_rules or [],
        user_confirmed=user_confirmed,
        status=status,
        scope_type=scope_type,
        scope_id=scope_id,
        active=active,
        expires_at=expires_at,
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def list_style_memories(db: Session, *, project_id, include_unconfirmed: bool = True) -> list[StyleMemory]:
    query = db.query(StyleMemory).filter(StyleMemory.project_id == project_id, StyleMemory.active.is_(True))
    if not include_unconfirmed:
        query = query.filter(StyleMemory.user_confirmed.is_(True))
    return query.order_by(StyleMemory.updated_at.desc(), StyleMemory.created_at.desc()).all()


def confirm_style_memory(db: Session, *, memory_id, user_confirmed: bool = True, status: str | None = "confirmed") -> StyleMemory | None:
    memory = db.query(StyleMemory).filter(StyleMemory.id == memory_id).first()
    if not memory:
        return None
    memory.user_confirmed = user_confirmed
    if status is not None:
        memory.status = status
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def reindex_project_knowledge(db: Session, *, project_id) -> tuple[int, int]:
    documents = (
        db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.project_id == project_id)
        .order_by(KnowledgeDocument.created_at.asc())
        .all()
    )

    rebuilt_chunks = 0
    for document in documents:
        rebuilt_chunks += _rebuild_document_chunks(db, document)

    db.commit()
    return len(documents), rebuilt_chunks


def _row_to_hit(row) -> KnowledgeChunkHit:
    metadata_json = row.metadata_json or {}
    confirmed = metadata_json.get("confirmed")
    if confirmed is None:
        confirmed = metadata_json.get("memory_class") != "style_memory"
    return KnowledgeChunkHit(
        chunk_id=row.chunk_id,
        document_id=row.document_id,
        document_title=row.document_title,
        document_type=row.document_type,
        memory_class=metadata_json.get("memory_class"),
        source_label=metadata_json.get("source_label") or row.document_title,
        confirmed=bool(confirmed) if confirmed is not None else None,
        score=round(float(row.score), 4),
        content=row.content,
        source_kind=metadata_json.get("source_kind") or row.document_type,
        citation=f"{row.document_type}:{row.document_title}",
        metadata_json=metadata_json,
    )


def _retrieve_knowledge_pgvector(
    db: Session,
    *,
    project_id,
    query: str,
    top_k: int,
    source_kinds: list[str] | None = None,
) -> list[KnowledgeChunkHit]:
    allowed = [_normalize_source_kind(item) for item in (source_kinds or []) if item and item.strip()]
    query_embedding = embed_text(query)
    params = {
        "project_id": str(project_id),
        "query_vector": _vector_literal(query_embedding),
        "top_k": top_k,
    }
    sql = """
        SELECT
            kc.id AS chunk_id,
            kc.document_id AS document_id,
            kd.title AS document_title,
            kd.type AS document_type,
            kc.content AS content,
            kc.metadata_json AS metadata_json,
            (1 - (kc.embedding_vector <=> CAST(:query_vector AS vector))) AS score
        FROM knowledge_chunks kc
        JOIN knowledge_documents kd ON kd.id = kc.document_id
        WHERE kc.project_id = :project_id
          AND kc.embedding_vector IS NOT NULL
    """
    if allowed:
        sql += " AND lower(coalesce(kd.type, 'misc')) = ANY(:source_kinds)"
        params["source_kinds"] = allowed
    sql += " ORDER BY kc.embedding_vector <=> CAST(:query_vector AS vector) ASC LIMIT :top_k"

    rows = db.execute(text(sql), params).mappings().all()
    return [_row_to_hit(row) for row in rows if float(row["score"] or 0.0) > 0]


def _retrieve_knowledge_fallback(
    db: Session,
    *,
    project_id,
    query: str,
    top_k: int,
    source_kinds: list[str] | None = None,
) -> list[KnowledgeChunkHit]:
    query_embedding = embed_text(query)
    rows = (
        db.query(KnowledgeChunk, KnowledgeDocument)
        .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
        .filter(KnowledgeChunk.project_id == project_id)
        .all()
    )

    allowed = {_normalize_source_kind(item) for item in (source_kinds or []) if item and item.strip()}
    hits: list[KnowledgeChunkHit] = []
    for chunk, document in rows:
        source_kind = _normalize_source_kind(document.type)
        if allowed and source_kind not in allowed:
            continue
        score = cosine_similarity(chunk.embedding or [], query_embedding)
        if score <= 0:
            continue
        metadata_json = chunk.metadata_json or _build_chunk_metadata(document)
        hits.append(
            KnowledgeChunkHit(
                chunk_id=chunk.id,
                document_id=document.id,
                document_title=document.title,
                document_type=document.type,
                memory_class=metadata_json.get("memory_class"),
                source_label=metadata_json.get("source_label") or document.title,
                confirmed=bool(metadata_json.get("confirmed", metadata_json.get("memory_class") != "style_memory")),
                score=round(score, 4),
                content=chunk.content,
                source_kind=metadata_json.get("source_kind") or document.type,
                citation=f"{document.type}:{document.title}",
                metadata_json=metadata_json,
            )
        )

    hits.sort(key=lambda item: item.score, reverse=True)
    return hits[:top_k]


def retrieve_knowledge(
    db: Session,
    *,
    project_id,
    query: str,
    top_k: int = 3,
    source_kinds: list[str] | None = None,
) -> list[KnowledgeChunkHit]:
    hits, _status = retrieve_knowledge_with_status(
        db,
        project_id=project_id,
        query=query,
        top_k=top_k,
        source_kinds=source_kinds,
    )
    return hits


def retrieve_knowledge_with_status(
    db: Session,
    *,
    project_id,
    query: str,
    top_k: int = 3,
    source_kinds: list[str] | None = None,
) -> tuple[list[KnowledgeChunkHit], dict]:
    status = vector_backend_status(db)
    if status["pgvector_ready"]:
        try:
            hits = _retrieve_knowledge_pgvector(
                db,
                project_id=project_id,
                query=query,
                top_k=top_k,
                source_kinds=source_kinds,
            )
            return hits, status
        except Exception as exc:
            fallback_status = {
                "mode": "fallback",
                "reason": f"pgvector query failed: {exc}",
                "pgvector_ready": False,
            }
            return (
                _retrieve_knowledge_fallback(
                    db,
                    project_id=project_id,
                    query=query,
                    top_k=top_k,
                    source_kinds=source_kinds,
                ),
                fallback_status,
            )

    return (
        _retrieve_knowledge_fallback(
            db,
            project_id=project_id,
            query=query,
            top_k=top_k,
            source_kinds=source_kinds,
        ),
        status,
    )


def format_knowledge_hits(hits: list[KnowledgeChunkHit]) -> str:
    if not hits:
        return "No memory hits."

    lines = ["Relevant memory:"]
    for index, hit in enumerate(hits, start=1):
        lines.append(f"{index}. [{hit.document_type}] {hit.document_title}")
        lines.append(hit.content)
    return "\n".join(lines)
