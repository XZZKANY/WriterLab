"""ai_prompt_templates 的纯工具函数直测。

只覆盖底层 helper（stringify_list / clip_context / build_context_block），
prompt 文案本身不锁，避免每次微调措辞都要改测试。
"""

from types import SimpleNamespace

from app.services import ai_prompt_templates as pt


def test_stringify_list_empty_or_none_returns_无():
    assert pt.stringify_list(None) == "无"
    assert pt.stringify_list([]) == "无"


def test_stringify_list_filters_blank_entries():
    assert pt.stringify_list(["a", "  ", "", "b"]) == "a；b"


def test_stringify_list_returns_无_when_all_blank():
    assert pt.stringify_list(["", "   "]) == "无"


def test_stringify_list_joins_with_chinese_semicolon():
    assert pt.stringify_list(["x", "y", "z"]) == "x；y；z"


def test_clip_context_returns_fallback_for_empty_or_none():
    assert pt.clip_context(None, "默认", 10) == "默认"
    assert pt.clip_context("", "默认", 10) == "默认"
    assert pt.clip_context("   ", "默认", 10) == "默认"


def test_clip_context_collapses_whitespace_then_truncates():
    raw = "abc   defghij  klmnop"
    # split + join 把多空格压成 1 个空格 → "abc defghij klmnop"
    assert pt.clip_context(raw, "fallback", 8) == "abc defg"


def test_clip_context_does_not_truncate_when_within_limit():
    assert pt.clip_context("hello", "fallback", 100) == "hello"


def test_build_context_block_uses_未知_when_objects_are_none():
    block = pt.build_context_block(None, None)
    assert "未知" in block
    assert "视角人物" in block
    assert "场景地点" in block


def test_build_context_block_includes_actual_pov_and_location_fields():
    pov = SimpleNamespace(
        name="林雨",
        personality="冷静多疑",
        speaking_style="短句、克制",
        status="正在调查",
    )
    location = SimpleNamespace(name="老旧档案室", description="灯光昏黄，潮气扑面")
    block = pt.build_context_block(pov, location)
    assert "林雨" in block
    assert "冷静多疑" in block
    assert "短句、克制" in block
    assert "正在调查" in block
    assert "老旧档案室" in block
    assert "灯光昏黄，潮气扑面" in block


def test_mode_labels_and_instructions_cover_all_revise_modes():
    # MODE_LABELS / MODE_INSTRUCTIONS 是给 revise prompt 用的；保证三套 key 一致。
    assert set(pt.MODE_LABELS.keys()) == set(pt.MODE_INSTRUCTIONS.keys())
    assert "trim" in pt.MODE_LABELS
    assert "literary" in pt.MODE_LABELS
    assert "unify" in pt.MODE_LABELS


def test_length_hints_cover_known_keys():
    assert {"short", "medium", "long"} <= set(pt.LENGTH_HINTS.keys())
