from fastapi import APIRouter

from app.api.branches import router as branches_router
from app.api.timeline_events import router as timeline_events_router
from app.api.scenes import router as scenes_router
from app.api.vn import router as vn_router

router = APIRouter(tags=["story"])
router.include_router(scenes_router)
router.include_router(branches_router)
router.include_router(timeline_events_router)
router.include_router(vn_router)
