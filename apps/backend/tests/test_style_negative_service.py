from types import SimpleNamespace
from uuid import UUID

from app.schemas.workflow import StyleNegativeRule
from app.services import style_negative_service as service


def test_match_style_negative_rules_supports_hard_and_soft_modes():
    rules = [
        StyleNegativeRule(label="hard-ban", severity="hard", match_mode="exact", pattern="forbidden"),
        StyleNegativeRule(label="soft-tone", severity="soft", match_mode="tag", pattern="explainy"),
        StyleNegativeRule(label="regex-ban", severity="hard", match_mode="regex", pattern=r"purple\s+prose"),
    ]

    matches = service.match_style_negative_rules("This is forbidden and a little explainy, but not purple prose.", rules)

    assert [item.label for item in matches] == ["hard-ban", "soft-tone", "regex-ban"]
    assert matches[0].severity == "hard"
    assert matches[1].severity == "soft"


def test_resolve_style_negative_rules_includes_scene_must_avoid(monkeypatch):
    scene = SimpleNamespace(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        must_avoid=["lecture tone", "moralizing"],
    )
    monkeypatch.setattr(service, "list_active_style_negative_rules", lambda db, project_id=None, branch_id=None: [])

    rules = service.resolve_style_negative_rules(object(), scene=scene, project_id=None, branch_id=None)

    assert [item.label for item in rules] == ["scene:lecture tone", "scene:moralizing"]
    assert all(item.severity == "hard" for item in rules)


def test_match_style_negative_rules_skips_inactive_rules():
    rules = [
        StyleNegativeRule(label="off", severity="hard", match_mode="exact", pattern="banned", active=False),
        StyleNegativeRule(label="on", severity="hard", match_mode="exact", pattern="banned", active=True),
    ]
    matches = service.match_style_negative_rules("the banned word appears", rules)
    assert [item.label for item in matches] == ["on"]


def test_match_style_negative_rules_handles_empty_or_none_text():
    rules = [StyleNegativeRule(label="x", severity="hard", match_mode="exact", pattern="bad")]
    assert service.match_style_negative_rules("", rules) == []
    assert service.match_style_negative_rules(None, rules) == []


def test_match_style_negative_rules_exact_mode_is_case_insensitive():
    rules = [StyleNegativeRule(label="case", severity="hard", match_mode="exact", pattern="Banned")]
    matches = service.match_style_negative_rules("BANNED items detected", rules)
    assert len(matches) == 1
    assert matches[0].matched_text == "Banned"


def test_match_style_negative_rules_regex_returns_actual_match_text():
    rules = [StyleNegativeRule(label="r", severity="hard", match_mode="regex", pattern=r"d\w+s")]
    matches = service.match_style_negative_rules("She runs and dodges effortlessly.", rules)
    assert len(matches) == 1
    assert matches[0].matched_text == "dodges"


def test_match_style_negative_rules_vector_mode_treated_as_substring():
    rules = [StyleNegativeRule(label="v", severity="soft", match_mode="vector", pattern="dramatic flair")]
    matches = service.match_style_negative_rules("with dramatic flair indeed", rules)
    assert [item.match_mode for item in matches] == ["vector"]


def test_match_style_negative_rules_synthetic_rule_id_prefix_for_id_none():
    rules = [
        StyleNegativeRule(label="synth", severity="hard", match_mode="exact", pattern="bad"),
    ]
    matches = service.match_style_negative_rules("a bad result", rules)
    assert matches[0].rule_id == "synthetic:synth"


def test_synthetic_scene_rules_skips_blank_must_avoid_entries():
    scene = SimpleNamespace(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        must_avoid=["", "   ", "actual"],
    )
    rules = service._synthetic_scene_rules(scene)
    assert [item.label for item in rules] == ["scene:actual"]


def test_synthetic_scene_rules_truncates_long_label_to_40_chars():
    scene = SimpleNamespace(
        id=UUID("33333333-3333-3333-3333-333333333333"),
        must_avoid=["x" * 200],
    )
    rules = service._synthetic_scene_rules(scene)
    # label = "scene:" + text[:40]
    assert rules[0].label == "scene:" + "x" * 40
