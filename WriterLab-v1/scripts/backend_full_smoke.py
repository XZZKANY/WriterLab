from __future__ import annotations

import argparse
import base64
import hashlib
import http.client
import json
import os
import socket
import struct
import sys
import threading
import time
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit


SMOKE_PROJECT_NAME = "WriterLab Smoke Project"
SMOKE_BOOK_TITLE = "Smoke Book"
SMOKE_CHAPTER_TITLE = "Smoke Chapter 1"
SMOKE_SCENE_TITLE = "Smoke Scene 1"
SMOKE_BRANCH_PREFIX = "smoke-branch"

SMOKE_SOURCE_TEXT = """鏃у煄闂ㄤ笅锛岄洦姘撮『鐫€闈掔煶鍙伴樁寰€涓嬫穼銆?娌堢牃鎶婃箍閫忕殑淇℃寜鍦ㄦ帉蹇冮噷锛岃繜杩熸病鏈夋媶寮€銆?杩滃浼犳潵涓€澹扮伀杞︽苯绗涳紝鍍忔妸鏁村骇澶滄櫄寰€鍓嶆帹浜嗕竴鏍笺€?"""

SMOKE_LATEST_TEXT = """鏃у煄闂ㄤ笅鐨勯洦鏇村瘑浜嗭紝闈掔煶鍙伴樁琚按鍏夌（寰楀彂浜€?娌堢牃鎶婇偅灏佽闆ㄦ蹈杞殑淇″帇鍦ㄦ帉蹇冿紝浠嶆棫娌℃湁鎷嗗紑銆?杩滃鍙堜紶鏉ヤ竴澹扮伀杞︽苯绗涳紝娼箍鐨勫鑹插儚琚繖澹伴暱楦ｈ交杞绘巰璧枫€?"""

SMOKE_GUIDANCE = [
    "Keep the prose concise and readable.",
    "Preserve the melancholy tone without drifting into explanation.",
]

SMOKE_OVERRIDE_REASON = "Acceptance smoke planner override"


@dataclass(frozen=True)
class ScenarioSpec:
    name: str
    expected_status: str
    auto_apply: bool = True
    run_resume: bool = False
    run_override: bool = False


SCENARIO_SPECS = {
    "happy_path": ScenarioSpec("happy_path", "completed", auto_apply=True, run_resume=True, run_override=True),
    "style_fail": ScenarioSpec("style_fail", "failed", auto_apply=True, run_resume=True, run_override=False),
    "planner_wait_review": ScenarioSpec("planner_wait_review", "waiting_user_review", auto_apply=True, run_resume=False, run_override=True),
    "guard_block": ScenarioSpec("guard_block", "waiting_user_review", auto_apply=True, run_resume=False, run_override=False),
    "check_issue": ScenarioSpec("check_issue", "completed", auto_apply=True, run_resume=False, run_override=False),
    "malformed_planner": ScenarioSpec("malformed_planner", "failed", auto_apply=True, run_resume=False, run_override=False),
}

DEFAULT_FIXTURE_MATRIX = [
    "happy_path",
    "style_fail",
    "planner_wait_review",
    "guard_block",
    "check_issue",
    "malformed_planner",
]


class SmokeFailure(RuntimeError):
    def __init__(self, message: str, *, report: dict[str, Any] | None = None):
        super().__init__(message)
        self.report = report


class ApiClient:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None, *, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        if params:
            query = urlencode({key: value for key, value in params.items() if value is not None})
            if query:
                url = f"{url}?{query}"
        parsed = urlsplit(url)
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload)
            headers["Content-Type"] = "application/json"
        connection_cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
        connection = connection_cls(parsed.hostname, parsed.port, timeout=self.timeout)
        try:
            request_path = parsed.path or "/"
            if parsed.query:
                request_path = f"{request_path}?{parsed.query}"
            connection.request(method.upper(), request_path, body=body, headers=headers)
            response = connection.getresponse()
            response_text = response.read().decode("utf-8", errors="ignore")
            if response.status >= 400:
                detail = response_text or response.reason
                raise SmokeFailure(f"{method.upper()} {path} failed with HTTP {response.status}: {detail}")
            if not response_text:
                return None
            return json.loads(response_text)
        except OSError as exc:
            raise SmokeFailure(f"{method.upper()} {path} failed: {exc.strerror or exc}") from exc
        finally:
            connection.close()

    def get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        return self.request("POST", path, payload=payload)

    def patch(self, path: str, payload: dict[str, Any]) -> Any:
        return self.request("PATCH", path, payload=payload)


