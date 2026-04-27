from app.models.scene import Scene


SCENE_STATUS_DRAFT = "draft"
SCENE_STATUS_GENERATED = "generated"
SCENE_STATUS_ANALYZED = "analyzed"
SCENE_STATUS_REVISION_READY = "revision_ready"


def mark_scene_status(scene: Scene, status: str) -> None:
    scene.status = status
