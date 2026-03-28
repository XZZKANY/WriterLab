from pydantic import BaseModel

from app.schemas.scene import SceneResponse
from app.schemas.character import CharacterResponse
from app.schemas.knowledge import KnowledgeChunkHit
from app.schemas.location import LocationResponse
from app.schemas.style_memory import StyleMemoryResponse
from app.schemas.timeline_event import TimelineEventResponse


class SceneContextResponse(BaseModel):
    scene: SceneResponse
    pov_character: CharacterResponse | None = None
    location: LocationResponse | None = None
    timeline_events: list[TimelineEventResponse] = []
    style_memories: list[StyleMemoryResponse] = []
    knowledge_hits: list[KnowledgeChunkHit] = []
    recent_scenes: list[dict] = []
