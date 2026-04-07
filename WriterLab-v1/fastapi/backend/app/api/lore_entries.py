from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.models.lore_entry import LoreEntry
from app.repositories.lore_repository import (
    delete_lore_entry as delete_lore_entry_query,
    get_lore_entry as get_lore_entry_query,
    list_lore_entries_by_project,
    update_lore_entry as update_lore_entry_query,
)
from app.schemas.lore_entry import (
    LoreEntryCreate,
    LoreEntryDeleteResponse,
    LoreEntryResponse,
    LoreEntryUpdate,
)

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
    return list_lore_entries_by_project(db, project_id)


@router.get("/{entry_id}", response_model=LoreEntryResponse)
def get_lore_entry(entry_id: UUID, db: Session = Depends(get_db)):
    lore_entry = get_lore_entry_query(db, entry_id)
    if not lore_entry:
        raise HTTPException(status_code=404, detail="Lore entry not found")
    return lore_entry


@router.patch("/{entry_id}", response_model=LoreEntryResponse)
def update_lore_entry(entry_id: UUID, payload: LoreEntryUpdate, db: Session = Depends(get_db)):
    lore_entry = get_lore_entry_query(db, entry_id)
    if not lore_entry:
        raise HTTPException(status_code=404, detail="Lore entry not found")
    return update_lore_entry_query(db, lore_entry, payload)


@router.delete("/{entry_id}", response_model=LoreEntryDeleteResponse)
def delete_lore_entry(entry_id: UUID, db: Session = Depends(get_db)):
    lore_entry = get_lore_entry_query(db, entry_id)
    if not lore_entry:
        raise HTTPException(status_code=404, detail="Lore entry not found")
    delete_lore_entry_query(db, lore_entry)
    return {"deleted": True, "lore_entry_id": entry_id}
