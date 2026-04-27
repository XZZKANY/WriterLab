from sqlalchemy.orm import Session

from app.models.scene import Scene
from app.models.scene_analysis import SceneAnalysis
from app.models.scene_analysis_item import SceneAnalysisItem
from app.models.scene_version import SceneVersion
from app.schemas.scene_analysis import SceneAnalysisResult
from app.schemas.scene_analysis_store import SceneAnalysisStoredResponse


def _latest_scene_version(db: Session, scene_id):
    return (
        db.query(SceneVersion)
        .filter(SceneVersion.scene_id == scene_id)
        .order_by(SceneVersion.created_at.desc())
        .first()
    )


def create_scene_analysis_record(
    db: Session,
    *,
    scene: Scene,
    result: SceneAnalysisResult,
    ai_run_id,
    project_id=None,
    status: str = "success",
) -> SceneAnalysis:
    version = _latest_scene_version(db, scene.id)
    analysis = SceneAnalysis(
        project_id=project_id,
        scene_id=scene.id,
        version_id=version.id if version else None,
        analysis_type="scene",
        status=status,
        summary=result.summary,
        raw_result_json=result.model_dump(),
        ai_run_id=ai_run_id,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    sort_order = 0
    for problem in result.problems:
        sort_order += 1
        db.add(
            SceneAnalysisItem(
                analysis_id=analysis.id,
                item_type="problem",
                title=problem.type,
                content=problem.message,
                severity=problem.severity,
                is_selected=False,
                sort_order=sort_order,
                metadata_json={"problem_type": problem.type},
            )
        )
    for suggestion in result.suggestions:
        sort_order += 1
        db.add(
            SceneAnalysisItem(
                analysis_id=analysis.id,
                item_type="suggestion",
                title="建议",
                content=suggestion,
                severity=None,
                is_selected=False,
                sort_order=sort_order,
                metadata_json=None,
            )
        )
    db.commit()
    db.refresh(analysis)
    return analysis


def get_scene_analysis(db: Session, analysis_id):
    return db.query(SceneAnalysis).filter(SceneAnalysis.id == analysis_id).first()


def list_scene_analyses(db: Session, scene_id, limit: int = 10) -> list[SceneAnalysis]:
    return (
        db.query(SceneAnalysis)
        .filter(SceneAnalysis.scene_id == scene_id)
        .order_by(SceneAnalysis.created_at.desc())
        .limit(limit)
        .all()
    )


def get_analysis_items(db: Session, analysis_id) -> list[SceneAnalysisItem]:
    return (
        db.query(SceneAnalysisItem)
        .filter(SceneAnalysisItem.analysis_id == analysis_id)
        .order_by(SceneAnalysisItem.sort_order.asc(), SceneAnalysisItem.id.asc())
        .all()
    )


def set_selected_analysis_items(db: Session, analysis_id, selected_item_ids: list) -> list[SceneAnalysisItem]:
    items = get_analysis_items(db, analysis_id)
    selected = set(selected_item_ids)
    for item in items:
        item.is_selected = item.id in selected
        db.add(item)
    db.commit()
    return get_analysis_items(db, analysis_id)


def get_selected_guidance_for_scene(db: Session, scene_id, analysis_id=None) -> tuple[list[str], SceneAnalysis | None]:
    analysis = None
    if analysis_id:
        analysis = get_scene_analysis(db, analysis_id)
    else:
        analysis = (
            db.query(SceneAnalysis)
            .filter(SceneAnalysis.scene_id == scene_id)
            .order_by(SceneAnalysis.created_at.desc())
            .first()
        )
    if not analysis:
        return [], None

    items = (
        db.query(SceneAnalysisItem)
        .filter(SceneAnalysisItem.analysis_id == analysis.id, SceneAnalysisItem.is_selected.is_(True))
        .order_by(SceneAnalysisItem.sort_order.asc())
        .all()
    )
    return [item.content for item in items], analysis


def to_scene_analysis_response(db: Session, analysis: SceneAnalysis) -> SceneAnalysisStoredResponse:
    return SceneAnalysisStoredResponse(
        id=analysis.id,
        project_id=analysis.project_id,
        scene_id=analysis.scene_id,
        version_id=analysis.version_id,
        analysis_type=analysis.analysis_type,
        status=analysis.status,
        summary=analysis.summary,
        ai_run_id=analysis.ai_run_id,
        created_at=analysis.created_at,
        items=get_analysis_items(db, analysis.id),
    )
