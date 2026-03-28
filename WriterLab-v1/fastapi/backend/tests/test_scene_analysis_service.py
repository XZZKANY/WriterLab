import pytest

from app.services.scene_analysis_service import _parse_model_output


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
