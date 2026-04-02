from fastapi import APIRouter

from app.api.books import router as books_router
from app.api.chapters import router as chapters_router
from app.api.projects import router as projects_router

router = APIRouter(tags=["project"])
router.include_router(projects_router)
router.include_router(books_router)
router.include_router(chapters_router)
