from sqlalchemy.orm import Session

from app.models.timeline_event import TimelineEvent


def list_timeline_events(db: Session, *, project_id, chapter_id=None, scene_id=None) -> list[TimelineEvent]:
    query = db.query(TimelineEvent).filter(TimelineEvent.project_id == project_id)
    if chapter_id is not None:
        query = query.filter(TimelineEvent.chapter_id == chapter_id)
    if scene_id is not None:
        query = query.filter(TimelineEvent.scene_id == scene_id)
    return query.order_by(TimelineEvent.created_at.desc()).all()


def get_timeline_event(db: Session, event_id):
    return db.query(TimelineEvent).filter(TimelineEvent.id == event_id).first()


def create_timeline_event(db: Session, payload) -> TimelineEvent:
    row = TimelineEvent(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_timeline_event(db: Session, row: TimelineEvent, payload) -> TimelineEvent:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_timeline_event(db: Session, row: TimelineEvent) -> None:
    db.delete(row)
    db.commit()
