"""ai_gateway_routing 直测。

T-6.B4.3.c 拆出的 B 块 + 路由矩阵。
"""

from types import SimpleNamespace

from app.services import ai_gateway_service as gateway
from app.services.ai_gateway_constants import DEFAULT_PROFILES, PROVIDER_FALLBACK_MATRIX
from app.services.ai_gateway_routing import (
    _matrix_rule,
    _profile_to_dict,
    _resolve_profiles,
    _step_runtime_profiles,
    get_provider_matrix,
)


# ---------- _profile_to_dict ----------

def test_profile_to_dict_copies_all_known_columns():
    orm = SimpleNamespace(
        name="write-primary",
        provider="openai",
        model="gpt-4o-mini",
        priority=10,
        temperature=0.7,
        max_tokens=2048,
        timeout_ms=120000,
        task_type="write",
        workflow_step=None,
        api_base="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        extra_headers={"X-Custom": "v"},
        requests_per_minute=60,
        monthly_budget_usd=100.0,
        routing_weight=1.5,
    )
    out = _profile_to_dict(orm)
    assert out["name"] == "write-primary"
    assert out["provider"] == "openai"
    assert out["model"] == "gpt-4o-mini"
    assert out["temperature"] == 0.7
    assert out["max_tokens"] == 2048
    assert out["api_base"] == "https://api.openai.com/v1"
    assert out["extra_headers"] == {"X-Custom": "v"}
    assert out["requests_per_minute"] == 60
    assert out["monthly_budget_usd"] == 100.0
    assert out["routing_weight"] == 1.5


# ---------- _matrix_rule ----------

def test_matrix_rule_returns_workflow_step_first():
    # planner 既能在 PROVIDER_FALLBACK_MATRIX 找到（作为 workflow_step）
    rule = _matrix_rule("analyze", "planner")
    assert rule["default_provider"] == PROVIDER_FALLBACK_MATRIX["planner"]["default_provider"]


def test_matrix_rule_falls_back_to_task_type():
    # 给一个 unknown workflow_step，应回到 task_type
    rule = _matrix_rule("analyze", "unknown-step")
    assert rule["default_provider"] == PROVIDER_FALLBACK_MATRIX["analyze"]["default_provider"]


def test_matrix_rule_returns_empty_for_unknown_task():
    rule = _matrix_rule("ghost-task", None)
    assert rule == {}


# ---------- get_provider_matrix ----------

def test_get_provider_matrix_includes_all_steps():
    response = get_provider_matrix()
    steps = {item.step for item in response.rules}
    assert steps == set(PROVIDER_FALLBACK_MATRIX.keys())


def test_get_provider_matrix_translates_fallback_targets():
    response = get_provider_matrix()
    write_rule = next(item for item in response.rules if item.step == "write")
    assert write_rule.default_provider == "openai"
    assert any(target.provider == "ollama" for target in write_rule.fallback_targets)


# ---------- _resolve_profiles ----------

class _FakeQuery:
    def __init__(self, items):
        self._items = list(items)

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._items)

    def first(self):
        return self._items[0] if self._items else None


class _DisabledExistsQuery:
    """专用于 disabled-exists 检查的 fake：filter().first() → 真实存在的 marker。"""

    def __init__(self):
        self._marker = SimpleNamespace()  # 任意非空对象都可以

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._marker


class _FakeDB:
    def __init__(self, enabled=None, disabled_exists=False):
        # enabled: 模拟 enabled_query.filter(...).all() 的返回（一组 ORM 风格对象）
        # disabled_exists: True 表示第二次 query（disabled 检查）应返回非空，导致返回空表
        self._enabled = enabled or []
        self._disabled_exists = disabled_exists
        self._call_count = 0

    def query(self, model):
        self._call_count += 1
        # 第一次是 enabled_query；返回 enabled 列表
        if self._call_count == 1:
            return _FakeQuery(self._enabled)
        # 后续是 disabled-exists 检查
        if self._disabled_exists:
            return _DisabledExistsQuery()
        return _FakeQuery([])


def test_resolve_profiles_returns_default_when_no_db_profiles():
    db = _FakeDB(enabled=[])
    out = _resolve_profiles(db, "analyze")
    # 应回到 DEFAULT_PROFILES["analyze"]
    assert out == DEFAULT_PROFILES["analyze"]


def test_resolve_profiles_uses_default_for_workflow_step_first():
    db = _FakeDB(enabled=[])
    out = _resolve_profiles(db, "analyze", workflow_step="planner")
    # workflow_step="planner" 命中 DEFAULT_PROFILES["planner"]
    assert out == DEFAULT_PROFILES["planner"]


def test_resolve_profiles_returns_empty_when_all_disabled():
    db = _FakeDB(enabled=[], disabled_exists=True)
    out = _resolve_profiles(db, "analyze")
    # disabled exists → 不回 DEFAULT_PROFILES，返回空表（用户已配置但禁用）
    assert out == []


# ---------- _step_runtime_profiles ----------

def test_step_runtime_profiles_routes_well_known_steps(monkeypatch):
    captured = []

    def fake_resolve(db, task_type, workflow_step=None):
        captured.append((task_type, workflow_step))
        return [{"name": f"{task_type}-x", "provider": "p", "model": "m"}]

    # **关键**：_step_runtime_profiles 内部 lazy import gateway._resolve_profiles，
    # 所以替换主模块属性才生效（不能替换 routing 子模块）
    monkeypatch.setattr(gateway, "_resolve_profiles", fake_resolve)

    _step_runtime_profiles(object(), "analyze")
    _step_runtime_profiles(object(), "planner")
    _step_runtime_profiles(object(), "write")
    _step_runtime_profiles(object(), "style")
    _step_runtime_profiles(object(), "check")
    assert ("analyze", None) in captured
    assert ("analyze", "planner") in captured
    assert ("write", None) in captured
    assert ("revise", "style") in captured
    assert ("analyze", "check") in captured


def test_step_runtime_profiles_falls_back_for_unknown_step(monkeypatch):
    captured = []

    def fake_resolve(db, task_type, workflow_step=None):
        captured.append((task_type, workflow_step))
        return []

    monkeypatch.setattr(gateway, "_resolve_profiles", fake_resolve)
    _step_runtime_profiles(object(), "ghost")
    assert captured == [("ghost", "ghost")]
