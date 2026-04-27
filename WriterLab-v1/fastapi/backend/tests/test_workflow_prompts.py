"""workflow_prompts 模块的纯函数直测。

T-6.A2 拆分后的 prompt 拼接函数；只验证字段是否进入提示词文本，避免锁死具体措辞。
"""

from types import SimpleNamespace

from app.schemas.workflow import WorkflowSceneRequest
from app.services.workflow_prompts import (
    _build_memory_candidate,
    _planner_prompt,
    _style_prompt,
)


def _scene(**overrides):
    defaults = {
        "title": "测试场景",
        "goal": "目标",
        "conflict": "冲突",
        "outcome": "结果",
        "must_include": ["必写"],
        "must_avoid": ["禁写"],
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _bundle(**overrides):
    defaults = {
        "recent_scenes": ["前情 1"],
        "lore_constraints": [SimpleNamespace(title="设定 A")],
        "style_memories": [SimpleNamespace(content="冷静节奏")],
    }
    defaults.update(overrides)
    return defaults


# ---------- _planner_prompt ----------

def test_planner_prompt_includes_scene_metadata_and_guidance():
    text = _planner_prompt(_scene(), _bundle(), ["保持紧张感"])
    assert "测试场景" in text
    assert "目标" in text
    assert "冲突" in text
    assert "结果" in text
    assert "保持紧张感" in text
    assert "前情 1" in text
    assert "设定 A" in text


def test_planner_prompt_handles_empty_scene_fields():
    text = _planner_prompt(_scene(goal=None, conflict=None, outcome=None), _bundle(), [])
    assert "Goal: " in text
    assert "Conflict: " in text
    assert "Outcome target: " in text


def test_planner_prompt_includes_concise_plan_directive():
    # 末行强约束模型只产出一份计划，不要附带其它内容。
    text = _planner_prompt(_scene(), _bundle(), [])
    assert text.rstrip().endswith("Produce a concise plan.")


# ---------- _style_prompt ----------

def test_style_prompt_includes_must_constraints_and_draft_tail():
    text = _style_prompt(_scene(), "原始草稿正文", _bundle())
    assert "测试场景" in text
    assert "必写" in text
    assert "禁写" in text
    assert "冷静节奏" in text
    # 草稿应作为最后一段，模型基于此重写。
    assert text.rstrip().endswith("原始草稿正文")


def test_style_prompt_falls_back_to_empty_lists_when_scene_missing_fields():
    text = _style_prompt(_scene(must_include=None, must_avoid=None), "draft", _bundle())
    assert "Must include: []" in text
    assert "Must avoid: []" in text


# ---------- _build_memory_candidate ----------

def _payload(guidance: list[str]) -> WorkflowSceneRequest:
    # 仅依赖 guidance 字段；其它必填项给最小值。
    return WorkflowSceneRequest(
        scene_id="00000000-0000-0000-0000-000000000000",
        guidance=guidance,
    )


def test_build_memory_candidate_with_guidance_uses_top_rules():
    rules = [f"规则 {i}" for i in range(8)]
    content, derived = _build_memory_candidate(_scene(title="夜雨"), _payload(rules), "draft")
    assert "夜雨" in content
    assert "规则 0" in content
    # content 仅取 4 条参与拼接；derived 仅留 6 条。
    assert "规则 4" not in content
    assert derived == rules[:6]


def test_build_memory_candidate_strips_blank_guidance_items():
    content, derived = _build_memory_candidate(
        _scene(),
        _payload(["", "   ", "有效规则"]),
        "draft",
    )
    assert "有效规则" in content
    assert derived == ["有效规则"]


def test_build_memory_candidate_falls_back_to_default_rules_when_no_guidance():
    content, derived = _build_memory_candidate(_scene(), _payload([]), "draft")
    assert "based on accepted draft tone" in content
    assert any("中文小说正文" in rule for rule in derived)
    assert len(derived) == 2


def test_build_memory_candidate_handles_scene_without_title():
    content, _ = _build_memory_candidate(_scene(title=None), _payload([]), "draft")
    assert "for scene" in content
