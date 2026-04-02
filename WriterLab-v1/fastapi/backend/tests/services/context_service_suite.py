from types import SimpleNamespace
from uuid import UUID

from app.schemas.workflow import ContextCompileCandidate
from app.services import context_service


class _EmptyQuery:
    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return []

    def first(self):
        return None


class _FakeDB:
    def query(self, model):
        return _EmptyQuery()


def test_select_diverse_candidates_reserves_slot_per_source_type():
    candidates = [
        ContextCompileCandidate(source_id="l1", source_type="lore", scope="project", title="Lore", score=0.9, similarity=0.9, recency=0.3, importance=0.9, token_count=120, diversity_slot="lore"),
        ContextCompileCandidate(source_id="r1", source_type="recent_scene", scope="branch", title="Recent", score=0.8, similarity=0.8, recency=0.8, importance=0.7, token_count=120, diversity_slot="recent"),
        ContextCompileCandidate(source_id="s1", source_type="style_memory", scope="project", title="Style", score=0.7, similarity=0.7, recency=0.6, importance=0.8, token_count=120, diversity_slot="style"),
    ]

    selected, diversity_counts, clipped = context_service._select_diverse_candidates(candidates, limit=2)

    assert len(selected) == 2
    assert diversity_counts["lore"] == 1
    assert diversity_counts["recent"] == 1
    assert clipped == ["style_memory:s1"]


def test_build_scene_context_records_summary_and_scope_resolution(monkeypatch):
    scene = SimpleNamespace(
        id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        chapter_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        scene_no=4,
        title="Rain Scene",
        goal="Escape",
        conflict="Storm",
        outcome="Temporary shelter",
        must_include=["lantern"],
        must_avoid=["sermon"],
        draft_text="Rain hit the roof.",
        status="draft",
        time_label="night",
        pov_character_id=None,
        location_id=None,
    )
    branch_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    monkeypatch.setattr(context_service, "_resolve_project_id", lambda scene, db: UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"))
    monkeypatch.setattr(context_service, "_chapter_window", lambda scene, db: (SimpleNamespace(id=scene.chapter_id), SimpleNamespace(id=UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"))))
    monkeypatch.setattr(
        context_service,
        "_recent_scene_context",
        lambda scene, db, branch_id=None: [
            {"scene_id": "scene-1", "title": "Before", "scene_no": 3, "time_label": "dusk", "summary": "word " * 2100, "branch_id": str(branch_id)},
        ],
    )
    monkeypatch.setattr(context_service, "retrieve_knowledge", lambda *args, **kwargs: [])

    bundle = context_service.build_scene_context(scene, _FakeDB(), branch_id=branch_id)
    snapshot = bundle["context_compile_snapshot"]

    assert snapshot.summary_triggered is True
    assert snapshot.summary_reason == "recent_scenes_over_2000_tokens"
    assert snapshot.hard_filter_result["project_match"] is True
    assert snapshot.scope_resolution["recent_scenes"] == "branch"
    assert snapshot.source_diversity_applied["recent"] >= 1
    assert snapshot.summary_output[0]["action_line"] == "word " * 2100
