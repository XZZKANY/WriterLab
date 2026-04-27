"use client";

import { useEffect, useMemo, useState } from "react";
import { WorkspaceShell } from "@/shared/ui/workspace-shell";
import { useRuntimeDiagnostics } from "@/features/runtime/hooks/use-runtime-diagnostics";
import { cancelWorkflowRun, fetchWorkflowRun, overrideWorkflowStep, resumeWorkflowRun } from "@/lib/api/workflow";

type DiffRow = { type: "add" | "remove" | "context"; text: string };
type ActiveContextSnapshot = { hard_filters?: string[]; hard_filter_result?: Record<string, unknown>; scope_resolution?: Record<string, unknown>; source_diversity_applied?: Record<string, unknown>; budget?: Record<string, unknown>; summary_reason?: string | null; deduped_sources?: string[]; clipped_sources?: string[]; candidates?: { source_type: string; source_id: string; title: string; score: number; diversity_slot?: string | null; summary_applied?: boolean }[]; summary_output?: unknown[] };
type WorkflowViolation = { type?: string | null; severity?: string | null; rule_id?: string | null; reason?: string | null; span?: string | null; suggestion?: string | null };
type WorkflowStep = { id: string; step_key: string; status: string; version?: number; attempt_no?: number; invalidated_by_step?: string | null; provider_mode?: string | null; provider?: string | null; model?: string | null; profile_name?: string | null; error_message?: string | null; fallback_count?: number | null; guardrail_blocked?: boolean | null; output_payload?: Record<string, unknown> | null; machine_output_snapshot?: Record<string, unknown> | null; effective_output_snapshot?: Record<string, unknown> | null; attempts?: Record<string, unknown>[]; edited_reason?: string | null };
type WorkflowRun = { id: string; status: string; provider_mode?: string | null; fixture_version?: string | null; fixture_scenario?: string | null; retry_count?: number; needs_merge?: boolean; quality_degraded?: boolean; resume_checkpoint?: string | null; resume_from_step?: string | null; worker_id?: string | null; lease_expires_at?: string | null; context_compile_snapshot?: ActiveContextSnapshot | null; output_payload?: Record<string, unknown> | null; error_message?: string | null; steps: WorkflowStep[] };

const section = "rounded-3xl border border-white/8 bg-zinc-900/80 p-5 shadow-2xl";
const field = "rounded-2xl border border-white/10 bg-zinc-950 px-4 py-3 text-sm text-zinc-200";

