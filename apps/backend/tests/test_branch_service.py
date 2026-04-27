from types import SimpleNamespace
from uuid import UUID

import pytest

from app.services.branch_service import build_line_diff, create_story_branch


def test_build_line_diff_marks_adds_and_removes():
    rows = build_line_diff("line1\nline2", "line1\nline3")
    assert rows[0]["type"] == "context"
    assert any(row["type"] == "remove" and row["text"] == "line2" for row in rows)
    assert any(row["type"] == "add" and row["text"] == "line3" for row in rows)


def test_create_story_branch_creates_snapshot_when_scene_has_no_versions(monkeypatch):
    project_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    scene_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    chapter_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    book_id = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
    snapshot_id = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")

    class _Query:
        def __init__(self, model):
            self.model = model

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def first(self):
            name = getattr(self.model, "__name__", "")
            if name == "Scene":
                return SimpleNamespace(id=scene_id, chapter_id=chapter_id, draft_text="Scene draft text")
            if name == "Chapter":
                return SimpleNamespace(id=chapter_id, book_id=book_id)
            if name == "Book":
                return SimpleNamespace(id=book_id, project_id=project_id)
            return None

    class _FakeDB:
        def query(self, model):
            return _Query(model)

        def add(self, row):
            return None

        def commit(self):
            return None

        def refresh(self, row):
            if getattr(row, "id", None) is None:
                row.id = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")

    snapshot_calls = []

    def _fake_create_scene_version(db, *, scene_id, content, source, label=None):
        snapshot_calls.append({"scene_id": scene_id, "content": content, "source": source, "label": label})
        return SimpleNamespace(id=snapshot_id)

    monkeypatch.setattr("app.services.branch_service.create_scene_version", _fake_create_scene_version)

    payload = SimpleNamespace(
        project_id=None,
        name="Dark Route",
        description=None,
        parent_branch_id=None,
        source_scene_id=scene_id,
        source_version_id=None,
        latest_version_id=None,
        metadata_json=None,
    )

    branch = create_story_branch(_FakeDB(), payload)

    assert snapshot_calls
    assert snapshot_calls[0]["scene_id"] == scene_id
    assert snapshot_calls[0]["source"] == "manual"
    assert branch.source_version_id == snapshot_id
    assert branch.latest_version_id == snapshot_id


def test_build_line_diff_returns_only_context_for_identical_text():
    rows = build_line_diff("a\nb\nc", "a\nb\nc")
    assert all(row["type"] == "context" for row in rows)
    assert [row["text"] for row in rows] == ["a", "b", "c"]


def test_build_line_diff_handles_empty_inputs():
    assert build_line_diff("", "") == []
    assert build_line_diff("", "added") == [{"type": "add", "text": "added"}]
    assert build_line_diff("removed", "") == [{"type": "remove", "text": "removed"}]


def test_build_line_diff_extra_lines_at_tail_become_add_or_remove():
    rows = build_line_diff("a\nb", "a\nb\nc\nd")
    types = [row["type"] for row in rows]
    assert types == ["context", "context", "add", "add"]
    assert [row["text"] for row in rows][2:] == ["c", "d"]


def test_create_story_branch_raises_when_project_cannot_be_resolved():
    """既无 project_id 又无 source_scene_id 时 _resolve_project_id 返回 None。"""

    class _NullQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return None

    class _FakeDB:
        def query(self, model):
            return _NullQuery()

    payload = SimpleNamespace(
        project_id=None,
        source_scene_id=None,
        name="x",
        description=None,
        parent_branch_id=None,
        source_version_id=None,
        latest_version_id=None,
        metadata_json=None,
    )

    with pytest.raises(ValueError, match="Project not found for branch"):
        create_story_branch(_FakeDB(), payload)


def test_create_story_branch_raises_when_source_scene_missing():
    project_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    scene_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

    class _NullQuery:
        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def first(self):
            return None

    class _FakeDB:
        def query(self, model):
            return _NullQuery()

    payload = SimpleNamespace(
        project_id=project_id,
        source_scene_id=scene_id,
        name="x",
        description=None,
        parent_branch_id=None,
        source_version_id=None,
        latest_version_id=None,
        metadata_json=None,
    )

    with pytest.raises(ValueError, match="Source scene not found"):
        create_story_branch(_FakeDB(), payload)
