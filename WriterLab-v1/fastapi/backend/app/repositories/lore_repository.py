from sqlalchemy.orm import Session

from app.models.character import Character
from app.models.location import Location
from app.models.lore_entry import LoreEntry


def list_characters_by_project(db: Session, project_id):
    return db.query(Character).filter(Character.project_id == project_id).order_by(Character.created_at.asc()).all()


def list_locations_by_project(db: Session, project_id):
    return db.query(Location).filter(Location.project_id == project_id).order_by(Location.created_at.asc()).all()


def list_lore_entries_by_project(db: Session, project_id):
    return db.query(LoreEntry).filter(LoreEntry.project_id == project_id).order_by(LoreEntry.created_at.asc()).all()
