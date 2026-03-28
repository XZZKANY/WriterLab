from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect

from app.api.ai import router as ai_router
from app.api.branches import router as branches_router
from app.api.books import router as books_router
from app.api.characters import router as characters_router
from app.api.chapters import router as chapters_router
from app.api.consistency import router as consistency_router
from app.api.health import router as health_router
from app.api.knowledge import router as knowledge_router
from app.api.locations import router as locations_router
from app.api.lore_entries import router as lore_entries_router
from app.api.projects import router as projects_router
from app.api.scenes import router as scenes_router
from app.api.settings import router as settings_router
from app.api.vn import router as vn_router
from app.db.schema_upgrades import apply_schema_upgrades
from app.db.session import engine
from app.services.workflow_service import ensure_workflow_runner_started

app = FastAPI(title="WriterLab API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(projects_router)
app.include_router(books_router)
app.include_router(chapters_router)
app.include_router(scenes_router)
app.include_router(characters_router)
app.include_router(locations_router)
app.include_router(lore_entries_router)
app.include_router(ai_router)
app.include_router(knowledge_router)
app.include_router(consistency_router)
app.include_router(branches_router)
app.include_router(vn_router)
app.include_router(settings_router)


def _assert_schema_is_migrated() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "alembic_version" not in tables:
        raise RuntimeError("Database schema is not managed yet. Run Alembic migrations before starting the API.")


@app.on_event("startup")
def on_startup() -> None:
    _assert_schema_is_migrated()
    apply_schema_upgrades(engine)
    ensure_workflow_runner_started()


@app.get("/")
def root():
    return {"message": "WriterLab backend is running"}