class RuntimeEventCollector:
    def __init__(self, base_url: str):
        self.ws_url = f"{base_url.rstrip('/')}/api/runtime/events"
        self._events: list[dict[str, Any]] = []
        self._error: str | None = None
        self._lock = threading.Lock()
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._socket: socket.socket | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="writerlab-smoke-events", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5)
        if self._error:
            raise SmokeFailure(f"runtime event collector failed to connect: {self._error}")

    def _connect_socket(self) -> socket.socket:
        parsed = urlsplit(self.ws_url)
        if parsed.scheme == "https":
            raise SmokeFailure("runtime event collector only supports ws/http endpoints in the local smoke environment")
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ).encode("utf-8")
        sock = socket.create_connection((host, port), timeout=5)
        sock.sendall(request)
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = sock.recv(4096)
            if not chunk:
                raise SmokeFailure("runtime event collector handshake closed before headers completed")
            response += chunk
        header_bytes, _ = response.split(b"\r\n\r\n", 1)
        header_text = header_bytes.decode("utf-8", errors="ignore")
        lines = header_text.split("\r\n")
        if not lines or "101" not in lines[0]:
            raise SmokeFailure(f"runtime event collector handshake failed: {lines[0] if lines else 'no response'}")
        headers = {}
        for line in lines[1:]:
            if ":" not in line:
                continue
            key_name, value = line.split(":", 1)
            headers[key_name.strip().lower()] = value.strip()
        expected_accept = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
        ).decode("ascii")
        if headers.get("sec-websocket-accept") != expected_accept:
            raise SmokeFailure("runtime event collector handshake returned an invalid Sec-WebSocket-Accept header")
        sock.settimeout(0.5)
        return sock

    @staticmethod
    def _recv_exact(sock: socket.socket, size: int) -> bytes:
        payload = b""
        while len(payload) < size:
            chunk = sock.recv(size - len(payload))
            if not chunk:
                raise EOFError("websocket stream ended unexpectedly")
            payload += chunk
        return payload

    def _recv_frame(self, sock: socket.socket) -> tuple[int, bytes]:
        header = self._recv_exact(sock, 2)
        first, second = header[0], header[1]
        opcode = first & 0x0F
        payload_length = second & 0x7F
        masked = bool(second & 0x80)
        if payload_length == 126:
            payload_length = struct.unpack("!H", self._recv_exact(sock, 2))[0]
        elif payload_length == 127:
            payload_length = struct.unpack("!Q", self._recv_exact(sock, 8))[0]
        mask = self._recv_exact(sock, 4) if masked else b""
        payload = self._recv_exact(sock, payload_length) if payload_length else b""
        if masked:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        return opcode, payload

    def _run(self) -> None:
        try:
            self._socket = self._connect_socket()
            self._ready.set()
            while not self._stop.is_set():
                try:
                    opcode, payload = self._recv_frame(self._socket)
                except TimeoutError:
                    continue
                except socket.timeout:
                    continue
                except Exception as exc:
                    if not self._stop.is_set():
                        self._error = str(exc)
                    break
                if opcode == 0x8:
                    break
                if opcode != 0x1:
                    continue
                try:
                    event = json.loads(payload.decode("utf-8", errors="ignore"))
                except Exception:
                    continue
                with self._lock:
                    self._events.append(event)
        except Exception as exc:
            self._error = str(exc)
            self._ready.set()
        finally:
            self._ready.set()

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._events)

    def stop(self) -> None:
        self._stop.set()
        if self._socket is not None:
            try:
                self._socket.close()
            except Exception:
                pass
        if self._thread is not None:
            self._thread.join(timeout=3)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fail(step: str, message: str) -> None:
    raise SmokeFailure(f"[{step}] {message}")


def ensure(condition: bool, step: str, message: str) -> None:
    if not condition:
        fail(step, message)


def add_assertion(scenario_report: dict[str, Any], name: str, condition: bool, detail: str) -> None:
    scenario_report.setdefault("assertions", []).append({"name": name, "ok": bool(condition), "detail": detail})
    if not condition:
        raise SmokeFailure(f"[scenario:{scenario_report['name']}] {detail}")


def find_by_name(items: list[dict[str, Any]], key: str, value: str) -> dict[str, Any] | None:
    for item in items:
        if item.get(key) == value:
            return item
    return None


def ensure_project(client: ApiClient, report: dict[str, Any]) -> dict[str, Any]:
    projects = client.get("/api/projects")
    project = find_by_name(projects, "name", SMOKE_PROJECT_NAME)
    created = False
    if project is None:
        project = client.post(
            "/api/projects",
            {
                "name": SMOKE_PROJECT_NAME,
                "description": "Reusable smoke namespace for WriterLab acceptance checks.",
                "genre": "mystery",
                "default_language": "zh-CN",
            },
        )
        created = True
    report["project"] = {"id": project["id"], "name": project["name"], "created": created}
    return project


def ensure_book(client: ApiClient, project_id: str, report: dict[str, Any]) -> dict[str, Any]:
    books = client.get("/api/books", params={"project_id": project_id})
    book = find_by_name(books, "title", SMOKE_BOOK_TITLE)
    created = False
    if book is None:
        book = client.post(
            "/api/books",
            {
                "project_id": project_id,
                "title": SMOKE_BOOK_TITLE,
                "summary": "Smoke acceptance fixture book.",
                "status": "draft",
            },
        )
        created = True
    report["book"] = {"id": book["id"], "title": book["title"], "created": created}
    return book


def ensure_chapter(client: ApiClient, book_id: str, report: dict[str, Any]) -> dict[str, Any]:
    chapters = client.get("/api/chapters", params={"book_id": book_id})
    chapter = find_by_name(chapters, "title", SMOKE_CHAPTER_TITLE)
    created = False
    if chapter is None:
        chapter = client.post(
            "/api/chapters",
            {
                "book_id": book_id,
                "chapter_no": 1,
                "title": SMOKE_CHAPTER_TITLE,
                "summary": "Smoke acceptance fixture chapter.",
                "status": "draft",
            },
        )
        created = True
    report["chapter"] = {"id": chapter["id"], "title": chapter["title"], "created": created}
    return chapter


def ensure_scene(client: ApiClient, chapter_id: str, report: dict[str, Any]) -> dict[str, Any]:
    scenes = client.get("/api/scenes", params={"chapter_id": chapter_id})
    scene = find_by_name(scenes, "title", SMOKE_SCENE_TITLE)
    created = False
    if scene is None:
        scene = client.post(
            "/api/scenes",
            {
                "chapter_id": chapter_id,
                "scene_no": 1,
                "title": SMOKE_SCENE_TITLE,
                "time_label": "澶滈洦",
                "goal": "纭绁炵鏉ヤ俊鐨勬潵婧?",
                "conflict": "涓昏杩熺枒涓嶆効鎷嗕俊",
                "outcome": "鎮康琚繘涓€姝ユ媺楂?",
                "must_include": ["鏃у煄闂?", "鐏溅姹界瑳"],
                "must_avoid": ["鏁欑▼鑵?"],
                "status": "draft",
                "draft_text": SMOKE_SOURCE_TEXT,
            },
        )
        created = True
    report["scene"] = {
        "id": scene["id"],
        "title": scene["title"],
        "scene_version": scene.get("scene_version"),
        "created": created,
    }
    return scene


