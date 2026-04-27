import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.runtime import router as runtime_router


def _write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_list_smoke_reports_returns_sorted_summaries(monkeypatch, tmp_path):
    _write_json(
        tmp_path / "backend-full-smoke-20260329-191932.json",
        {
            "finished_at": "2026-03-29T11:19:49.827782+00:00",
            "requested_provider_mode": "smoke_fixture",
            "effective_provider_mode": "smoke_fixture",
            "failure_stage": None,
            "scenarios": [
                {
                    "name": "happy_path",
                    "expected_status": "completed",
                    "actual_status": "completed",
                    "assertions": [{"name": "baseline_completed", "ok": True, "detail": "ok"}],
                }
            ],
        },
    )
    _write_json(
        tmp_path / "frontend-live-smoke-20260329-192003.json",
        {
            "checkedAt": "2026-03-29T11:20:03.960Z",
            "ok": True,
            "statusCode": 200,
            "url": "http://127.0.0.1:3000/editor",
            "markers": {
                "Workflow Debug": True,
                "Runtime Readiness": True,
                "Runtime Self-Check Alert": True,
            },
        },
    )

    monkeypatch.setattr("app.services.smoke_report_service.SMOKE_LOG_DIR", tmp_path)
    app = FastAPI()
    app.include_router(runtime_router)
    client = TestClient(app)

    response = client.get("/api/runtime/smoke-reports")

    assert response.status_code == 200
    payload = response.json()
    assert [item["report_type"] for item in payload] == ["frontend_live_smoke", "backend_full_smoke"]
    assert payload[0]["filename"] == "frontend-live-smoke-20260329-192003.json"
    assert payload[0]["success"] is True
    assert payload[1]["provider_mode"] == "smoke_fixture"
    assert payload[1]["scenario_count"] == 1


