"""ai_run_service 直测。

`save_ai_run` 是 ai_runs 表的写入入口。逻辑很简单：构造 AIRun ORM 行 +
db.add + db.commit。这里用 RecordingDB 验证 jsonable_encoder 对 None 与
真实 dict 的不同处理，以及所有字段被原样落入。
"""

from types import SimpleNamespace
from uuid import UUID

from app.services import ai_run_service


class _RecordingDB:
    def __init__(self):
        self.added: list = []
        self.commits = 0

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1


def _base_kwargs():
    return {
        "run_id": UUID("11111111-1111-1111-1111-111111111111"),
        "scene_id": UUID("22222222-2222-2222-2222-222222222222"),
        "run_type": "analyze",
        "model": "deepseek-chat",
        "input_payload": {"prompt": "hi"},
        "raw_response": "raw text",
        "parsed_response": {"summary": "s"},
        "status": "success",
        "error_message": None,
        "latency_ms": 123,
    }


def test_save_ai_run_writes_minimum_required_fields():
    db = _RecordingDB()
    ai_run_service.save_ai_run(db, **_base_kwargs())
    assert len(db.added) == 1
    assert db.commits == 1
    row = db.added[0]
    assert row.id == UUID("11111111-1111-1111-1111-111111111111")
    assert row.scene_id == UUID("22222222-2222-2222-2222-222222222222")
    assert row.run_type == "analyze"
    assert row.model == "deepseek-chat"
    assert row.raw_response == "raw text"
    assert row.status == "success"
    assert row.error_message is None
    assert row.latency_ms == 123
    # input_payload 与 parsed_response 经过 jsonable_encoder
    assert row.input_payload == {"prompt": "hi"}
    assert row.parsed_response == {"summary": "s"}


def test_save_ai_run_passes_through_optional_fields():
    db = _RecordingDB()
    project_id = UUID("33333333-3333-3333-3333-333333333333")
    kwargs = _base_kwargs()
    kwargs.update(
        task_type="analyze",
        provider="deepseek",
        prompt_version="analyze-scene.v5",
        fallback_used=False,
        token_usage={"prompt_tokens": 10, "completion_tokens": 20},
        project_id=project_id,
    )
    ai_run_service.save_ai_run(db, **kwargs)
    row = db.added[0]
    assert row.task_type == "analyze"
    assert row.provider == "deepseek"
    assert row.prompt_version == "analyze-scene.v5"
    assert row.fallback_used is False
    assert row.token_usage == {"prompt_tokens": 10, "completion_tokens": 20}
    assert row.project_id == project_id


def test_save_ai_run_handles_none_parsed_response():
    """parsed_response=None 应保留为 None（不被 jsonable_encoder 转成 'null' 字符串）。"""
    db = _RecordingDB()
    kwargs = _base_kwargs()
    kwargs["parsed_response"] = None
    ai_run_service.save_ai_run(db, **kwargs)
    assert db.added[0].parsed_response is None


def test_save_ai_run_handles_none_token_usage():
    db = _RecordingDB()
    kwargs = _base_kwargs()
    kwargs["token_usage"] = None
    ai_run_service.save_ai_run(db, **kwargs)
    assert db.added[0].token_usage is None


def test_save_ai_run_records_failure_status_with_error_message():
    db = _RecordingDB()
    kwargs = _base_kwargs()
    kwargs.update(
        status="failed",
        error_message="model timed out",
        raw_response=None,
        parsed_response=None,
    )
    ai_run_service.save_ai_run(db, **kwargs)
    row = db.added[0]
    assert row.status == "failed"
    assert row.error_message == "model timed out"
    assert row.raw_response is None
    assert row.parsed_response is None


def test_save_ai_run_with_no_scene_id_supports_orphan_runs():
    """有些 AI 调用未必绑定 scene（例如 provider 健康探测）；scene_id=None 应可接受。"""
    db = _RecordingDB()
    kwargs = _base_kwargs()
    kwargs["scene_id"] = None
    ai_run_service.save_ai_run(db, **kwargs)
    assert db.added[0].scene_id is None


def test_save_ai_run_input_payload_is_serialized_via_jsonable_encoder():
    """jsonable_encoder 会把 datetime / UUID 等转成可 JSON 的形式。"""
    import datetime

    db = _RecordingDB()
    kwargs = _base_kwargs()
    kwargs["input_payload"] = {
        "prompt": "x",
        "started_at": datetime.datetime(2025, 1, 1, 12, 0, 0),
        "scene_uuid": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
    }
    ai_run_service.save_ai_run(db, **kwargs)
    payload = db.added[0].input_payload
    # datetime 应被序列化为 ISO 字符串
    assert isinstance(payload["started_at"], str)
    assert "2025-01-01" in payload["started_at"]
    # UUID 应被序列化为字符串
    assert payload["scene_uuid"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
