from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.models.character import Character
from app.repositories.lore_repository import (
    delete_character as delete_character_query,
    get_character as get_character_query,
    list_characters_by_project,
    update_character as update_character_query,
)
from app.schemas.character import (
    CharacterCreate,
    CharacterDeleteResponse,
    CharacterResponse,
    CharacterUpdate,
)

router = APIRouter(prefix="/api/characters", tags=["characters"])


@router.post("", response_model=CharacterResponse)
def create_character(payload: CharacterCreate, db: Session = Depends(get_db)):
    character = Character(
        project_id=payload.project_id,
        name=payload.name,
        aliases=payload.aliases,
        appearance=payload.appearance,
        personality=payload.personality,
        background=payload.background,
        motivation=payload.motivation,
        speaking_style=payload.speaking_style,
        status=payload.status,
        secrets=payload.secrets,
    )
    db.add(character)
    db.commit()
    db.refresh(character)
    return character


@router.get("", response_model=list[CharacterResponse])
def list_characters(project_id: UUID, db: Session = Depends(get_db)):
    return list_characters_by_project(db, project_id)


@router.get("/{character_id}", response_model=CharacterResponse)
def get_character(character_id: UUID, db: Session = Depends(get_db)):
    character = get_character_query(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


@router.patch("/{character_id}", response_model=CharacterResponse)
def update_character(character_id: UUID, payload: CharacterUpdate, db: Session = Depends(get_db)):
    character = get_character_query(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return update_character_query(db, character, payload)


@router.delete("/{character_id}", response_model=CharacterDeleteResponse)
def delete_character(character_id: UUID, db: Session = Depends(get_db)):
    character = get_character_query(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    delete_character_query(db, character)
    return {"deleted": True, "character_id": character_id}
