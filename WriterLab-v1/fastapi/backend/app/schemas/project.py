from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.book import BookResponse
from app.schemas.chapter import ChapterResponse
from app.schemas.scene import SceneResponse


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    genre: str | None = None
    default_language: str = "zh-CN"


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    genre: str | None
    default_language: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectDeleteResponse(BaseModel):
    deleted: bool
    project_id: UUID


class ProjectCountsResponse(BaseModel):
    books: int
    chapters: int
    scenes: int


class ProjectOverviewResponse(BaseModel):
    project: ProjectResponse
    books: list[BookResponse]
    chapters_by_book: dict[str, list[ChapterResponse]]
    scenes_by_chapter: dict[str, list[SceneResponse]]
    counts: ProjectCountsResponse