def update_scene_text(client: ApiClient, scene: dict[str, Any], *, target_text: str, label: str) -> dict[str, Any]:
    payload = {
        "title": SMOKE_SCENE_TITLE,
        "time_label": "澶滈洦",
        "goal": "纭绁炵鏉ヤ俊鐨勬潵婧?",
        "conflict": "涓昏杩熺枒涓嶆願鎷嗕俊",
        "outcome": "鎮康琚繘涓€姝ユ媺楂?",
        "must_include": ["鏃у煄闂?", "鐏溅姹界瑳"],
        "must_avoid": ["鏁欑▼鑵?"],
        "status": "draft",
        "draft_text": target_text,
        "expected_scene_version": scene["scene_version"],
        "version_source": "manual",
        "version_label": label,
    }
    return client.patch(f"/api/scenes/{scene['id']}", payload)


def latest_non_invalidated_step(workflow: dict[str, Any], step_key: str) -> dict[str, Any] | None:
    candidates = [step for step in workflow.get("steps", []) if step.get("step_key") == step_key and step.get("status") != "invalidated"]
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item.get("attempt_no", 0), item.get("version", 0)))


def step_attempt_count(workflow: dict[str, Any], step_key: str, *, include_invalidated: bool = True) -> int:
    return len(
        [
            step
            for step in workflow.get("steps", [])
            if step.get("step_key") == step_key and (include_invalidated or step.get("status") != "invalidated")
        ]
    )


def poll_workflow(client: ApiClient, workflow_id: str, *, timeout_seconds: int = 150) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last = None
    while time.time() < deadline:
        workflow = client.get(f"/api/ai/workflows/{workflow_id}")
        last = workflow
        if workflow.get("status") not in {"queued", "queued_resume", "running"}:
            return workflow
        time.sleep(2)
    raise SmokeFailure(f"Workflow {workflow_id} did not reach a terminal state within {timeout_seconds} seconds. Last status: {last.get('status') if last else 'unknown'}")


def workflow_snapshot_summary(workflow: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": workflow["id"],
        "status": workflow["status"],
        "provider_mode": workflow.get("provider_mode"),
        "fixture_version": workflow.get("fixture_version"),
        "fixture_scenario": workflow.get("fixture_scenario"),
        "resume_checkpoint": workflow.get("resume_checkpoint"),
        "resume_from_step": workflow.get("resume_from_step"),
        "retry_count": workflow.get("retry_count"),
        "needs_merge": workflow.get("needs_merge"),
        "quality_degraded": workflow.get("quality_degraded"),
        "error_message": workflow.get("error_message"),
        "output_payload": workflow.get("output_payload"),
        "step_statuses": [
            {
                "step_key": step.get("step_key"),
                "status": step.get("status"),
                "version": step.get("version"),
                "attempt_no": step.get("attempt_no"),
                "provider_mode": step.get("provider_mode"),
                "provider": step.get("provider"),
                "model": step.get("model"),
                "profile_name": step.get("profile_name"),
                "fallback_count": step.get("fallback_count"),
                "invalidated_by_step": step.get("invalidated_by_step"),
                "user_edited": step.get("user_edited"),
            }
            for step in workflow.get("steps", [])
        ],
    }


def summarize_run_events(collector: RuntimeEventCollector, run_id: str, *, settle_seconds: float = 1.0) -> dict[str, Any]:
    time.sleep(settle_seconds)
    events = [item for item in collector.snapshot() if item.get("run_id") == run_id]
    counts = Counter(item.get("event") or "runtime" for item in events)
    return {
        "count": len(events),
        "counts": dict(counts),
        "events": events[-40:],
    }


def assert_event_present(scenario_report: dict[str, Any], event_summary: dict[str, Any], event_name: str, detail: str) -> None:
    add_assertion(scenario_report, f"event:{event_name}", event_summary.get("counts", {}).get(event_name, 0) > 0, detail)


def scenario_payload(scene_id: str, provider_mode: str, fixture_scenario: str, *, auto_apply: bool) -> dict[str, Any]:
    return {
        "scene_id": scene_id,
        "length": "short",
        "guidance": SMOKE_GUIDANCE,
        "auto_apply": auto_apply,
        "provider_mode": provider_mode,
        "fixture_scenario": fixture_scenario,
    }


