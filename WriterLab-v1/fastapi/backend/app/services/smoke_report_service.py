from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import HTTPException

SmokeReportType = Literal["backend_full_smoke", "frontend_live_smoke"]

REPO_ROOT = Path(__file__).resolve().parents[4]
SMOKE_LOG_DIR = REPO_ROOT / "scripts" / "logs"


def list_smoke_report_summaries() -> list[dict[str, Any]]:
    if not SMOKE_LOG_DIR.exists():
        return []

    summaries: list[dict[str, Any]] = []
    for path in SMOKE_LOG_DIR.glob("*.json"):
        report_type = _detect_report_type(path.name)
        if report_type is None:
            continue
        try:
            report = _load_report_json(path)
        except HTTPException:
            continue
        summaries.append(_build_summary(path, report_type, report))
    summaries.sort(key=lambda item: item["created_at"], reverse=True)
    return summaries


def get_latest_smoke_reports() -> dict[str, Any]:
    latest: dict[str, Any] = {
        "backend_full_smoke": None,
        "frontend_live_smoke": None,
    }
    for summary in list_smoke_report_summaries():
        report_type = summary["report_type"]
        if latest[report_type] is None:
            latest[report_type] = summary
    return latest


def get_smoke_report_detail(filename: str) -> dict[str, Any]:
    path = _resolve_report_path(filename)
    report_type = _detect_report_type(path.name)
    if report_type is None:
        raise HTTPException(status_code=422, detail="Unknown smoke report type.")
    report = _load_report_json(path)
    summary = _build_summary(path, report_type, report)
    detail: dict[str, Any] = {
        **summary,
        "requested_provider_mode": None,
        "effective_provider_mode": None,
        "provider_preflight": None,
        "blocking_reasons": [],
        "scenarios": [],
        "frontend_summary": None,
        "report": report,
    }
    if report_type == "backend_full_smoke":
        detail.update(
            {
                "requested_provider_mode": _string_or_none(report.get("requested_provider_mode")),
                "effective_provider_mode": _string_or_none(report.get("effective_provider_mode")),
                "provider_preflight": report.get("provider_preflight") if isinstance(report.get("provider_preflight"), dict) else None,
                "blocking_reasons": _string_list(report.get("blocking_reasons")),
                "scenarios": [_build_backend_scenario(item) for item in report.get("scenarios", []) if isinstance(item, dict)],
            }
        )
    else:
        detail["frontend_summary"] = {
            "filename": path.name,
            "created_at": summary["created_at"],
            "success": bool(report.get("ok")),
            "status_code": _int_or_none(report.get("statusCode")),
            "url": _string_or_none(report.get("url")),
            "markers": _bool_dict(report.get("markers")),
        }
    return detail


def get_smoke_report_regression(filename: str) -> dict[str, Any]:
    current_detail = get_smoke_report_detail(filename)
    current_summary = _summary_from_detail(current_detail)
    baseline_summary = _select_baseline_summary(current_summary)
    response: dict[str, Any] = {
        "report_type": current_summary["report_type"],
        "filename": current_summary["filename"],
        "comparable": False,
        "regression_free": True,
        "current_report": current_summary,
        "baseline_report": None,
        "findings": [],
    }
    if baseline_summary is None:
        return response

    baseline_detail = get_smoke_report_detail(baseline_summary["filename"])
    findings = _build_regression_findings(current_detail, baseline_detail)
    response.update(
        {
            "comparable": True,
            "regression_free": len(findings) == 0,
            "baseline_report": baseline_summary,
            "findings": findings,
        }
    )
    return response


def _resolve_report_path(filename: str) -> Path:
    candidate = (SMOKE_LOG_DIR / filename).resolve()
    base = SMOKE_LOG_DIR.resolve()
    if candidate.parent != base:
        raise HTTPException(status_code=404, detail="Smoke report not found.")
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Smoke report not found.")
    return candidate


