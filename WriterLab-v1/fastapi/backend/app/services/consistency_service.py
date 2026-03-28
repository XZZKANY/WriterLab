import json
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.character import Character
from app.models.consistency_issue import ConsistencyIssue
from app.models.location import Location
from app.models.scene import Scene
from app.services.ai_gateway_service import call_ai_gateway
from app.services.context_service import build_scene_context

_COLOR_WORDS = ["黑", "白", "灰", "银", "金", "蓝", "红", "绿", "紫", "棕", "褐", "琥珀"]
_TIME_WORDS = ["清晨", "早晨", "上午", "中午", "午后", "傍晚", "夜里", "深夜", "凌晨"]


def _resolve_project_id(scene: Scene, db: Session):
    chapter = db.query(Chapter).filter(Chapter.id == scene.chapter_id).first()
    if not chapter:
        return None
    book = db.query(Book).filter(Book.id == chapter.book_id).first()
    return book.project_id if book else None


def _clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _extract_feature_color(text: str, feature: str) -> str | None:
    for color in _COLOR_WORDS:
        patterns = [
            rf"{color}色?{feature}",
            rf"{feature}.{{0,4}}?{color}色?",
        ]
        if any(re.search(pattern, text) for pattern in patterns):
            return color
    return None


def _appearance_issues(scene: Scene, draft_text: str, db: Session) -> list[dict[str, Any]]:
    if not scene.pov_character_id:
        return []
    character = db.query(Character).filter(Character.id == scene.pov_character_id).first()
    if not character or not character.appearance:
        return []

    appearance = _clean_text(character.appearance)
    text = draft_text or ""
    issues: list[dict[str, Any]] = []

    eye_color = _extract_feature_color(appearance, "眼")
    draft_eye_color = _extract_feature_color(text, "眼")
    if eye_color and draft_eye_color and eye_color != draft_eye_color:
        issues.append(
            {
                "issue_type": "appearance_conflict",
                "severity": "high",
                "source": "规则检查",
                "message": f"{character.name} 的外貌设定提到 {eye_color}色眼睛，但当前正文出现了 {draft_eye_color}色眼睛。",
                "fix_suggestion": f"把正文里的眼部颜色改回 {eye_color}色，或明确说明这是有意发生的变化。",
                "evidence_json": {
                    "character": character.name,
                    "appearance": appearance,
                    "expected_eye_color": eye_color,
                    "draft_eye_color": draft_eye_color,
                },
            }
        )

    hair_color = _extract_feature_color(appearance, "发")
    draft_hair_color = _extract_feature_color(text, "发")
    if hair_color and draft_hair_color and hair_color != draft_hair_color:
        issues.append(
            {
                "issue_type": "appearance_conflict",
                "severity": "medium",
                "source": "规则检查",
                "message": f"{character.name} 的外貌设定提到 {hair_color}色头发，但正文里出现了 {draft_hair_color}色头发。",
                "fix_suggestion": f"统一发色描述，避免让读者误以为人物外貌发生了未交代的变化。",
                "evidence_json": {
                    "character": character.name,
                    "appearance": appearance,
                    "expected_hair_color": hair_color,
                    "draft_hair_color": draft_hair_color,
                },
            }
        )

    return issues


def _timeline_conflict_issues(scene: Scene, draft_text: str, bundle: dict) -> list[dict[str, Any]]:
    text = draft_text or ""
    scene_time = _clean_text(scene.time_label)
    recent_time_labels = [item.get("time_label") for item in bundle.get("recent_scenes", []) if item.get("time_label")]
    timeline_labels = [getattr(item, "event_time_label", None) for item in bundle.get("timeline_events", []) if getattr(item, "event_time_label", None)]
    known_time_labels = [label for label in [scene_time, *recent_time_labels, *timeline_labels] if label]

    issues: list[dict[str, Any]] = []
    if scene_time and scene_time not in text:
        issues.append(
            {
                "issue_type": "time_label_missing",
                "severity": "low",
                "source": "规则检查",
                "message": f"当前场景设定时间为“{scene_time}”，但正文里没有明确体现。",
                "fix_suggestion": "补上一句时间提示或环境线索，让读者知道这一幕发生在什么时段。",
                "evidence_json": {"time_label": scene_time},
            }
        )

    conflicting = [label for label in _TIME_WORDS if label in text and label not in known_time_labels]
    if scene_time and conflicting:
        issues.append(
            {
                "issue_type": "timeline_conflict",
                "severity": "medium",
                "source": "规则检查",
                "message": f"正文里出现了与当前场景时间不一致的时间词：{', '.join(conflicting)}。",
                "fix_suggestion": "统一这一幕的时间线索，避免同时出现多个互相冲突的时段描述。",
                "evidence_json": {
                    "scene_time_label": scene_time,
                    "conflicting_labels": conflicting,
                    "known_time_labels": known_time_labels,
                },
            }
        )

    return issues