def run_happy_path_scenario(client: ApiClient, collector: RuntimeEventCollector, scene: dict[str, Any], provider_mode: str) -> dict[str, Any]:
    scenario_report: dict[str, Any] = {
        "name": "happy_path",
        "requested_provider_mode": provider_mode,
        "effective_provider_mode": provider_mode,
        "fixture_scenario": "happy_path",
        "expected_status": "completed",
        "actual_status": None,
        "resume_checkpoint": None,
        "step_statuses": [],
        "event_summary": {},
        "assertions": [],
    }
    baseline_run = client.post("/api/ai/workflows/scene/run-sync", scenario_payload(scene["id"], provider_mode, "happy_path", auto_apply=True))
    scenario_report["effective_provider_mode"] = baseline_run.get("provider_mode")
    scenario_report["actual_status"] = baseline_run.get("status")
    scenario_report["baseline_response"] = workflow_snapshot_summary(baseline_run)
    add_assertion(scenario_report, "baseline_completed", baseline_run.get("status") == "completed", f"happy_path baseline should complete, got {baseline_run.get('status')}")

    workflow = client.get(f"/api/ai/workflows/{baseline_run['id']}")
    scenario_report["baseline"] = workflow_snapshot_summary(workflow)
    scenario_report["resume_checkpoint"] = workflow.get("resume_checkpoint")
    scenario_report["step_statuses"] = scenario_report["baseline"]["step_statuses"]
    add_assertion(scenario_report, "has_plan_step", latest_non_invalidated_step(workflow, "plan") is not None, "happy_path must include a completed plan step")
    add_assertion(scenario_report, "has_write_step", latest_non_invalidated_step(workflow, "write") is not None, "happy_path must include a completed write step")

    checkpoint_step = latest_non_invalidated_step(workflow, workflow.get("resume_checkpoint"))
    add_assertion(scenario_report, "resume_checkpoint_present", checkpoint_step is not None, "happy_path must expose a valid resume checkpoint")
    resume_response = client.post(
        f"/api/ai/workflows/{workflow['id']}/resume",
        {
            "idempotency_key": f"smoke-happy-resume-{int(time.time())}",
            "expected_step_version": checkpoint_step["version"],
            "resume_from_step": "write",
        },
    )
    add_assertion(scenario_report, "resume_queued", resume_response.get("status") == "queued_resume", "happy_path resume must queue the workflow")
    resumed_workflow = poll_workflow(client, workflow["id"])
    scenario_report["after_resume"] = workflow_snapshot_summary(resumed_workflow)
    add_assertion(scenario_report, "resume_appended_write", step_attempt_count(resumed_workflow, "write") >= 2, "happy_path resume must append another write attempt")

    latest_plan = latest_non_invalidated_step(resumed_workflow, "plan")
    add_assertion(scenario_report, "override_source_plan_exists", latest_plan is not None, "planner override requires a plan step")
    effective_snapshot = latest_plan.get("effective_output_snapshot")
    override_snapshot = deepcopy(effective_snapshot) if isinstance(effective_snapshot, dict) else {"content": effective_snapshot}
    override_snapshot["smoke_override_note"] = "planner override applied by acceptance smoke"
    write_count_before_override = step_attempt_count(resumed_workflow, "write")
    override_response = client.post(
        f"/api/ai/workflows/{workflow['id']}/steps/plan/override",
        {
            "idempotency_key": f"smoke-happy-override-{int(time.time())}",
            "expected_step_version": latest_plan["version"],
            "derived_from_version": latest_plan["version"],
            "edited_reason": SMOKE_OVERRIDE_REASON,
            "effective_output_snapshot": override_snapshot,
        },
    )
    add_assertion(scenario_report, "override_queued", override_response.get("status") == "queued_resume", "planner override must queue resume")
    add_assertion(scenario_report, "override_resumes_from_write", override_response.get("resume_from_step") == "write", "planner override must resume from write")
    overridden_workflow = poll_workflow(client, workflow["id"])
    scenario_report["after_override"] = workflow_snapshot_summary(overridden_workflow)
    override_step = max(
        [step for step in overridden_workflow.get("steps", []) if step.get("step_key") == "plan" and step.get("user_edited")],
        key=lambda item: (item.get("attempt_no", 0), item.get("version", 0)),
        default=None,
    )
    add_assertion(scenario_report, "override_creates_user_edited_plan", override_step is not None, "planner override must create a user-edited plan step")
    invalidated = [
        step
        for step in overridden_workflow.get("steps", [])
        if step.get("status") == "invalidated" and step.get("invalidated_by_step") == override_step["id"]
    ] if override_step else []
    add_assertion(scenario_report, "override_invalidates_downstream", len(invalidated) > 0, "planner override must invalidate downstream steps")
    add_assertion(scenario_report, "override_appends_write_attempt", step_attempt_count(overridden_workflow, "write") > write_count_before_override, "planner override resume must append another write attempt")
    add_assertion(scenario_report, "override_keeps_provider_mode", overridden_workflow.get("provider_mode") == "smoke_fixture", "planner override flow must preserve smoke_fixture mode")

    scenario_report["event_summary"] = summarize_run_events(collector, workflow["id"])
    assert_event_present(scenario_report, scenario_report["event_summary"], "step_started", "happy_path must emit step_started events")
    assert_event_present(scenario_report, scenario_report["event_summary"], "step_completed", "happy_path must emit step_completed events")
    assert_event_present(scenario_report, scenario_report["event_summary"], "workflow_resumed", "happy_path must emit workflow_resumed events during resume/override")
    return scenario_report


