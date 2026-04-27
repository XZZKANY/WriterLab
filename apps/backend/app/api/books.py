from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.models.book import Book
from app.repositories.project_repository import list_books_by_project
from app.schemas.book import BookCreate, BookResponse

router = APIRouter(prefix="/api/books", tags=["books"])


@router.post("", response_model=BookResponse)
def create_book(payload: BookCreate, db: Session = Depends(get_db)):
    book = Book(
        project_id=payload.project_id,
        title=payload.title,
        summary=payload.summary,
        status=payload.status,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@router.get("", response_model=list[BookResponse])
def list_books(project_id: UUID, db: Session = Depends(get_db)):
    return list_books_by_project(db, project_id)
