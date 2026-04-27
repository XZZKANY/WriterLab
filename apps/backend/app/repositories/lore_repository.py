from sqlalchemy.orm import Session

from app.models.character import Character
from app.models.location import Location
from app.models.lore_entry import LoreEntry


def list_characters_by_project(db: Session, project_id):
    return db.query(Character).filter(Character.project_id == project_id).order_by(Character.created_at.asc()).all()


def get_character(db: Session, character_id):
    return db.query(Character).filter(Character.id == character_id).first()


def update_character(db: Session, character, payload):
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(character, key, value)
    db.commit()
    db.refresh(character)
    return character


def delete_character(db: Session, character):
    db.delete(character)
    db.commit()
    return True


def list_locations_by_project(db: Session, project_id):
    return db.query(Location).filter(Location.project_id == project_id).order_by(Location.created_at.asc()).all()


def get_location(db: Session, location_id):
    return db.query(Location).filter(Location.id == location_id).first()


def update_location(db: Session, location, payload):
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(location, key, value)
    db.commit()
    db.refresh(location)
    return location


def delete_location(db: Session, location):
    db.delete(location)
    db.commit()
    return True


def list_lore_entries_by_project(db: Session, project_id):
    return db.query(LoreEntry).filter(LoreEntry.project_id == project_id).order_by(LoreEntry.created_at.asc()).all()


def get_lore_entry(db: Session, lore_entry_id):
    return db.query(LoreEntry).filter(LoreEntry.id == lore_entry_id).first()


def update_lore_entry(db: Session, lore_entry, payload):
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(lore_entry, key, value)
    db.commit()
    db.refresh(lore_entry)
    return lore_entry


def delete_lore_entry(db: Session, lore_entry):
    db.delete(lore_entry)
    db.commit()
    return True
