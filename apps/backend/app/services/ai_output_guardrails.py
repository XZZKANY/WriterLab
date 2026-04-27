from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.schemas.workflow import GuardOutput, Violation


@dataclass
class GuardrailResult:
    ok: bool
    reason: str | None = None


_STYLE_META_PATTERNS = [
    r"(?m)^\s*---+\s*$",
    r"(?im)^\s*#{1,6}\s",
    r"(?im)^\s*(?:[-*]\s|\d+\.\s)",
    r"(?im)^\s*(?:summary|analysis|notes?|rewrite|revision|explanation)\s*[:：]",
    r"(?im)^\s*(?:总结|分析|建议|润色说明|改写说明|说明|注释)\s*[:：]",
    r"(?i)\b(?:improvement|improved version|analysis|explanation|summary|rewrite|revision|notes?)\b",
]

_ASSISTANT_GUIDANCE_PATTERNS = [
    r"这个故事告诉我们",
    r"这个故事.*展现了",
    r"请注意[:：]",
    r"如果您(?:还)?有任何问题",
    r"如果您在实施上述建议",
    r"如果需要进一步",
    r"希望这些建议",
    r"希望对你有所帮助",
    r"祝您(?:成功|好运|有个愉快的一天)",
    r"当然可以",
    r"以下是(?:几个|一些|可能的|具体的)?",
    r"总之[，,]",
    r"此外[，,]",
    r"非常感谢你的回答",
    r"谢谢你的回答",
    r"建议您寻求专业",
    r"现实中遇到困难时",
    r"通过这些方法",
    r"保持乐观的心态",
    r"欢迎继续提问",
    r"如果读者想了解更多",
    r"在面对工作压力时",
    r"如何在工作中",
    r"如何有效管理时间",
    r"如何在工作中保持专注",
]

_ANALYSIS_HINT_PATTERNS = [
    r"(?i)\b(summary|problem|issue|suggestion|goal|emotion|pacing|consistency|character|logic)\b",
    r"(总结|问题|建议|目标|情绪|节奏|一致性|角色|逻辑)",
]

_ANALYSIS_SECTION_PATTERNS = [
    r"(?im)^\s*(summary|problems?|issues?|suggestions?)\s*[:：]",
    r"(?im)^\s*(总结|问题|建议|目标|情绪流)\s*[:：]",
]

_GENERIC_COMMENTARY_PATTERNS = [
    r"这个故事.*(?:展现|强调|突出了)",
    r"希望这样的设定能够满足您的需求",
    r"如果需要进一步修改或扩展",
    r"以下是可能的发展方向",
    r"以上就是关于",
    r"当然，我们可以继续",
]

_NON_PROSE_LINE_PATTERNS = [
    r"^\s*---+\s*$",
    r"^\s*#{1,6}\s",
    r"^\s*(?:[-*]\s|\d+\.\s)",
]

_NON_PROSE_PARAGRAPH_PATTERNS = [
    r"^\s*(?:总结|分析|建议|润色说明|改写说明|说明|注释)\s*[:：]?",
    r"^\s*(?:summary|analysis|notes?|rewrite|revision|explanation)\s*[:：]?",
]


def _normalize_for_compare(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff\u3040-\u30ff]+", "", text or "")


def _count_japanese_script(text: str) -> int:
    return len(re.findall(r"[\u3040-\u30ff]", text or ""))


def _count_cjk(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text or ""))


def _count_latin_letters(text: str) -> int:
    return len(re.findall(r"[A-Za-z]", text or ""))


def _contains_meta_patterns(text: str) -> bool:
    return any(re.search(pattern, text or "") for pattern in _STYLE_META_PATTERNS)


def _contains_assistant_guidance(text: str) -> bool:
    return any(re.search(pattern, text or "", re.IGNORECASE) for pattern in _ASSISTANT_GUIDANCE_PATTERNS)


def _analysis_hint_hits(text: str) -> int:
    return sum(1 for pattern in _ANALYSIS_HINT_PATTERNS if re.search(pattern, text or ""))


def _analysis_section_hits(text: str) -> int:
    return sum(1 for pattern in _ANALYSIS_SECTION_PATTERNS if re.search(pattern, text or ""))