def run_style_fail_scenario(client: ApiClient, collector: RuntimeEventCollector, scene: dict[str, Any], provider_mode: str) -> dict[str, Any]:
    scenario_report: dict[str, Any] = {
        "name": "style_fail",
        "requested_provider_mode": provider_mode,
        "effective_provider_mode": provider_mode,
        "fixture_scenario": "style_fail",
        "expected_status": "failed",
        "actual_status": None,
        "resume_checkpoint": None,
        "step_statuses": [],
        "event_summary": {},
        "assertions": [],
    }
    baseline_run = client.post("/api/ai/workflows/scene/run-sync", scenario_payload(scene["id"], provider_mode, "style_fail", auto_apply=True))
    scenario_report["effective_provider_mode"] = baseline_run.get("provider_mode")
    scenario_report["actual_status"] = baseline_run.get("status")
    scenario_report["baseline_response"] = workflow_snapshot_summary(baseline_run)
    add_assertion(scenario_report, "baseline_failed", baseline_run.get("status") == "failed", f"style_fail should fail, got {baseline_run.get('status')}")

    workflow = client.get(f"/api/ai/workflows/{baseline_run['id']}")
    scenario_report["baseline"] = workflow_snapshot_summary(workflow)
    scenario_report["resume_checkpoint"] = workflow.get("resume_checkpoint")
    scenario_report["step_statuses"] = scenario_report["baseline"]["step_statuses"]
    style_step = latest_non_invalidated_step(workflow, "style")
    write_step = latest_non_invalidated_step(workflow, "write")
    add_assertion(scenario_report, "style_step_failed", style_step is not None and style_step.get("status") == "failed", "style_fail must fail on the style step")
    add_assertion(scenario_report, "resume_checkpoint_is_write", workflow.get("resume_checkpoint") == "write", "style_fail must expose write as the stable resume checkpoint")
    add_assertion(scenario_report, "write_step_exists", write_step is not None, "style_fail must complete write before failing")
    analyze_count_before = step_attempt_count(workflow, "analyze")
    plan_count_before = step_attempt_count(workflow, "plan")
    write_count_before = step_attempt_count(workflow, "write")
    style_count_before = step_attempt_count(workflow, "style")

    resume_response = client.post(
        f"/api/ai/workflows/{workflow['id']}/resume",
        {
            "idempotency_key": f"smoke-style-resume-{int(time.time())}",
            "expected_step_version": write_step["version"],
        },
    )
    add_assertion(scenario_report, "resume_queued", resume_response.get("status") == "queued_resume", "style_fail resume must queue the workflow")
    add_assertion(scenario_report, "resume_from_style", resume_response.get("resume_from_step") == "style", "style_fail resume must continue from style")

    resumed_workflow = poll_workflow(client, workflow["id"])
    scenario_report["after_resume"] = workflow_snapshot_summary(resumed_workflow)
    add_assertion(scenario_report, "resume_completes", resumed_workflow.get("status") == "completed", f"style_fail resumed workflow should complete, got {resumed_workflow.get('status')}")
    add_assertion(scenario_report, "analyze_not_rerun", step_attempt_count(resumed_workflow, "analyze") == analyze_count_before, "style_fail resume must not rerun analyze")
    add_assertion(scenario_report, "plan_not_rerun", step_attempt_count(resumed_workflow, "plan") == plan_count_before, "style_fail resume must not rerun plan")
    add_assertion(scenario_report, "write_not_rerun", step_attempt_count(resumed_workflow, "write") == write_count_before, "style_fail resume must not rerun write")
    add_assertion(scenario_report, "style_rerun_once", step_attempt_count(resumed_workflow, "style") > style_count_before, "style_fail resume must append a new style attempt")

    scenario_report["event_summary"] = summarize_run_events(collector, workflow["id"])
    assert_event_present(scenario_report, scenario_report["event_summary"], "step_failed", "style_fail must emit step_failed events")
    assert_event_present(scenario_report, scenario_report["event_summary"], "workflow_resumed", "style_fail resume must emit workflow_resumed")
    assert_event_present(scenario_report, scenario_report["event_summary"], "step_completed", "style_fail resume must emit completed step events")
    return scenario_report


def run_planner_wait_review_scenario(client: ApiClient, collector: RuntimeEventCollector, scene: dict[str, Any], provider_mode: str) -> dict[str, Any]:
    scenario_report: dict[str, Any] = {
        "name": "planner_wait_review",
        "requested_provider_mode": provider_mode,
        "effective_provider_mode": provider_mode,
        "fixture_scenario": "planner_wait_review",
        "expected_status": "waiting_user_review",
        "actual_status": None,
        "resume_checkpoint": None,
        "step_statuses": [],
        "event_summary": {},
        "assertions": [],
    }
    baseline_run = client.post("/api/ai/workflows/scene/run-sync", scenario_payload(scene["id"], provider_mode, "planner_wait_review", auto_apply=True))
    scenario_report["effective_provider_mode"] = baseline_run.get("provider_mode")
    scenario_report["actual_status"] = baseline_run.get("status")
    scenario_report["baseline_response"] = workflow_snapshot_summary(baseline_run)
    add_assertion(scenario_report, "baseline_waiting_review", baseline_run.get("status") == "waiting_user_review", f"planner_wait_review should pause for review, got {baseline_run.get('status')}")

    workflow = client.get(f"/api/ai/workflows/{baseline_run['id']}")
    scenario_report["baseline"] = workflow_snapshot_summary(workflow)
    scenario_report["resume_checkpoint"] = workflow.get("resume_checkpoint")
    scenario_report["step_statuses"] = scenario_report["baseline"]["step_statuses"]
    plan_step = latest_non_invalidated_step(workflow, "plan")
    add_assertion(scenario_report, "plan_waiting_review", plan_step is not None and plan_step.get("status") == "waiting_user_review", "planner_wait_review must stop at the plan step")
    add_assertion(scenario_report, "plan_has_machine_snapshot", bool(plan_step and plan_step.get("machine_output_snapshot")), "planner_wait_review must keep machine_output_snapshot")
    add_assertion(scenario_report, "plan_has_effective_snapshot", bool(plan_step and plan_step.get("effective_output_snapshot")), "planner_wait_review must keep effective_output_snapshot")

    effective_snapshot = plan_step.get("effective_output_snapshot") if plan_step else {}
    override_snapshot = deepcopy(effective_snapshot) if isinstance(effective_snapshot, dict) else {"content": effective_snapshot}
    override_snapshot["smoke_override_note"] = "planner_wait_review override"
    override_response = client.post(
        f"/api/ai/workflows/{workflow['id']}/steps/plan/override",
        {
            "idempotency_key": f"smoke-plan-review-{int(time.time())}",
            "expected_step_version": plan_step["version"],
            "derived_from_version": plan_step["version"],
            "edited_reason": SMOKE_OVERRIDE_REASON,
            "effective_output_snapshot": override_snapshot,
        },
    )
    add_assertion(scenario_report, "override_queued", override_response.get("status") == "queued_resume", "planner_wait_review override must queue resume")
    add_assertion(scenario_report, "override_resumes_from_write", override_response.get("resume_from_step") == "write", "planner_wait_review override must resume from write")

    resumed_workflow = poll_workflow(client, workflow["id"])
    scenario_report["after_override"] = workflow_snapshot_summary(resumed_workflow)
    add_assertion(scenario_report, "override_preserves_mode", resumed_workflow.get("provider_mode") == "smoke_fixture", "planner_wait_review override must preserve smoke_fixture mode")
    add_assertion(scenario_report, "override_progresses_to_write", latest_non_invalidated_step(resumed_workflow, "write") is not None, "planner_wait_review override must continue into downstream steps")
    add_assertion(scenario_report, "override_not_failed", resumed_workflow.get("status") != "failed", "planner_wait_review override flow must not fail")

    scenario_report["event_summary"] = summarize_run_events(collector, workflow["id"])
    assert_event_present(scenario_report, scenario_report["event_summary"], "workflow_waiting_review", "planner_wait_review must emit workflow_waiting_review")
    assert_event_present(scenario_report, scenario_report["event_summary"], "workflow_resumed", "planner_wait_review override must emit workflow_resumed")
    return scenario_report