export default function RuntimeDebugWorkbench() {
  const [busyKey, setBusyKey] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [workflowIdInput, setWorkflowIdInput] = useState("");
  const [workflow, setWorkflow] = useState<WorkflowRun | null>(null);
  const [runtimeConnection, setRuntimeConnection] = useState<"idle" | "connected" | "reconnecting">("idle");
  const [selectedWorkflowStepId, setSelectedWorkflowStepId] = useState("");
  const [plannerOverrideDraft, setPlannerOverrideDraft] = useState("");
  const diagnostics = useRuntimeDiagnostics({ setBusyKey, setMessage: (ok, nextError) => { setMessage(ok); setError(nextError ?? null); } });
  const { providerSettings, providerRuntime, providerMatrix, runtimeSelfCheck, selectedSmokeRegression, selectedSmokeReport, selectedSmokeReportFilename, smokeLatest, smokeReports, updateProviderField, saveProviderSettingsState, loadProviderRuntimeState, loadRuntimeReadiness, loadSmokeLatestState, loadSmokeReportsState, refreshAllDiagnostics, setSelectedSmokeReportFilename } = diagnostics;
  const selectedWorkflowStep = workflow?.steps.find((step) => step.id === selectedWorkflowStepId) ?? null;
  const workflowPreview = readPayloadString(workflow?.output_payload, "final_text") || readPayloadString(workflow?.output_payload, "partial_text");
  const workflowAutoApplied = readPayloadBoolean(workflow?.output_payload, "auto_applied") === true;
  const workflowSafeToApply = readPayloadBoolean(workflow?.output_payload, "safe_to_apply") !== false;
  const rejectedPreview = readPayloadString(workflow?.steps.find((step) => step.guardrail_blocked)?.output_payload, "rejected_text_preview");
  const selectedWorkflowStepDiffRows = selectedWorkflowStep ? makeDiffRows(snapshotToText(selectedWorkflowStep.machine_output_snapshot), snapshotToText(selectedWorkflowStep.effective_output_snapshot ?? selectedWorkflowStep.output_payload)) : [];
  const workflowViolations = readPayloadArray<WorkflowViolation>(selectedWorkflowStep?.output_payload ?? workflow?.output_payload, "violations");
  const activeContextSnapshot = useMemo<ActiveContextSnapshot | null>(() => {
    const snapshot = selectedWorkflowStep?.output_payload?.context_compile_snapshot;
    if (snapshot && typeof snapshot === "object" && !Array.isArray(snapshot)) return snapshot as ActiveContextSnapshot;
    return workflow?.context_compile_snapshot ?? null;
  }, [selectedWorkflowStep, workflow]);

  useEffect(() => {
    if (!workflow?.steps.length) return setSelectedWorkflowStepId("");
    if (!workflow.steps.some((step) => step.id === selectedWorkflowStepId)) setSelectedWorkflowStepId(workflow.steps[workflow.steps.length - 1]?.id ?? "");
  }, [selectedWorkflowStepId, workflow]);

  useEffect(() => {
    if (selectedWorkflowStep?.step_key === "plan") {
      setPlannerOverrideDraft((current) => current || snapshotToText(selectedWorkflowStep.effective_output_snapshot ?? selectedWorkflowStep.output_payload));
    }
  }, [selectedWorkflowStep]);

  async function refreshAll() {
    setBusyKey("refreshAll");
    setMessage(null);
    setError(null);
    try {
      await refreshAllDiagnostics();
      if (workflow?.id) await loadWorkflowRun(workflow.id, false);
      setMessage("运行诊断已刷新");
    } catch (nextError) {
      setError(toErrorMessage(nextError, "刷新运行诊断失败"));
    } finally {
      setBusyKey("");
    }
  }

  async function loadWorkflowRun(workflowId = workflowIdInput.trim(), showBusy = true) {
    if (!workflowId) throw new Error("请输入 workflow id");
    if (showBusy) setBusyKey("loadWorkflow");
    try {
      const payload = await fetchWorkflowRun<WorkflowRun>(workflowId);
      setWorkflowIdInput(workflowId);
      setWorkflow(payload);
      setRuntimeConnection(["queued", "queued_resume", "running"].includes(payload.status) ? "connected" : "idle");
      return payload;
    } finally {
      if (showBusy) setBusyKey("");
    }
  }

  async function pollWorkflow(id: string) {
    setRuntimeConnection("connected");
    try {
      for (let attempt = 0; attempt < 40; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 1500));
        const payload = await fetchWorkflowRun<WorkflowRun>(id);
        setWorkflow(payload);
        if (["completed", "partial_success", "failed", "cancelled", "waiting_user_review"].includes(payload.status)) {
          return payload;
        }
      }
      throw new Error("工作流轮询超时");
    } finally {
      setRuntimeConnection("idle");
    }
  }

  async function retryWorkflow() {
    if (!workflow?.id) return;
    setBusyKey("retryWorkflow");
    setMessage(null);
    setError(null);
    try {
      const queued = await resumeWorkflowRun<WorkflowRun>(workflow.id, {
        idempotency_key: `resume-${Date.now()}`,
        expected_step_version: getResumeVersion(workflow),
        resume_from_step: workflow.resume_from_step ?? undefined,
      });
      setWorkflow(queued);
      if (!["completed", "partial_success", "failed", "cancelled", "waiting_user_review"].includes(queued.status)) {
        await pollWorkflow(queued.id);
      }
      await Promise.all([loadRuntimeReadiness(), loadProviderRuntimeState()]);
      setMessage("工作流已重新排队");
    } catch (nextError) {
      setError(toErrorMessage(nextError, "重试工作流失败"));
    } finally {
      setBusyKey("");
    }
  }

  async function cancelWorkflow() {
    if (!workflow?.id) return;
    setBusyKey("cancelWorkflow");
    setMessage(null);
    setError(null);
    try {
      setWorkflow(await cancelWorkflowRun<WorkflowRun>(workflow.id));
      setRuntimeConnection("idle");
      setMessage("工作流已取消");
    } catch (nextError) {
      setError(toErrorMessage(nextError, "取消工作流失败"));
    } finally {
      setBusyKey("");
    }
  }

  async function overridePlanner() {
    if (!workflow?.id || !selectedWorkflowStep || selectedWorkflowStep.step_key !== "plan") return;
    setBusyKey("retryWorkflow");
    setMessage(null);
    setError(null);
    try {
      const version = selectedWorkflowStep.version ?? 0;
      const queued = await overrideWorkflowStep<WorkflowRun>(workflow.id, selectedWorkflowStep.step_key, {
        idempotency_key: `override-${Date.now()}`,
        expected_step_version: version,
        derived_from_version: version,
        edited_reason: "runtime debug workbench planner override",
        effective_output_snapshot: parsePlannerSnapshot(plannerOverrideDraft),
      });
      setWorkflow(queued);
      if (!["completed", "partial_success", "failed", "cancelled", "waiting_user_review"].includes(queued.status)) {
        await pollWorkflow(queued.id);
      }
      await Promise.all([loadRuntimeReadiness(), loadProviderRuntimeState()]);
      setMessage("规划步骤已覆写并继续执行");
    } catch (nextError) {
      setError(toErrorMessage(nextError, "覆写规划步骤失败"));
    } finally {
      setBusyKey("");
    }
  }

  return <WorkspaceShell title="运行诊断" eyebrow="WriterLab" description="集中查看 Workflow Debug、运行时就绪度、Smoke Console、Provider Matrix、Context Compiler 与运行时自检告警。" actions={<button className={buttonClass("rounded-full border border-white/10 px-4 py-2 text-sm", busyKey === "refreshAll")} onClick={() => void refreshAll()} disabled={busyKey === "refreshAll"} type="button">{busyKey === "refreshAll" ? "刷新中..." : "刷新全部"}</button>}>
    {message ? <Notice tone="success" text={message} /> : null}
    {error ? <Notice tone="error" text={error} /> : null}
    <section className={section}>
      <div className="flex items-start justify-between gap-4"><div><h2 className="text-xl font-semibold">Workflow Debug</h2><p className="mt-1 text-sm text-zinc-500">通过 workflow id 检查 run、step 快照、恢复点与人工覆写。</p></div><div className="text-right text-xs text-zinc-500"><div>WS: {runtimeConnection}</div><div>run: {workflowStatusText(workflow?.status)}</div><div>checkpoint: {workflow?.resume_checkpoint || "n/a"}</div></div></div>
      <div className="mt-4 grid gap-3 lg:grid-cols-[1.15fr_0.85fr]"><input className={field} value={workflowIdInput} onChange={(event) => setWorkflowIdInput(event.target.value)} placeholder="输入 workflow id 后加载运行态" /><button className="rounded-2xl border border-white/10 px-4 py-3 text-sm" onClick={() => void loadWorkflowRun().catch((nextError) => setError(toErrorMessage(nextError, "读取工作流失败")))} type="button">加载 Workflow Run</button></div>
      <div className="mt-4 flex flex-wrap gap-3"><button className={buttonClass("rounded-full border border-white/10 px-4 py-2 text-sm", busyKey === "retryWorkflow")} onClick={() => void retryWorkflow()} disabled={!workflow?.id || busyKey === "retryWorkflow"} type="button">{busyKey === "retryWorkflow" ? "Retrying..." : "Resume / Retry"}</button><button className={buttonClass("rounded-full border border-white/10 px-4 py-2 text-sm", busyKey === "cancelWorkflow")} onClick={() => void cancelWorkflow()} disabled={!workflow?.id || busyKey === "cancelWorkflow"} type="button">{busyKey === "cancelWorkflow" ? "Cancelling..." : "Cancel"}</button></div>
      <div className="mt-4 grid gap-3 text-xs text-zinc-500 sm:grid-cols-2 lg:grid-cols-3"><Metric label="resume_from_step" value={workflow?.resume_from_step || "n/a"} /><Metric label="needs_merge" value={workflow?.needs_merge ? "true" : "false"} /><Metric label="quality_degraded" value={workflow?.quality_degraded ? "true" : "false"} /><Metric label="provider_mode" value={workflow?.provider_mode || "live"} /><Metric label="fixture_version" value={workflow?.fixture_version || "n/a"} /><Metric label="fixture_scenario" value={workflow?.fixture_scenario || "n/a"} /><Metric label="worker" value={workflow?.worker_id || "n/a"} /><Metric label="lease_expires_at" value={formatTime(workflow?.lease_expires_at)} /><Metric label="retry_count" value={String(workflow?.retry_count ?? 0)} /></div>
      {workflowPreview ? <div className="mt-4 rounded-2xl bg-zinc-900/70 px-4 py-4 text-sm text-zinc-300">{workflowAutoApplied ? "Workflow output was auto-applied to the scene." : workflowSafeToApply ? "Workflow output is safe but still awaiting manual application." : "Workflow output requires review before it can be applied."}<pre className="mt-3 whitespace-pre-wrap text-xs leading-6 text-zinc-400">{workflowPreview}</pre></div> : null}
      {rejectedPreview ? <pre className="mt-4 whitespace-pre-wrap rounded-2xl border border-rose-400/15 bg-rose-500/10 px-4 py-4 text-xs leading-6 text-rose-100">{rejectedPreview}</pre> : null}
      <div className="mt-4 space-y-3"><select className={`${field} w-full`} value={selectedWorkflowStep?.id ?? ""} onChange={(event) => setSelectedWorkflowStepId(event.target.value)}><option value="">Select step</option>{(workflow?.steps ?? []).map((step) => <option key={step.id} value={step.id}>{displayStepTitle(step)} - {workflowStatusText(step.status)} - v{step.version ?? 0}/a{step.attempt_no ?? 0}</option>)}</select>{(workflow?.steps ?? []).length ? <div className="grid gap-3">{(workflow?.steps ?? []).map((step) => <button key={step.id} type="button" className={`rounded-2xl border px-4 py-3 text-left text-xs ${selectedWorkflowStep?.id === step.id ? "border-zinc-100 bg-zinc-100 text-black" : "border-white/10 bg-zinc-900/70 text-zinc-300"}`} onClick={() => setSelectedWorkflowStepId(step.id)}><div className="font-semibold">{displayStepTitle(step)}</div><div className="mt-1">status: {workflowStatusText(step.status)} | version: {step.version ?? 0} | attempt: {step.attempt_no ?? 0}</div><div className="mt-1">provider_mode: {step.provider_mode || workflow?.provider_mode || "live"} | provider: {step.provider || "n/a"} | model: {step.model || "n/a"}</div><div className="mt-1">profile_name: {step.profile_name || "n/a"} | fallback_count: {step.fallback_count ?? 0}</div></button>)}</div> : null}</div>
    </section>
    <section className={section}>
      {selectedWorkflowStep ? <><div className="grid gap-4 lg:grid-cols-2"><Snapshot title="Machine Snapshot" value={snapshotToText(selectedWorkflowStep.machine_output_snapshot)} /><Snapshot title="Effective Snapshot" value={snapshotToText(selectedWorkflowStep.effective_output_snapshot ?? selectedWorkflowStep.output_payload)} /></div>{selectedWorkflowStepDiffRows.length ? <div className="mt-4 space-y-1">{selectedWorkflowStepDiffRows.map((row, index) => <div key={`${row.type}-${index}`} className={`rounded-xl px-3 py-2 text-xs ${lineClass(row.type)}`}>{row.type === "add" ? "+ " : row.type === "remove" ? "- " : "  "}{row.text || " "}</div>)}</div> : null}{workflowViolations.length ? <div className="mt-4 space-y-2">{workflowViolations.map((item, index) => <Status key={`${item.rule_id || item.type || "violation"}-${index}`} title={`${item.type || "violation"} | ${item.severity || "unknown"}`} lines={[`rule_id: ${item.rule_id || "no-rule-id"}`, `reason: ${item.reason || "No reason provided"}`, `span: ${item.span || "n/a"}`, `suggestion: ${item.suggestion || "n/a"}`]} tone="error" />)}</div> : null}{selectedWorkflowStep.step_key === "plan" ? <div className="mt-4 rounded-2xl bg-zinc-900/70 px-4 py-4"><div className="flex items-center justify-between gap-3"><div><div className="text-sm font-semibold text-zinc-100">Planner Override</div><div className="mt-1 text-xs text-zinc-500">提交后会调用 `/resume`，继续后续步骤。</div></div><button className={buttonClass("rounded-full bg-zinc-100 px-4 py-2 text-xs text-black", busyKey === "retryWorkflow")} onClick={() => void overridePlanner()} disabled={busyKey === "retryWorkflow"} type="button">{busyKey === "retryWorkflow" ? "Submitting..." : "Submit Override"}</button></div><textarea className="mt-3 min-h-[180px] w-full rounded-2xl border border-white/10 bg-zinc-950 px-4 py-3 font-mono text-xs leading-6 text-zinc-200" value={plannerOverrideDraft} onChange={(event) => setPlannerOverrideDraft(event.target.value)} /></div> : null}</> : <div className="rounded-2xl border border-dashed border-white/10 px-4 py-6 text-sm text-zinc-500">Load a workflow run and then pick a step to inspect the structured debug view.</div>}
    </section>
    <section className={section}>
      <div className="flex items-center justify-between gap-4"><div><h2 className="text-xl font-semibold">运行时就绪度</h2><p className="mt-1 text-sm text-zinc-500">查看 API 配置、provider 状态、步骤就绪度与 profile 明细。</p></div><button className="rounded-full border border-white/10 px-4 py-2 text-sm" onClick={() => void loadProviderRuntimeState().catch((nextError) => setError(toErrorMessage(nextError, "读取运行时状态失败")))} type="button">刷新</button></div>
      <div className="mt-4 rounded-2xl border border-white/6 bg-[#1d1d1d] p-4"><div className="flex items-center justify-between gap-4"><div><div className="text-sm font-semibold text-zinc-100">Cloud API Config</div><div className="mt-1 text-xs text-zinc-500">运行时和 smoke 统一复用这一套 provider 设置。</div></div><button className={buttonClass("rounded-full bg-zinc-100 px-4 py-2 text-sm text-black", busyKey === "saveProviderSettings")} onClick={() => void saveProviderSettingsState().catch((nextError) => setError(toErrorMessage(nextError, "保存 API 配置失败")))} disabled={busyKey === "saveProviderSettings"} type="button">{busyKey === "saveProviderSettings" ? "Saving..." : "Save API Config"}</button></div><div className="mt-4 space-y-4">{providerSettings.map((item) => <div key={item.provider} className="rounded-2xl bg-zinc-900/70 px-4 py-4"><div className="flex items-center justify-between gap-4"><div className="text-sm font-semibold text-zinc-100">{providerLabel(item.provider)}</div><div className="text-xs text-zinc-500">{item.has_api_key ? `Saved: ${item.api_key_masked ?? "configured"}` : "No API key saved yet"}</div></div><div className="mt-3 grid gap-3"><input className={field} value={item.api_base} onChange={(event) => updateProviderField(item.provider, "api_base", event.target.value)} placeholder="API Base URL" /><input className={field} type="password" value={item.api_key ?? ""} onChange={(event) => updateProviderField(item.provider, "api_key", event.target.value)} placeholder={item.has_api_key ? "留空则保留已保存密钥；输入新值则覆盖" : "Paste API key here"} /></div></div>)}</div></div>
      {providerRuntime ? <><div className="mt-4 grid gap-3 lg:grid-cols-2">{providerRuntime.providers.map((item) => <Status key={item.provider} title={item.provider} tone={item.enabled && item.remaining_cooldown_seconds === 0 ? "success" : "error"} lines={[`enabled: ${item.enabled ? "true" : "false"}`, `consecutive_failures: ${item.consecutive_failures}`, `remaining_cooldown_seconds: ${item.remaining_cooldown_seconds}`, `open_until: ${item.open_until || "n/a"}`, `enabled_reason: ${item.enabled_reason || "none"}`, `last_error: ${item.last_error || "none"}`]} />)}</div><div className="mt-4 grid gap-3 lg:grid-cols-2">{providerRuntime.steps.map((item) => <Status key={item.step} title={item.step} tone={item.ready ? "success" : "error"} lines={[`ready: ${item.ready ? "true" : "false"}`, `candidate_profiles: ${item.candidate_profiles.join(", ") || "none"}`, `blocking_reasons: ${item.blocking_reasons.join(" | ") || "none"}`]} />)}</div><div className="mt-4 space-y-3">{providerRuntime.profiles.map((item) => <Status key={`${item.profile_name}-${item.provider}-${item.model}`} title={item.profile_name} lines={[`provider/model: ${item.provider} / ${item.model}`, `task_type/workflow_step: ${item.task_type || "n/a"} / ${item.workflow_step || "n/a"}`, `spent/budget: ${item.spent_usd} / ${item.monthly_budget_usd ?? "n/a"}`, `requests_per_minute: ${item.requests_per_minute ?? "n/a"}`, `enabled: ${item.enabled ? "true" : "false"}`, `skip_reason: ${item.skip_reason || "none"}`]} />)}</div></> : <div className="mt-4 rounded-2xl border border-dashed border-white/10 px-4 py-6 text-sm text-zinc-500">运行时自检告警：尚未加载运行时数据。</div>}
    </section>
    <section className={section}>
      <div className="flex items-center justify-between gap-4"><div><h2 className="text-xl font-semibold">Smoke Console</h2><p className="mt-1 text-sm text-zinc-500">Read-only acceptance report browser for fixture smoke、live provider smoke 与 frontend live UI smoke。</p></div><button className="rounded-full border border-white/10 px-4 py-2 text-sm" onClick={() => void Promise.all([loadSmokeLatestState(), loadSmokeReportsState()]).catch((nextError) => setError(toErrorMessage(nextError, "刷新 smoke 报告失败")))} type="button">Refresh</button></div>
      <div className="mt-4 grid gap-3 lg:grid-cols-2"><Status title="Latest Backend Smoke" tone={smokeLatest?.backend_full_smoke?.success ? "success" : "neutral"} lines={[`type: ${smokeReportTypeLabel(smokeLatest?.backend_full_smoke?.report_type, smokeLatest?.backend_full_smoke?.provider_mode)}`, `provider_mode: ${smokeLatest?.backend_full_smoke?.provider_mode || "n/a"}`, `success: ${smokeLatest?.backend_full_smoke?.success ? "true" : "false"}`, `failure_stage: ${smokeLatest?.backend_full_smoke?.failure_stage || "none"}`, `scenario_count: ${smokeLatest?.backend_full_smoke?.scenario_count ?? 0}`, `created_at: ${formatTime(smokeLatest?.backend_full_smoke?.created_at)}`]} /><Status title="Latest Frontend Smoke" tone={smokeLatest?.frontend_live_smoke?.success ? "success" : "neutral"} lines={[`type: ${smokeReportTypeLabel(smokeLatest?.frontend_live_smoke?.report_type, smokeLatest?.frontend_live_smoke?.provider_mode)}`, `success: ${smokeLatest?.frontend_live_smoke?.success ? "true" : "false"}`, `created_at: ${formatTime(smokeLatest?.frontend_live_smoke?.created_at)}`, `filename: ${smokeLatest?.frontend_live_smoke?.filename || "暂无"}`]} /></div>
      <div className="mt-4 grid gap-3 lg:grid-cols-2"><select className={field} value={selectedSmokeReportFilename} onChange={(event) => setSelectedSmokeReportFilename(event.target.value)}>{smokeReports.map((item) => <option key={item.filename} value={item.filename}>{smokeReportTypeLabel(item.report_type, item.provider_mode)} · {item.filename}</option>)}</select><div className="rounded-2xl bg-zinc-900/70 px-4 py-3 text-xs text-zinc-500">reports: {smokeReports.length} | regression_findings: {selectedSmokeRegression?.findings.length ?? 0}</div></div>
      {selectedSmokeReport ? <div className="mt-4 space-y-4"><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"><Metric label="type" value={smokeReportTypeLabel(selectedSmokeReport.report_type, selectedSmokeReport.provider_mode)} /><Metric label="success" value={selectedSmokeReport.success ? "true" : "false"} /><Metric label="failure_stage" value={selectedSmokeReport.failure_stage || "none"} /><Metric label="provider_mode" value={selectedSmokeReport.provider_mode || selectedSmokeReport.effective_provider_mode || "n/a"} /><Metric label="scenario_count" value={String(selectedSmokeReport.scenario_count)} /><Metric label="created_at" value={formatTime(selectedSmokeReport.created_at)} /></div>{selectedSmokeRegression ? <div className="space-y-2"><Status title="Regression Compare" tone={selectedSmokeRegression.regression_free ? "success" : "error"} lines={[`comparable: ${selectedSmokeRegression.comparable ? "true" : "false"}`, `regression_free: ${selectedSmokeRegression.regression_free ? "true" : "false"}`, `current_report: ${selectedSmokeRegression.current_report.filename}`, `baseline_report: ${selectedSmokeRegression.baseline_report?.filename || "n/a"}`]} />{selectedSmokeRegression.findings.map((finding) => <Status key={`${finding.scope}-${finding.key}`} title={`${finding.scope} | ${finding.key}`} tone="error" lines={[finding.message, `baseline: ${String(finding.baseline_value ?? "n/a")}`, `current: ${String(finding.current_value ?? "n/a")}`]} />)}</div> : null}{selectedSmokeReport.scenarios.slice(0, 6).map((scenario) => <Status key={`${scenario.name}-${scenario.fixture_scenario || "default"}`} title={scenario.name} tone={scenario.expected_status === scenario.actual_status ? "success" : "neutral"} lines={[`expected: ${scenario.expected_status || "n/a"}`, `actual: ${scenario.actual_status || "n/a"}`, `resume_checkpoint: ${scenario.resume_checkpoint || "n/a"}`, `event_count: ${String(scenario.event_summary?.count ?? 0)}`, ...(scenario.assertions ?? []).slice(0, 4).map((assertion) => `${assertion.ok ? "PASS" : "FAIL"} | ${assertion.name} | ${assertion.detail || "n/a"}`)]} />)}</div> : <div className="mt-4 rounded-2xl border border-dashed border-white/10 px-4 py-6 text-sm text-zinc-500">Select a smoke report to inspect its structured detail.</div>}
    </section>
    <section className={section}>
      <h2 className="text-xl font-semibold">Provider Matrix</h2>
      <div className="mt-4 space-y-3">{providerMatrix.length ? providerMatrix.map((rule) => <Status key={rule.step} title={rule.step} lines={[`${rule.default_provider} / ${rule.default_model}`, `timeout: ${rule.timeout_ms} ms`, `retry: ${rule.retry_count}`, `fallback: ${rule.fallback_targets.map((item) => `${item.provider}/${item.model}`).join(" -> ") || "none"}`, `quality degraded: ${rule.quality_degraded_on_fallback ? "true" : "false"}`, rule.fallback_to_ollama_when]} />) : <div className="rounded-2xl border border-dashed border-white/10 px-4 py-6 text-sm text-zinc-500">暂未读取到 provider matrix。</div>}</div>
    </section>
    <section className={section}>
      <h2 className="text-xl font-semibold">Context Compiler</h2>
      {activeContextSnapshot ? <div className="mt-4 space-y-3"><div className="rounded-2xl bg-zinc-900/70 px-4 py-3 text-xs text-zinc-500">hard filters: {(activeContextSnapshot.hard_filters ?? []).join(" | ") || "none"}</div><div className="grid gap-3 sm:grid-cols-2"><pre className="rounded-2xl bg-zinc-900/70 px-4 py-4 text-xs leading-6">{JSON.stringify(activeContextSnapshot.hard_filter_result ?? {}, null, 2)}</pre><pre className="rounded-2xl bg-zinc-900/70 px-4 py-4 text-xs leading-6">{JSON.stringify(activeContextSnapshot.scope_resolution ?? {}, null, 2)}</pre><pre className="rounded-2xl bg-zinc-900/70 px-4 py-4 text-xs leading-6">{JSON.stringify(activeContextSnapshot.source_diversity_applied ?? {}, null, 2)}</pre><pre className="rounded-2xl bg-zinc-900/70 px-4 py-4 text-xs leading-6">{JSON.stringify(activeContextSnapshot.budget ?? {}, null, 2)}</pre></div>{(activeContextSnapshot.candidates ?? []).slice(0, 8).map((item) => <Status key={`${item.source_type}-${item.source_id}`} title={item.title} lines={[`type: ${item.source_type}`, `score: ${item.score.toFixed(4)}`, `slot: ${item.diversity_slot || "n/a"}`, item.summary_applied ? "summary applied" : "full item"]} />)}{activeContextSnapshot.summary_output?.length ? <pre className="rounded-2xl bg-zinc-900/70 px-4 py-4 text-xs leading-6">{JSON.stringify(activeContextSnapshot.summary_output, null, 2)}</pre> : null}</div> : runtimeSelfCheck ? <div className="mt-4 grid gap-3 lg:grid-cols-2"><Status title="Compile Inputs" lines={[`rule_count: ${runtimeSelfCheck.provider_matrix.rule_count}`, `provider_steps: ${runtimeSelfCheck.provider_matrix.steps.join(", ") || "none"}`, `open_circuit: ${runtimeSelfCheck.provider_runtime.providers_with_open_circuit.join(", ") || "none"}`, `providers_disabled: ${runtimeSelfCheck.provider_runtime.providers_disabled.join(", ") || "none"}`]} /><Status title="Recommended Checks" lines={Object.entries(runtimeSelfCheck.recommended_checks).flatMap(([group, commands]) => [`${group}:`, ...commands])} /></div> : <div className="mt-4 rounded-2xl border border-dashed border-white/10 px-4 py-6 text-sm text-zinc-500">当前没有独立 API 能在未加载 workflow run 时提供完整 context compile snapshot，因此这里会优先展示 workflow payload 内的 `context_compile_snapshot`，否则回落到 runtime self-check 概览。</div>}
    </section>
  </WorkspaceShell>;
}

