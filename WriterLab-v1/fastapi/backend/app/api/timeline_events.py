from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.timeline_repository import get_timeline_event, list_timeline_events
from app.schemas.timeline_event import (
    TimelineEventCreate,
    TimelineEventDeleteResponse,
    TimelineEventResponse,
    TimelineEventUpdate,
)
from app.services.timeline_service import (
    create_timeline_event,
    delete_timeline_event,
    update_timeline_event,
)

router = APIRouter(prefix="/api/timeline-events", tags=["timeline"])


@router.get("", response_model=list[TimelineEventResponse])
def list_timeline_events_api(
    project_id: UUID,
    chapter_id: UUID | None = None,
    scene_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    return list_timeline_events(db, project_id=project_id, chapter_id=chapter_id, scene_id=scene_id)


@router.post("", response_model=TimelineEventResponse)
def create_timeline_event_api(payload: TimelineEventCreate, db: Session = Depends(get_db)):
    return create_timeline_event(db, payload)


@router.get("/{event_id}", response_model=TimelineEventResponse)
def get_timeline_event_api(event_id: UUID, db: Session = Depends(get_db)):
    row = get_timeline_event(db, event_id)
    if not row:
        raise HTTPException(status_code=404, detail="Timeline event not found")
    return row


@router.patch("/{event_id}", response_model=TimelineEventResponse)
def update_timeline_event_api(event_id: UUID, payload: TimelineEventUpdate, db: Session = Depends(get_db)):
    row = get_timeline_event(db, event_id)
    if not row:
        raise HTTPException(status_code=404, detail="Timeline event not found")
    return update_timeline_event(db, row, payload)


@router.delete("/{event_id}", response_model=TimelineEventDeleteResponse)
def delete_timeline_event_api(event_id: UUID, db: Session = Depends(get_db)):
    row = get_timeline_event(db, event_id)
    if not row:
        raise HTTPException(status_code=404, detail="Timeline event not found")
    delete_timeline_event(db, row)
    return TimelineEventDeleteResponse(deleted=True, timeline_event_id=event_id)
