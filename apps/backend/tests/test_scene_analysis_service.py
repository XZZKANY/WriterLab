import pytest

from app.schemas.scene_analysis import SceneAnalysisResult, SceneProblem
from app.services.scene_analysis_service import (
    _clean_line,
    _coerce_result,
    _derive_summary,
    _ensure_non_empty_items,
    _extract_bullets,
    _normalize_problem,
    _parse_model_output,
)


def test_parse_model_output_rejects_generic_commentary_text():
    raw = """
    这个故事通过人物对话和细节描写展现了复杂关系，
    也说明了在面对未知时保持冷静的重要性。
    如果需要进一步修改或扩展，可以继续发展情节。
    """

    with pytest.raises(ValueError):
        _parse_model_output(raw)


def test_parse_model_output_accepts_valid_json_analysis():
    raw = """
    {
      "summary": "林岚试图确认对方是否记得旧案线索。",
      "scene_goal_detected": "确认对方是否掌握关键真相",
      "emotional_flow": ["试探", "警惕", "不安"],
      "problems": [
        {
          "type": "logic",
          "severity": "medium",
          "message": "林岚的追问还缺一个更明确的触发理由。"
        }
      ],
      "suggestions": ["补一处林岚为什么必须当场追问的动机。"]
    }
    """

    result, parse_error = _parse_model_output(raw)

    assert parse_error is None
    assert result.summary
    assert result.problems[0].type == "logic"


def test_parse_model_output_recovers_from_fenced_json_block():
    raw = """
    模型先有一段说明，然后给出 JSON：
    ```json
    {
      "summary": "ok",
      "emotional_flow": [],
      "problems": [
        {"type": "logic", "severity": "low", "message": "x"}
      ],
      "suggestions": ["y"]
    }
    ```
    """
    result, parse_error = _parse_model_output(raw)
    assert parse_error is None
    assert result.problems[0].message == "x"


def test_clean_line_collapses_whitespace_and_strips_marks():
    assert _clean_line("  - 这是一条问题：") == "这是一条问题"
    assert _clean_line("\t\n*  问题 1  \r\n") == "问题 1"


def test_extract_bullets_collects_dash_and_star_items_after_heading():
    raw = "建议：\n- 第一条\n* 第二条\n- 第三条\n- 第四条会被 limit 截掉"
    bullets = _extract_bullets(raw, headings=("建议",), limit=3)
    assert len(bullets) == 3
    assert "第一条" in bullets[0]


def test_extract_bullets_returns_empty_when_heading_absent():
    raw = "正文里没有任何对应小节的标题。\n- 这条不算"
    assert _extract_bullets(raw, headings=("建议",), limit=3) == []


def test_derive_summary_returns_default_when_text_blank():
    assert _derive_summary("") == "已完成场景分析，但模型没有返回可用摘要。"
    assert _derive_summary("   ") == "已完成场景分析，但模型没有返回可用摘要。"


def test_derive_summary_truncates_at_200_chars():
    long_text = "测" * 500
    assert len(_derive_summary(long_text)) == 200


def test_normalize_problem_returns_none_for_non_dict_or_empty_message():
    assert _normalize_problem("not a dict") is None
    assert _normalize_problem({"type": "logic", "severity": "low", "message": ""}) is None


def test_normalize_problem_falls_back_unknown_type_to_logic():
    item = {"type": "unknown", "severity": "low", "message": "x"}
    assert _normalize_problem(item).type == "logic"


def test_normalize_problem_maps_moderate_severity_to_medium():
    item = {"type": "logic", "severity": "moderate", "message": "x"}
    assert _normalize_problem(item).severity == "medium"


def test_normalize_problem_keeps_known_combo():
    item = {"type": "pacing", "severity": "high", "message": "x"}
    out = _normalize_problem(item)
    assert out.type == "pacing"
    assert out.severity == "high"


def test_coerce_result_raises_when_not_dict():
    with pytest.raises(ValueError):
        _coerce_result("not a dict")


def test_coerce_result_strips_invalid_problems_and_filters_blank_lists():
    raw = {
        "summary": "  s  ",
        "scene_goal_detected": "",
        "emotional_flow": ["a", "  ", "b", "  c  "],
        "suggestions": "not a list",
        "problems": ["bad", {"type": "logic", "severity": "low", "message": "ok"}],
    }
    result = _coerce_result(raw)
    assert result.summary == "s"
    assert result.scene_goal_detected is None
    assert result.emotional_flow == ["a", "b", "c"]
    assert result.suggestions == []
    assert len(result.problems) == 1
    assert result.problems[0].message == "ok"


def test_ensure_non_empty_items_passthrough_when_already_populated():
    result = SceneAnalysisResult(
        summary="s",
        scene_goal_detected="g",
        emotional_flow=[],
        problems=[SceneProblem(type="logic", severity="low", message="m")],
        suggestions=[],
    )
    same = _ensure_non_empty_items(result)
    assert same is result


def test_ensure_non_empty_items_supplies_default_problem_and_suggestion():
    result = SceneAnalysisResult(
        summary="",
        scene_goal_detected=None,
        emotional_flow=[],
        problems=[],
        suggestions=[],
    )
    filled = _ensure_non_empty_items(result)
    assert filled.summary
    assert len(filled.problems) == 1
    assert len(filled.suggestions) == 1
