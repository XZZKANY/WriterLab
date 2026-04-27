from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.character import Character
from app.models.location import Location
from app.models.lore_entry import LoreEntry
from app.models.scene import Scene
from app.models.story_branch import StoryBranch
from app.models.style_memory import StyleMemory
from app.models.timeline_event import TimelineEvent
from app.schemas.workflow import ContextCompileCandidate, ContextCompileSnapshot
from app.services.knowledge_service import retrieve_knowledge


DEFAULT_BUDGET_RATIO = {
    "lore": 0.40,
    "recent_scenes": 0.30,
    "user_prompt": 0.20,
    "style_memory": 0.10,
}

BUDGET_LIMITS = {
    "lore": (0.20, 0.40),
    "recent_scenes": (0.20, 0.40),
    "user_prompt": (0.15, 0.55),
    "style_memory": (0.05, 0.15),
}


@dataclass
class _CandidateRow:
    source_id: str
    source_type: str
    scope: str
    title: str
    content: str
    created_at: datetime | None
    importance: float


def _resolve_project_id(scene: Scene, db: Session):
    chapter = db.query(Chapter).filter(Chapter.id == scene.chapter_id).first()
    if not chapter:
        return None
    book = db.query(Book).filter(Book.id == chapter.book_id).first()
    return book.project_id if book else None


def _chapter_window(scene: Scene, db: Session) -> tuple[Chapter | None, Chapter | None]:
    current = db.query(Chapter).filter(Chapter.id == scene.chapter_id).first()
    if not current:
        return None, None
    previous = (
        db.query(Chapter)
        .filter(Chapter.book_id == current.book_id, Chapter.chapter_no < current.chapter_no)
        .order_by(Chapter.chapter_no.desc())
        .first()
    )
    return current, previous


def _scene_query(scene: Scene) -> str:
    parts = [
        scene.title or "",
        scene.goal or "",
        scene.conflict or "",
        scene.outcome or "",
        " ".join(scene.must_include or []),
        " ".join(scene.must_avoid or []),
        scene.draft_text or "",
    ]
    return "\n".join(part for part in parts if part).strip()


def _token_count(text: str) -> int:
    return max(len((text or "").split()), 1 if (text or "").strip() else 0)


def _overlap_similarity(query: str, content: str) -> float:
    left = {item for item in query.lower().split() if item}
    right = {item for item in content.lower().split() if item}
    if not left or not right:
        return 0.0
    return len(left & right) / max(len(left), 1)


def _recency_score(value: datetime | None) -> float:
    if value is None:
        return 0.2
    age_days = max((datetime.utcnow() - value).days, 0)
    return max(0.0, 1.0 - min(age_days / 30.0, 1.0))


def _score_candidate(query: str, row: _CandidateRow) -> ContextCompileCandidate:
    similarity = _overlap_similarity(query, row.content)
    recency = _recency_score(row.created_at)
    importance = max(min(row.importance, 1.0), 0.0)
    score = round((similarity * 0.5) + (recency * 0.3) + (importance * 0.2), 4)
    return ContextCompileCandidate(
        source_id=row.source_id,
        source_type=row.source_type,
        scope=row.scope,
        title=row.title,
        score=score,
        similarity=round(similarity, 4),
        recency=round(recency, 4),
        importance=round(importance, 4),
        token_count=_token_count(row.content),
        summary_applied=False,
        diversity_slot=_candidate_diversity_slot(row.source_type),
    )


def _apply_budget(total_tokens: int = 4000) -> dict[str, int | float]:
    return {
        "total_tokens": total_tokens,
        "lore_ratio": DEFAULT_BUDGET_RATIO["lore"],
        "lore_min_ratio": BUDGET_LIMITS["lore"][0],
        "lore_max_ratio": BUDGET_LIMITS["lore"][1],
        "recent_scenes_ratio": DEFAULT_BUDGET_RATIO["recent_scenes"],
        "recent_scenes_min_ratio": BUDGET_LIMITS["recent_scenes"][0],
        "recent_scenes_max_ratio": BUDGET_LIMITS["recent_scenes"][1],
        "user_prompt_ratio": DEFAULT_BUDGET_RATIO["user_prompt"],
        "user_prompt_min_ratio": BUDGET_LIMITS["user_prompt"][0],
        "style_memory_ratio": DEFAULT_BUDGET_RATIO["style_memory"],
        "style_memory_min_ratio": BUDGET_LIMITS["style_memory"][0],
        "style_memory_max_ratio": BUDGET_LIMITS["style_memory"][1],
        "lore_tokens": int(total_tokens * DEFAULT_BUDGET_RATIO["lore"]),
        "recent_scenes_tokens": int(total_tokens * DEFAULT_BUDGET_RATIO["recent_scenes"]),
        "user_prompt_min_tokens": int(total_tokens * BUDGET_LIMITS["user_prompt"][0]),
        "style_memory_tokens": int(total_tokens * DEFAULT_BUDGET_RATIO["style_memory"]),
    }


