import uuid

from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.character import Character
from app.models.location import Location
from app.models.scene import Scene
from app.schemas.scene_revise import ReviseMode, ReviseSceneResult
from app.services.ai_errors import AIErrorType, AIServiceError
from app.services.ai_gateway_service import call_ai_gateway
from app.services.ai_output_guardrails import sanitize_revise_output, validate_style_output
from app.services.ai_prompt_templates import REVISE_SCENE_PROMPT_VERSION, build_context_block, build_revise_prompt
from app.services.ai_run_service import save_ai_run
from app.services.scene_status_service import SCENE_STATUS_REVISION_READY, mark_scene_status


def _cleanup_revised_text(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if "<think>" in text and "</think>" in text:
        _, _, text = text.partition("</think>")
        text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()

    for prefix in (
        "润色结果：",
        "改写结果：",
        "正文：",
        "输出：",
        "以下是润色后的正文：",
        "以下是修改后的正文：",
    ):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
    return text


def _resolve_project_id(scene: Scene, db: Session) -> uuid.UUID | None:
    chapter = db.query(Chapter).filter(Chapter.id == scene.chapter_id).first()
    if not chapter:
        return None
    book = db.query(Book).filter(Book.id == chapter.book_id).first()
    return book.project_id if book else None


def revise_scene(scene: Scene, db: Session, mode: ReviseMode) -> tuple[ReviseSceneResult, uuid.UUID]:
    run_id = uuid.uuid4()
    source_text = (scene.draft_text or "").strip()
    if not source_text:
        raise AIServiceError(AIErrorType.VALIDATION, "场景草稿为空，无法执行润色。", run_id=run_id)

    pov = db.query(Character).filter(Character.id == scene.pov_character_id).first() if scene.pov_character_id else None
    location = db.query(Location).filter(Location.id == scene.location_id).first() if scene.location_id else None

    context_block = build_context_block(pov, location)
    prompt = build_revise_prompt(scene, mode=mode, context_block=context_block)
    input_payload = {
        "scene_id": str(scene.id),
        "scene_title": scene.title,
        "task_type": "revise",
        "mode": mode,
        "prompt_version": REVISE_SCENE_PROMPT_VERSION,
        "context_block": context_block,
        "prompt": prompt,
    }

    raw_response = None
    parsed_response = None
    status = "error"
    error_message = None
    provider = None
    model = None
    fallback_used = None
    latency_ms = 0

    try:
        try:
            gateway_result = call_ai_gateway(
                db,
                task_type="revise",
                prompt=prompt,
                params={"temperature": 0.35, "top_p": 0.9},
            )
        except RuntimeError as exc:
            raise AIServiceError(AIErrorType.NETWORK, str(exc), run_id=run_id) from exc

        raw_response = gateway_result.text
        provider = gateway_result.provider
        model = gateway_result.model
        fallback_used = gateway_result.fallback_used
        latency_ms = gateway_result.latency_ms

        revised_text = _cleanup_revised_text(raw_response)
        revised_text, cleanup_notes = sanitize_revise_output(revised_text)
        if not revised_text:
            raise AIServiceError(AIErrorType.MODEL_OUTPUT, "润色输出为空，或已被清洗为无效说明文本。", run_id=run_id)

        style_guard = validate_style_output(source_text, revised_text)
        if not style_guard.ok:
            raise AIServiceError(AIErrorType.MODEL_OUTPUT, style_guard.reason or "润色输出未通过质量守门。", run_id=run_id)

        changed = revised_text != source_text
        notes = list(cleanup_notes)
        if not changed:
            notes.append("润色结果与原稿基本一致，本次没有产生需要采纳的改动。")

        result = ReviseSceneResult(
            revised_text=revised_text,
            notes=notes,
            changed=changed,
            version_created=False,
            version_source=None,
            version_id=None,
            message="已生成可预览的润色稿。" if changed else "润色完成，但没有形成明显可采纳改动。",
            reason=None if changed else "no_changes",
        )
        if changed:
            mark_scene_status(scene, SCENE_STATUS_REVISION_READY)
            db.add(scene)
            db.commit()
        parsed_response = result.model_dump()
        status = "success"
        return result, run_id
    except AIServiceError as exc:
        error_message = exc.message
        raise
    except Exception as exc:
        error_message = str(exc)
        raise AIServiceError(AIErrorType.UNKNOWN, str(exc), run_id=run_id) from exc
    finally:
        save_ai_run(
            db,
            run_id=run_id,
            scene_id=scene.id,
            project_id=_resolve_project_id(scene, db),
            run_type="revise_scene",
            task_type="revise",
            provider=provider,
            model=model or "unknown",
            prompt_version=REVISE_SCENE_PROMPT_VERSION,
            fallback_used=fallback_used,
            input_payload=input_payload,
            raw_response=raw_response,
            parsed_response=parsed_response,
            status=status,
            error_message=error_message,
            latency_ms=latency_ms,
        )
