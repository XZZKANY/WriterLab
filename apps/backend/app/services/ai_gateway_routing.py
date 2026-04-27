"""AI 网关 profile 路由解析与展示矩阵（B 块）。

承接来自 ai_gateway_service.py 的 5 个函数：
- `_resolve_profiles`：从 ModelProfile 表读 enabled profile，按 workflow_step / task_type
  匹配；无 enabled 时回落到 `DEFAULT_PROFILES`
- `_step_runtime_profiles`：把"运行诊断"的 step 名映射到 `_resolve_profiles` 的合适入参
- `_profile_to_dict`：把 ORM ModelProfile 对象拍平成 dict
- `_matrix_rule`：从 `PROVIDER_FALLBACK_MATRIX` 取某个 step 的规则（fallback 到 task_type）
- `get_provider_matrix`：把 `PROVIDER_FALLBACK_MATRIX` 序列化为对外 ProviderMatrixResponse

**关于 monkeypatch 主目标 + 同模块互相调用**：
- `_resolve_profiles` 在 7 处测试中被 `monkeypatch.setattr(gateway, "_resolve_profiles", ...)` 替换
- `_step_runtime_profiles` 在 3 处被替换
- 这两个函数都在本模块；`_step_runtime_profiles` 内部要调 `_resolve_profiles`。
  如果用普通 `_resolve_profiles(...)` 引用本模块的同名函数，则 monkeypatch 替换主模块属性
  对本模块内部调用**无效**。所以 `_step_runtime_profiles` 内部走 lazy import：
  `from app.services.ai_gateway_service import _resolve_profiles`，每次调用从主模块
  __dict__ 解析最新绑定，让测试 patch 仍能命中。

主模块通过顶部 `from app.services.ai_gateway_routing import _resolve_profiles, ...` 拉回，
让 `call_ai_gateway` 与 `get_provider_runtime_state` 内部 LOAD_GLOBAL 走主模块属性。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.model_profile import ModelProfile
from app.schemas.workflow import (
    ProviderFallbackRule,
    ProviderFallbackTarget,
    ProviderMatrixResponse,
)
from app.services.ai_gateway_constants import DEFAULT_PROFILES, PROVIDER_FALLBACK_MATRIX


def _profile_to_dict(profile: ModelProfile) -> dict:
    return {
        "name": profile.name,
        "provider": profile.provider,
        "model": profile.model,
        "priority": profile.priority,
        "temperature": profile.temperature,
        "max_tokens": profile.max_tokens,
        "timeout_ms": profile.timeout_ms,
        "task_type": profile.task_type,
        "workflow_step": profile.workflow_step,
        "api_base": profile.api_base,
        "api_key_env": profile.api_key_env,
        "extra_headers": profile.extra_headers,
        "requests_per_minute": profile.requests_per_minute,
        "monthly_budget_usd": profile.monthly_budget_usd,
        "routing_weight": profile.routing_weight,
    }


def _resolve_profiles(db: Session, task_type: str, workflow_step: str | None = None) -> list[dict]:
    enabled_query = db.query(ModelProfile).filter(ModelProfile.is_enabled.is_(True))
    if workflow_step:
        db_profiles = (
            enabled_query.filter(ModelProfile.workflow_step == workflow_step)
            .order_by(ModelProfile.priority.asc(), ModelProfile.routing_weight.desc())
            .all()
        )
        if db_profiles:
            return [_profile_to_dict(profile) for profile in db_profiles]
        disabled_exists = (
            db.query(ModelProfile)
            .filter(ModelProfile.workflow_step == workflow_step)
            .first()
        )
        if disabled_exists:
            return []

    db_profiles = (
        enabled_query.filter(ModelProfile.task_type == task_type)
        .order_by(ModelProfile.priority.asc(), ModelProfile.routing_weight.desc())
        .all()
    )
    if db_profiles:
        return [_profile_to_dict(profile) for profile in db_profiles]
    disabled_exists = (
        db.query(ModelProfile)
        .filter(ModelProfile.task_type == task_type)
        .first()
    )
    if disabled_exists:
        return []
    matrix_key = workflow_step or task_type
    return DEFAULT_PROFILES.get(matrix_key, DEFAULT_PROFILES.get(task_type, []))


def _matrix_rule(task_type: str, workflow_step: str | None = None) -> dict:
    return PROVIDER_FALLBACK_MATRIX.get(workflow_step or task_type, PROVIDER_FALLBACK_MATRIX.get(task_type, {}))


def get_provider_matrix() -> ProviderMatrixResponse:
    rules = []
    for step, rule in PROVIDER_FALLBACK_MATRIX.items():
        rules.append(
            ProviderFallbackRule(
                step=step,
                default_provider=rule["default_provider"],
                default_model=rule["default_model"],
                timeout_ms=int(rule["timeout_ms"]),
                retry_count=int(rule["retry_count"]),
                fallback_targets=[ProviderFallbackTarget(**target) for target in rule.get("fallback_targets", [])],
                fallback_to_ollama_when=str(rule["fallback_to_ollama_when"]),
                quality_degraded_on_fallback=bool(rule.get("quality_degraded_on_fallback", False)),
            )
        )
    return ProviderMatrixResponse(rules=rules)


def _step_runtime_profiles(db: Session, step: str) -> list[dict]:
    # lazy import 主模块里的 _resolve_profiles 绑定，以让测试中
    # `monkeypatch.setattr(gateway, "_resolve_profiles", fake)` 在本函数内部生效。
    # 注意：直接 import _resolve_profiles 会绑定到本模块的版本，monkeypatch 主模块的就失效。
    from app.services.ai_gateway_service import _resolve_profiles

    if step == "analyze":
        return _resolve_profiles(db, "analyze")
    if step == "planner":
        return _resolve_profiles(db, "analyze", workflow_step="planner")
    if step == "write":
        return _resolve_profiles(db, "write")
    if step == "style":
        return _resolve_profiles(db, "revise", workflow_step="style")
    if step == "check":
        return _resolve_profiles(db, "analyze", workflow_step="check")
    return _resolve_profiles(db, step, workflow_step=step)
