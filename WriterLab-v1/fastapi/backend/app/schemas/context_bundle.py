from pydantic import BaseModel

from app.schemas.character import CharacterResponse
from app.schemas.knowledge import KnowledgeChunkHit
from app.schemas.style_memory import StyleMemoryResponse
from app.schemas.location import LocationResponse
from app.schemas.lore_entry import LoreEntryResponse
from app.schemas.timeline_event import TimelineEventResponse


class SceneSummary(BaseModel):
    title: str
    goal: str | None = None
    conflict: str | None = None
    outcome: str | None = None
    time_label: str | None = None


class ContextBundleResponse(BaseModel):
    scene_summary: SceneSummary
    pov_character: CharacterResponse | None = None
    location: LocationResponse | None = None
    lore_constraints: list[LoreEntryResponse] = []
    timeline_events: list[TimelineEventResponse] = []
    style_memories: list[StyleMemoryResponse] = []
    knowledge_hits: list[KnowledgeChunkHit] = []
    recent_scenes: list[dict] = []
    must_include: list[str] = []
    must_avoid: list[str] = []
