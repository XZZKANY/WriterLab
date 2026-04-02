import json
import re
import uuid

from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.scene import Scene
from app.schemas.scene_analysis import SceneAnalysisResult, SceneProblem
from app.services.ai_errors import AIErrorType, AIServiceError
from app.services.ai_output_guardrails import validate_analysis_output
from app.services.ai_gateway_service import call_ai_gateway
from app.services.ai_prompt_templates import ANALYZE_SCENE_PROMPT_VERSION, build_analysis_prompt
from app.services.ai_run_service import save_ai_run


def _clean_line(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" \n\r\t-:：*#")


def _extract_bullets(raw_text: str, headings: tuple[str, ...], limit: int = 3) -> list[str]:
    lines = [line.strip() for line in raw_text.splitlines()]
    collected: list[str] = []
    in_section = False
    heading_set = tuple(heading.lower() for heading in headings)

    for line in lines:
        normalized = _clean_line(line)
        lowered = normalized.lower()
        if any(heading in lowered for heading in heading_set):
            in_section = True
            continue
        if in_section and normalized and not line.startswith(("-", "*", "1", "2", "3", "4", "5", "6", "7", "8", "9")):
            if "：" in normalized or ":" in normalized:
                break
        if in_section and line.lstrip().startswith(("-", "*")):
            content = _clean_line(line)
            if content:
                collected.append(content)
        if len(collected) >= limit:
            break
    return collected


def _derive_summary(raw_text: str) -> str:
    cleaned = _clean_line(raw_text)
    if not cleaned:
        return "已完成场景分析，但模型没有返回可用摘要。"
    return cleaned[:200]


def _fallback_result(raw_text: str) -> SceneAnalysisResult:
    suggestions = _extract_bullets(raw_text, ("suggestions", "建议", "修改建议"))
    problems_text = _extract_bullets(raw_text, ("problems", "问题", "警告", "风险"))
    problems = [
        SceneProblem(type="logic", severity="medium", message=text)
        for text in problems_text[:3]
    ]

    if not suggestions:
        suggestions = ["重新梳理这一场的目标、冲突和结果，并据此补出一条更明确的场景推进线。"]

    if not problems:
        problems = [
            SceneProblem(
                type="logic",
                severity="medium",
                message="模型没有稳定返回结构化问题，请先检查这场戏的目标、冲突和信息是否表达清楚。",
            )
        ]

    return SceneAnalysisResult(
        summary=_derive_summary(raw_text),
        scene_goal_detected=None,
        emotional_flow=[],
        problems=problems,
        suggestions=suggestions,
    )


def _normalize_problem(item: object) -> SceneProblem | None:
    if not isinstance(item, dict):
        return None

    type_raw = str(item.get("type", "")).strip().lower()
    severity_raw = str(item.get("severity", "")).strip().lower()
    message = str(item.get("message", "")).strip()
    if not message:
        return None

    type_map = {
        "pacing": "pacing",
        "consistency": "consistency",
        "character": "character",
        "logic": "logic",
    }
    severity_map = {
        "low": "low",
        "medium": "medium",
        "high": "high",
        "moderate": "medium",
    }

    return SceneProblem(
        type=type_map.get(type_raw, "logic"),
        severity=severity_map.get(severity_raw, "medium"),
        message=message,
    )


def _coerce_result(data: object) -> SceneAnalysisResult:
    if not isinstance(data, dict):
        raise ValueError("model output is not a json object")

    emotional_flow = data.get("emotional_flow", [])
    suggestions = data.get("suggestions", [])
    problems = data.get("problems", [])

    if not isinstance(emotional_flow, list):
        emotional_flow = []
    if not isinstance(suggestions, list):
        suggestions = []
    if not isinstance(problems, list):
        problems = []

    normalized_problems = [problem for item in problems if (problem := _normalize_problem(item)) is not None]

    return SceneAnalysisResult(
        summary=str(data.get("summary", "")).strip(),
        scene_goal_detected=(str(data.get("scene_goal_detected")).strip() if data.get("scene_goal_detected") not in (None, "", False) else None),
        emotional_flow=[str(item).strip() for item in emotional_flow if str(item).strip()],
        problems=normalized_problems,
        suggestions=[str(item).strip() for item in suggestions if str(item).strip()],
    )


