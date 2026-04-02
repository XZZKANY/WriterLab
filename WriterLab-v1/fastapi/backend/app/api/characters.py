from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.models.character import Character
from app.repositories.lore_repository import list_characters_by_project
from app.schemas.character import CharacterCreate, CharacterResponse

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
