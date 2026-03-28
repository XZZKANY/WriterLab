import uuid

from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.character import Character
from app.models.location import Location
from app.models.scene import Scene
from app.schemas.scene_write import WriteSceneResult
from app.services.ai_errors import AIErrorType, AIServiceError
from app.services.ai_gateway_service import call_ai_gateway
from app.services.ai_output_guardrails import sanitize_write_output, validate_write_output
from app.services.ai_prompt_templates import (
    LENGTH_HINTS,
    WRITE_SCENE_PROMPT_VERSION,
    build_context_block,
    build_write_prompt,
)
from app.services.ai_run_service import save_ai_run
from app.services.knowledge_service import format_knowledge_hits, retrieve_knowledge
from app.services.scene_analysis_store_service import get_analysis_items, get_selected_guidance_for_scene
from app.services.scene_status_service import SCENE_STATUS_GENERATED, mark_scene_status
from app.services.scene_version_service import create_scene_version

MIN_LENGTH_HINT = {
    "short": 280,
    "medium": 520,
    "long": 850,
}


def _clean_list(value: list | None) -> list[str]:
    if not value:
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _cleanup_draft_text(raw_text: str) -> str:
    text = raw_text.strip()
    if "<think>" in text and "</think>" in text:
        _, _, text = text.partition("</think>")
        text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("text"):
            text = text[4:].strip()
    for prefix in ["正文：", "场景正文：", "生成正文：", "以下是正文：", "以下是生成的正文："]:
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
    for marker in ["\n\n说明：", "\n\n注：", "\n\n备注：", "\n\n分析：", "\n\n想法：", "\n\nNotes:"]:
        if marker in text:
            text = text.split(marker, 1)[0].strip()
    return text


def _needs_template_fallback(text: str) -> bool:
    if not text.strip():
        return True
    return any(marker in text for marker in ["我不能", "我无法", "抱歉", "作为AI", "作为一个AI", "不能满足"])


def _build_template_draft(scene: Scene, *, length: str, pov_name: str, location_name: str) -> str:
    title = scene.title or "这个场景"
    goal = scene.goal or "把眼前的局面推进下去"
    conflict = scene.conflict or "外部压力和内心迟疑同时逼近"
    outcome = scene.outcome or "局势发生变化，但仍留下后续张力"
    include_items = _clean_list(scene.must_include)
    include_line = f"她没有忘记眼前必须出现的要素：{'、'.join(include_items)}。" if include_items else ""

    opening = (
        (scene.draft_text or "").strip()
        or f"{title}开始时，{pov_name}已经站在{location_name}里。周围的一切都压着她的神经，她知道自己不能继续拖下去。"
    )
    middle = f"她此刻最明确的念头，是{goal}。可真正拦在面前的，却是{conflict}。"
    turning = f"{include_line}局面在细微处开始偏转，原本还能维持的平衡被悄悄打破。"
    closing = f"等这一轮交锋暂时落下时，结果已经朝着{outcome}滑去，留下明显的后续空间。"

    if length == "short":
        return f"{opening}\n\n{middle}{turning}{closing}"
    if length == "medium":
        return f"{opening}\n\n{middle}{turning}\n\n{pov_name}先收住情绪，把注意力落回最实际的细节上。{closing}"
    return f"{opening}\n\n{middle}{turning}\n\n{pov_name}没有立刻把情绪摆出来，而是慢慢观察光线、距离和人的反应。时间被拖长后，每个动作都开始拥有重量。{closing}"