def _rule_issues(scene: Scene, draft_text: str, db: Session, bundle: dict | None = None) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    text = draft_text or ""
    context_bundle = bundle or build_scene_context(scene, db)

    for item in scene.must_include or []:
        if item and item not in text:
            issues.append(
                {
                    "issue_type": "must_include_missing",
                    "severity": "high",
                    "source": "规则检查",
                    "message": f"正文缺少必须出现的元素：{item}。",
                    "fix_suggestion": "把这个关键元素明确写回当前场景，避免后续剧情失去承接点。",
                    "evidence_json": {"item": item},
                }
            )

    for item in scene.must_avoid or []:
        if item and item in text:
            issues.append(
                {
                    "issue_type": "must_avoid_violation",
                    "severity": "high",
                    "source": "规则检查",
                    "message": f"正文触发了禁写内容：{item}。",
                    "fix_suggestion": "删掉或改写这部分内容，避免与当前设定或创作约束冲突。",
                    "evidence_json": {"item": item},
                }
            )

    if scene.location_id:
        location = db.query(Location).filter(Location.id == scene.location_id).first()
        if location and location.name and location.name not in text:
            issues.append(
                {
                    "issue_type": "location_anchor",
                    "severity": "low",
                    "source": "规则检查",
                    "message": f"正文没有明显提到当前场景地点“{location.name}”。",
                    "fix_suggestion": "补一到两处地点锚点，让读者知道人物此刻身处何处。",
                    "evidence_json": {"location": location.name},
                }
            )

    issues.extend(_appearance_issues(scene, text, db))
    issues.extend(_timeline_conflict_issues(scene, text, context_bundle))
    return issues


def _llm_issues(scene: Scene, draft_text: str, db: Session, bundle: dict | None = None) -> list[dict[str, Any]]:
    context_bundle = bundle or build_scene_context(scene, db)
    prompt = (
        "你是长篇小说一致性审校助手。请检查当前正文是否与设定、近期剧情、时间线和风格记忆发生冲突。\n"
        "只返回 JSON 数组，不要写解释，不要写 markdown。\n"
        "每个元素必须包含 type、severity、message，可选字段 evidence、suggestion。\n"
        "type 优先使用：appearance_conflict / timeline_conflict / title_drift / motivation_drift / lore_conflict / llm_review。\n"
        "severity 只能是 low / medium / high。\n"
        f"当前场景：{json.dumps(context_bundle['scene_summary'], ensure_ascii=False)}\n"
        f"近期场景：{json.dumps(context_bundle.get('recent_scenes', []), ensure_ascii=False)}\n"
        f"时间线：{json.dumps([{'title': item.title, 'time': item.event_time_label, 'description': item.description} for item in context_bundle['timeline_events']], ensure_ascii=False)}\n"
        f"设定约束：{json.dumps([{'title': item.title, 'content': item.content} for item in context_bundle['lore_constraints']], ensure_ascii=False)}\n"
        f"风格记忆：{json.dumps([item.content for item in context_bundle['style_memories']], ensure_ascii=False)}\n"
        f"必须包含：{json.dumps(context_bundle['must_include'], ensure_ascii=False)}\n"
        f"必须避免：{json.dumps(context_bundle['must_avoid'], ensure_ascii=False)}\n"
        f"当前正文：\n{draft_text}"
    )
    try:
        result = call_ai_gateway(db, task_type="analyze", workflow_step="check", prompt=prompt, params={"temperature": 0.1})
    except Exception:
        return []

    raw = (result.text or "").strip()
    try:
        parsed = json.loads(raw)
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []

    issues: list[dict[str, Any]] = []
    for item in parsed[:6]:
        if not isinstance(item, dict):
            continue
        message = str(item.get("message", "")).strip()
        if not message:
            continue
        issues.append(
            {
                "issue_type": str(item.get("type", "llm_review")).strip() or "llm_review",
                "severity": str(item.get("severity", "medium")).strip() or "medium",
                "source": "LLM复核",
                "message": message,
                "fix_suggestion": str(item.get("suggestion", "")).strip() or None,
                "evidence_json": item.get("evidence") if isinstance(item.get("evidence"), dict) else {"source": "llm"},
            }
        )
    return issues


def scan_scene_consistency(
    db: Session,
    *,
    scene: Scene,
    draft_text: str | None = None,
    workflow_run_id=None,
) -> list[ConsistencyIssue]:
    text = (draft_text if draft_text is not None else scene.draft_text) or ""
    project_id = _resolve_project_id(scene, db)
    bundle = build_scene_context(scene, db)

    db.query(ConsistencyIssue).filter(ConsistencyIssue.scene_id == scene.id).delete()
    issue_specs = _rule_issues(scene, text, db, bundle=bundle)
    issue_specs.extend(_llm_issues(scene, text, db, bundle=bundle))

    deduped: list[dict[str, Any]] = []
    seen = set()
    for spec in issue_specs:
        key = (spec.get("issue_type"), spec.get("message"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(spec)

    issues: list[ConsistencyIssue] = []
    for spec in deduped:
        issue = ConsistencyIssue(
            project_id=project_id,
            scene_id=scene.id,
            workflow_run_id=workflow_run_id,
            issue_type=spec["issue_type"],
            severity=spec["severity"],
            source=spec.get("source"),
            fix_suggestion=spec.get("fix_suggestion"),
            message=spec["message"],
            evidence_json=spec.get("evidence_json"),
        )
        db.add(issue)
        issues.append(issue)

    db.commit()
    for issue in issues:
        db.refresh(issue)
    return issues
