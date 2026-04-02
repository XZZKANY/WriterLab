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
