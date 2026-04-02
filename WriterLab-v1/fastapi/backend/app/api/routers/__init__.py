from app.api.routers.health import router as health_router
from app.api.routers.lore import router as lore_router
from app.api.routers.project import router as project_router
from app.api.routers.runtime import router as runtime_router
from app.api.routers.settings import router as settings_router
from app.api.routers.story import router as story_router
from app.api.routers.workflow import router as workflow_router

__all__ = [
    "health_router",
    "lore_router",
    "project_router",
    "runtime_router",
    "settings_router",
    "story_router",
    "workflow_router",
]