def _ensure_non_empty_items(result: SceneAnalysisResult) -> SceneAnalysisResult:
    if result.problems or result.suggestions:
        return result

    summary = result.summary.strip() or "模型没有返回可用的结构化分析。"
    return SceneAnalysisResult(
        summary=summary,
        scene_goal_detected=result.scene_goal_detected,
        emotional_flow=result.emotional_flow,
        problems=[
            SceneProblem(
                type="logic",
                severity="medium",
                message="这次分析没有产出结构化问题，建议先检查场景目标、冲突和结果是否足够清楚。",
            )
        ],
        suggestions=[
            "把这一场的目标、阻碍和结果各写成一句话，再重新分析一次。",
        ],
    )


def _parse_model_output(raw_text: str) -> tuple[SceneAnalysisResult, str | None]:
    parse_errors: list[str] = []
    try:
        return _ensure_non_empty_items(_coerce_result(json.loads(raw_text))), None
    except Exception as exc:
        parse_errors.append(f"layer1:{exc}")

    block_match = re.search(r"```json(.*?)```", raw_text, re.S)
    if block_match:
        try:
            return _ensure_non_empty_items(_coerce_result(json.loads(block_match.group(1).strip()))), None
        except Exception as exc:
            parse_errors.append(f"layer2:{exc}")
    else:
        parse_errors.append("layer2:no_json_block")

    raise ValueError("; ".join(parse_errors))


def _resolve_project_id(scene: Scene, db: Session) -> uuid.UUID | None:
    chapter = db.query(Chapter).filter(Chapter.id == scene.chapter_id).first()
    if not chapter:
        return None
    book = db.query(Book).filter(Book.id == chapter.book_id).first()
    return book.project_id if book else None


def analyze_scene(
    scene: Scene,
    db: Session,
    *,
    provider_mode: str = "live",
    fixture_scenario: str = "happy_path",
    return_gateway_result: bool = False,
) -> tuple[SceneAnalysisResult, uuid.UUID] | tuple[SceneAnalysisResult, uuid.UUID, object]:
    run_id = uuid.uuid4()
    if not (scene.draft_text or "").strip():
        raise AIServiceError(AIErrorType.VALIDATION, "场景正文为空，无法分析", run_id=run_id)

    prompt = build_analysis_prompt(scene)
    input_payload = {
        "scene_id": str(scene.id),
        "scene_title": scene.title,
        "prompt_version": ANALYZE_SCENE_PROMPT_VERSION,
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
                task_type="analyze",
                prompt=prompt,
                params={"temperature": 0.2},
                provider_mode=provider_mode,
                fixture_scenario=fixture_scenario,
            )
        except RuntimeError as exc:
            raise AIServiceError(AIErrorType.NETWORK, str(exc), run_id=run_id) from exc

        raw_response = gateway_result.text
        provider = gateway_result.provider
        model = gateway_result.model
        fallback_used = gateway_result.fallback_used
        latency_ms = gateway_result.latency_ms

        analysis_guard = validate_analysis_output(raw_response)
        if not analysis_guard.ok:
            raise AIServiceError(AIErrorType.MODEL_OUTPUT, analysis_guard.reason or "analysis output failed quality checks", run_id=run_id)

        result, parse_error = _parse_model_output(raw_response)
        parsed_response = result.model_dump()
        status = "success"
        error_message = None
        if return_gateway_result:
            return result, run_id, gateway_result
        return result, run_id
    except ValueError as exc:
        error_message = f"analyze output is not valid structured JSON: {exc}"
        raise AIServiceError(AIErrorType.MODEL_OUTPUT, error_message, run_id=run_id) from exc
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
            run_type="analyze_scene",
            task_type="analyze",
            provider=provider,
            model=model or "unknown",
            prompt_version=ANALYZE_SCENE_PROMPT_VERSION,
            fallback_used=fallback_used,
            input_payload=input_payload,
            raw_response=raw_response,
            parsed_response=parsed_response,
            status=status,
            error_message=error_message,
            latency_ms=latency_ms,
        )
