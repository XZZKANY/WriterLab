from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.models.chapter import Chapter
from app.schemas.chapter import ChapterCreate, ChapterResponse

router = APIRouter(prefix="/api/chapters", tags=["chapters"])


@router.post("", response_model=ChapterResponse)
def create_chapter(payload: ChapterCreate, db: Session = Depends(get_db)):
    chapter = Chapter(
        book_id=payload.book_id,
        chapter_no=payload.chapter_no,
        title=payload.title,
        summary=payload.summary,
        status=payload.status,
    )
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter


@router.get("", response_model=list[ChapterResponse])
def list_chapters(book_id: UUID, db: Session = Depends(get_db)):
    return db.query(Chapter).filter(Chapter.book_id == book_id).order_by(Chapter.chapter_no.asc()).all()