def _enforce_scene_constraints(scene: Scene, draft_text: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    text = draft_text
    avoid_items = _clean_list(scene.must_avoid)

    missing_items = [item for item in _clean_list(scene.must_include) if item not in text]
    if missing_items:
        supplement = "、".join(missing_items)
        text = f"{text}\n\n她重新扫过现场，把{supplement}也纳入眼前正在发生的一切。".strip()
        notes.append("已自动补入缺失的 must_include 要素。")

    hit_avoid_items = [item for item in avoid_items if item in text]
    if hit_avoid_items:
        for item in hit_avoid_items:
            text = text.replace(item, "那个暂时没有被说破的事实")
        notes.append("已弱化正文中直接命中的 must_avoid 内容。")

    return text, notes


def _resolve_project_id(scene: Scene, db: Session) -> uuid.UUID | None:
    chapter = db.query(Chapter).filter(Chapter.id == scene.chapter_id).first()
    if not chapter:
        return None
    book = db.query(Book).filter(Book.id == chapter.book_id).first()
    return book.project_id if book else None


def write_scene(
    scene: Scene,
    db: Session,
    length: str,
    guidance: list[str] | None = None,
    analysis_id=None,
) -> tuple[WriteSceneResult, uuid.UUID]:
    run_id = uuid.uuid4()
    request_guidance = [item.strip() for item in (guidance or []) if item and item.strip()]
    if length not in LENGTH_HINTS:
        raise AIServiceError(AIErrorType.VALIDATION, "length 只能是 short、medium 或 long", run_id=run_id)

    pov = db.query(Character).filter(Character.id == scene.pov_character_id).first() if scene.pov_character_id else None
    location = db.query(Location).filter(Location.id == scene.location_id).first() if scene.location_id else None
    project_id = _resolve_project_id(scene, db)
    selected_guidance, selected_analysis = get_selected_guidance_for_scene(db, scene.id, analysis_id=analysis_id)
    final_guidance = selected_guidance or request_guidance
    unselected_guidance_count = 0
    if selected_analysis is not None:
        analysis_items = get_analysis_items(db, selected_analysis.id)
        unselected_guidance_count = max(len(analysis_items) - len(selected_guidance), 0)

    context_block = build_context_block(pov, location)
    retrieval_query = "\n".join(
        [
            scene.title or "",
            scene.goal or "",
            scene.conflict or "",
            scene.outcome or "",
            " ".join(_clean_list(scene.must_include)),
            " ".join(final_guidance),
        ]
    ).strip()
    knowledge_hits = retrieve_knowledge(db, project_id=project_id, query=retrieval_query, top_k=3) if project_id else []
    knowledge_block = format_knowledge_hits(knowledge_hits)
    prompt = build_write_prompt(
        scene,
        context_block=context_block,
        knowledge_block=knowledge_block,
        length=length,
        guidance=final_guidance,
    )
    input_payload = {
        "scene_id": str(scene.id),
        "scene_title": scene.title,
        "project_id": str(project_id) if project_id else None,
        "task_type": "write",
        "prompt_version": WRITE_SCENE_PROMPT_VERSION,
        "analysis_id": str(selected_analysis.id) if selected_analysis else (str(analysis_id) if analysis_id else None),
        "guidance": final_guidance,
        "request_guidance": request_guidance,
        "context_block": context_block,
        "knowledge_hits": [hit.model_dump() for hit in knowledge_hits],
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
            gateway_result = call_ai_gateway(db, task_type="write", prompt=prompt, params={"temperature": 0.5, "top_p": 0.9})
        except RuntimeError as exc:
            raise AIServiceError(AIErrorType.NETWORK, str(exc), run_id=run_id) from exc

        raw_response = gateway_result.text
        provider = gateway_result.provider
        model = gateway_result.model
        fallback_used = gateway_result.fallback_used
        latency_ms = gateway_result.latency_ms

        notes: list[str] = []
        draft_text = _cleanup_draft_text(raw_response)
        draft_text, cleanup_notes = sanitize_write_output(draft_text)
        notes.extend(cleanup_notes)
        if _needs_template_fallback(draft_text):
            draft_text = _build_template_draft(
                scene,
                length=length,
                pov_name=pov.name if pov and pov.name else "主视角人物",
                location_name=location.name if location and location.name else "当前地点",
            )
            notes.append("模型输出不可用，已返回稳定兜底草稿。")

        if not draft_text:
            raise AIServiceError(AIErrorType.MODEL_OUTPUT, "模型未返回可用正文", run_id=run_id)

        write_guard = validate_write_output(draft_text)
        if not write_guard.ok:
            draft_text = _build_template_draft(
                scene,
                length=length,
                pov_name=pov.name if pov and pov.name else "主视角人物",
                location_name=location.name if location and location.name else "当前地点",
            )
            notes.append(f"模型输出不符合正文要求，已改用稳定兜底草稿：{write_guard.reason}")

        draft_text, constraint_notes = _enforce_scene_constraints(scene, draft_text)
        notes.extend(constraint_notes)
        if len(draft_text) < MIN_LENGTH_HINT[length]:
            notes.append("本次生成篇幅偏短，可以再次生成。")

        version = create_scene_version(
            db,
            scene_id=scene.id,
            content=draft_text,
            source="write",
            label="AI生成初稿",
        )
        mark_scene_status(scene, SCENE_STATUS_GENERATED)
        db.add(scene)
        db.commit()
        result = WriteSceneResult(
            draft_text=draft_text,
            notes=notes,
            analysis_id_used=selected_analysis.id if selected_analysis is not None else analysis_id,
            selected_guidance=final_guidance,
            unselected_guidance_count=unselected_guidance_count,
            knowledge_hit_count=len(knowledge_hits),
            changed=True,
            version_created=version is not None,
            version_source="write" if version is not None else None,
            version_id=version.id if version is not None else None,
            message="已生成正文。",
            reason=None,
        )
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
            project_id=project_id,
            run_type="write_scene",
            task_type="write",
            provider=provider,
            model=model or "unknown",
            prompt_version=WRITE_SCENE_PROMPT_VERSION,
            fallback_used=fallback_used,
            input_payload=input_payload,
            raw_response=raw_response,
            parsed_response=parsed_response,
            status=status,
            error_message=error_message,
            latency_ms=latency_ms,
        )
