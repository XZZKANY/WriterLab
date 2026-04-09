from sqlalchemy.orm import Session

from app.repositories.timeline_repository import (
    create_timeline_event as create_timeline_event_record,
    delete_timeline_event as delete_timeline_event_record,
    update_timeline_event as update_timeline_event_record,
)


def create_timeline_event(db: Session, payload):
    return create_timeline_event_record(db, payload)


def update_timeline_event(db: Session, row, payload):
    return update_timeline_event_record(db, row, payload)


def delete_timeline_event(db: Session, row):
    delete_timeline_event_record(db, row)
