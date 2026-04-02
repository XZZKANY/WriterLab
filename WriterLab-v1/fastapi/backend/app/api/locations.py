from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.models.location import Location
from app.repositories.lore_repository import list_locations_by_project
from app.schemas.location import LocationCreate, LocationUpdate, LocationResponse

router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.post("", response_model=LocationResponse)
def create_location(payload: LocationCreate, db: Session = Depends(get_db)):
    location = Location(
        project_id=payload.project_id,
        name=payload.name,
        description=payload.description,
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


@router.get("", response_model=list[LocationResponse])
def list_locations(project_id: UUID, db: Session = Depends(get_db)):
    return list_locations_by_project(db, project_id)


@router.get("/{location_id}", response_model=LocationResponse)
def get_location(location_id: UUID, db: Session = Depends(get_db)):
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


@router.patch("/{location_id}", response_model=LocationResponse)
def update_location(location_id: UUID, payload: LocationUpdate, db: Session = Depends(get_db)):
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(location, key, value)

    db.commit()
    db.refresh(location)
    return location
