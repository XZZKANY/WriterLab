from sqlalchemy.orm import Session

from app.models.scene import Scene
from app.models.scene_version import SceneVersion


def get_scene(db: Session, scene_id):
    return db.query(Scene).filter(Scene.id == scene_id).first()


def get_scene_version(db: Session, scene_id, version_id):
    return (
        db.query(SceneVersion)
        .filter(SceneVersion.id == version_id, SceneVersion.scene_id == scene_id)
        .first()
    )


def list_scenes_by_chapter(db: Session, chapter_id):
    return db.query(Scene).filter(Scene.chapter_id == chapter_id).order_by(Scene.scene_no.asc()).all()


def list_scene_versions(db: Session, scene_id):
    return (
        db.query(SceneVersion)
        .filter(SceneVersion.scene_id == scene_id)
        .order_by(SceneVersion.created_at.desc())
        .all()
    )
