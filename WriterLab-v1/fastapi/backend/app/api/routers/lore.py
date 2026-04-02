from fastapi import APIRouter

from app.api.characters import router as characters_router
from app.api.locations import router as locations_router
from app.api.lore_entries import router as lore_entries_router

router = APIRouter(tags=["lore"])
router.include_router(characters_router)
router.include_router(locations_router)
router.include_router(lore_entries_router)
