from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.character import Character
from app.models.location import Location
from app.models.lore_entry import LoreEntry
from app.models.scene import Scene
from app.models.style_memory import StyleMemory
from app.models.timeline_event import TimelineEvent
from app.services.knowledge_service import retrieve_knowledge


def _resolve_project_id(scene: Scene, db: Session):
    chapter = db.query(Chapter).filter(Chapter.id == scene.chapter_id).first()
    if not chapter:
        return None
    book = db.query(Book).filter(Book.id == chapter.book_id).first()
    return book.project_id if book else None


def _scene_query(scene: Scene) -> str:
    parts = [
        scene.title or "",
        scene.goal or "",
        scene.conflict or "",
        scene.outcome or "",
        " ".join(scene.must_include or []),
        " ".join(scene.must_avoid or []),
    ]
    return "\n".join(part for part in parts if part).strip()


def _recent_scene_context(scene: Scene, db: Session) -> list[dict]:
    current_chapter = db.query(Chapter).filter(Chapter.id == scene.chapter_id).first()
    if not current_chapter:
        return []

    recent_scenes = (
        db.query(Scene)
        .filter(Scene.chapter_id == scene.chapter_id, Scene.scene_no < scene.scene_no)
        .order_by(Scene.scene_no.desc())
        .limit(5)
        .all()
    )

    previous_chapter = (
        db.query(Chapter)
        .filter(Chapter.book_id == current_chapter.book_id, Chapter.chapter_no < current_chapter.chapter_no)
        .order_by(Chapter.chapter_no.desc())
        .first()
    )
    if previous_chapter:
        recent_scenes.extend(
            db.query(Scene)
            .filter(Scene.chapter_id == previous_chapter.id)
            .order_by(Scene.scene_no.desc())
            .limit(3)
            .all()
        )

    serialized: list[dict] = []
    seen_scene_ids = set()
    for item in recent_scenes:
        if item.id in seen_scene_ids:
            continue
        seen_scene_ids.add(item.id)
        serialized.append(
            {
                "scene_id": str(item.id),
                "title": item.title,
                "scene_no": item.scene_no,
                "time_label": item.time_label,
                "summary": (item.outcome or item.conflict or item.goal or item.draft_text or "")[:240],
            }
        )
    return serialized


def build_scene_context(scene: Scene, db: Session):
    pov_character = None
    location = None
    lore_constraints = []
    timeline_events = []
    style_memories = []
    knowledge_hits = []
    recent_scenes = []

    if scene.pov_character_id:
        pov_character = db.query(Character).filter(Character.id == scene.pov_character_id).first()

    if scene.location_id:
        location = db.query(Location).filter(Location.id == scene.location_id).first()

    project_id = _resolve_project_id(scene, db)
    if project_id:
        recent_scenes = _recent_scene_context(scene, db)
        lore_constraints = (
            db.query(LoreEntry)
            .filter(LoreEntry.project_id == project_id, LoreEntry.canonical.is_(True))
            .order_by(LoreEntry.priority.desc(), LoreEntry.created_at.asc())
            .limit(5)
            .all()
        )
        timeline_events = (
            db.query(TimelineEvent)
            .filter(TimelineEvent.project_id == project_id)
            .order_by(TimelineEvent.created_at.desc())
            .limit(8)
            .all()
        )
        style_memories = (
            db.query(StyleMemory)
            .filter(
                StyleMemory.project_id == project_id,
                StyleMemory.user_confirmed.is_(True),
            )
            .order_by(StyleMemory.updated_at.desc())
            .limit(8)
            .all()
        )
        knowledge_hits = retrieve_knowledge(
            db,
            project_id=project_id,
            query="\n".join(
                [
                    _scene_query(scene),
                    "\n".join(item["summary"] for item in recent_scenes if item.get("summary")),
                    "\n".join(event.description for event in timeline_events),
                ]
            ).strip(),
            top_k=5,
            source_kinds=["character", "location", "lore", "rules", "timeline", "style"],
        )

    return {
        "scene_summary": {
            "title": scene.title,
            "goal": scene.goal,
            "conflict": scene.conflict,
            "outcome": scene.outcome,
            "time_label": scene.time_label,
        },
        "pov_character": pov_character,
        "location": location,
        "lore_constraints": lore_constraints,
        "timeline_events": timeline_events,
        "style_memories": style_memories,
        "knowledge_hits": knowledge_hits,
        "recent_scenes": recent_scenes,
        "must_include": scene.must_include or [],
        "must_avoid": scene.must_avoid or [],
    }
