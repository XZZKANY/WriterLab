import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ai import router as ai_router
from app.api.books import router as books_router
from app.api.branches import router as branches_router
from app.api.chapters import router as chapters_router
from app.api.characters import router as characters_router
from app.api.consistency import router as consistency_router
from app.api.health import router as health_router
from app.api.knowledge import router as knowledge_router
from app.api.locations import router as locations_router
from app.api.lore_entries import router as lore_entries_router
from app.api.projects import router as projects_router
from app.api.runtime import router as runtime_router
from app.api.scenes import router as scenes_router
from app.api.settings import router as settings_router
from app.api.timeline_events import router as timeline_events_router
from app.api.vn import router as vn_router
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

# 健康检查
app.include_router(health_router)

# 项目层（项目 / 书 / 章节）
app.include_router(projects_router)
app.include_router(books_router)
app.include_router(chapters_router)

# 故事层（场景 / 分支 / 时间线 / VN 导出）
app.include_router(scenes_router)
app.include_router(branches_router)
app.include_router(timeline_events_router)
app.include_router(vn_router)

# 设定层（角色 / 地点 / 词条）
app.include_router(characters_router)
app.include_router(locations_router)
app.include_router(lore_entries_router)

# 工作流与知识
app.include_router(ai_router)
app.include_router(knowledge_router)
app.include_router(consistency_router)

# 设置与运行时观测
app.include_router(settings_router)
app.include_router(runtime_router)


@app.get("/")
def root():
    return {"message": "WriterLab backend is running"}