def _looks_like_json_payload(text: str) -> bool:
    lowered = (text or "").lower()
    stripped = (text or "").strip()
    return (
        stripped.startswith("{")
        or stripped.startswith("[")
        or "```json" in lowered
        or '"summary"' in lowered
        or '"problems"' in lowered
        or '"suggestions"' in lowered
    )


def _split_paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", (text or "").replace("\r\n", "\n")) if part.strip()]


def sanitize_write_output(raw_text: str) -> tuple[str, list[str]]:
    text = (raw_text or "").replace("\r\n", "\n").strip()
    if not text:
        return "", []

    notes: list[str] = []
    kept: list[str] = []
    removed_any = False

    for paragraph in _split_paragraphs(text):
        lines = [line.rstrip() for line in paragraph.splitlines() if line.strip()]
        if not lines:
            continue

        if all(any(re.search(pattern, line) for pattern in _NON_PROSE_LINE_PATTERNS) for line in lines):
            removed_any = True
            continue
        if any(re.search(pattern, paragraph, re.IGNORECASE) for pattern in _NON_PROSE_PARAGRAPH_PATTERNS):
            removed_any = True
            continue
        if _contains_assistant_guidance(paragraph) or any(
            re.search(pattern, paragraph, re.IGNORECASE) for pattern in _GENERIC_COMMENTARY_PATTERNS
        ):
            removed_any = True
            continue
        if len(lines) >= 2 and all(re.search(r"^\s*(?:[-*]\s|\d+\.\s)", line) for line in lines):
            removed_any = True
            continue

        kept.append(paragraph)

    cleaned = "\n\n".join(kept).strip()
    if removed_any:
        notes.append("已移除说明腔、提纲或建议型段落，只保留可直接用于正文的内容。")
    return cleaned, notes


def sanitize_revise_output(raw_text: str) -> tuple[str, list[str]]:
    text = (raw_text or "").replace("\r\n", "\n").strip()
    if not text:
        return "", []

    notes: list[str] = []
    kept: list[str] = []
    seen: set[str] = set()
    removed_any = False

    for paragraph in _split_paragraphs(text):
        normalized = re.sub(r"\s+", " ", paragraph).strip()
        if not normalized or normalized in seen:
            removed_any = True
            continue
        seen.add(normalized)

        if any(re.search(pattern, paragraph, re.IGNORECASE) for pattern in _NON_PROSE_PARAGRAPH_PATTERNS):
            removed_any = True
            continue
        if _contains_assistant_guidance(paragraph):
            removed_any = True
            continue
        if any(re.search(pattern, paragraph, re.IGNORECASE) for pattern in _GENERIC_COMMENTARY_PATTERNS):
            removed_any = True
            continue
        if re.search(r"(?m)^\s*(?:[-*]|\d+\.)\s", paragraph):
            removed_any = True
            continue

        kept.append(paragraph)

    cleaned = "\n\n".join(kept).strip()
    if removed_any:
        notes.append("已移除问答腔、建议腔或说明性段落，只保留可直接用于正文的润色结果。")
    return cleaned, notes


def validate_analysis_output(raw_text: str) -> GuardrailResult:
    stripped = (raw_text or "").strip()
    if not stripped:
        return GuardrailResult(False, "analyze output is empty")

    if _looks_like_json_payload(stripped):
        return GuardrailResult(True)

    hint_hits = _analysis_hint_hits(stripped)
    section_hits = _analysis_section_hits(stripped)
    bullet_count = len(re.findall(r"(?m)^\s*(?:[-*]|\d+\.)\s", stripped))

    if any(re.search(pattern, stripped, re.IGNORECASE) for pattern in _GENERIC_COMMENTARY_PATTERNS):
        return GuardrailResult(False, "analyze output looks like generic commentary instead of structured scene analysis")
    if _contains_assistant_guidance(stripped):
        return GuardrailResult(False, "analyze output looks like assistant guidance instead of structured scene analysis")
    if _contains_meta_patterns(stripped) and section_hits == 0:
        return GuardrailResult(False, "analyze output looks like generic commentary instead of structured scene analysis")
    if hint_hits < 2 and bullet_count < 2:
        return GuardrailResult(False, "analyze output looks like generic commentary instead of structured scene analysis")
    if section_hits >= 2 or (hint_hits >= 2 and bullet_count >= 2):
        return GuardrailResult(True)
    return GuardrailResult(False, "analyze output is not strict structured analysis")