def _summarize_recent_scenes(scenes: list[dict]) -> list[dict]:
    summaries: list[dict] = []
    for item in scenes:
        summaries.append(
            {
                "scene_id": item["scene_id"],
                "action_line": item.get("summary") or item.get("title") or "",
                "state_delta": item.get("time_label") or "",
                "causal_links": [],
                "unresolved_hooks": [],
                "must_carry_forward": [item.get("title")] if item.get("title") else [],
            }
        )
    return summaries


def _candidate_diversity_slot(source_type: str) -> str:
    if source_type in {"recent_scene", "timeline"}:
        return "recent"
    if source_type in {"style_memory", "style"}:
        return "style"
    return "lore"


def _select_diverse_candidates(candidates: list[ContextCompileCandidate], *, limit: int = 20) -> tuple[list[ContextCompileCandidate], dict[str, int], list[str]]:
    selected: list[ContextCompileCandidate] = []
    clipped_sources: list[str] = []
    diversity_counts = {"lore": 0, "recent": 0, "style": 0}
    handled_ids: set[str] = set()

    for slot in ("lore", "recent", "style"):
        candidate = next((item for item in candidates if item.diversity_slot == slot), None)
        if candidate is None:
            continue
        handled_ids.add(f"{candidate.source_type}:{candidate.source_id}")
        if len(selected) >= limit:
            clipped_sources.append(f"{candidate.source_type}:{candidate.source_id}")
            continue
        selected.append(candidate)
        diversity_counts[slot] += 1

    for candidate in candidates:
        if f"{candidate.source_type}:{candidate.source_id}" in handled_ids:
            continue
        if candidate in selected:
            continue
        if len(selected) >= limit:
            clipped_sources.append(f"{candidate.source_type}:{candidate.source_id}")
            continue
        selected.append(candidate)
        diversity_counts[candidate.diversity_slot or "lore"] = diversity_counts.get(candidate.diversity_slot or "lore", 0) + 1

    return selected[:limit], diversity_counts, clipped_sources


def _recent_scene_context(scene: Scene, db: Session, *, branch_id: UUID | None = None) -> list[dict]:
    current_chapter, previous_chapter = _chapter_window(scene, db)
    if not current_chapter:
        return []

    branch_anchor_scene_no = None
    if branch_id:
        branch = db.query(StoryBranch).filter(StoryBranch.id == branch_id).first()
        if branch and branch.source_scene_id:
            source_scene = db.query(Scene).filter(Scene.id == branch.source_scene_id).first()
            if source_scene and source_scene.chapter_id == scene.chapter_id:
                branch_anchor_scene_no = source_scene.scene_no

    chapter_query = db.query(Scene).filter(Scene.chapter_id == scene.chapter_id, Scene.scene_no < scene.scene_no)
    if branch_anchor_scene_no is not None:
        chapter_query = chapter_query.filter(Scene.scene_no <= branch_anchor_scene_no)
    recent_scenes = chapter_query.order_by(Scene.scene_no.desc()).limit(5).all()
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
                "branch_id": str(branch_id) if branch_id else None,
            }
        )
    return serialized