function Notice({ tone, text }: { tone: "success" | "error"; text: string }) { return <div className={`rounded-2xl border px-4 py-4 text-sm ${tone === "success" ? "border-emerald-400/15 bg-emerald-500/10 text-emerald-100" : "border-rose-400/15 bg-rose-500/10 text-rose-100"}`}>{text}</div>; }
function Metric({ label, value }: { label: string; value: string }) { return <div className="rounded-2xl bg-zinc-900/70 px-3 py-3">{label}: {value}</div>; }
function Snapshot({ title, value }: { title: string; value: string }) { return <div><div className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-zinc-500">{title}</div><pre className="min-h-[180px] whitespace-pre-wrap rounded-2xl bg-zinc-900/70 px-4 py-4 text-xs leading-6">{value || "n/a"}</pre></div>; }
function Status({ title, lines, tone = "neutral" }: { title: string; lines: string[]; tone?: "success" | "error" | "neutral" }) { const cls = tone === "success" ? "border border-emerald-400/15 bg-emerald-500/10 text-emerald-100" : tone === "error" ? "border border-rose-400/15 bg-rose-500/10 text-rose-100" : "bg-zinc-900/70 text-zinc-300"; return <div className={`rounded-2xl px-4 py-4 text-sm ${cls}`}><div className="font-semibold text-zinc-100">{title}</div><div className="mt-2 space-y-1 text-xs leading-6">{lines.map((line, index) => <div key={`${title}-${index}`}>{line}</div>)}</div></div>; }
function buttonClass(base: string, busy = false) { return `${base} transition disabled:cursor-not-allowed disabled:opacity-50 ${busy ? "cursor-wait opacity-60 grayscale" : ""}`; }
function toErrorMessage(error: unknown, fallback: string) { return error instanceof Error ? error.message : fallback; }
function workflowStatusText(status?: string | null) { return ({ queued: "排队中", queued_resume: "等待续跑", running: "执行中", waiting_user_review: "等待人工处理", completed: "已完成", partial_success: "部分完成", failed: "失败", cancelled: "已取消" } as Record<string, string>)[status ?? ""] ?? status ?? "未运行"; }
function displayStepTitle(step: WorkflowStep) { return `${String(step.output_payload?.agent_label || "流程 Agent")} · ${step.step_key}`; }
function formatTime(value?: string | null) { return value ? new Date(value).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }) : "未记录"; }
function readPayloadString(payload: Record<string, unknown> | null | undefined, key: string) { return typeof payload?.[key] === "string" ? (payload[key] as string) : ""; }
function readPayloadBoolean(payload: Record<string, unknown> | null | undefined, key: string) { return typeof payload?.[key] === "boolean" ? (payload[key] as boolean) : null; }
function readPayloadArray<T>(payload: Record<string, unknown> | null | undefined, key: string) { return Array.isArray(payload?.[key]) ? (payload[key] as T[]) : []; }
function snapshotToText(value: unknown) { return typeof value === "string" ? value : value ? JSON.stringify(value, null, 2) : ""; }
function makeDiffRows(beforeText: string, afterText: string) { const before = beforeText.split("\n"); const after = afterText.split("\n"); const rows: DiffRow[] = []; const max = Math.max(before.length, after.length); for (let index = 0; index < max; index += 1) { if ((before[index] ?? "") === (after[index] ?? "")) rows.push({ type: "context", text: before[index] ?? "" }); else { if (before[index] !== undefined) rows.push({ type: "remove", text: before[index] }); if (after[index] !== undefined) rows.push({ type: "add", text: after[index] }); } } return rows; }
function lineClass(type: DiffRow["type"]) { return type === "add" ? "bg-emerald-500/10 text-emerald-200" : type === "remove" ? "bg-rose-500/10 text-rose-200" : "bg-[#232323] text-zinc-300"; }
function getResumeVersion(run: WorkflowRun | null) { return run?.steps.reduce((max, step) => Math.max(max, step.version ?? 0), 0) ?? 0; }
function providerLabel(provider: "openai" | "deepseek" | "xai") { return provider === "openai" ? "OpenAI" : provider === "deepseek" ? "DeepSeek" : "xAI / Grok"; }
function smokeReportTypeLabel(reportType?: "backend_full_smoke" | "frontend_live_smoke", providerMode?: string | null) { if (!reportType) return "n/a"; return reportType === "frontend_live_smoke" ? "frontend live UI smoke" : providerMode === "live" ? "live provider smoke" : "fixture acceptance"; }
function parsePlannerSnapshot(value: string) { try { const parsed = JSON.parse(value); return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : { summary: value.split("\n")[0] || "人工覆写规划", raw_plan: value }; } catch { return { summary: value.split("\n")[0] || "人工覆写规划", raw_plan: value }; } }
