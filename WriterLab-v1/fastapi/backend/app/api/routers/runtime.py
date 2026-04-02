from fastapi import APIRouter

from app.api.runtime import router as runtime_router

router = APIRouter(tags=["runtime"])
router.include_router(runtime_router)
