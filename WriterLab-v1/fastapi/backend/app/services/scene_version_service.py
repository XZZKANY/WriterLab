from sqlalchemy.orm import Session

from app.models.scene import Scene
from app.models.scene_version import SceneVersion


def create_scene_version(
    db: Session,
    *,
    scene_id,
    content: str,
    source: str,
    label: str | None = None,
    scene_version: int | None = None,
    workflow_step_id=None,
) -> SceneVersion | None:
    if not content.strip():
        return None

    latest_version = (
        db.query(SceneVersion)
        .filter(SceneVersion.scene_id == scene_id)
        .order_by(SceneVersion.created_at.desc())
        .first()
    )
    if latest_version and latest_version.content == content and latest_version.source == source:
        return None

    version = SceneVersion(
        scene_id=scene_id,
        content=content,
        source=source,
        label=label,
        scene_version=scene_version or 1,
        workflow_step_id=workflow_step_id,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def list_scene_versions(db: Session, scene_id, limit: int = 10) -> list[SceneVersion]:
    return (
        db.query(SceneVersion)
        .filter(SceneVersion.scene_id == scene_id)
        .order_by(SceneVersion.created_at.desc())
        .limit(limit)
        .all()
    )


def restore_scene_version(db: Session, *, scene: Scene, version: SceneVersion) -> SceneVersion:
    scene.draft_text = version.content
    scene.scene_version = (scene.scene_version or 0) + 1
    db.add(scene)
    db.commit()
    db.refresh(scene)

    restored_version = SceneVersion(
        scene_id=scene.id,
        content=version.content,
        source="restore",
        label=f"restore version {version.id}",
        scene_version=scene.scene_version,
    )
    db.add(restored_version)
    db.commit()
    db.refresh(restored_version)
    return restored_version