def run_guard_block_scenario(client: ApiClient, collector: RuntimeEventCollector, scene: dict[str, Any], provider_mode: str) -> dict[str, Any]:
    scenario_report: dict[str, Any] = {
        "name": "guard_block",
        "requested_provider_mode": provider_mode,
        "effective_provider_mode": provider_mode,
        "fixture_scenario": "guard_block",
        "expected_status": "waiting_user_review",
        "actual_status": None,
        "resume_checkpoint": None,
        "step_statuses": [],
        "event_summary": {},
        "assertions": [],
    }
    baseline_run = client.post("/api/ai/workflows/scene/run-sync", scenario_payload(scene["id"], provider_mode, "guard_block", auto_apply=True))
    scenario_report["effective_provider_mode"] = baseline_run.get("provider_mode")
    scenario_report["actual_status"] = baseline_run.get("status")
    scenario_report["baseline_response"] = workflow_snapshot_summary(baseline_run)
    add_assertion(scenario_report, "baseline_waiting_review", baseline_run.get("status") == "waiting_user_review", f"guard_block should wait for review, got {baseline_run.get('status')}")

    workflow = client.get(f"/api/ai/workflows/{baseline_run['id']}")
    scenario_report["baseline"] = workflow_snapshot_summary(workflow)
    scenario_report["resume_checkpoint"] = workflow.get("resume_checkpoint")
    scenario_report["step_statuses"] = scenario_report["baseline"]["step_statuses"]
    guard_step = latest_non_invalidated_step(workflow, "guard")
    store_step = latest_non_invalidated_step(workflow, "store")
    add_assertion(scenario_report, "guard_waiting_review", guard_step is not None and guard_step.get("status") == "waiting_user_review", "guard_block must block at guard")
    add_assertion(scenario_report, "store_waiting_review", store_step is not None and store_step.get("status") == "waiting_user_review", "guard_block must carry review state into store")
    add_assertion(scenario_report, "guard_violations_present", bool((guard_step or {}).get("effective_output_snapshot", {}).get("violations")), "guard_block must include structured guard violations")

    scenario_report["event_summary"] = summarize_run_events(collector, workflow["id"])
    assert_event_present(scenario_report, scenario_report["event_summary"], "workflow_waiting_review", "guard_block must emit workflow_waiting_review")
    return scenario_report


def run_check_issue_scenario(client: ApiClient, collector: RuntimeEventCollector, scene: dict[str, Any], provider_mode: str) -> dict[str, Any]:
    scenario_report: dict[str, Any] = {
        "name": "check_issue",
        "requested_provider_mode": provider_mode,
        "effective_provider_mode": provider_mode,
        "fixture_scenario": "check_issue",
        "expected_status": "completed",
        "actual_status": None,
        "resume_checkpoint": None,
        "step_statuses": [],
        "event_summary": {},
        "assertions": [],
    }
    baseline_run = client.post("/api/ai/workflows/scene/run-sync", scenario_payload(scene["id"], provider_mode, "check_issue", auto_apply=True))
    scenario_report["effective_provider_mode"] = baseline_run.get("provider_mode")
    scenario_report["actual_status"] = baseline_run.get("status")
    scenario_report["baseline_response"] = workflow_snapshot_summary(baseline_run)
    add_assertion(scenario_report, "baseline_completed", baseline_run.get("status") == "completed", f"check_issue should complete, got {baseline_run.get('status')}")

    workflow = client.get(f"/api/ai/workflows/{baseline_run['id']}")
    scenario_report["baseline"] = workflow_snapshot_summary(workflow)
    scenario_report["resume_checkpoint"] = workflow.get("resume_checkpoint")
    scenario_report["step_statuses"] = scenario_report["baseline"]["step_statuses"]
    check_step = latest_non_invalidated_step(workflow, "check")
    issue_count = ((check_step or {}).get("effective_output_snapshot") or {}).get("issue_count")
    add_assertion(scenario_report, "issues_surface_in_check_step", isinstance(issue_count, int) and issue_count > 0, "check_issue must surface structured issues in the check step")

    scenario_report["event_summary"] = summarize_run_events(collector, workflow["id"])
    assert_event_present(scenario_report, scenario_report["event_summary"], "step_started", "check_issue must emit step_started events")
    assert_event_present(scenario_report, scenario_report["event_summary"], "step_completed", "check_issue must emit step_completed events")
    return scenario_report