def _detect_report_type(filename: str) -> SmokeReportType | None:
    if filename.startswith("backend-full-smoke-"):
        return "backend_full_smoke"
    if filename.startswith("frontend-live-smoke-"):
        return "frontend_live_smoke"
    return None


def _load_report_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Smoke report not found.") from exc
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="Smoke report is not readable UTF-8 JSON.") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="Smoke report is not valid JSON.") from exc


def _build_summary(path: Path, report_type: SmokeReportType, report: dict[str, Any]) -> dict[str, Any]:
    created_at = _coerce_created_at(report, path, report_type)
    if report_type == "backend_full_smoke":
        return {
            "report_type": report_type,
            "filename": path.name,
            "created_at": created_at,
            "provider_mode": _string_or_none(report.get("effective_provider_mode") or report.get("requested_provider_mode")),
            "failure_stage": _string_or_none(report.get("failure_stage")),
            "success": _backend_report_success(report),
            "scenario_count": len(report.get("scenarios", [])) if isinstance(report.get("scenarios"), list) else 0,
        }
    return {
        "report_type": report_type,
        "filename": path.name,
        "created_at": created_at,
        "provider_mode": None,
        "failure_stage": None,
        "success": bool(report.get("ok")),
        "scenario_count": 0,
    }


def _summary_from_detail(detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_type": detail["report_type"],
        "filename": detail["filename"],
        "created_at": detail["created_at"],
        "provider_mode": detail.get("provider_mode"),
        "failure_stage": detail.get("failure_stage"),
        "success": bool(detail.get("success")),
        "scenario_count": int(detail.get("scenario_count") or 0),
    }


def _build_backend_scenario(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": _string_or_none(item.get("name")) or "unknown",
        "fixture_scenario": _string_or_none(item.get("fixture_scenario")),
        "expected_status": _string_or_none(item.get("expected_status")),
        "actual_status": _string_or_none(item.get("actual_status")),
        "resume_checkpoint": _string_or_none(item.get("resume_checkpoint")),
        "step_statuses": item.get("step_statuses") if isinstance(item.get("step_statuses"), list) else [],
        "event_summary": item.get("event_summary") if isinstance(item.get("event_summary"), dict) else {},
        "assertions": [
            {
                "name": _string_or_none(assertion.get("name")) or "assertion",
                "ok": bool(assertion.get("ok")),
                "detail": _string_or_none(assertion.get("detail")),
            }
            for assertion in item.get("assertions", [])
            if isinstance(assertion, dict)
        ],
    }


def _select_baseline_summary(current_summary: dict[str, Any]) -> dict[str, Any] | None:
    current_created_at = _parse_iso_datetime(current_summary["created_at"])
    candidates: list[dict[str, Any]] = []
    for summary in list_smoke_report_summaries():
        if summary["filename"] == current_summary["filename"]:
            continue
        if summary["report_type"] != current_summary["report_type"]:
            continue
        if not bool(summary.get("success")):
            continue
        if current_summary["report_type"] == "backend_full_smoke" and summary.get("provider_mode") != current_summary.get("provider_mode"):
            continue
        if _parse_iso_datetime(summary["created_at"]) >= current_created_at:
            continue
        candidates.append(summary)
    if not candidates:
        return None
    candidates.sort(key=lambda item: _parse_iso_datetime(item["created_at"]), reverse=True)
    return candidates[0]


def _build_regression_findings(current_detail: dict[str, Any], baseline_detail: dict[str, Any]) -> list[dict[str, Any]]:
    if current_detail["report_type"] == "backend_full_smoke":
        return _build_backend_regression_findings(current_detail, baseline_detail)
    return _build_frontend_regression_findings(current_detail, baseline_detail)