def build_scene_context(scene: Scene, db: Session, *, branch_id: UUID | None = None):
    project_id = _resolve_project_id(scene, db)
    pov_character = None
    location = None
    if scene.pov_character_id:
        pov_character = db.query(Character).filter(Character.id == scene.pov_character_id).first()
    if scene.location_id:
        location = db.query(Location).filter(Location.id == scene.location_id).first()

    current_chapter, previous_chapter = _chapter_window(scene, db)
    recent_scenes = _recent_scene_context(scene, db, branch_id=branch_id) if project_id else []
    lore_constraints = []
    timeline_events = []
    style_memories = []
    knowledge_hits = []
    scope_resolution = {
        "canonical_lore": "project",
        "timeline": "branch" if branch_id else "project",
        "recent_scenes": "branch" if branch_id else "project",
        "style_seed": "project",
        "must_avoid_style": "project+character_or_pov",
    }
    snapshot = ContextCompileSnapshot(
        project_id=project_id,
        branch_id=branch_id,
        chapter_id=scene.chapter_id,
        scene_id=scene.id,
        hard_filters=[
            f"project_id={project_id}" if project_id else "project_id=None",
            f"branch_id={branch_id}" if branch_id else "branch_id=None",
            f"chapter_id={scene.chapter_id}",
            "not_archived=true",
        ],
        hard_filter_result={
            "project_match": bool(project_id),
            "branch_match": str(branch_id) if branch_id else "project_default",
            "chapter_window_match": bool(current_chapter),
            "previous_chapter_included": bool(previous_chapter),
            "not_archived": True,
        },
        budget=_apply_budget(),
        scope_resolution=scope_resolution,
    )

    if project_id:
        lore_constraints = (
            db.query(LoreEntry)
            .filter(LoreEntry.project_id == project_id, LoreEntry.canonical.is_(True))
            .order_by(LoreEntry.priority.desc(), LoreEntry.created_at.asc())
            .limit(8)
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
                StyleMemory.active.is_(True),
                StyleMemory.user_confirmed.is_(True),
            )
            .order_by(StyleMemory.updated_at.desc())
            .limit(8)
            .all()
        )
        knowledge_hits = retrieve_knowledge(
            db,
            project_id=project_id,
            query=_scene_query(scene),
            top_k=6,
            source_kinds=["character", "location", "lore", "rules", "timeline", "style"],
        )

    query = _scene_query(scene)
    candidates: list[ContextCompileCandidate] = []
    deduped_sources: list[str] = []
    seen_sources: dict[str, int] = {}

    for item in lore_constraints:
        scored = _score_candidate(
            query,
            _CandidateRow(str(item.id), "lore", "project", item.title, item.content, item.updated_at, min(item.priority / 100.0, 1.0)),
        )
        candidates.append(scored)
    for item in timeline_events:
        scored = _score_candidate(
            query,
            _CandidateRow(str(item.id), "timeline", "branch" if branch_id else "project", item.title, item.description, item.updated_at, 0.7 if item.canonical else 0.5),
        )
        candidates.append(scored)
    for item in style_memories:
        scored = _score_candidate(
            query,
            _CandidateRow(str(item.id), "style_memory", item.scope_type, item.content[:80], item.content, item.updated_at, 0.8 if item.user_confirmed else 0.5),
        )
        candidates.append(scored)
    for item in recent_scenes:
        scored = _score_candidate(
            query,
            _CandidateRow(item["scene_id"], "recent_scene", "branch" if branch_id else "project", item["title"], item.get("summary") or "", None, 0.75),
        )
        candidates.append(scored)
    for item in knowledge_hits:
        scored = _score_candidate(
            query,
            _CandidateRow(str(item.chunk_id), item.document_type or "knowledge", "project", item.document_title, item.content, None, 0.65),
        )
        candidates.append(scored)

    ranked = sorted(candidates, key=lambda item: item.score, reverse=True)
    filtered_candidates: list[ContextCompileCandidate] = []
    for item in ranked:
        source_prefix = f"{item.source_type}:{item.source_id}"
        seen_sources[source_prefix] = seen_sources.get(source_prefix, 0) + 1
        if seen_sources[source_prefix] > 1:
            deduped_sources.append(source_prefix)
            continue
        filtered_candidates.append(item)
    selected_candidates, diversity_counts, diversity_clipped = _select_diverse_candidates(filtered_candidates, limit=20)
    snapshot.candidates = selected_candidates
    snapshot.deduped_sources = deduped_sources
    snapshot.source_diversity_applied = diversity_counts
    snapshot.clipped_sources.extend(diversity_clipped)

    recent_scene_tokens = sum(_token_count(item.get("summary") or "") for item in recent_scenes)
    recent_budget = int(snapshot.budget["recent_scenes_tokens"])
    if recent_scene_tokens > 2000 or recent_scene_tokens > recent_budget:
        snapshot.summary_triggered = True
        snapshot.summary_reason = "recent_scenes_over_2000_tokens" if recent_scene_tokens > 2000 else "recent_scenes_over_budget"
        recent_scenes = _summarize_recent_scenes(recent_scenes)
        snapshot.summary_output = list(recent_scenes)
        summary_ids = {item["scene_id"] for item in recent_scenes}
        snapshot.clipped_sources.extend(sorted(summary_ids))
        for candidate in snapshot.candidates:
            if candidate.source_id in summary_ids:
                candidate.summary_applied = True

    return {
        "scene_summary": {
            "title": scene.title,
            "goal": scene.goal,
            "conflict": scene.conflict,
            "outcome": scene.outcome,
            "time_label": scene.time_label,
            "status": scene.status,
            "draft_text": scene.draft_text,
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
        "context_compile_snapshot": snapshot,
    }