def test_latest_smoke_reports_returns_per_type_latest(monkeypatch, tmp_path):
    _write_json(
        tmp_path / "backend-full-smoke-20260329-191932.json",
        {
            "finished_at": "2026-03-29T11:19:49.827782+00:00",
            "effective_provider_mode": "smoke_fixture",
            "scenarios": [],
        },
    )
    _write_json(
        tmp_path / "backend-full-smoke-20260329-192023.json",
        {
            "finished_at": "2026-03-29T11:20:24.827782+00:00",
            "effective_provider_mode": "live",
            "failure_stage": "preflight_blocked",
            "scenarios": [],
        },
    )
    _write_json(
        tmp_path / "frontend-live-smoke-20260329-192003.json",
        {
            "checkedAt": "2026-03-29T11:20:03.960Z",
            "ok": True,
            "markers": {"Workflow Debug": True},
        },
    )

    monkeypatch.setattr("app.services.smoke_report_service.SMOKE_LOG_DIR", tmp_path)
    app = FastAPI()
    app.include_router(runtime_router)
    client = TestClient(app)

    response = client.get("/api/runtime/smoke-reports/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["backend_full_smoke"]["filename"] == "backend-full-smoke-20260329-192023.json"
    assert payload["backend_full_smoke"]["failure_stage"] == "preflight_blocked"
    assert payload["frontend_live_smoke"]["filename"] == "frontend-live-smoke-20260329-192003.json"


def test_smoke_report_detail_returns_backend_scenarios(monkeypatch, tmp_path):
    _write_json(
        tmp_path / "backend-full-smoke-20260329-191932.json",
        {
            "finished_at": "2026-03-29T11:19:49.827782+00:00",
            "requested_provider_mode": "smoke_fixture",
            "effective_provider_mode": "smoke_fixture",
            "provider_preflight": {"summary": {"ok": True}},
            "blocking_reasons": [],
            "failure_stage": None,
            "scenarios": [
                {
                    "name": "style_fail",
                    "fixture_scenario": "style_fail",
                    "expected_status": "completed",
                    "actual_status": "completed",
                    "resume_checkpoint": "style",
                    "step_statuses": [{"step_key": "style", "status": "failed"}],
                    "event_summary": {"counts": {"step_failed": 1, "workflow_resumed": 1}},
                    "assertions": [{"name": "style_failed_once", "ok": True, "detail": "style failed then resumed"}],
                }
            ],
        },
    )

    monkeypatch.setattr("app.services.smoke_report_service.SMOKE_LOG_DIR", tmp_path)
    app = FastAPI()
    app.include_router(runtime_router)
    client = TestClient(app)

    response = client.get("/api/runtime/smoke-reports/backend-full-smoke-20260329-191932.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["report_type"] == "backend_full_smoke"
    assert payload["requested_provider_mode"] == "smoke_fixture"
    assert payload["effective_provider_mode"] == "smoke_fixture"
    assert payload["scenario_count"] == 1
    assert payload["scenarios"][0]["name"] == "style_fail"
    assert payload["scenarios"][0]["event_summary"]["counts"]["step_failed"] == 1
    assert payload["scenarios"][0]["assertions"][0]["ok"] is True
    assert payload["report"]["provider_preflight"]["summary"]["ok"] is True


def test_smoke_report_detail_returns_frontend_summary(monkeypatch, tmp_path):
    _write_json(
        tmp_path / "frontend-live-smoke-20260329-192003.json",
        {
            "checkedAt": "2026-03-29T11:20:03.960Z",
            "ok": True,
            "statusCode": 200,
            "url": "http://127.0.0.1:3000/editor",
            "markers": {
                "Workflow Debug": True,
                "Runtime Readiness": True,
                "Runtime Self-Check Alert": True,
            },
        },
    )

    monkeypatch.setattr("app.services.smoke_report_service.SMOKE_LOG_DIR", tmp_path)
    app = FastAPI()
    app.include_router(runtime_router)
    client = TestClient(app)

    response = client.get("/api/runtime/smoke-reports/frontend-live-smoke-20260329-192003.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["report_type"] == "frontend_live_smoke"
    assert payload["frontend_summary"]["success"] is True
    assert payload["frontend_summary"]["status_code"] == 200
    assert payload["frontend_summary"]["markers"]["Workflow Debug"] is True


def test_smoke_report_detail_returns_explicit_errors(monkeypatch, tmp_path):
    (tmp_path / "backend-full-smoke-20260329-191932.json").write_text("{ bad json", encoding="utf-8")

    monkeypatch.setattr("app.services.smoke_report_service.SMOKE_LOG_DIR", tmp_path)
    app = FastAPI()
    app.include_router(runtime_router)
    client = TestClient(app)

    missing = client.get("/api/runtime/smoke-reports/backend-full-smoke-20260329-111111.json")
    bad_json = client.get("/api/runtime/smoke-reports/backend-full-smoke-20260329-191932.json")

    assert missing.status_code == 404
    assert missing.json()["detail"] == "Smoke report not found."
    assert bad_json.status_code == 422
    assert bad_json.json()["detail"] == "Smoke report is not valid JSON."


def test_backend_smoke_regression_returns_findings_and_uses_same_mode_baseline(monkeypatch, tmp_path):
    _write_json(
        tmp_path / "backend-full-smoke-20260329-191000.json",
        {
            "finished_at": "2026-03-29T11:10:00+00:00",
            "effective_provider_mode": "live",
            "scenarios": [
                {
                    "name": "happy_path",
                    "expected_status": "completed",
                    "actual_status": "completed",
                    "step_statuses": [{"step_key": "plan", "status": "completed"}],
                    "event_summary": {"counts": {"step_started": 1, "step_completed": 1}},
                    "assertions": [{"name": "baseline_completed", "ok": True}],
                }
            ],
        },
    )
    _write_json(
        tmp_path / "backend-full-smoke-20260329-191500.json",
        {
            "finished_at": "2026-03-29T11:15:00+00:00",
            "effective_provider_mode": "smoke_fixture",
            "scenarios": [
                {
                    "name": "happy_path",
                    "expected_status": "completed",
                    "actual_status": "completed",
                    "step_statuses": [{"step_key": "plan", "status": "completed"}],
                    "event_summary": {"counts": {"step_started": 1, "step_completed": 1}},
                    "assertions": [{"name": "baseline_completed", "ok": True}],
                }
            ],
        },
    )
    _write_json(
        tmp_path / "backend-full-smoke-20260329-192000.json",
        {
            "finished_at": "2026-03-29T11:20:00+00:00",
            "effective_provider_mode": "smoke_fixture",
            "failure_stage": "execution_failed",
            "scenarios": [
                {
                    "name": "happy_path",
                    "expected_status": "completed",
                    "actual_status": "failed",
                    "step_statuses": [{"step_key": "plan", "status": "failed"}],
                    "event_summary": {"counts": {"step_started": 1, "step_completed": 0}},
                    "assertions": [{"name": "baseline_completed", "ok": False}],
                }
            ],
        },
    )

    monkeypatch.setattr("app.services.smoke_report_service.SMOKE_LOG_DIR", tmp_path)
    app = FastAPI()
    app.include_router(runtime_router)
    client = TestClient(app)

    response = client.get("/api/runtime/smoke-reports/backend-full-smoke-20260329-192000.json/regression")

    assert response.status_code == 200
    payload = response.json()
    assert payload["comparable"] is True
    assert payload["regression_free"] is False
    assert payload["baseline_report"]["filename"] == "backend-full-smoke-20260329-191500.json"
    assert payload["baseline_report"]["provider_mode"] == "smoke_fixture"
    scopes = {item["scope"] for item in payload["findings"]}
    assert {"report", "scenario", "assertion", "event", "step"} <= scopes


def test_backend_smoke_regression_without_baseline_is_not_comparable(monkeypatch, tmp_path):
    _write_json(
        tmp_path / "backend-full-smoke-20260329-192000.json",
        {
            "finished_at": "2026-03-29T11:20:00+00:00",
            "effective_provider_mode": "smoke_fixture",
            "scenarios": [
                {
                    "name": "happy_path",
                    "expected_status": "completed",
                    "actual_status": "completed",
                    "assertions": [{"name": "baseline_completed", "ok": True}],
                }
            ],
        },
    )

    monkeypatch.setattr("app.services.smoke_report_service.SMOKE_LOG_DIR", tmp_path)
    app = FastAPI()
    app.include_router(runtime_router)
    client = TestClient(app)

    response = client.get("/api/runtime/smoke-reports/backend-full-smoke-20260329-192000.json/regression")

    assert response.status_code == 200
    payload = response.json()
    assert payload["comparable"] is False
    assert payload["regression_free"] is True
    assert payload["baseline_report"] is None
    assert payload["findings"] == []


def test_frontend_smoke_regression_detects_marker_and_status_regression(monkeypatch, tmp_path):
    _write_json(
        tmp_path / "frontend-live-smoke-20260329-191000.json",
        {
            "checkedAt": "2026-03-29T11:10:00Z",
            "ok": True,
            "statusCode": 200,
            "markers": {
                "Workflow Debug": True,
                "Runtime Readiness": True,
            },
        },
    )
    _write_json(
        tmp_path / "frontend-live-smoke-20260329-192000.json",
        {
            "checkedAt": "2026-03-29T11:20:00Z",
            "ok": False,
            "statusCode": 500,
            "markers": {
                "Workflow Debug": False,
                "Runtime Readiness": True,
            },
        },
    )

    monkeypatch.setattr("app.services.smoke_report_service.SMOKE_LOG_DIR", tmp_path)
    app = FastAPI()
    app.include_router(runtime_router)
    client = TestClient(app)

    response = client.get("/api/runtime/smoke-reports/frontend-live-smoke-20260329-192000.json/regression")

    assert response.status_code == 200
    payload = response.json()
    assert payload["comparable"] is True
    assert payload["baseline_report"]["filename"] == "frontend-live-smoke-20260329-191000.json"
    scopes = {item["scope"] for item in payload["findings"]}
    assert "report" in scopes
    assert "marker" in scopes