def _build_backend_regression_findings(current_detail: dict[str, Any], baseline_detail: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    baseline_success = bool(baseline_detail.get("success"))
    current_success = bool(current_detail.get("success"))
    if baseline_success and not current_success:
        findings.append(
            _finding(
                "report",
                "success",
                "Smoke report regressed from success to failure.",
                baseline_success,
                current_success,
            )
        )

    baseline_failure_stage = baseline_detail.get("failure_stage")
    current_failure_stage = current_detail.get("failure_stage")
    if (baseline_failure_stage or "") != (current_failure_stage or "") and current_failure_stage:
        findings.append(
            _finding(
                "report",
                "failure_stage",
                "Failure stage regressed compared with the latest successful baseline.",
                baseline_failure_stage,
                current_failure_stage,
            )
        )

    baseline_scenarios = {item["name"]: item for item in baseline_detail.get("scenarios", []) if isinstance(item, dict)}
    current_scenarios = {item["name"]: item for item in current_detail.get("scenarios", []) if isinstance(item, dict)}
    for scenario_name, baseline_scenario in baseline_scenarios.items():
        current_scenario = current_scenarios.get(scenario_name)
        if current_scenario is None:
            findings.append(
                _finding(
                    "scenario",
                    scenario_name,
                    "Scenario is missing from the current smoke report.",
                    baseline_scenario.get("actual_status"),
                    None,
                )
            )
            continue

        if (baseline_scenario.get("actual_status") or "") != (current_scenario.get("actual_status") or ""):
            if _status_rank(current_scenario.get("actual_status")) < _status_rank(baseline_scenario.get("actual_status")):
                findings.append(
                    _finding(
                        "scenario",
                        scenario_name,
                        "Scenario status regressed compared with the latest successful baseline.",
                        baseline_scenario.get("actual_status"),
                        current_scenario.get("actual_status"),
                    )
                )

        baseline_assertions = {
            item.get("name"): item
            for item in baseline_scenario.get("assertions", [])
            if isinstance(item, dict) and item.get("name")
        }
        current_assertions = {
            item.get("name"): item
            for item in current_scenario.get("assertions", [])
            if isinstance(item, dict) and item.get("name")
        }
        for assertion_name, baseline_assertion in baseline_assertions.items():
            current_assertion = current_assertions.get(assertion_name)
            if baseline_assertion.get("ok") is True and (current_assertion is None or current_assertion.get("ok") is not True):
                findings.append(
                    _finding(
                        "assertion",
                        f"{scenario_name}:{assertion_name}",
                        "Assertion regressed from pass to fail.",
                        True,
                        current_assertion.get("ok") if current_assertion else None,
                    )
                )

        baseline_events = ((baseline_scenario.get("event_summary") or {}).get("counts") or {}) if isinstance(baseline_scenario.get("event_summary"), dict) else {}
        current_events = ((current_scenario.get("event_summary") or {}).get("counts") or {}) if isinstance(current_scenario.get("event_summary"), dict) else {}
        for event_name in ("step_started", "step_completed", "step_failed", "workflow_waiting_review", "workflow_resumed"):
            baseline_count = _int_or_zero(baseline_events.get(event_name))
            current_count = _int_or_zero(current_events.get(event_name))
            if baseline_count > 0 and current_count == 0:
                findings.append(
                    _finding(
                        "event",
                        f"{scenario_name}:{event_name}",
                        "Required event disappeared compared with the latest successful baseline.",
                        baseline_count,
                        current_count,
                    )
                )

        baseline_steps = {
            item.get("step_key"): item
            for item in baseline_scenario.get("step_statuses", [])
            if isinstance(item, dict) and item.get("step_key")
        }
        current_steps = {
            item.get("step_key"): item
            for item in current_scenario.get("step_statuses", [])
            if isinstance(item, dict) and item.get("step_key")
        }
        for step_key, baseline_step in baseline_steps.items():
            current_step = current_steps.get(step_key)
            if current_step is None:
                findings.append(
                    _finding(
                        "step",
                        f"{scenario_name}:{step_key}",
                        "Step is missing from the current smoke report.",
                        baseline_step.get("status"),
                        None,
                    )
                )
                continue
            baseline_status = baseline_step.get("status")
            current_status = current_step.get("status")
            if _status_rank(current_status) < _status_rank(baseline_status):
                findings.append(
                    _finding(
                        "step",
                        f"{scenario_name}:{step_key}",
                        "Step status regressed compared with the latest successful baseline.",
                        baseline_status,
                        current_status,
                    )
                )
    return findings


def _build_frontend_regression_findings(current_detail: dict[str, Any], baseline_detail: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    current_summary = current_detail.get("frontend_summary") or {}
    baseline_summary = baseline_detail.get("frontend_summary") or {}

    baseline_success = bool(baseline_summary.get("success"))
    current_success = bool(current_summary.get("success"))
    if baseline_success and not current_success:
        findings.append(
            _finding(
                "report",
                "success",
                "Frontend live smoke regressed from success to failure.",
                baseline_success,
                current_success,
            )
        )

    baseline_status_code = baseline_summary.get("status_code")
    current_status_code = current_summary.get("status_code")
    if baseline_status_code == 200 and current_status_code != 200:
        findings.append(
            _finding(
                "report",
                "status_code",
                "Frontend live smoke status code regressed from 200.",
                baseline_status_code,
                current_status_code,
            )
        )

    baseline_markers = baseline_summary.get("markers") if isinstance(baseline_summary.get("markers"), dict) else {}
    current_markers = current_summary.get("markers") if isinstance(current_summary.get("markers"), dict) else {}
    for marker_name, baseline_value in baseline_markers.items():
        current_value = current_markers.get(marker_name)
        if bool(baseline_value) and not bool(current_value):
            findings.append(
                _finding(
                    "marker",
                    marker_name,
                    "Frontend live smoke marker regressed from true to false.",
                    bool(baseline_value),
                    bool(current_value),
                )
            )
    return findings


def _backend_report_success(report: dict[str, Any]) -> bool:
    if report.get("failure_stage") or report.get("error"):
        return False
    scenarios = report.get("scenarios")
    if not isinstance(scenarios, list):
        return True
    for item in scenarios:
        if not isinstance(item, dict):
            continue
        expected = item.get("expected_status")
        actual = item.get("actual_status")
        if expected is not None and actual is not None and expected != actual:
            return False
        for assertion in item.get("assertions", []):
            if isinstance(assertion, dict) and not bool(assertion.get("ok")):
                return False
    return True


def _coerce_created_at(report: dict[str, Any], path: Path, report_type: SmokeReportType) -> str:
    candidates = []
    if report_type == "backend_full_smoke":
        candidates.extend([report.get("finished_at"), report.get("started_at")])
    else:
        candidates.extend([report.get("checkedAt"), report.get("finished_at"), report.get("started_at")])
    for candidate in candidates:
        if isinstance(candidate, str) and candidate:
            return candidate
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def _parse_iso_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _status_rank(value: Any) -> int:
    ranks = {
        "completed": 6,
        "skipped": 6,
        "waiting_user_review": 5,
        "queued_resume": 4,
        "queued": 4,
        "running": 4,
        "partial_success": 4,
        "invalidated": 3,
        "cancelled": 2,
        "failed": 1,
    }
    if not isinstance(value, str):
        return 0
    return ranks.get(value, 0)


def _finding(scope: str, key: str, message: str, baseline_value: Any, current_value: Any) -> dict[str, Any]:
    return {
        "scope": scope,
        "key": key,
        "message": message,
        "baseline_value": baseline_value,
        "current_value": current_value,
    }


def _int_or_zero(value: Any) -> int:
    return value if isinstance(value, int) else 0


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _bool_dict(value: Any) -> dict[str, bool]:
    if not isinstance(value, dict):
        return {}
    return {str(key): bool(item) for key, item in value.items()}
