"""runtime_status_service 直测。

该模块用模块级 dict + 锁维护启动期 status snapshot，被 health 路由与 startup_checks 共用。
之前没有直测覆盖；这里补关键不变量：
- snapshot 是 deepcopy（外部修改不能污染内部状态）
- reset 后回到 default
- mark_* 系列只动它该动的字段
- "ready" 阶段会清空 startup_error
"""

from app.services import runtime_status_service as rs


def setup_function():
    # 每个用例前都把模块级 status 重置；该模块本身就是 process-wide singleton。
    rs.reset_runtime_status()


def test_default_snapshot_has_expected_shape():
    snap = rs.get_runtime_status_snapshot()
    assert snap["schema_ready"] is False
    assert snap["recovery_scan_completed"] is False
    assert snap["recovered_runs"] == 0
    assert snap["workflow_runner_started"] is False
    assert snap["last_startup_stage"] == "not_started"
    assert snap["startup_error"] is None
    assert "version" in snap


def test_snapshot_is_deepcopy_isolated_from_internal_state():
    snap = rs.get_runtime_status_snapshot()
    snap["schema_ready"] = True
    snap["recovered_runs"] = 999
    fresh = rs.get_runtime_status_snapshot()
    assert fresh["schema_ready"] is False
    assert fresh["recovered_runs"] == 0


def test_mark_schema_ready_only_flips_schema_field():
    rs.mark_schema_ready(True)
    snap = rs.get_runtime_status_snapshot()
    assert snap["schema_ready"] is True
    # 其它字段不变
    assert snap["recovery_scan_completed"] is False
    assert snap["last_startup_stage"] == "not_started"

    rs.mark_schema_ready(False)
    assert rs.get_runtime_status_snapshot()["schema_ready"] is False


def test_mark_recovery_scan_completed_clamps_negative_to_zero():
    rs.mark_recovery_scan_completed(-5)
    snap = rs.get_runtime_status_snapshot()
    assert snap["recovery_scan_completed"] is True
    assert snap["recovered_runs"] == 0


def test_mark_recovery_scan_completed_persists_positive_count():
    rs.mark_recovery_scan_completed(7)
    snap = rs.get_runtime_status_snapshot()
    assert snap["recovery_scan_completed"] is True
    assert snap["recovered_runs"] == 7


def test_mark_workflow_runner_started_default_true():
    rs.mark_workflow_runner_started()
    assert rs.get_runtime_status_snapshot()["workflow_runner_started"] is True
    rs.mark_workflow_runner_started(False)
    assert rs.get_runtime_status_snapshot()["workflow_runner_started"] is False


def test_mark_startup_stage_records_value():
    rs.mark_startup_stage("schema_validation")
    assert rs.get_runtime_status_snapshot()["last_startup_stage"] == "schema_validation"


def test_mark_startup_stage_ready_clears_previous_error():
    rs.mark_startup_error("schema_upgrade", "boom")
    assert rs.get_runtime_status_snapshot()["startup_error"] == "boom"
    rs.mark_startup_stage("ready")
    snap = rs.get_runtime_status_snapshot()
    assert snap["last_startup_stage"] == "ready"
    assert snap["startup_error"] is None


def test_mark_startup_error_records_stage_and_message():
    rs.mark_startup_error("workflow_recovery", "lease lookup failed")
    snap = rs.get_runtime_status_snapshot()
    assert snap["last_startup_stage"] == "workflow_recovery"
    assert snap["startup_error"] == "lease lookup failed"


def test_reset_runtime_status_returns_to_defaults():
    rs.mark_schema_ready(True)
    rs.mark_recovery_scan_completed(3)
    rs.mark_workflow_runner_started(True)
    rs.mark_startup_error("schema_validation", "fail")
    rs.reset_runtime_status()
    snap = rs.get_runtime_status_snapshot()
    assert snap["schema_ready"] is False
    assert snap["recovery_scan_completed"] is False
    assert snap["recovered_runs"] == 0
    assert snap["workflow_runner_started"] is False
    assert snap["last_startup_stage"] == "not_started"
    assert snap["startup_error"] is None
