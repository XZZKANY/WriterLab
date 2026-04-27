from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.scene import Scene
from app.models.scene_version import SceneVersion
from app.models.story_branch import StoryBranch
from app.schemas.branch import StoryBranchCreate
from app.services.scene_version_service import create_scene_version


def _resolve_project_id(db: Session, *, project_id=None, source_scene_id=None):
    if project_id is not None:
        return project_id
    if source_scene_id is None:
        return None
    scene = db.query(Scene).filter(Scene.id == source_scene_id).first()
    if scene is None:
        return None
    chapter = db.query(Chapter).filter(Chapter.id == scene.chapter_id).first()
    if chapter is None:
        return None
    book = db.query(Book).filter(Book.id == chapter.book_id).first()
    return book.project_id if book else None


def create_story_branch(db: Session, payload: StoryBranchCreate) -> StoryBranch:
    project_id = _resolve_project_id(db, project_id=payload.project_id, source_scene_id=payload.source_scene_id)
    if project_id is None:
        raise ValueError("Project not found for branch")

    scene = None
    if payload.source_scene_id is not None:
        scene = db.query(Scene).filter(Scene.id == payload.source_scene_id).first()
        if scene is None:
            raise ValueError("Source scene not found")

    latest_version_id = payload.latest_version_id or payload.source_version_id
    if latest_version_id is None and payload.source_scene_id is not None:
        latest = (
            db.query(SceneVersion)
            .filter(SceneVersion.scene_id == payload.source_scene_id)
            .order_by(SceneVersion.created_at.desc())
            .first()
        )
        latest_version_id = latest.id if latest else None
        if latest is None and scene and (scene.draft_text or "").strip():
            latest = create_scene_version(
                db,
                scene_id=scene.id,
                content=scene.draft_text,
                source="manual",
                label=f"branch source snapshot: {payload.name}",
            )
            latest_version_id = latest.id if latest else None

    branch = StoryBranch(
        project_id=project_id,
        name=payload.name,
        description=payload.description,
        parent_branch_id=payload.parent_branch_id,
        source_scene_id=payload.source_scene_id,
        source_version_id=payload.source_version_id or latest_version_id,
        latest_version_id=latest_version_id,
        metadata_json=payload.metadata_json,
    )
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return branch


def list_story_branches(db: Session, *, project_id=None, source_scene_id=None) -> list[StoryBranch]:
    query = db.query(StoryBranch)
    if project_id is not None:
        query = query.filter(StoryBranch.project_id == project_id)
    if source_scene_id is not None:
        query = query.filter(StoryBranch.source_scene_id == source_scene_id)
    return query.order_by(StoryBranch.updated_at.desc(), StoryBranch.created_at.desc()).all()


def build_line_diff(source_text: str, branch_text: str) -> list[dict]:
    source_lines = (source_text or "").splitlines()
    branch_lines = (branch_text or "").splitlines()
    rows: list[dict] = []
    max_len = max(len(source_lines), len(branch_lines))
    for index in range(max_len):
        left = source_lines[index] if index < len(source_lines) else None
        right = branch_lines[index] if index < len(branch_lines) else None
        if left == right:
            rows.append({"type": "context", "text": left or ""})
            continue
        if left is not None:
            rows.append({"type": "remove", "text": left})
        if right is not None:
            rows.append({"type": "add", "text": right})
    return rows


def get_branch_source_chapter_id(db: Session, branch: StoryBranch):
    if branch.source_scene_id is None:
        return None
    scene = db.query(Scene).filter(Scene.id == branch.source_scene_id).first()
    return scene.chapter_id if scene else None


def get_branch_diff(db: Session, branch: StoryBranch) -> tuple[str, str, list[dict]]:
    source_version = None
    latest_version = None
    if branch.source_version_id:
        source_version = db.query(SceneVersion).filter(SceneVersion.id == branch.source_version_id).first()
    if branch.latest_version_id:
        latest_version = db.query(SceneVersion).filter(SceneVersion.id == branch.latest_version_id).first()

    source_text = source_version.content if source_version else ""
    branch_text = latest_version.content if latest_version else ""
    return source_text, branch_text, build_line_diff(source_text, branch_text)


def adopt_story_branch(db: Session, branch: StoryBranch) -> tuple[Scene, SceneVersion | None]:
    if branch.source_scene_id is None:
        raise ValueError("Branch has no source scene")

    scene = db.query(Scene).filter(Scene.id == branch.source_scene_id).first()
    if scene is None:
        raise ValueError("Scene not found")

    latest_version = None
    if branch.latest_version_id:
        latest_version = db.query(SceneVersion).filter(SceneVersion.id == branch.latest_version_id).first()
    if latest_version is None:
        raise ValueError("Branch has no latest version")

    scene.draft_text = latest_version.content
    db.add(scene)
    db.commit()
    db.refresh(scene)

    adopted_version = create_scene_version(
        db,
        scene_id=scene.id,
        content=latest_version.content,
        source="restore",
        label=f"adopt branch {branch.name}",
    )
    return scene, adopted_version
