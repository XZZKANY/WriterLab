from fastapi import APIRouter

from app.api.settings import router as settings_router

router = APIRouter(tags=["settings"])
router.include_router(settings_router)
