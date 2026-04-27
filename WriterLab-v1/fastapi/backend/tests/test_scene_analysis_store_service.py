"""scene_analysis_store_service 直测。

用 FakeQuery / FakeDB 隔离真实数据库。聚焦：
- create_scene_analysis_record 是否正确把 problems / suggestions 拍平为 items
- set_selected_analysis_items 的"重设 is_selected"语义
- get_selected_guidance_for_scene 在 analysis_id 显式 / 缺省时的分支
- 公开查询函数（get / list / items）的查询链路代理
"""

from types import SimpleNamespace
from uuid import UUID

from app.schemas.scene_analysis import SceneAnalysisResult, SceneProblem
from app.services import scene_analysis_store_service as store


# ---------- 辅助：可控的 fake DB ----------

class _Query:
    def __init__(self, items):
        self._items = list(items)

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._items[0] if self._items else None

    def limit(self, n):
        return _Query(self._items[:n])

    def all(self):
        return list(self._items)


class _RecordingDB:
    """按模型类型分别存放预备数据 + 记录所有 add 调用。"""

    def __init__(self, by_model: dict | None = None):
        self._by_model = by_model or {}
        self.added: list = []
        self.commits = 0

    def query(self, model):
        # 简化：根据模型 __name__ 路由到预备列表
        name = getattr(model, "__name__", "")
        return _Query(self._by_model.get(name, []))

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        if not getattr(obj, "id", None):
            obj.id = UUID("11111111-1111-1111-1111-111111111111")


# ---------- create_scene_analysis_record ----------

