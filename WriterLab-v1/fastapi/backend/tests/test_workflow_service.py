from types import SimpleNamespace

from app.services.workflow_service import _agent_meta, _build_memory_candidate, _with_agent_meta


def test_agent_meta_maps_guard_and_memory_steps():
    guard = _agent_meta("guard")
    memory = _agent_meta("memory")

    assert guard["agent_key"] == "guardrail"
    assert guard["agent_name"] == "Guardrail Agent"
    assert memory["agent_key"] == "memory_curator"
    assert memory["agent_name"] == "Memory Curator Agent"


def test_with_agent_meta_keeps_payload_and_adds_labels():
    payload = _with_agent_meta("write", {"draft_length": 1200})

    assert payload["draft_length"] == 1200
    assert payload["agent_key"] == "writer"
    assert payload["agent_name"] == "Writer Agent"


def test_build_memory_candidate_prefers_guidance_rules():
    scene = SimpleNamespace(title="雨夜仓库")
    payload = SimpleNamespace(guidance=["对白更克制", "动作描写更具体", "保持悬疑节奏"])

    content, rules = _build_memory_candidate(scene, payload, "一些正文")

    assert "对白更克制" in content
    assert rules[:2] == ["对白更克制", "动作描写更具体"]


def test_build_memory_candidate_has_safe_fallback_without_guidance():
    scene = SimpleNamespace(title="雨夜仓库")
    payload = SimpleNamespace(guidance=[])

    content, rules = _build_memory_candidate(scene, payload, "一些正文")

    assert "雨夜仓库" in content
    assert any("中文小说正文" in rule for rule in rules)
