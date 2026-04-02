from fastapi import APIRouter

from app.api.ai import router as ai_router
from app.api.consistency import router as consistency_router
from app.api.knowledge import router as knowledge_router

router = APIRouter(tags=["workflow"])
router.include_router(ai_router)
router.include_router(knowledge_router)
router.include_router(consistency_router)
