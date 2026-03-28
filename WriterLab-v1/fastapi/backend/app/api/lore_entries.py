from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.models.lore_entry import LoreEntry
from app.schemas.lore_entry import LoreEntryCreate, LoreEntryResponse

router = APIRouter(prefix="/api/lore-entries", tags=["lore_entries"])


@router.post("", response_model=LoreEntryResponse)
def create_lore_entry(payload: LoreEntryCreate, db: Session = Depends(get_db)):
    lore_entry = LoreEntry(
        project_id=payload.project_id,
        category=payload.category,
        title=payload.title,
        content=payload.content,
        priority=payload.priority,
        canonical=payload.canonical,
    )
    db.add(lore_entry)
    db.commit()
    db.refresh(lore_entry)
    return lore_entry


@router.get("", response_model=list[LoreEntryResponse])
def list_lore_entries(project_id: UUID, db: Session = Depends(get_db)):
    return db.query(LoreEntry).filter(LoreEntry.project_id == project_id).order_by(LoreEntry.created_at.asc()).all()