def run_malformed_planner_scenario(client: ApiClient, collector: RuntimeEventCollector, scene: dict[str, Any], provider_mode: str) -> dict[str, Any]:
    scenario_report: dict[str, Any] = {
        "name": "malformed_planner",
        "requested_provider_mode": provider_mode,
        "effective_provider_mode": provider_mode,
        "fixture_scenario": "malformed_planner",
        "expected_status": "failed",
        "actual_status": None,
        "resume_checkpoint": None,
        "step_statuses": [],
        "event_summary": {},
        "assertions": [],
    }
    baseline_run = client.post("/api/ai/workflows/scene/run-sync", scenario_payload(scene["id"], provider_mode, "malformed_planner", auto_apply=True))
    scenario_report["effective_provider_mode"] = baseline_run.get("provider_mode")
    scenario_report["actual_status"] = baseline_run.get("status")
    scenario_report["baseline_response"] = workflow_snapshot_summary(baseline_run)
    add_assertion(scenario_report, "baseline_failed", baseline_run.get("status") == "failed", f"malformed_planner should fail, got {baseline_run.get('status')}")

    workflow = client.get(f"/api/ai/workflows/{baseline_run['id']}")
    scenario_report["baseline"] = workflow_snapshot_summary(workflow)
    scenario_report["resume_checkpoint"] = workflow.get("resume_checkpoint")
    scenario_report["step_statuses"] = scenario_report["baseline"]["step_statuses"]
    plan_step = latest_non_invalidated_step(workflow, "plan")
    add_assertion(scenario_report, "plan_failed", plan_step is not None and plan_step.get("status") == "failed", "malformed_planner must fail at the plan step")
    add_assertion(scenario_report, "write_not_started", latest_non_invalidated_step(workflow, "write") is None, "malformed_planner must not reach write")

    scenario_report["event_summary"] = summarize_run_events(collector, workflow["id"])
    assert_event_present(scenario_report, scenario_report["event_summary"], "step_failed", "malformed_planner must emit step_failed")
    return scenario_report


def run_scenario(client: ApiClient, collector: RuntimeEventCollector, scene: dict[str, Any], provider_mode: str, scenario_name: str) -> dict[str, Any]:
    if scenario_name == "happy_path":
        return run_happy_path_scenario(client, collector, scene, provider_mode)
    if scenario_name == "style_fail":
        return run_style_fail_scenario(client, collector, scene, provider_mode)
    if scenario_name == "planner_wait_review":
        return run_planner_wait_review_scenario(client, collector, scene, provider_mode)
    if scenario_name == "guard_block":
        return run_guard_block_scenario(client, collector, scene, provider_mode)
    if scenario_name == "check_issue":
        return run_check_issue_scenario(client, collector, scene, provider_mode)
    if scenario_name == "malformed_planner":
        return run_malformed_planner_scenario(client, collector, scene, provider_mode)
    raise SmokeFailure(f"Unknown fixture scenario: {scenario_name}")


def run_branch_smoke(client: ApiClient, *, project_id: str, scene_id: str, versions: list[dict[str, Any]]) -> dict[str, Any]:
    source_version = versions[1]
    latest_version = versions[0]
    branch_name = f"{SMOKE_BRANCH_PREFIX}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    branch = client.post(
        "/api/branches",
        {
            "project_id": project_id,
            "name": branch_name,
            "description": "Acceptance smoke branch",
            "source_scene_id": scene_id,
            "source_version_id": source_version["id"],
            "latest_version_id": latest_version["id"],
            "metadata_json": {"smoke": True},
        },
    )
    diff = client.get(f"/api/branches/{branch['id']}/diff")
    ensure(len(diff.get("diff_rows", [])) > 0, "branch.diff", "Branch diff must contain rows")
    ensure(diff.get("source_text") != diff.get("branch_text"), "branch.diff", "Branch diff must show a text change")
    adopt = client.post(f"/api/branches/{branch['id']}/adopt", {})
    ensure(adopt.get("current_text") == SMOKE_LATEST_TEXT, "branch.adopt", "Branch adopt must restore the latest smoke text")
    return {
        "branch_id": branch["id"],
        "name": branch["name"],
        "source_version_id": source_version["id"],
        "latest_version_id": latest_version["id"],
        "diff_row_count": len(diff.get("diff_rows", [])),
        "adopted_version_id": adopt.get("adopted_version_id"),
    }


def resolve_scenarios(provider_mode: str, scenario: str) -> list[str]:
    if scenario != "all":
        if scenario not in SCENARIO_SPECS:
            raise SmokeFailure(f"Unsupported scenario: {scenario}")
        return [scenario]
    if provider_mode == "live":
        return ["happy_path"]
    return list(DEFAULT_FIXTURE_MATRIX)


