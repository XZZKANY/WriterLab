from types import SimpleNamespace

from app.models.character import Character
from app.models.location import Location
from app.services.consistency_service import _rule_issues


class _FakeQuery:
    def __init__(self, item):
        self.item = item

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.item


class _FakeDB:
    def __init__(self, location=None, character=None):
        self.location = location
        self.character = character

    def query(self, model):
        if model is Location:
            return _FakeQuery(self.location)
        if model is Character:
            return _FakeQuery(self.character)
        return _FakeQuery(None)


def test_rule_issues_detect_missing_and_forbidden_constraints():
    scene = SimpleNamespace(
        must_include=["amulet"],
        must_avoid=["pistol"],
        location_id="loc-1",
        time_label="dawn",
        pov_character_id=None,
    )
    location = SimpleNamespace(name="Clocktower")
    issues = _rule_issues(scene, "At dawn the hero hides a pistol.", _FakeDB(location), bundle={"recent_scenes": [], "timeline_events": []})
    issue_types = {item["issue_type"] for item in issues}
    assert "must_include_missing" in issue_types
    assert "must_avoid_violation" in issue_types
    assert "location_anchor" in issue_types


def test_rule_issues_detect_appearance_conflict():
    scene = SimpleNamespace(
        must_include=[],
        must_avoid=[],
        location_id=None,
        time_label=None,
        pov_character_id="char-1",
    )
    character = SimpleNamespace(name="林岚", appearance="蓝色眼睛，黑色长发")
    issues = _rule_issues(scene, "林岚抬起头，金色眼睛在昏光里一闪。", _FakeDB(character=character), bundle={"recent_scenes": [], "timeline_events": []})

    assert any(item["issue_type"] == "appearance_conflict" for item in issues)


def test_rule_issues_detect_timeline_conflict():
    scene = SimpleNamespace(
        must_include=[],
        must_avoid=[],
        location_id=None,
        time_label="清晨",
        pov_character_id=None,
    )
    bundle = {
        "recent_scenes": [{"time_label": "清晨"}],
        "timeline_events": [],
    }

    issues = _rule_issues(scene, "夜里风声贴着窗缝挤进来。", _FakeDB(), bundle=bundle)

    issue_types = {item["issue_type"] for item in issues}
    assert "time_label_missing" in issue_types
    assert "timeline_conflict" in issue_types
