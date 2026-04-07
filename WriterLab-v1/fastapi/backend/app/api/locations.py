from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.models.location import Location
from app.repositories.lore_repository import (
    delete_location as delete_location_query,
    get_location as get_location_query,
    list_locations_by_project,
    update_location as update_location_query,
)
from app.schemas.location import (
    LocationCreate,
    LocationDeleteResponse,
    LocationResponse,
    LocationUpdate,
)

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
    location = get_location_query(db, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


@router.patch("/{location_id}", response_model=LocationResponse)
def update_location(location_id: UUID, payload: LocationUpdate, db: Session = Depends(get_db)):
    location = get_location_query(db, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return update_location_query(db, location, payload)


@router.delete("/{location_id}", response_model=LocationDeleteResponse)
def delete_location(location_id: UUID, db: Session = Depends(get_db)):
    location = get_location_query(db, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    delete_location_query(db, location)
    return {"deleted": True, "location_id": location_id}
