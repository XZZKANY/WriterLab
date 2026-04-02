from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.ai import router as ai_router
from app.api.branches import router as branches_router
from app.api.scenes import router as scenes_router
from app.db.session import get_db


def _fake_workflow_step(step_key: str, **overrides):
    now = datetime.utcnow()
    payload = {
        "id": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1"),
        "workflow_run_id": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa0"),
        "step_key": step_key,
        "step_order": 2,
        "schema_version": "workflow_step.v1",
        "version": 1,
        "attempt_no": 1,
        "parent_step_id": None,
        "invalidated_by_step": None,
        "status": "completed",
        "input_hash": "input-hash",
        "output_hash": "output-hash",
        "provider_mode": "smoke_fixture",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "profile_name": "fixture-plan-happy_path",
        "input_payload": {"scene_version": 2},
        "output_payload": {"attempts": [{"provider": "openai", "model": "gpt-4o-mini"}]},
        "machine_output_snapshot": {"draft": "machine"},
        "effective_output_snapshot": {"draft": "effective"},
        "attempts": [{"provider": "openai", "model": "gpt-4o-mini"}],
        "error_message": None,
        "fallback_used": False,
        "fallback_count": 0,
        "guardrail_blocked": False,
        "user_edited": False,
        "edited_at": None,
        "edited_reason": None,
        "prompt_tokens": 120,
        "completion_tokens": 180,
        "started_at": now,
        "finished_at": now,
        "duration_ms": 250,
        "latency_ms": 250,
        "created_at": now,
        "updated_at": now,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def _fake_workflow_run(**overrides):
    now = datetime.utcnow()
    payload = {
        "id": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa0"),
        "project_id": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2"),
        "scene_id": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3"),
        "branch_id": None,
        "run_type": "scene_pipeline",
        "status": "completed",
        "current_step": "done",
        "provider_mode": "smoke_fixture",
        "fixture_version": "v1",
        "fixture_scenario": "happy_path",
        "input_payload": {"scene_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3", "scene_version": 2},
        "output_payload": {"final_text": "Smoke output"},
        "error_message": None,
        "retry_count": 1,
        "worker_id": None,
        "queued_at": now,
        "heartbeat_at": now,
        "lease_expires_at": now,
        "cancel_requested_at": None,
        "cancelled_at": None,
        "started_at": now,
        "completed_at": now,
        "needs_merge": False,
        "quality_degraded": True,
        "resume_from_step": None,
        "context_compile_snapshot": {
            "schema_version": "context_compile_snapshot.v1",
            "project_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2",
            "branch_id": None,
            "chapter_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4",
            "scene_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3",
            "hard_filters": ["same_project", "same_branch"],
            "hard_filter_result": {"same_project": True, "same_branch": True},
            "candidates": [
                {
                    "source_id": "lore-1",
                    "source_type": "lore",
                    "scope": "project",
                    "title": "Lore Bible",
                    "score": 0.91,
                    "similarity": 0.9,
                    "recency": 0.8,
                    "importance": 0.95,
                    "token_count": 120,
                    "summary_applied": False,
                    "diversity_slot": "lore",
                }
            ],
            "budget": {"lore": 400, "recent_scenes": 300, "user_prompt": 250, "style_memory": 100},
            "summary_triggered": False,
            "summary_reason": None,
            "summary_output": [],
            "clipped_sources": [],
            "deduped_sources": [],
            "source_diversity_applied": {"lore": 1},
            "scope_resolution": {"project_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2", "branch_id": None},
        },
        "resume_checkpoint": "plan",
        "created_at": now,
        "updated_at": now,
        "steps": [],
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_scene_context_endpoint_returns_compile_snapshot(monkeypatch):
    app = FastAPI()
    app.include_router(scenes_router)

    scene_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    fake_scene = SimpleNamespace(id=scene_id, title="Smoke Scene 1", status="draft", draft_text="seed", scene_version=2)

    class _FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return fake_scene

    class _FakeDB:
        def query(self, model):
            return _FakeQuery()

    app.dependency_overrides[get_db] = lambda: _FakeDB()
    monkeypatch.setattr(
        "app.api.scenes.build_scene_context",
        lambda scene, db, branch_id=None: {
            "scene_summary": {"title": "Smoke Scene 1", "status": "draft", "draft_text": "seed"},
            "pov_character": None,
            "location": None,
            "timeline_events": [],
            "style_memories": [],
            "knowledge_hits": [],
            "recent_scenes": [],
            "context_compile_snapshot": {
                "schema_version": "context_compile_snapshot.v1",
                "project_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "branch_id": None,
                "chapter_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                "scene_id": str(scene_id),
                "hard_filters": ["same_project", "same_branch"],
                "hard_filter_result": {"same_project": True, "same_branch": True},
                "candidates": [
                    {
                        "source_id": "scene-1",
                        "source_type": "recent_scene",
                        "scope": "branch",
                        "title": "Scene Zero",
                        "score": 0.88,
                        "similarity": 0.87,
                        "recency": 0.82,
                        "importance": 0.9,
                        "token_count": 90,
                        "summary_applied": False,
                        "diversity_slot": "recent_scenes",
                    }
                ],
                "budget": {"recent_scenes": 300, "lore": 400, "user_prompt": 200, "style_memory": 100},
                "summary_triggered": True,
                "summary_reason": "recent scenes exceeded budget",
                "summary_output": [{"action_line": "Mira enters the station", "state_delta": "Rain intensifies"}],
                "clipped_sources": ["scene-clip-1"],
                "deduped_sources": ["scene-dup-1"],
                "source_diversity_applied": {"recent_scenes": 1},
                "scope_resolution": {"project_id": "cccccccc-cccc-cccc-cccc-cccccccccccc", "branch_id": None},
            },
        },
    )

    client = TestClient(app)
    response = client.get(f"/api/scenes/{scene_id}/context")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scene_version"] == 2
    assert payload["context_compile_snapshot"]["hard_filter_result"]["same_project"] is True
    assert payload["context_compile_snapshot"]["summary_reason"] == "recent scenes exceeded budget"
    assert payload["context_compile_snapshot"]["scope_resolution"]["project_id"] == "cccccccc-cccc-cccc-cccc-cccccccccccc"


def test_get_workflow_endpoint_returns_debug_fields(monkeypatch):
    app = FastAPI()
    app.include_router(ai_router)

    run = _fake_workflow_run()
    plan_step = _fake_workflow_step(
        "plan",
        step_order=2,
        version=3,
        attempt_no=3,
        machine_output_snapshot={"outline": "machine"},
        effective_output_snapshot={"outline": "effective"},
        output_payload={"attempts": [{"provider": "openai", "model": "gpt-4o-mini"}]},
    )
    invalidated_write = _fake_workflow_step(
        "write",
        step_order=3,
        version=4,
        attempt_no=4,
        status="invalidated",
        invalidated_by_step=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
        fallback_count=1,
    )

    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr("app.api.ai.get_workflow_run", lambda db, workflow_id: run)
    monkeypatch.setattr("app.api.ai.list_workflow_steps", lambda db, workflow_id: [plan_step, invalidated_write])

    client = TestClient(app)
    response = client.get(f"/api/ai/workflows/{run.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["resume_checkpoint"] == "plan"
    assert payload["provider_mode"] == "smoke_fixture"
    assert payload["fixture_version"] == "v1"
    assert payload["fixture_scenario"] == "happy_path"
    assert payload["quality_degraded"] is True
    assert payload["context_compile_snapshot"]["budget"]["lore"] == 400
    assert payload["steps"][0]["machine_output_snapshot"]["outline"] == "machine"
    assert payload["steps"][0]["provider_mode"] == "smoke_fixture"
    assert payload["steps"][0]["profile_name"] == "fixture-plan-happy_path"
    assert payload["steps"][1]["status"] == "invalidated"
    assert payload["steps"][1]["fallback_count"] == 1


def test_override_workflow_endpoint_returns_queued_resume(monkeypatch):
    app = FastAPI()
    app.include_router(ai_router)

    run = _fake_workflow_run(status="queued_resume", current_step="queued", resume_from_step="write")
    override_step = _fake_workflow_step(
        "plan",
        step_order=2,
        version=4,
        attempt_no=4,
        user_edited=True,
        edited_reason="Acceptance smoke planner override",
        effective_output_snapshot={"outline": "override"},
    )
    invalidated_write = _fake_workflow_step(
        "write",
        step_order=3,
        version=5,
        attempt_no=5,
        status="invalidated",
        invalidated_by_step=override_step.id,
    )

    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr("app.api.ai.get_workflow_run", lambda db, workflow_id: run)
    monkeypatch.setattr("app.api.ai.override_workflow_step", lambda db, run, step_key, payload: run)
    monkeypatch.setattr("app.api.ai.list_workflow_steps", lambda db, workflow_id: [override_step, invalidated_write])

    client = TestClient(app)
    response = client.post(
        f"/api/ai/workflows/{run.id}/steps/plan/override",
        json={
            "idempotency_key": "override-smoke-1",
            "expected_step_version": 3,
            "derived_from_version": 3,
            "edited_reason": "Acceptance smoke planner override",
            "effective_output_snapshot": {"outline": "override"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued_resume"
    assert payload["resume_from_step"] == "write"
    assert payload["steps"][0]["user_edited"] is True
    assert payload["steps"][1]["invalidated_by_step"] == str(override_step.id)


def test_create_branch_endpoint_returns_smoke_contract(monkeypatch):
    app = FastAPI()
    app.include_router(branches_router)

    branch_id = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
    project_id = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    scene_id = UUID("99999999-9999-9999-9999-999999999999")
    now = datetime.utcnow()
    fake_branch = SimpleNamespace(
        id=branch_id,
        project_id=project_id,
        name="smoke-branch-20260329-010000",
        description="Acceptance smoke branch",
        parent_branch_id=None,
        source_scene_id=scene_id,
        source_version_id=UUID("12121212-1212-1212-1212-121212121212"),
        latest_version_id=UUID("34343434-3434-3434-3434-343434343434"),
        status="active",
        metadata_json={"smoke": True},
        created_at=now,
        updated_at=now,
    )

    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr("app.api.branches.create_story_branch", lambda db, payload: fake_branch)
    monkeypatch.setattr(
        "app.api.branches._serialize_branch",
        lambda db, branch: {
            "id": branch.id,
            "project_id": branch.project_id,
            "name": branch.name,
            "description": branch.description,
            "parent_branch_id": branch.parent_branch_id,
            "source_scene_id": branch.source_scene_id,
            "source_chapter_id": UUID("56565656-5656-5656-5656-565656565656"),
            "source_version_id": branch.source_version_id,
            "latest_version_id": branch.latest_version_id,
            "latest_version_label": "smoke latest snapshot",
            "status": branch.status,
            "metadata_json": branch.metadata_json,
            "created_at": branch.created_at,
            "updated_at": branch.updated_at,
        },
    )

    client = TestClient(app)
    response = client.post(
        "/api/branches",
        json={
            "project_id": str(project_id),
            "name": "smoke-branch-20260329-010000",
            "description": "Acceptance smoke branch",
            "source_scene_id": str(scene_id),
            "source_version_id": "12121212-1212-1212-1212-121212121212",
            "latest_version_id": "34343434-3434-3434-3434-343434343434",
            "metadata_json": {"smoke": True},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "smoke-branch-20260329-010000"
    assert payload["latest_version_label"] == "smoke latest snapshot"
    assert payload["metadata_json"]["smoke"] is True
