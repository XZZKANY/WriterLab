from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.scene_repository import (
    get_scene as get_scene_record,
    get_scene_version as get_scene_version_record,
    list_scene_versions as list_scene_version_records,
    list_scenes_by_chapter,
)
from app.schemas.context_bundle import ContextBundleResponse
from app.schemas.scene import SceneCreate, SceneResponse, SceneUpdate
from app.schemas.scene_context import SceneContextResponse
from app.schemas.scene_version import RestoreVersionResponse, SceneVersionResponse
from app.services.context_service import build_scene_context
from app.services.scene_status_service import SCENE_STATUS_DRAFT, mark_scene_status
from app.services.scene_version_service import create_scene_version, list_scene_versions, restore_scene_version

router = APIRouter(prefix="/api/scenes", tags=["scenes"])


@router.post("", response_model=SceneResponse)
def create_scene(payload: SceneCreate, db: Session = Depends(get_db)):
    scene = Scene(
        chapter_id=payload.chapter_id,
        scene_no=payload.scene_no,
        title=payload.title,
        pov_character_id=payload.pov_character_id,
        location_id=payload.location_id,
        time_label=payload.time_label,
        goal=payload.goal,
        conflict=payload.conflict,
        outcome=payload.outcome,
        must_include=payload.must_include,
        must_avoid=payload.must_avoid,
        status=payload.status,
        draft_text=payload.draft_text,
    )
    db.add(scene)
    db.commit()
    db.refresh(scene)
    if scene.draft_text:
        create_scene_version(
            db,
            scene_id=scene.id,
            content=scene.draft_text,
            source="manual",
            label="initial draft",
            scene_version=scene.scene_version,
        )
    return scene


@router.get("", response_model=list[SceneResponse])
def list_scenes(chapter_id: UUID, db: Session = Depends(get_db)):
    return list_scenes_by_chapter(db, chapter_id)


@router.get("/{scene_id}/context", response_model=SceneContextResponse)
def get_scene_context(scene_id: UUID, branch_id: UUID | None = None, db: Session = Depends(get_db)):
    scene = get_scene_record(db, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    bundle = build_scene_context(scene, db, branch_id=branch_id)

    return {
        "scene": bundle["scene_summary"],
        "scene_status": scene.status,
        "scene_version": scene.scene_version,
        "pov_character": bundle["pov_character"],
        "location": bundle["location"],
        "timeline_events": bundle["timeline_events"],
        "style_memories": bundle["style_memories"],
        "knowledge_hits": bundle["knowledge_hits"],
        "recent_scenes": bundle["recent_scenes"],
        "context_compile_snapshot": bundle.get("context_compile_snapshot"),
    }


@router.patch("/{scene_id}", response_model=SceneResponse)
def update_scene(scene_id: UUID, payload: SceneUpdate, db: Session = Depends(get_db)):
    scene = get_scene_record(db, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    previous_draft_text = scene.draft_text or ""
    update_data = payload.model_dump(exclude_unset=True)
    expected_scene_version = update_data.pop("expected_scene_version", None)
    version_source = update_data.pop("version_source", None) or "manual"
    version_label = update_data.pop("version_label", None) or "manual update"
    if expected_scene_version is not None and expected_scene_version != scene.scene_version:
        raise HTTPException(status_code=409, detail="Scene version mismatch")
    should_create_version = (
        "draft_text" in update_data
        and update_data["draft_text"] is not None
        and update_data["draft_text"] != previous_draft_text
    )

    for key, value in update_data.items():
        setattr(scene, key, value)

    if should_create_version and "status" not in update_data:
        mark_scene_status(scene, SCENE_STATUS_DRAFT)
    if should_create_version:
        scene.scene_version = (scene.scene_version or 0) + 1

    db.commit()
    db.refresh(scene)

    if should_create_version:
        create_scene_version(
            db,
            scene_id=scene.id,
            content=scene.draft_text or "",
            source=version_source,
            label=version_label,
            scene_version=scene.scene_version,
        )

    return scene


@router.get("/{scene_id}/bundle", response_model=ContextBundleResponse)
def get_scene_bundle(scene_id: UUID, branch_id: UUID | None = None, db: Session = Depends(get_db)):
    scene = get_scene_record(db, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return build_scene_context(scene, db, branch_id=branch_id)


@router.get("/{scene_id}/versions", response_model=list[SceneVersionResponse])
def get_scene_versions(scene_id: UUID, db: Session = Depends(get_db)):
    scene = get_scene_record(db, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return list_scene_version_records(db, scene_id)


@router.post("/{scene_id}/versions/{version_id}/restore", response_model=RestoreVersionResponse)
def restore_version(scene_id: UUID, version_id: UUID, db: Session = Depends(get_db)):
    scene = get_scene_record(db, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    version = get_scene_version_record(db, scene_id, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Scene version not found")

    restored = restore_scene_version(db, scene=scene, version=version)
    return RestoreVersionResponse(
        success=True,
        version_id=restored.id,
        restored_to_scene_id=scene.id,
        current_text=scene.draft_text or "",
    )
