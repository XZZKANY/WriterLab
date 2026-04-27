"""scene_revise_service 中的纯辅助函数直测。

只覆盖 `_cleanup_revised_text`（不触达 DB）。`revise_scene` 的主流程依赖 AI 网关，
由 workflow_service 测试套件覆盖。
"""

from app.services import scene_revise_service as sr


def test_cleanup_revised_text_strips_think_block():
    text = "<think>internal</think>\n润色结果：天明。"
    assert sr._cleanup_revised_text(text) == "天明。"


def test_cleanup_revised_text_strips_code_fence():
    assert sr._cleanup_revised_text("```\n夜风刮过窗。\n```") == "夜风刮过窗。"


def test_cleanup_revised_text_strips_known_prefixes():
    for prefix in ["润色结果：", "改写结果：", "正文：", "输出：", "以下是润色后的正文：", "以下是修改后的正文："]:
        assert sr._cleanup_revised_text(f"{prefix}夜风刮过窗。") == "夜风刮过窗。"


def test_cleanup_revised_text_handles_none_and_empty():
    assert sr._cleanup_revised_text("") == ""
    assert sr._cleanup_revised_text(None) == ""
    assert sr._cleanup_revised_text("   ") == ""


def test_cleanup_revised_text_passthrough_clean_input():
    assert sr._cleanup_revised_text("一句正常的中文正文。") == "一句正常的中文正文。"


def test_cleanup_revised_text_only_strips_known_prefixes_at_start():
    # 中间出现 "正文：" 不该被吃掉
    text = "她说：正文：这只是引用。"
    assert sr._cleanup_revised_text(text) == "她说：正文：这只是引用。"
