"""scene_write_service 中的纯辅助函数直测。

针对 `_clean_list`、`_cleanup_draft_text`、`_needs_template_fallback`、
`_enforce_scene_constraints` 这些不触达 DB / AI 网关的小工具，补 happy + 边界用例。
write_scene 主调用涉及 AI gateway 与 DB，由 workflow_service 套件覆盖；这里只测纯函数。
"""

from types import SimpleNamespace

from app.services import scene_write_service as sw


# ---------- _clean_list ----------

def test_clean_list_returns_empty_for_none_or_empty():
    assert sw._clean_list(None) == []
    assert sw._clean_list([]) == []


def test_clean_list_strips_blank_entries():
    assert sw._clean_list(["a", "  b  ", "", "   ", "c"]) == ["a", "b", "c"]


def test_clean_list_coerces_non_string_to_string():
    assert sw._clean_list([1, "2", "  3  "]) == ["1", "2", "3"]


# ---------- _cleanup_draft_text ----------

def test_cleanup_draft_text_strips_think_block():
    text = "<think>internal reasoning</think>\n场景正文：天还没亮。"
    cleaned = sw._cleanup_draft_text(text)
    assert "internal reasoning" not in cleaned
    assert cleaned.startswith("天还没亮")


def test_cleanup_draft_text_strips_code_fence_with_language_tag():
    text = "```text\n夜风刮过窗。\n```"
    assert sw._cleanup_draft_text(text) == "夜风刮过窗。"


def test_cleanup_draft_text_strips_known_chinese_prefixes():
    for prefix in ["正文：", "场景正文：", "生成正文：", "以下是正文：", "以下是生成的正文："]:
        assert sw._cleanup_draft_text(f"{prefix}夜风刮过窗。") == "夜风刮过窗。"


def test_cleanup_draft_text_drops_trailing_explanation_blocks():
    text = "夜风刮过窗。\n\n说明：这是一段尾注。"
    assert sw._cleanup_draft_text(text) == "夜风刮过窗。"
    text = "夜风刮过窗。\n\nNotes: cut everything after this"
    assert sw._cleanup_draft_text(text) == "夜风刮过窗。"


def test_cleanup_draft_text_passthrough_for_clean_input():
    assert sw._cleanup_draft_text("这是一段正常正文。") == "这是一段正常正文。"


# ---------- _needs_template_fallback ----------

def test_needs_template_fallback_true_for_empty_text():
    assert sw._needs_template_fallback("") is True
    assert sw._needs_template_fallback("   ") is True


def test_needs_template_fallback_true_when_model_refuses():
    for refusal in ["我不能这样写", "我无法生成", "抱歉，作为一个AI...", "作为AI 助手", "不能满足你的请求"]:
        assert sw._needs_template_fallback(refusal) is True, refusal


def test_needs_template_fallback_false_for_normal_draft():
    assert sw._needs_template_fallback("夜里下了雨，街道湿滑。林雨没说话。") is False


# ---------- _enforce_scene_constraints ----------

def test_enforce_scene_constraints_no_change_when_no_must_lists():
    scene = SimpleNamespace(must_include=None, must_avoid=None)
    text, notes = sw._enforce_scene_constraints(scene, "原始文本")
    assert text == "原始文本"
    assert notes == []


def test_enforce_scene_constraints_appends_when_must_include_missing():
    scene = SimpleNamespace(must_include=["伞", "短信"], must_avoid=None)
    text, notes = sw._enforce_scene_constraints(scene, "她站在街边看雨。")
    # 缺失项应作为补充段被加入
    assert "伞" in text
    assert "短信" in text
    assert any("must_include" in note for note in notes)


def test_enforce_scene_constraints_does_not_add_when_already_present():
    scene = SimpleNamespace(must_include=["伞"], must_avoid=None)
    text, notes = sw._enforce_scene_constraints(scene, "她抓紧伞站在街边。")
    assert text == "她抓紧伞站在街边。"
    assert notes == []


def test_enforce_scene_constraints_softens_must_avoid_hits():
    scene = SimpleNamespace(must_include=None, must_avoid=["凶手就是哥哥"])
    text, notes = sw._enforce_scene_constraints(scene, "她忽然意识到，凶手就是哥哥。")
    assert "凶手就是哥哥" not in text
    assert "那个暂时没有被说破的事实" in text
    assert any("must_avoid" in note for note in notes)


def test_enforce_scene_constraints_handles_both_lists_simultaneously():
    scene = SimpleNamespace(must_include=["伞"], must_avoid=["真名"])
    text, notes = sw._enforce_scene_constraints(scene, "她说出了真名。")
    assert "真名" not in text
    assert "伞" in text
    assert len(notes) == 2
