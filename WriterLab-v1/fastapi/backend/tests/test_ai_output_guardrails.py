from app.services.ai_output_guardrails import (
    sanitize_revise_output,
    sanitize_write_output,
    validate_analysis_output,
    validate_prose_for_auto_apply,
    validate_style_output,
    validate_write_output,
)


def test_validate_analysis_output_rejects_generic_commentary():
    candidate = """
    这段整体已经很有感染力了。
    建议你再补一点环境描写，人物情绪会更完整。
    """

    result = validate_analysis_output(candidate)

    assert result.ok is False
    assert "commentary" in (result.reason or "")


def test_validate_analysis_output_accepts_structured_json():
    candidate = """
    {
      "summary": "这一段建立了重逢时的压迫感。",
      "scene_goal_detected": "让主角决定是否开口",
      "emotional_flow": ["戒备", "迟疑", "逼近崩溃"],
      "problems": [
        {
          "type": "pacing",
          "severity": "medium",
          "message": "前两段环境描写偏长，压缩后会更利于进入冲突。"
        }
      ],
      "suggestions": ["更早交代站台广播，让场景位置更稳。"]
    }
    """

    result = validate_analysis_output(candidate)

    assert result.ok is True


def test_validate_style_output_rejects_meta_and_language_drift():
    source = "林岚推开旧站台的门，冷风裹着铁锈味扑到脸上。她没有立刻说话，只盯着尽头那盏忽明忽暗的灯。"
    candidate = """
    以下是润色后的版本：
    1. Add more atmosphere.
    2. Explain the emotional subtext.
    """

    result = validate_style_output(source, candidate)

    assert result.ok is False


def test_validate_style_output_accepts_close_prose_revision():
    source = "林岚推开旧站台的门，冷风裹着铁锈味扑到脸上。她没有立刻说话，只盯着尽头那盏忽明忽暗的灯。"
    candidate = "林岚推开旧站台的门，冷风带着铁锈气息扑面而来。她没有马上开口，只盯着尽头那盏忽明忽暗的灯。"

    result = validate_style_output(source, candidate)

    assert result.ok is True


def test_validate_style_output_rejects_aggressive_length_change():
    source = "林岚推开旧站台的门，冷风裹着铁锈味扑到脸上。她没有立刻说话，只盯着尽头那盏忽明忽暗的灯。"
    candidate = "林岚沉默。"

    result = validate_style_output(source, candidate)

    assert result.ok is False
    assert "length" in (result.reason or "")


def test_validate_prose_for_auto_apply_blocks_rewrite_notes():
    candidate = """
    改写说明：
    我保留了原文情节，并加强了人物情绪层次。
    """

    result = validate_prose_for_auto_apply(candidate)

    assert result.ok is False


def test_sanitize_write_output_removes_meta_sections_and_keeps_prose():
    candidate = """
    ---

    这个故事通过对话和细节的描述，展现了人物之间的复杂关系。
    如果需要进一步修改或扩展，请随时告知。

    ### 林岚的下一步计划

    1. 深入调查
    2. 间接接触

    她重新扫过现场，把试探性对白也纳入眼前正在发生的一切。
    """

    cleaned, notes = sanitize_write_output(candidate)

    assert "如果需要进一步修改或扩展" not in cleaned
    assert "###" not in cleaned
    assert "深入调查" not in cleaned
    assert "她重新扫过现场" in cleaned
    assert notes


def test_validate_write_output_rejects_generic_commentary():
    candidate = """
    这个故事通过对话和细节的描述，展现了人物之间的复杂关系以及他们之间交流的方式。
    希望这样的设定能够满足您的需求。如果需要进一步修改或扩展，请随时告知。
    """

    result = validate_write_output(candidate)

    assert result.ok is False
    assert "commentary" in (result.reason or "")


def test_sanitize_revise_output_removes_assistant_guidance_sections():
    candidate = """
    当然可以！以下是几个具体的建议，可以帮助你更好地利用友谊的力量。

    1. 开放沟通
    2. 共同经历

    林岚重新抬眼，意识到自己真正想确认的并不是答案本身，而是对方仍愿不愿意面对那段过去。

    如果您还有其他问题，请随时提问。祝您成功！
    """

    cleaned, notes = sanitize_revise_output(candidate)

    assert "当然可以" not in cleaned
    assert "如果您还有其他问题" not in cleaned
    assert "林岚重新抬眼" in cleaned
    assert notes


def test_validate_style_output_rejects_assistant_guidance_loops():
    source = "林岚盯着对方的眼睛，没有立刻追问，只让沉默在两人之间缓慢发酵。"
    candidate = """
    这个故事告诉我们，真正的友谊需要时间和耐心去培养。

    如果您在实施上述建议时遇到任何问题，请随时回来寻求更多支持和建议。
    """

    result = validate_style_output(source, candidate)

    assert result.ok is False
    assert "assistant-style advice" in (result.reason or "")