def validate_style_output(source_text: str, candidate_text: str) -> GuardrailResult:
    candidate = (candidate_text or "").strip()
    source = (source_text or "").strip()
    if not candidate:
        return GuardrailResult(False, "style output is empty")
    if _contains_meta_patterns(candidate):
        return GuardrailResult(False, "style output contains commentary, headings, or list formatting instead of pure scene prose")
    if _contains_assistant_guidance(candidate):
        return GuardrailResult(False, "style output contains assistant-style advice or Q&A content instead of scene prose")
    if any(re.search(pattern, candidate, re.IGNORECASE) for pattern in _GENERIC_COMMENTARY_PATTERNS):
        return GuardrailResult(False, "style output contains commentary instead of pure scene prose")

    source_norm = _normalize_for_compare(source)
    candidate_norm = _normalize_for_compare(candidate)
    if source_norm:
        ratio = len(candidate_norm) / max(len(source_norm), 1)
        if ratio < 0.60 or ratio > 1.45:
            return GuardrailResult(False, f"style output changed length too aggressively (ratio={ratio:.2f})")

        similarity = SequenceMatcher(None, source_norm[:4000], candidate_norm[:4000]).ratio()
        if similarity < 0.20:
            return GuardrailResult(False, f"style output drifted too far from the draft (similarity={similarity:.2f})")

    source_japanese = _count_japanese_script(source)
    candidate_japanese = _count_japanese_script(candidate)
    candidate_cjk = _count_cjk(candidate)
    if candidate_japanese >= max(10, source_japanese + 8) and candidate_japanese > max(6, int(candidate_cjk * 0.2)):
        return GuardrailResult(False, "style output unexpectedly switched into Japanese-heavy text")

    source_cjk = _count_cjk(source)
    candidate_latin = _count_latin_letters(candidate)
    if source_cjk >= 20 and candidate_latin > max(40, int(len(candidate) * 0.35)):
        return GuardrailResult(False, "style output drifted away from the source language")

    return validate_prose_for_auto_apply(candidate)


def validate_write_output(text: str) -> GuardrailResult:
    stripped = (text or "").strip()
    if not stripped:
        return GuardrailResult(False, "write output is empty")
    if any(re.search(pattern, stripped, re.IGNORECASE) for pattern in _GENERIC_COMMENTARY_PATTERNS):
        return GuardrailResult(False, "write output contains generic commentary instead of scene prose")
    if _contains_assistant_guidance(stripped):
        return GuardrailResult(False, "write output contains assistant-style advice instead of scene prose")
    return validate_prose_for_auto_apply(stripped)


def validate_prose_for_auto_apply(text: str) -> GuardrailResult:
    stripped = (text or "").strip()
    if not stripped:
        return GuardrailResult(False, "final prose is empty")
    if _contains_meta_patterns(stripped):
        return GuardrailResult(False, "final prose still looks like commentary or rewrite notes")
    if any(re.search(pattern, stripped, re.IGNORECASE) for pattern in _GENERIC_COMMENTARY_PATTERNS):
        return GuardrailResult(False, "final prose still contains generic commentary")
    if _contains_assistant_guidance(stripped):
        return GuardrailResult(False, "final prose still contains assistant-style advice or Q&A content")
    return GuardrailResult(True)


def build_guard_output(text: str, *, step_key: str = "guard") -> GuardOutput:
    result = validate_prose_for_auto_apply(text)
    if result.ok:
        return GuardOutput(safe_to_apply=True, needs_rewrite=False, needs_user_review=False, violations=[])

    violation = Violation(
        type=f"{step_key}_violation",
        span=None,
        rule_id=f"{step_key}.invalid_output",
        severity="high",
        reason=result.reason or "Guardrail rejected the candidate output",
        suggestion="Rewrite the output or merge manually after review.",
    )
    return GuardOutput(
        safe_to_apply=False,
        needs_rewrite=True,
        needs_user_review=True,
        violations=[violation],
    )
