from pydantic import BaseModel, Field

from app.schemas.character import CharacterResponse
from app.schemas.context_bundle import SceneSummary
from app.schemas.knowledge import KnowledgeChunkHit
from app.schemas.location import LocationResponse
from app.schemas.style_memory import StyleMemoryResponse
from app.schemas.timeline_event import TimelineEventResponse
from app.schemas.workflow import ContextCompileSnapshot


class SceneContextResponse(BaseModel):
    scene: SceneSummary
    scene_status: str | None = None
    scene_version: int | None = None
    pov_character: CharacterResponse | None = None
    location: LocationResponse | None = None
    timeline_events: list[TimelineEventResponse] = Field(default_factory=list)
    style_memories: list[StyleMemoryResponse] = Field(default_factory=list)
    knowledge_hits: list[KnowledgeChunkHit] = Field(default_factory=list)
    recent_scenes: list[dict] = Field(default_factory=list)
    context_compile_snapshot: ContextCompileSnapshot | None = None
