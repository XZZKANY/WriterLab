# WriterLab Runtime Runbook

## Standard Startup Order
1. Install backend dependencies:
   `powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\install-backend.ps1`
2. Run backend static checks:
   `powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\check-backend.ps1`
3. Start backend.
   `start-backend.ps1` now runs `alembic upgrade head` before launching FastAPI.
   `powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\start-backend.ps1`
4. Run frontend checks:
   `powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1`
5. Start frontend:
   `powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\start-frontend.ps1`
6. Run live smoke after the stack is up:
   `powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\check-backend.ps1 -FullSmoke`
   `powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\check-backend.ps1 -FullSmoke -Scenario style_fail`
   `powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\check-backend.ps1 -FullSmoke -LiveProviders`
   `powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1 -LiveUiSmoke`

## Live Smoke Matrix
- Backend deterministic smoke:
  `check-backend.ps1 -FullSmoke`
  This now defaults to `provider_mode=smoke_fixture` and runs the deterministic fixture matrix: `happy_path`, `style_fail`, `planner_wait_review`, `guard_block`, `check_issue`, `malformed_planner`.
- Backend deterministic single-scenario smoke:
  `check-backend.ps1 -FullSmoke -Scenario guard_block`
  Use this when debugging one deterministic branch without running the full matrix.
- Backend live-provider smoke:
  `check-backend.ps1 -FullSmoke -LiveProviders`
  Use this only when validating real cloud/local model availability.
- Backend readiness:
  `GET /api/health`
  Expect `schema_ready=true`, `workflow_runner_started=true`, `provider_matrix_loaded=true`, and `provider_runtime_ready=true` when live-provider smoke can continue into workflow execution.
- Runtime self-check:
  `GET /api/runtime/self-check`
  Expect backend root info, health snapshot, pgvector status, provider matrix summary, workflow runtime readiness, and provider runtime summary.
- Provider runtime state:
  `GET /api/runtime/provider-state`
  Expect provider-level circuit/enablement data, profile-level skip reasons, and step-level readiness for `analyze`, `planner`, `write`, `style`, and `check`.
- Provider matrix:
  `GET /api/ai/provider-matrix`
  Expect step-level fallback rules to be present.
- Workflow flow:
  deterministic fixture matrix -> inspect `Workflow Debug` -> validate runtime events -> explicit `/resume` / Planner override subflows where applicable -> verify downstream invalidation and resumed attempts.
- Branch flow:
  create branch -> diff -> adopt.
- Frontend live UI smoke:
  request `/editor` over raw socket and verify `Workflow Debug`, `Runtime Readiness`, and `Runtime Self-Check Alert` markers in the HTML.

## Smoke Data Namespace
- The acceptance flow reuses one fixed namespace in the local database:
  `WriterLab Smoke Project` -> `Smoke Book` -> `Smoke Chapter 1` -> `Smoke Scene 1`
- Branch smoke uses timestamped names prefixed with `smoke-branch-`.
- This flow is intentionally mutating inside the smoke namespace. It will append scene versions and smoke branches, but it will not touch non-smoke data.

## Smoke Reports
- `check-backend.ps1 -FullSmoke` writes a JSON report to `scripts/logs/backend-full-smoke-*.json`
- `check-frontend.ps1 -LiveUiSmoke` writes a JSON report to `scripts/logs/frontend-live-smoke-*.json`
- Smoke report browsing APIs:
  `GET /api/runtime/smoke-reports`
  `GET /api/runtime/smoke-reports/latest`
  `GET /api/runtime/smoke-reports/{filename}`
  `GET /api/runtime/smoke-reports/{filename}/regression`
- Backend reports include at least:
  `requested_provider_mode`, `effective_provider_mode`, `requested_scenario`, `health`, `self_check`, `provider_matrix`, `provider_preflight`, `seed_data`, `workflow`, `branch`, `scenarios`
- Each `scenarios[]` entry records:
  `name`, `fixture_scenario`, `expected_status`, `actual_status`, `resume_checkpoint`, `step_statuses`, `event_summary`, `assertions`
- Any failed assertion should leave a partial report behind so the last successful step is visible.
- Regression compare is computed at read time. It does not modify historical JSON files under `scripts/logs`.
- Regression baseline selection is fixed to the most recent earlier successful report with the same report type. Backend reports must also match `provider_mode`.
- `smoke_fixture` and `live` backend reports never compare against each other.

## Failure Interpretation
- `failure_stage=preflight_blocked`
  Provider runtime is currently blocking live-provider smoke execution. Treat this as an environment/runtime readiness issue, not a workflow logic regression.
- `failure_stage=execution_failed`
  Provider preflight passed and the workflow/context/branch chain itself failed. Treat this as a real smoke execution regression.
- `smoke_fixture` mode does not participate in live provider readiness, fallback ranking, or circuit state management.
- Runtime event capture is now part of deterministic smoke acceptance. Missing `step_started`, `step_completed`, `step_failed`, `workflow_waiting_review`, or `workflow_resumed` events for the relevant scenario should be treated as a smoke failure.
- `check-backend.ps1 -FullSmoke` now prints one of:
  `Preflight blocked by provider runtime`
  `Workflow execution failed after preflight passed`

## Known Environment Caveat
- `npm.cmd run build:node` may fail with Windows `spawn EPERM` in restricted shells.
- Treat that as an environment limitation unless TypeScript compilation also fails.
- `scripts/check-frontend.ps1` now treats `spawn EPERM` as a warning, not a code regression.
- `check-frontend.ps1 -LiveUiSmoke` does not use `Invoke-WebRequest`; it uses a raw socket Node script to avoid local PowerShell web-client anomalies.

## Health and Self-Check Endpoints
- `GET /api/health`
  Returns readiness booleans for schema, workflow runner, recovery scan, pgvector, provider matrix, and backend version.
- `GET /api/runtime/self-check`
  Aggregates backend root info, health, knowledge retrieval mode, provider matrix readiness, workflow runtime status, and recommended local verification commands.

## Recovery Semantics
- Startup runs `recover_expired_workflow_runs` before the workflow runner starts.
- If startup fails, `last_startup_stage` and `startup_error` will surface through `/api/health` and `/api/runtime/self-check`.

## Demo Data Repair
- Demo repair is optional and not part of the normal startup path.
- Dry run:
  `D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe D:\WritierLab\WriterLab-v1\scripts\fix_demo_garbled_data.py`
- Apply:
  `D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe D:\WritierLab\WriterLab-v1\scripts\fix_demo_garbled_data.py --apply`
