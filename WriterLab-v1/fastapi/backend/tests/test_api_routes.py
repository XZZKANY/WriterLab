from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.ai import router as ai_router
from app.api.branches import router as branches_router
from app.api.knowledge import router as knowledge_router
from app.api.settings import router as settings_router
from app.api.vn import router as vn_router
from app.db.session import get_db


def test_vn_export_endpoint():
    app = FastAPI()
    app.include_router(vn_router)
    client = TestClient(app)

    response = client.post(
        "/api/vn/export",
        json={"draft_text": "Mira: Hello there.\nThe sun is setting.", "scene_title": "Sunset"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Sunset"
    assert len(payload["lines"]) == 2


def test_branch_diff_endpoint(monkeypatch):
    app = FastAPI()
    app.include_router(branches_router)

    class _BranchQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return SimpleNamespace(
                id="00000000-0000-0000-0000-000000000001",
                name="Dark Route",
                source_scene_id="00000000-0000-0000-0000-000000000010",
                source_version_id="00000000-0000-0000-0000-000000000002",
                latest_version_id="00000000-0000-0000-0000-000000000003",
            )

    class _FakeDB:
        def query(self, model):
            return _BranchQuery()

    app.dependency_overrides[get_db] = lambda: _FakeDB()

    monkeypatch.setattr(
        "app.api.branches.get_branch_diff",
        lambda db, branch: ("old text", "new text", [{"type": "add", "text": "new text"}]),
    )
    monkeypatch.setattr("app.api.branches.get_branch_source_chapter_id", lambda db, branch: "00000000-0000-0000-0000-000000000020")
    monkeypatch.setattr("app.api.branches._version_label", lambda db, version_id: "snapshot")

    client = TestClient(app)
    response = client.get("/api/branches/00000000-0000-0000-0000-000000000001/diff")

    assert response.status_code == 200
    payload = response.json()
    assert payload["branch_name"] == "Dark Route"
    assert payload["base_text"] == "old text"
    assert payload["source_text"] == "old text"
    assert payload["branch_text"] == "new text"
    assert payload["diff_rows"][0]["type"] == "add"


def test_branch_list_endpoint(monkeypatch):
    app = FastAPI()
    app.include_router(branches_router)

    project_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    now = datetime.utcnow()

    class _ProjectQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return SimpleNamespace(id=project_id)

    class _FakeDB:
        def query(self, model):
            return _ProjectQuery()

    app.dependency_overrides[get_db] = lambda: _FakeDB()
    monkeypatch.setattr(
        "app.api.branches.list_story_branches",
        lambda db, project_id, source_scene_id=None: [
            SimpleNamespace(
                id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
                project_id=project_id,
                name="Dark Route",
                description="Branch draft",
                parent_branch_id=None,
                source_scene_id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
                source_version_id=None,
                latest_version_id=None,
                status="active",
                metadata_json=None,
                created_at=now,
                updated_at=now,
            )
        ],
    )
    monkeypatch.setattr("app.api.branches.get_branch_source_chapter_id", lambda db, branch: UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"))
    monkeypatch.setattr("app.api.branches._version_label", lambda db, version_id: "branch snapshot")

    client = TestClient(app)
    response = client.get(f"/api/branches?project_id={project_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["name"] == "Dark Route"
    assert payload[0]["source_chapter_id"] == "dddddddd-dddd-dddd-dddd-dddddddddddd"
    assert payload[0]["latest_version_label"] == "branch snapshot"


def test_branch_adopt_endpoint(monkeypatch):
    app = FastAPI()
    app.include_router(branches_router)

    branch_id = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
    scene_id = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
    now = datetime.utcnow()

    class _BranchQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return SimpleNamespace(id=branch_id, name="Dark Route")

    class _FakeDB:
        def query(self, model):
            return _BranchQuery()

    app.dependency_overrides[get_db] = lambda: _FakeDB()
    monkeypatch.setattr(
        "app.api.branches.adopt_story_branch",
        lambda db, branch: (
            SimpleNamespace(id=scene_id, draft_text="Adopted text"),
            SimpleNamespace(id=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")),
        ),
    )

    client = TestClient(app)
    response = client.post(f"/api/branches/{branch_id}/adopt")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scene_id"] == str(scene_id)
    assert payload["current_text"] == "Adopted text"
    assert payload["adopted_version_id"] == "ffffffff-ffff-ffff-ffff-ffffffffffff"


def test_knowledge_search_endpoint_reports_retrieval_reason(monkeypatch):
    app = FastAPI()
    app.include_router(knowledge_router)

    project_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    class _Query:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return SimpleNamespace(id=project_id)

    class _FakeDB:
        def query(self, model):
            return _Query()

    app.dependency_overrides[get_db] = lambda: _FakeDB()
    monkeypatch.setattr(
        "app.api.knowledge.retrieve_knowledge_with_status",
        lambda *args, **kwargs: (
            [],
            {
                "mode": "fallback",
                "reason": "pgvector extension files are not installed on this PostgreSQL instance",
                "pgvector_ready": False,
            },
        ),
    )

    client = TestClient(app)
    response = client.get(f"/api/knowledge/search?project_id={project_id}&query=dragon")

    assert response.status_code == 200
    payload = response.json()
    assert payload["retrieval_mode"] == "fallback"
    assert "pgvector" in payload["retrieval_reason"]
    assert payload["pgvector_ready"] is False


def test_scene_workflow_async_endpoint(monkeypatch):
    app = FastAPI()
    app.include_router(ai_router)

    scene_id = UUID("b816b1bd-96b8-486e-a56b-4a26b396b562")
    now = datetime.utcnow()
    fake_run = SimpleNamespace(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        project_id=None,
        scene_id=scene_id,
        branch_id=None,
        run_type="scene_pipeline",
        status="queued",
        current_step="queued",
        input_payload={"scene_id": str(scene_id)},
        output_payload=None,
        error_message=None,
        retry_count=0,
        queued_at=now,
        heartbeat_at=None,
        lease_expires_at=None,
        cancel_requested_at=None,
        cancelled_at=None,
        started_at=None,
        completed_at=None,
        created_at=now,
        updated_at=now,
        steps=[],
    )

    class _FakeQuery:
        def __init__(self, result):
            self.result = result

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.result

    class _FakeDB:
        def query(self, model):
            return _FakeQuery(SimpleNamespace(id=scene_id))

    app.dependency_overrides[get_db] = lambda: _FakeDB()
    monkeypatch.setattr("app.api.ai.queue_scene_workflow", lambda db, scene, payload: fake_run)
    monkeypatch.setattr("app.api.ai.list_workflow_steps", lambda db, workflow_id: [])

    client = TestClient(app)
    response = client.post(
        "/api/ai/workflows/scene",
        json={"scene_id": str(scene_id), "length": "medium", "guidance": [], "auto_apply": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["current_step"] == "queued"
    assert payload["queued_at"] is not None


def test_scene_workflow_sync_endpoint(monkeypatch):
    app = FastAPI()
    app.include_router(ai_router)

    scene_id = UUID("b816b1bd-96b8-486e-a56b-4a26b396b562")
    now = datetime.utcnow()
    fake_run = SimpleNamespace(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        project_id=None,
        scene_id=scene_id,
        branch_id=None,
        run_type="scene_pipeline",
        status="partial_success",
        current_step="done",
        input_payload={"scene_id": str(scene_id)},
        output_payload={"final_text": "generated", "partial_text": "generated", "error_summary": "style: timeout"},
        error_message="style: timeout",
        retry_count=0,
        queued_at=now,
        heartbeat_at=now,
        lease_expires_at=now,
        cancel_requested_at=None,
        cancelled_at=None,
        started_at=now,
        completed_at=now,
        created_at=now,
        updated_at=now,
        steps=[],
    )

    class _FakeQuery:
        def __init__(self, result):
            self.result = result

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.result

    class _FakeDB:
        def query(self, model):
            return _FakeQuery(SimpleNamespace(id=scene_id))

    app.dependency_overrides[get_db] = lambda: _FakeDB()
    monkeypatch.setattr("app.api.ai.execute_scene_workflow", lambda db, scene, payload: fake_run)
    monkeypatch.setattr("app.api.ai.list_workflow_steps", lambda db, workflow_id: [])

    client = TestClient(app)
    response = client.post(
        "/api/ai/workflows/scene/run-sync",
        json={"scene_id": str(scene_id), "length": "medium", "guidance": [], "auto_apply": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "partial_success"
    assert payload["output_payload"]["partial_text"] == "generated"


def test_scene_workflow_retry_endpoint(monkeypatch):
    app = FastAPI()
    app.include_router(ai_router)

    workflow_id = UUID("33333333-3333-3333-3333-333333333333")
    now = datetime.utcnow()
    fake_run = SimpleNamespace(
        id=workflow_id,
        project_id=None,
        scene_id=None,
        branch_id=None,
        run_type="scene_pipeline",
        status="queued",
        current_step="queued",
        input_payload={},
        output_payload=None,
        error_message=None,
        retry_count=1,
        queued_at=now,
        heartbeat_at=None,
        lease_expires_at=None,
        cancel_requested_at=None,
        cancelled_at=None,
        started_at=None,
        completed_at=None,
        created_at=now,
        updated_at=now,
        steps=[],
    )

    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr("app.api.ai.get_workflow_run", lambda db, workflow_id: fake_run)
    monkeypatch.setattr("app.api.ai.retry_workflow_run", lambda db, run: fake_run)
    monkeypatch.setattr("app.api.ai.list_workflow_steps", lambda db, workflow_id: [])

    client = TestClient(app)
    response = client.post(f"/api/ai/workflows/{workflow_id}/retry")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["retry_count"] == 1


def test_scene_workflow_cancel_endpoint(monkeypatch):
    app = FastAPI()
    app.include_router(ai_router)

    workflow_id = UUID("44444444-4444-4444-4444-444444444444")
    now = datetime.utcnow()
    fake_run = SimpleNamespace(
        id=workflow_id,
        project_id=None,
        scene_id=None,
        branch_id=None,
        run_type="scene_pipeline",
        status="cancelled",
        current_step="cancelled",
        input_payload={},
        output_payload={"cancelled": True},
        error_message="Workflow cancelled by user",
        retry_count=0,
        queued_at=now,
        heartbeat_at=None,
        lease_expires_at=None,
        cancel_requested_at=now,
        cancelled_at=now,
        started_at=now,
        completed_at=now,
        created_at=now,
        updated_at=now,
        steps=[],
    )

    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr("app.api.ai.get_workflow_run", lambda db, workflow_id: fake_run)
    monkeypatch.setattr("app.api.ai.cancel_workflow_run", lambda db, run: fake_run)
    monkeypatch.setattr("app.api.ai.list_workflow_steps", lambda db, workflow_id: [])

    client = TestClient(app)
    response = client.post(f"/api/ai/workflows/{workflow_id}/cancel")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "cancelled"
    assert payload["cancelled_at"] is not None


def test_knowledge_search_endpoint(monkeypatch):
    app = FastAPI()
    app.include_router(knowledge_router)

    project_id = UUID("55555555-5555-5555-5555-555555555555")

    class _FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return SimpleNamespace(id=project_id)

    class _FakeDB:
        def query(self, model):
            return _FakeQuery()

    app.dependency_overrides[get_db] = lambda: _FakeDB()
    monkeypatch.setattr(
        "app.api.knowledge.retrieve_knowledge_with_status",
        lambda db, project_id, query, top_k, source_kinds: (
            [
                {
                    "chunk_id": "66666666-6666-6666-6666-666666666666",
                    "document_id": "77777777-7777-7777-7777-777777777777",
                    "document_title": "Lore Bible",
                    "document_type": "lore",
                    "memory_class": "canonical_lore",
                    "source_label": "Lore Bible",
                    "confirmed": True,
                    "score": 0.88,
                    "content": "The capital is Azure.",
                    "source_kind": "lore",
                    "citation": "lore:Lore Bible",
                    "metadata_json": {"memory_class": "canonical_lore"},
                }
            ],
            {"mode": "pgvector", "reason": "pgvector is active", "pgvector_ready": True},
        ),
    )

    client = TestClient(app)
    response = client.get(f"/api/knowledge/search?project_id={project_id}&query=capital&top_k=3")

    assert response.status_code == 200
    payload = response.json()
    assert payload["retrieval_mode"] == "pgvector"
    assert payload["retrieval_reason"] == "pgvector is active"
    assert payload["hits"][0]["memory_class"] == "canonical_lore"


def test_confirm_style_memory_endpoint(monkeypatch):
    app = FastAPI()
    app.include_router(knowledge_router)

    memory_id = UUID("88888888-8888-8888-8888-888888888888")
    now = datetime.utcnow()
    fake_memory = SimpleNamespace(
        id=memory_id,
        project_id=UUID("99999999-9999-9999-9999-999999999999"),
        scene_id=None,
        memory_type="style_rule",
        content="Use restrained inner monologue.",
        source_excerpt=None,
        derived_rules=["avoid overexplaining"],
        user_confirmed=True,
        status="confirmed",
        created_at=now,
        updated_at=now,
    )

    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr("app.api.knowledge.confirm_style_memory", lambda db, memory_id, user_confirmed, status: fake_memory)

    client = TestClient(app)
    response = client.post(f"/api/knowledge/style-memories/{memory_id}/confirm", json={"user_confirmed": True, "status": "confirmed"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_confirmed"] is True
    assert payload["status"] == "confirmed"


def test_get_provider_settings_endpoint(monkeypatch):
    app = FastAPI()
    app.include_router(settings_router)

    monkeypatch.setattr(
        "app.api.settings.get_provider_settings_response",
        lambda: [
            {"provider": "openai", "api_base": "https://api.openai.com/v1", "has_api_key": True, "api_key_masked": "sk-****"},
            {"provider": "deepseek", "api_base": "https://api.deepseek.com/v1", "has_api_key": False, "api_key_masked": None},
            {"provider": "xai", "api_base": "https://api.x.ai/v1", "has_api_key": False, "api_key_masked": None},
        ],
    )

    client = TestClient(app)
    response = client.get("/api/settings/providers")

    assert response.status_code == 200
    payload = response.json()
    assert payload["providers"][0]["provider"] == "openai"
    assert payload["providers"][0]["has_api_key"] is True


def test_update_provider_settings_endpoint(monkeypatch):
    app = FastAPI()
    app.include_router(settings_router)

    monkeypatch.setattr(
        "app.api.settings.save_provider_settings",
        lambda payload: {
            "openai": {"provider": "openai", "api_key": "sk-test", "api_base": "https://api.openai.com/v1"},
            "deepseek": {"provider": "deepseek", "api_key": "", "api_base": "https://api.deepseek.com/v1"},
            "xai": {"provider": "xai", "api_key": "", "api_base": "https://api.x.ai/v1"},
        },
    )
    monkeypatch.setattr(
        "app.api.settings.get_provider_settings_response",
        lambda: [
            {"provider": "openai", "api_base": "https://api.openai.com/v1", "has_api_key": True, "api_key_masked": "sk-****"},
            {"provider": "deepseek", "api_base": "https://api.deepseek.com/v1", "has_api_key": False, "api_key_masked": None},
            {"provider": "xai", "api_base": "https://api.x.ai/v1", "has_api_key": False, "api_key_masked": None},
        ],
    )

    client = TestClient(app)
    response = client.put(
        "/api/settings/providers",
        json={"openai": {"api_key": "sk-test", "api_base": "https://api.openai.com/v1"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "API 配置已保存"
    assert "openai" in payload["saved_providers"]
