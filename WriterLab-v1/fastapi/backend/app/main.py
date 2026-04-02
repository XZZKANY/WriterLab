import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import (
    health_router,
    lore_router,
    project_router,
    runtime_router,
    settings_router,
    story_router,
    workflow_router,
)
from app.tasks.startup_checks import run_startup_sequence

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    run_startup_sequence()
    yield


app = FastAPI(title="WriterLab API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(project_router)
app.include_router(story_router)
app.include_router(lore_router)
app.include_router(workflow_router)
app.include_router(settings_router)
app.include_router(runtime_router)


@app.get("/")
def root():
    return {"message": "WriterLab backend is running"}