def run_full_smoke(base_url: str, report_path: Path, *, provider_mode: str, scenario: str) -> dict[str, Any]:
    client = ApiClient(base_url=base_url)
    report: dict[str, Any] = {
        "started_at": iso_now(),
        "base_url": base_url,
        "requested_provider_mode": provider_mode,
        "effective_provider_mode": provider_mode,
        "requested_scenario": scenario,
        "health": {},
        "self_check": {},
        "provider_matrix": {},
        "provider_preflight": {},
        "seed_data": {},
        "workflow": {},
        "branch": {},
        "scenarios": [],
        "failure_stage": None,
        "blocking_reasons": [],
    }
    collector = RuntimeEventCollector(base_url)

    try:
        health = client.get("/api/health")
        self_check = client.get("/api/runtime/self-check")
        provider_matrix = client.get("/api/ai/provider-matrix")
        provider_state = client.get("/api/runtime/provider-state")
        ensure(health.get("status") == "ok", "health", "Backend health status is not ok")
        ensure(health.get("schema_ready") is True, "health", "schema_ready must be true")
        ensure(health.get("workflow_runner_started") is True, "health", "workflow_runner_started must be true")
        ensure(health.get("provider_matrix_loaded") is True, "health", "provider_matrix_loaded must be true")
        ensure(health.get("provider_runtime_ready") in {True, False}, "health", "provider_runtime_ready must be present")
        ensure(self_check.get("workflow_runtime", {}).get("recovery_scan_completed") is True, "self_check", "recovery scan must be completed")
        ensure(len(provider_matrix.get("rules", [])) > 0, "provider_matrix", "provider matrix must contain rules")
        report["health"] = health
        report["self_check"] = self_check
        report["provider_matrix"] = {
            "rule_count": len(provider_matrix.get("rules", [])),
            "steps": [rule.get("step") for rule in provider_matrix.get("rules", [])],
        }
        report["provider_preflight"] = {
            "summary": self_check.get("provider_runtime", {}),
            "providers": provider_state.get("providers", []),
            "steps": provider_state.get("steps", []),
        }

        provider_runtime = self_check.get("provider_runtime", {})
        if provider_mode == "live" and provider_runtime.get("ok") is False:
            report["failure_stage"] = "preflight_blocked"
            blocked_steps = list(provider_runtime.get("blocked_steps", []))
            step_reasons = []
            for step in provider_state.get("steps", []):
                if step.get("step") in blocked_steps:
                    step_reasons.extend(step.get("blocking_reasons", []))
            report["blocking_reasons"] = sorted(set(blocked_steps + step_reasons))
            raise SmokeFailure(
                "Preflight blocked by provider runtime: " + "; ".join(report["blocking_reasons"]) if report["blocking_reasons"] else "Preflight blocked by provider runtime",
                report=report,
            )

        project = ensure_project(client, report["seed_data"])
        book = ensure_book(client, project["id"], report["seed_data"])
        chapter = ensure_chapter(client, book["id"], report["seed_data"])
        scene = ensure_scene(client, chapter["id"], report["seed_data"])

        scene = update_scene_text(client, scene, target_text=SMOKE_SOURCE_TEXT, label="smoke source snapshot")
        scene = update_scene_text(client, scene, target_text=SMOKE_LATEST_TEXT, label="smoke latest snapshot")
        versions = client.get(f"/api/scenes/{scene['id']}/versions")
        ensure(len(versions) >= 2, "seed_data", "Smoke scene must have at least two stored versions")
        report["seed_data"]["versions"] = [
            {"id": item["id"], "label": item.get("label"), "source": item.get("source"), "created_at": item.get("created_at")}
            for item in versions[:5]
        ]

        context = client.get(f"/api/scenes/{scene['id']}/context")
        snapshot = context.get("context_compile_snapshot")
        ensure(isinstance(snapshot, dict), "context", "context_compile_snapshot must be present")
        ensure(isinstance(snapshot.get("hard_filter_result"), dict), "context", "hard_filter_result must be present")
        ensure(isinstance(snapshot.get("budget"), dict), "context", "budget must be present")
        ensure(isinstance(snapshot.get("scope_resolution"), dict), "context", "scope_resolution must be present")
        report["seed_data"]["context"] = {
            "scene_version": context.get("scene_version"),
            "candidate_count": len(snapshot.get("candidates", [])),
            "summary_reason": snapshot.get("summary_reason"),
            "deduped_sources": snapshot.get("deduped_sources", []),
            "clipped_sources": snapshot.get("clipped_sources", []),
        }

        collector.start()
        scenario_names = resolve_scenarios(provider_mode, scenario)
        for scenario_name in scenario_names:
            scenario_report = run_scenario(client, collector, scene, provider_mode, scenario_name)
            report["scenarios"].append(scenario_report)
            if scenario_name == "happy_path":
                report["workflow"] = {
                    key: value
                    for key, value in scenario_report.items()
                    if key in {"baseline_response", "baseline", "after_resume", "after_override"}
                }

        if report["scenarios"]:
            report["effective_provider_mode"] = report["scenarios"][0].get("effective_provider_mode") or report["effective_provider_mode"]

        if provider_mode == "smoke_fixture":
            report["branch"] = run_branch_smoke(client, project_id=project["id"], scene_id=scene["id"], versions=versions)

        report["finished_at"] = iso_now()
        return report
    except SmokeFailure as exc:
        if report.get("failure_stage") is None:
            report["failure_stage"] = "execution_failed"
        if not report.get("blocking_reasons"):
            report["blocking_reasons"] = [str(exc)]
        exc.report = report
        raise
    except Exception as exc:
        report["failure_stage"] = report.get("failure_stage") or "execution_failed"
        if not report.get("blocking_reasons"):
            report["blocking_reasons"] = [str(exc)]
        raise SmokeFailure(str(exc), report=report) from exc
    finally:
        collector.stop()


def write_report(report_path: Path, report: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run WriterLab backend full acceptance smoke.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--report-path", required=True)
    parser.add_argument("--provider-mode", choices=["smoke_fixture", "live"], default="smoke_fixture")
    parser.add_argument("--scenario", choices=["all", *SCENARIO_SPECS.keys()], default="all")
    args = parser.parse_args()

    report_path = Path(args.report_path)
    report: dict[str, Any] = {"started_at": iso_now(), "base_url": args.base_url, "requested_scenario": args.scenario}
    try:
        report = run_full_smoke(args.base_url, report_path, provider_mode=args.provider_mode, scenario=args.scenario)
        write_report(report_path, report)
        print(f"Backend full smoke passed. Report: {report_path}")
        return 0
    except Exception as exc:
        report = getattr(exc, "report", report)
        report["finished_at"] = iso_now()
        report["error"] = str(exc)
        write_report(report_path, report)
        print(f"Backend full smoke failed. Report: {report_path}", file=sys.stderr)
        if report.get("failure_stage") == "preflight_blocked":
            print("Preflight blocked by provider runtime.", file=sys.stderr)
        elif report.get("failure_stage") == "execution_failed":
            print("Workflow execution failed after preflight passed.", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