def test_create_scene_analysis_record_flattens_problems_and_suggestions():
    scene = SimpleNamespace(id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
    result = SceneAnalysisResult(
        summary="主线推进",
        scene_goal_detected="dummy",
        emotional_flow=["紧张"],
        problems=[
            SceneProblem(type="logic", severity="medium", message="问题 1"),
            SceneProblem(type="pacing", severity="high", message="问题 2"),
        ],
        suggestions=["建议 A", "建议 B"],
    )
    db = _RecordingDB()
    analysis = store.create_scene_analysis_record(
        db,
        scene=scene,
        result=result,
        ai_run_id=UUID("22222222-2222-2222-2222-222222222222"),
        project_id=UUID("33333333-3333-3333-3333-333333333333"),
    )
    # add 顺序：1 个 SceneAnalysis + 2 个 problem item + 2 个 suggestion item
    assert len(db.added) == 5
    assert db.commits == 2  # 一次主记录 + 一次批量 items
    # SceneAnalysis 字段正确
    assert analysis.scene_id == scene.id
    assert analysis.summary == "主线推进"
    assert analysis.analysis_type == "scene"
    assert analysis.status == "success"
    assert analysis.ai_run_id == UUID("22222222-2222-2222-2222-222222222222")
    assert analysis.project_id == UUID("33333333-3333-3333-3333-333333333333")

    items = db.added[1:]
    problem_items = [it for it in items if it.item_type == "problem"]
    suggestion_items = [it for it in items if it.item_type == "suggestion"]
    assert len(problem_items) == 2
    assert len(suggestion_items) == 2
    # 问题项保留 type / severity / message
    assert problem_items[0].title == "logic"
    assert problem_items[0].severity == "medium"
    assert problem_items[0].content == "问题 1"
    assert problem_items[0].metadata_json == {"problem_type": "logic"}
    assert problem_items[0].is_selected is False
    # 建议项无 severity，title 固定
    assert suggestion_items[0].title == "建议"
    assert suggestion_items[0].severity is None
    assert suggestion_items[0].content == "建议 A"
    assert suggestion_items[0].metadata_json is None
    # sort_order 全局递增
    sort_orders = [it.sort_order for it in items]
    assert sort_orders == [1, 2, 3, 4]


def test_create_scene_analysis_record_links_latest_scene_version():
    """如果 scene 已有 version，analysis.version_id 应被关联。"""
    scene = SimpleNamespace(id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
    result = SceneAnalysisResult(summary="s", emotional_flow=[], problems=[], suggestions=[])
    latest_version = SimpleNamespace(id=UUID("55555555-5555-5555-5555-555555555555"))
    db = _RecordingDB(by_model={"SceneVersion": [latest_version]})
    analysis = store.create_scene_analysis_record(
        db, scene=scene, result=result, ai_run_id=None,
    )
    assert analysis.version_id == latest_version.id


def test_create_scene_analysis_record_handles_no_scene_version():
    scene = SimpleNamespace(id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
    result = SceneAnalysisResult(summary="s", emotional_flow=[], problems=[], suggestions=[])
    db = _RecordingDB()  # SceneVersion 列表空
    analysis = store.create_scene_analysis_record(
        db, scene=scene, result=result, ai_run_id=None,
    )
    assert analysis.version_id is None


def test_create_scene_analysis_record_status_can_be_overridden():
    scene = SimpleNamespace(id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
    result = SceneAnalysisResult(summary="s", emotional_flow=[], problems=[], suggestions=[])
    db = _RecordingDB()
    analysis = store.create_scene_analysis_record(
        db, scene=scene, result=result, ai_run_id=None, status="failed",
    )
    assert analysis.status == "failed"


# ---------- list / get / get_analysis_items ----------

def test_list_scene_analyses_returns_query_with_limit():
    """简单确认查询链路被代理。"""
    items = [SimpleNamespace(id=i) for i in range(5)]
    db = _RecordingDB(by_model={"SceneAnalysis": items})
    out = store.list_scene_analyses(db, "scene-1", limit=3)
    assert [a.id for a in out] == [0, 1, 2]


def test_get_scene_analysis_returns_first():
    target = SimpleNamespace(id=UUID("99999999-9999-9999-9999-999999999999"))
    db = _RecordingDB(by_model={"SceneAnalysis": [target]})
    assert store.get_scene_analysis(db, target.id) is target


def test_get_analysis_items_returns_all_in_order():
    items = [SimpleNamespace(sort_order=i, id=i) for i in range(3)]
    db = _RecordingDB(by_model={"SceneAnalysisItem": items})
    out = store.get_analysis_items(db, "analysis-1")
    assert len(out) == 3


# ---------- set_selected_analysis_items ----------

def test_set_selected_analysis_items_marks_only_selected_ids():
    """传入的 id 集合内的 item 标 is_selected=True；其余标 False。"""
    items = [
        SimpleNamespace(id=UUID("a1111111-1111-1111-1111-111111111111"), is_selected=True),
        SimpleNamespace(id=UUID("a2222222-2222-2222-2222-222222222222"), is_selected=False),
        SimpleNamespace(id=UUID("a3333333-3333-3333-3333-333333333333"), is_selected=True),
    ]
    db = _RecordingDB(by_model={"SceneAnalysisItem": items})
    store.set_selected_analysis_items(
        db,
        "analysis-1",
        [UUID("a2222222-2222-2222-2222-222222222222")],
    )
    # 只有第二个被标 True
    assert items[0].is_selected is False
    assert items[1].is_selected is True
    assert items[2].is_selected is False
    # 三个 item 都被 add 一次
    assert len(db.added) == 3
    assert db.commits == 1


def test_set_selected_analysis_items_clears_all_when_empty_list():
    items = [
        SimpleNamespace(id="a", is_selected=True),
        SimpleNamespace(id="b", is_selected=True),
    ]
    db = _RecordingDB(by_model={"SceneAnalysisItem": items})
    store.set_selected_analysis_items(db, "analysis-1", [])
    assert all(item.is_selected is False for item in items)


# ---------- get_selected_guidance_for_scene ----------

def test_get_selected_guidance_returns_empty_when_no_analysis():
    db = _RecordingDB()
    guidance, analysis = store.get_selected_guidance_for_scene(db, "scene-1")
    assert guidance == []
    assert analysis is None


def test_get_selected_guidance_uses_specific_analysis_when_id_given():
    target = SimpleNamespace(id=UUID("99999999-9999-9999-9999-999999999999"), scene_id="x")
    selected_item = SimpleNamespace(content="选中的指引", sort_order=0)
    db = _RecordingDB(
        by_model={
            "SceneAnalysis": [target],
            "SceneAnalysisItem": [selected_item],
        }
    )
    guidance, analysis = store.get_selected_guidance_for_scene(
        db,
        scene_id="不重要",
        analysis_id=UUID("99999999-9999-9999-9999-999999999999"),
    )
    assert analysis is target
    assert guidance == ["选中的指引"]


def test_get_selected_guidance_falls_back_to_latest_analysis():
    """analysis_id 缺省时，应取该 scene 最新一条 analysis。"""
    latest = SimpleNamespace(id=UUID("99999999-9999-9999-9999-999999999999"), scene_id="x")
    selected_item = SimpleNamespace(content="选中", sort_order=0)
    db = _RecordingDB(
        by_model={
            "SceneAnalysis": [latest],
            "SceneAnalysisItem": [selected_item],
        }
    )
    guidance, analysis = store.get_selected_guidance_for_scene(db, "x")
    assert analysis is latest
    assert guidance == ["选中"]


# ---------- to_scene_analysis_response ----------

def test_to_scene_analysis_response_packs_analysis_and_items():
    analysis = SimpleNamespace(
        id=UUID("99999999-9999-9999-9999-999999999999"),
        project_id=UUID("11111111-1111-1111-1111-111111111111"),
        scene_id=UUID("22222222-2222-2222-2222-222222222222"),
        version_id=None,
        analysis_type="scene",
        status="success",
        summary="s",
        ai_run_id=None,
        created_at=__import__("datetime").datetime.utcnow(),
    )
    item = SimpleNamespace(
        id=UUID("33333333-3333-3333-3333-333333333333"),
        analysis_id=analysis.id,
        item_type="problem",
        title="logic",
        content="m",
        severity="medium",
        is_selected=False,
        sort_order=1,
        metadata_json={"problem_type": "logic"},
        created_at=__import__("datetime").datetime.utcnow(),
        updated_at=__import__("datetime").datetime.utcnow(),
    )
    db = _RecordingDB(by_model={"SceneAnalysisItem": [item]})
    response = store.to_scene_analysis_response(db, analysis)
    assert response.id == analysis.id
    assert response.summary == "s"
    assert len(response.items) == 1
    assert response.items[0].title == "logic"
