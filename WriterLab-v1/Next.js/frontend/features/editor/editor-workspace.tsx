"use client";

import { useSearchParams } from "next/navigation";
import { type ComponentProps, useEffect, useMemo, useState } from "react";
import { SidebarPanels } from "@/features/editor/sidebar-panels";
import { VersionsPane } from "@/features/editor/versions-pane";
import { WorkspaceHeader } from "@/features/editor/workspace-header";
import { WritingPane } from "@/features/editor/writing-pane";
import {
  adoptBranch as adoptBranchRequest,
  createBranch as createBranchRequest,
  fetchBranchDiff,
  fetchBranchesByScene,
  fetchSceneContext,
  fetchSceneVersions,
  restoreSceneVersion,
  updateScene,
} from "@/lib/api/scenes";
import {
  analyzeScene as analyzeSceneRequest,
  cancelWorkflowRun,
  exportVn as exportVnRequest,
  fetchSceneAnalyses,
  fetchWorkflowRun,
  overrideWorkflowStep,
  queueSceneWorkflow,
  resumeWorkflowRun,
  reviseScene as reviseSceneRequest,
  scanConsistency as scanConsistencyRequest,
  updateAnalysisSelection,
  writeScene as writeSceneRequest,
} from "@/lib/api/workflow";
import {
  type SmokeReportType,
  useEditorRuntimeWorkbench,
} from "@/features/editor/use-editor-runtime-workbench";

type Tab = "writing" | "versions";
type SideTab = "analysis" | "warnings";
type LengthMode = "short" | "medium" | "long";
type ReviseMode = "trim" | "literary" | "unify";
type ApplyMode = "strict" | "manual";
type WorkflowProviderMode = "live" | "smoke_fixture";
type SceneStatus = "" | "draft" | "generated" | "analyzed" | "revision_ready";
type VersionSource = "manual" | "write" | "revise" | "restore" | "workflow";
type DiffRow = { type: "add" | "remove" | "context"; text: string };
type SidebarPanelsProps = ComponentProps<typeof SidebarPanels>;
type IssueItem = SidebarPanelsProps["issues"][number];
type TimelineItem = SidebarPanelsProps["timeline"][number];
type MemoryItem = SidebarPanelsProps["memories"][number];
type KnowledgeHitItem = SidebarPanelsProps["knowledgeHits"][number];
type RecentSceneItem = SidebarPanelsProps["recentScenes"][number];
type ActiveContextSnapshot = SidebarPanelsProps["activeContextSnapshot"];
type WorkflowViolation = SidebarPanelsProps["workflowViolations"][number];
type VnExportState = SidebarPanelsProps["vnExport"];

type AnalysisItem = {
  id: string;
  item_type: string;
  title?: string | null;
  severity?: string | null;
  content: string;
  is_selected: boolean;
};

type AnalysisStore = { id: string; items: AnalysisItem[] };
type AnalysisResult = { summary?: string; problems?: { severity: string }[] };
type SceneVersion = { id: string; content: string; source: VersionSource; label: string | null; created_at: string };
type Branch = { id: string; name: string; updated_at: string };
type BranchDiff = {
  branch_name?: string | null;
  source_chapter_id?: string | null;
  source_version_label?: string | null;
  latest_version_label?: string | null;
  base_text?: string | null;
  branch_text?: string | null;
  diff_rows?: DiffRow[];
};
type WorkflowStep = {
  id: string;
  step_key: string;
  status: string;
  version?: number;
  attempt_no?: number;
  invalidated_by_step?: string | null;
  provider_mode?: string | null;
  provider?: string | null;
  model?: string | null;
  profile_name?: string | null;
  error_message?: string | null;
  fallback_count?: number | null;
  guardrail_blocked?: boolean | null;
  output_payload?: Record<string, unknown> | null;
  machine_output_snapshot?: Record<string, unknown> | null;
  effective_output_snapshot?: Record<string, unknown> | null;
  attempts?: Record<string, unknown>[];
  edited_reason?: string | null;
};
type WorkflowRun = {
  id: string;
  status: string;
  provider_mode?: string | null;
  fixture_version?: string | null;
  fixture_scenario?: string | null;
  retry_count?: number;
  needs_merge?: boolean;
  quality_degraded?: boolean;
  resume_checkpoint?: string | null;
  resume_from_step?: string | null;
  worker_id?: string | null;
  lease_expires_at?: string | null;
  context_compile_snapshot?: ActiveContextSnapshot;
  output_payload?: Record<string, unknown> | null;
  error_message?: string | null;
  steps: WorkflowStep[];
};
type SceneContextPayload = {
  scene?: { title?: string | null; draft_text?: string | null; status?: SceneStatus };
  scene_status?: SceneStatus;
  timeline_events?: TimelineItem[];
  style_memories?: MemoryItem[];
  knowledge_hits?: KnowledgeHitItem[];
  recent_scenes?: RecentSceneItem[];
  context_compile_snapshot?: ActiveContextSnapshot;
};
type UpdateScenePayload = { scene_status?: SceneStatus; status?: SceneStatus };
type AnalyzeScenePayload = { success: boolean; message?: string; data?: AnalysisResult };
type WriteScenePayload = {
  success: boolean;
  message?: string;
  data?: { draft_text: string; notes?: string[]; message?: string };
};
type ReviseScenePayload = {
  success: boolean;
  message?: string;
  data?: { changed?: boolean; revised_text: string; notes?: string[]; message?: string };
};
type RestoreVersionPayload = { current_text: string };
type ConsistencyPayload = { issues?: IssueItem[]; summary?: string | null };
type AdoptBranchPayload = { current_text: string };

const sceneLabel: Record<SceneStatus, string> = { "": "未记录", draft: "草稿", generated: "已生成", analyzed: "已分析", revision_ready: "待确认润色稿" };
const workflowLabel: Record<string, string> = { queued: "排队中", queued_resume: "等待续跑", running: "执行中", waiting_user_review: "等待人工处理", completed: "已完成", partial_success: "部分完成", failed: "失败", cancelled: "已取消" };
const issueLabel: Record<string, string> = { must_include_missing: "缺少必写项", must_avoid_violation: "命中禁写项", location_anchor: "地点锚点缺失", time_label_missing: "时间标记缺失", timeline_conflict: "时间线冲突", appearance_conflict: "外貌设定冲突", title_drift: "称谓漂移", motivation_drift: "动机漂移", lore_conflict: "设定冲突", llm_review: "LLM 复核问题" };
const severityLabel: Record<string, string> = { high: "高", medium: "中", low: "低" };
const busyLabel: Record<string, string> = { loadScene: "正在加载场景…", saveScene: "正在保存正文…", analyzeScene: "正在分析场景…", writeScene: "正在生成草稿…", reviseScene: "正在润色正文…", runWorkflow: "正在执行工作流…", scanConsistency: "正在扫描一致性…", exportVn: "正在导出 VN…", saveProviderSettings: "正在保存 API 配置…", applyRevision: "正在采纳润色稿…", restoreVersion: "正在恢复版本…", createBranch: "正在创建分支…", adoptBranch: "正在采纳支线版本…", retryWorkflow: "正在重试工作流…", cancelWorkflow: "正在取消工作流…", toggleAnalysis: "正在更新分析项状态…" };

const fmt = (value?: string | null) => value ? new Date(value).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }) : "未记录";
const normalizeText = (value: string) => value.replace(/\r\n/g, "\n").trim();
const readPayloadString = (payload: Record<string, unknown> | null | undefined, key: string) => typeof payload?.[key] === "string" ? (payload[key] as string) : "";
const readPayloadBoolean = (payload: Record<string, unknown> | null | undefined, key: string) => typeof payload?.[key] === "boolean" ? (payload[key] as boolean) : null;
const readPayloadArray = <T,>(payload: Record<string, unknown> | null | undefined, key: string) => Array.isArray(payload?.[key]) ? (payload?.[key] as T[]) : [];
const snapshotToText = (value: unknown) => typeof value === "string" ? value : value ? JSON.stringify(value, null, 2) : "";
const displayIssueSource = (value?: string | null) => !value?.trim() ? "规则检查 / LLM 复核" : value === "LLM复核" ? "LLM 复核" : value;
const deriveIssueSuggestion = (issue: IssueItem) => issue.fix_suggestion?.trim() || "根据提示回看正文，优先修正会影响剧情理解的部分。";
const lineClass = (type: DiffRow["type"]) =>
  type === "add"
    ? "bg-emerald-500/10 text-emerald-200"
    : type === "remove"
      ? "bg-rose-500/10 text-rose-200"
      : "bg-[#232323] text-zinc-300";
const buttonClass = (base: string, busy = false) => `${base} transition disabled:cursor-not-allowed disabled:opacity-50 ${busy ? "cursor-wait opacity-60 grayscale" : ""}`;
const workflowStatusText = (status?: string | null) => workflowLabel[status ?? ""] ?? status ?? "未运行";
const displayStepTitle: SidebarPanelsProps["displayStepTitle"] = (step) => {
  const stepDetail = step as WorkflowStep;
  return `${stepDetail.output_payload?.agent_label || "流程 Agent"} · ${step.step_key}`;
};
const getResumeVersion = (run: WorkflowRun | null) => run?.steps.reduce((max, step) => Math.max(max, step.version ?? 0), 0) ?? 0;
const looksGarbledText = (value?: string | null) => !!(value ?? "").trim() && (/[A-ÿ]|�/.test(value ?? "") || /\?{2,}/.test(value ?? ""));
const displayVersionLabel = (item: SceneVersion) => item.label || item.source;
const smokeReportTypeLabel = (reportType: SmokeReportType, providerMode?: string | null) => reportType === "frontend_live_smoke" ? "frontend live UI smoke" : providerMode === "live" ? "live provider smoke" : "fixture acceptance";
const smokeScenarioOutcomeLabel = (scenario: { name: string; actual_status?: string | null }) => `${scenario.name} ${scenario.actual_status || "unknown"}`;

function LoadingDots({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-[#202020] px-4 py-3 text-sm text-zinc-300">
      <span className="inline-flex gap-1">
        <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:-0.2s]" />
        <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:-0.1s]" />
        <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-zinc-500" />
      </span>
      <span>{label}</span>
    </div>
  );
}

function makeDiffRows(beforeText: string, afterText: string) {
  const before = beforeText.split("\n");
  const after = afterText.split("\n");
  const rows: DiffRow[] = [];
  const max = Math.max(before.length, after.length);
  for (let index = 0; index < max; index += 1) {
    if ((before[index] ?? "") === (after[index] ?? "")) rows.push({ type: "context", text: before[index] ?? "" });
    else {
      if (before[index] !== undefined) rows.push({ type: "remove", text: before[index] });
      if (after[index] !== undefined) rows.push({ type: "add", text: after[index] });
    }
  }
  return rows;
}

export default function EditorWorkspace() {
  const searchParams = useSearchParams();
  const [tab, setTab] = useState<Tab>("writing");
  const [sideTab, setSideTab] = useState<SideTab>("analysis");
  const [sceneId, setSceneId] = useState(searchParams.get("scene_id") ?? "b816b1bd-96b8-486e-a56b-4a26b396b562");
  const [title, setTitle] = useState("");
  const [status, setStatus] = useState<SceneStatus>("");
  const [draft, setDraft] = useState("");
  const [lengthMode, setLengthMode] = useState<LengthMode>("medium");
  const [reviseMode, setReviseMode] = useState<ReviseMode>("trim");
  const [applyMode, setApplyMode] = useState<ApplyMode>("strict");
  const [workflowProviderMode, setWorkflowProviderMode] = useState<WorkflowProviderMode>("live");
  const [fixtureScenario, setFixtureScenario] = useState("happy_path");
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [analysisStore, setAnalysisStore] = useState<AnalysisStore | null>(null);
  const [generatedDraft, setGeneratedDraft] = useState("");
  const [generatedNotes, setGeneratedNotes] = useState<string[]>([]);
  const [revisedDraft, setRevisedDraft] = useState("");
  const [revisionBase, setRevisionBase] = useState("");
  const [revisionNotes, setRevisionNotes] = useState<string[]>([]);
  const [versions, setVersions] = useState<SceneVersion[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState("");
  const [compareVersionId, setCompareVersionId] = useState("");
  const [branches, setBranches] = useState<Branch[]>([]);
  const [selectedBranchId, setSelectedBranchId] = useState("");
  const [branchDiff, setBranchDiff] = useState<BranchDiff | null>(null);
  const [branchName, setBranchName] = useState("");
  const [branchDescription, setBranchDescription] = useState("");
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [knowledgeHits, setKnowledgeHits] = useState<KnowledgeHitItem[]>([]);
  const [recentScenes, setRecentScenes] = useState<RecentSceneItem[]>([]);
  const [contextSnapshot, setContextSnapshot] = useState<ActiveContextSnapshot>(null);
  const [workflow, setWorkflow] = useState<WorkflowRun | null>(null);
  const [selectedWorkflowStepId, setSelectedWorkflowStepId] = useState("");
  const [plannerOverrideDraft, setPlannerOverrideDraft] = useState("");
  const [issues, setIssues] = useState<IssueItem[]>([]);
  const [issueSummary, setIssueSummary] = useState<string | null>(null);
  const [showAllIssues, setShowAllIssues] = useState(false);
  const [vnExport, setVnExport] = useState<VnExportState>(null);
  const [busyKey, setBusyKey] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [runtimeConnection, setRuntimeConnection] = useState<"idle" | "connected" | "reconnecting">("idle");
  const {
    providerSettings,
    providerRuntime,
    providerMatrix,
    runtimeSelfCheck,
    selectedSmokeRegression,
    selectedSmokeReport,
    selectedSmokeReportFilename,
    smokeLatest,
    smokeReports,
    updateProviderField,
    saveProviderSettingsState,
    loadProviderRuntimeState,
    loadRuntimeReadiness,
    loadSmokeLatestState,
    loadSmokeReportsState,
    setSelectedSmokeReportFilename,
  } = useEditorRuntimeWorkbench({ setBusyKey, setMessage });

  const selectedVersion = versions.find((item) => item.id === selectedVersionId) ?? null;
  const compareVersion = versions.find((item) => item.id === compareVersionId) ?? null;
  const guidance = (analysisStore?.items ?? []).filter((item) => item.is_selected).map((item) => item.content);
  const workflowPreview = readPayloadString(workflow?.output_payload ?? null, "final_text") || readPayloadString(workflow?.output_payload ?? null, "partial_text");
  const workflowAutoApplied = readPayloadBoolean(workflow?.output_payload ?? null, "auto_applied") === true;
  const workflowSafeToApply = readPayloadBoolean(workflow?.output_payload ?? null, "safe_to_apply") !== false;
  const rejectedPreview = (() => {
    const blockedStep = workflow?.steps.find((step) => step.guardrail_blocked);
    return typeof blockedStep?.output_payload?.rejected_text_preview === "string" ? (blockedStep.output_payload?.rejected_text_preview as string) : "";
  })();
  const versionDiffRows = selectedVersion && compareVersion ? makeDiffRows(compareVersion.content, selectedVersion.content) : [];
  const visibleIssues = showAllIssues ? issues : issues.filter((item) => item.severity === "high").length ? issues.filter((item) => item.severity === "high") : issues.slice(0, 3);
  const contextSummary = useMemo(() => [`提示 ${guidance.length}`, `时间线 ${timeline.length}`, `风格记忆 ${memories.length}`, `近期场景 ${recentScenes.length}`].join(" · "), [guidance.length, memories.length, recentScenes.length, timeline.length]);
  const latestBackendSmoke = smokeLatest?.backend_full_smoke ?? null;
  const latestFrontendSmoke = smokeLatest?.frontend_live_smoke ?? null;
  const backendSmokeReports = smokeReports.filter((item) => item.report_type === "backend_full_smoke");
  const frontendSmokeReports = smokeReports.filter((item) => item.report_type === "frontend_live_smoke");
  const workflowRuntimeEvents = (workflow?.steps ?? []).map((step) => ({ event: `step_${step.status}`, step: step.step_key, provider: step.provider ?? null, message: step.error_message ?? null }));
  const workflowEventCounts = workflowRuntimeEvents.reduce<Record<string, number>>((acc, item) => { acc[item.event] = (acc[item.event] ?? 0) + 1; return acc; }, {});
  const selectedWorkflowStep = workflow?.steps.find((step) => step.id === selectedWorkflowStepId) ?? null;
  const selectedWorkflowStepDiffRows = selectedWorkflowStep ? makeDiffRows(snapshotToText(selectedWorkflowStep.machine_output_snapshot), snapshotToText(selectedWorkflowStep.effective_output_snapshot ?? selectedWorkflowStep.output_payload)) : [];
  const selectedStyleHardHits = readPayloadArray<string>(selectedWorkflowStep?.output_payload ?? null, "hard_negative_hits");
  const selectedStyleSoftHits = readPayloadArray<string>(selectedWorkflowStep?.output_payload ?? null, "soft_negative_hits");
  const selectedRewriteSuggestions = readPayloadArray<string>(selectedWorkflowStep?.output_payload ?? null, "rewrite_suggestions");
  const selectedNegativeMatches = readPayloadArray<Record<string, unknown>>(selectedWorkflowStep?.output_payload ?? null, "negative_matches");
  const selectedGuardSafeToApply = readPayloadBoolean(selectedWorkflowStep?.output_payload ?? null, "safe_to_apply");
  const selectedGuardNeedsRewrite = readPayloadBoolean(selectedWorkflowStep?.output_payload ?? null, "needs_rewrite");
  const selectedGuardNeedsUserReview = readPayloadBoolean(selectedWorkflowStep?.output_payload ?? null, "needs_user_review");
  const workflowViolations = readPayloadArray<WorkflowViolation>(selectedWorkflowStep?.output_payload ?? workflow?.output_payload ?? null, "violations");

  useEffect(() => {
    void loadScene();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!workflow?.steps.length) return;
    if (!workflow.steps.some((step) => step.id === selectedWorkflowStepId)) setSelectedWorkflowStepId(workflow.steps[workflow.steps.length - 1]?.id ?? "");
  }, [selectedWorkflowStepId, workflow]);

  useEffect(() => {
    if (selectedWorkflowStep?.step_key === "plan") setPlannerOverrideDraft((current) => current || snapshotToText(selectedWorkflowStep.effective_output_snapshot ?? selectedWorkflowStep.output_payload));
  }, [selectedWorkflowStep]);

  function setMessage(ok: string | null, error: string | null = null) {
    setStatusMessage(ok);
    setErrorMessage(error);
  }

  function clearDerived() {
    setAnalysis(null);
    setGeneratedDraft("");
    setGeneratedNotes([]);
    setRevisedDraft("");
    setRevisionBase("");
    setRevisionNotes([]);
    setWorkflow(null);
    setSelectedWorkflowStepId("");
    setPlannerOverrideDraft("");
    setVnExport(null);
    setRuntimeConnection("idle");
  }

  async function loadVersions(targetSceneId = sceneId.trim()) {
    const payload = await fetchSceneVersions<SceneVersion[]>(targetSceneId);
    setVersions(payload);
    setSelectedVersionId((current) => payload.some((item) => item.id === current) ? current : payload[0]?.id ?? "");
    setCompareVersionId((current) => payload.some((item) => item.id === current) ? current : payload[1]?.id ?? "");
  }

  async function loadAnalyses(targetSceneId = sceneId.trim()) {
    const payload = await fetchSceneAnalyses<AnalysisStore[]>(targetSceneId);
    setAnalysisStore(payload[0] ?? null);
  }

  async function loadBranchDiffState(branchId: string) {
    if (!branchId) return setBranchDiff(null);
    setBranchDiff(await fetchBranchDiff<BranchDiff>(branchId));
  }

  async function loadBranches(targetSceneId = sceneId.trim()) {
    const payload = await fetchBranchesByScene<Branch[]>(targetSceneId);
    setBranches(payload);
    const nextId = payload.some((item) => item.id === selectedBranchId) ? selectedBranchId : payload[0]?.id ?? "";
    setSelectedBranchId(nextId);
    await loadBranchDiffState(nextId);
  }

  async function loadScene() {
    if (!sceneId.trim()) return setErrorMessage("请先填写 scene_id");
    setBusyKey("loadScene");
    setMessage(null);
    try {
      const payload = await fetchSceneContext<SceneContextPayload>(sceneId.trim());
      setTitle(payload.scene?.title ?? "");
      setStatus(payload.scene_status ?? payload.scene?.status ?? "draft");
      setDraft(payload.scene?.draft_text ?? "");
      setTimeline(payload.timeline_events ?? []);
      setMemories(payload.style_memories ?? []);
      setKnowledgeHits(payload.knowledge_hits ?? []);
      setRecentScenes(payload.recent_scenes ?? []);
      setContextSnapshot(payload.context_compile_snapshot ?? null);
      setIssues([]);
      setIssueSummary(null);
      setShowAllIssues(false);
      clearDerived();
      await Promise.all([loadVersions(sceneId.trim()), loadAnalyses(sceneId.trim()), loadBranches(sceneId.trim())]);
      setMessage("场景已加载。");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "读取场景失败");
    } finally {
      setBusyKey("");
    }
  }

  async function patchScene(nextDraft = draft, source = "manual", label = "manual update") {
    const payload = await updateScene<UpdateScenePayload>(sceneId.trim(), { title: title.trim() || undefined, draft_text: nextDraft, version_source: source, version_label: label });
    setStatus(payload.scene_status ?? payload.status ?? status);
  }

  async function saveScene() {
    if (!sceneId.trim()) return setErrorMessage("请先填写 scene_id");
    setBusyKey("saveScene");
    setMessage(null);
    try {
      await patchScene(draft, "manual", "manual save");
      await loadVersions();
      setMessage("正文已保存并生成新版本。");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "保存失败");
    } finally {
      setBusyKey("");
    }
  }

  async function analyzeScene() {
    if (!sceneId.trim()) return setErrorMessage("请先填写 scene_id");
    if (!draft.trim()) return setErrorMessage("请先输入正文。");
    setBusyKey("analyzeScene");
    setMessage(null);
    try {
      await patchScene(draft, "manual", "analyze source");
      const payload = await analyzeSceneRequest<AnalyzeScenePayload>({ scene_id: sceneId.trim() });
      if (!payload.success || !payload.data) return setErrorMessage(payload.message ?? "分析失败");
      setAnalysis(payload.data);
      await loadAnalyses();
      setStatus("analyzed");
      setSideTab((payload.data.problems ?? []).length ? "warnings" : "analysis");
      setMessage("分析完成。");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "分析失败");
    } finally {
      setBusyKey("");
    }
  }

  async function toggleAnalysisItem(itemId: string, nextSelected: boolean) {
    if (!analysisStore) return;
    setBusyKey("toggleAnalysis");
    setMessage(null);
    try {
      const selectedIds = (analysisStore.items ?? []).filter((item) => item.is_selected).map((item) => item.id);
      const nextIds = nextSelected ? [...new Set([...selectedIds, itemId])] : selectedIds.filter((id) => id !== itemId);
      setAnalysisStore(await updateAnalysisSelection<AnalysisStore>(analysisStore.id, { selected_item_ids: nextIds }));
      setMessage(nextIds.length ? "已更新工作流提示。" : "已清空工作流提示。");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "更新分析选择失败");
    } finally {
      setBusyKey("");
    }
  }

  async function writeScene() {
    if (!sceneId.trim()) return setErrorMessage("请先填写 scene_id");
    setBusyKey("writeScene");
    setMessage(null);
    try {
      await patchScene(draft, "manual", "write source");
      const payload = await writeSceneRequest<WriteScenePayload>({ scene_id: sceneId.trim(), length: lengthMode, analysis_id: analysisStore?.id ?? null, guidance });
      if (!payload.success || !payload.data) return setErrorMessage(payload.message ?? "扩写失败");
      setGeneratedDraft(payload.data.draft_text);
      setGeneratedNotes(payload.data.notes ?? []);
      setStatus("generated");
      setMessage(payload.data.message ?? "已生成建议稿。");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "扩写失败");
    } finally {
      setBusyKey("");
    }
  }

  async function reviseScene() {
    if (!sceneId.trim()) return setErrorMessage("请先填写 scene_id");
    if (!draft.trim()) return setErrorMessage("请先输入正文。");
    setBusyKey("reviseScene");
    setMessage(null);
    try {
      await patchScene(draft, "manual", "revise source");
      const payload = await reviseSceneRequest<ReviseScenePayload>({ scene_id: sceneId.trim(), mode: reviseMode });
      if (!payload.success || !payload.data) return setErrorMessage(payload.message ?? "润色失败");
      if (!payload.data.changed || normalizeText(payload.data.revised_text) === normalizeText(draft)) {
        setRevisionNotes(payload.data.notes ?? []);
        return setMessage(payload.data.message ?? "当前正文无需额外修改。");
      }
      setRevisionBase(draft);
      setRevisedDraft(payload.data.revised_text);
      setRevisionNotes(payload.data.notes ?? []);
      setStatus("revision_ready");
      setMessage(payload.data.message ?? "已生成润色稿。");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "润色失败");
    } finally {
      setBusyKey("");
    }
  }

  function acceptGeneratedDraft() {
    if (!generatedDraft.trim()) return;
    setDraft(generatedDraft);
    setMessage("建议稿已回填到正文，请记得保存。");
  }

  function rejectGeneratedDraft() {
    setGeneratedDraft("");
    setGeneratedNotes([]);
    setMessage("已丢弃建议稿。");
  }

  async function applyRevision() {
    if (!revisedDraft.trim()) return;
    setBusyKey("applyRevision");
    setMessage(null);
    try {
      await patchScene(revisedDraft, "revise", `apply ${reviseMode}`);
      setDraft(revisedDraft);
      setRevisedDraft("");
      setRevisionBase("");
      setRevisionNotes([]);
      setStatus("draft");
      await loadVersions();
      setMessage("润色稿已采纳。");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "采纳润色稿失败");
    } finally {
      setBusyKey("");
    }
  }

  function discardRevision() {
    setRevisedDraft("");
    setRevisionBase("");
    setRevisionNotes([]);
    setMessage("已丢弃润色稿。");
  }

  async function restoreVersion() {
    if (!sceneId.trim() || !selectedVersionId) return;
    setBusyKey("restoreVersion");
    setMessage(null);
    try {
      const payload = await restoreSceneVersion<RestoreVersionPayload>(sceneId.trim(), selectedVersionId);
      setDraft(payload.current_text);
      clearDerived();
      setStatus("draft");
      await Promise.all([loadVersions(), loadBranches()]);
      setMessage("版本已恢复。");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "恢复版本失败");
    } finally {
      setBusyKey("");
    }
  }

  async function createBranch() {
    if (!sceneId.trim()) return setErrorMessage("请先填写 scene_id");
    if (!branchName.trim()) return setErrorMessage("请填写分支名称。");
    setBusyKey("createBranch");
    setMessage(null);
    try {
      const payload = await createBranchRequest<Branch>({ name: branchName.trim(), description: branchDescription.trim() || undefined, source_scene_id: sceneId.trim(), source_version_id: selectedVersionId || undefined, metadata_json: { created_from: "editor" } });
      setBranchName("");
      setBranchDescription("");
      await loadBranches(sceneId.trim());
      setSelectedBranchId(payload.id);
      await loadBranchDiffState(payload.id);
      setTab("versions");
      setMessage("分支已创建。");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "创建分支失败");
    } finally {
      setBusyKey("");
    }
  }

  async function runConsistencyScan(nextDraft = draft, showBusy = false) {
    if (!sceneId.trim()) return;
    if (showBusy) {
      setBusyKey("scanConsistency");
      setMessage(null);
    }
    try {
      const payload = await scanConsistencyRequest<ConsistencyPayload>({ scene_id: sceneId.trim(), draft_text: nextDraft });
      setIssues(payload.issues ?? []);
      setIssueSummary(payload.summary ?? null);
      setShowAllIssues(false);
      if ((payload.issues ?? []).length) setSideTab("warnings");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "一致性扫描失败");
    } finally {
      if (showBusy) setBusyKey("");
    }
  }

  async function adoptBranch() {
    if (!selectedBranchId) return setErrorMessage("请先选择要采纳的分支。");
    setBusyKey("adoptBranch");
    setMessage(null);
    try {
      const payload = await adoptBranchRequest<AdoptBranchPayload>(selectedBranchId);
      setDraft(payload.current_text);
      clearDerived();
      setStatus("draft");
      await Promise.all([loadVersions(), loadBranches(), runConsistencyScan(payload.current_text, false)]);
      setMessage("分支已采纳并回填正文。");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "采纳分支失败");
    } finally {
      setBusyKey("");
    }
  }

  async function pollWorkflow(id: string) {
    setRuntimeConnection("connected");
    for (let attempt = 0; attempt < 60; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 1500));
      const payload = await fetchWorkflowRun<WorkflowRun>(id);
      setWorkflow(payload);
      if (["completed", "partial_success", "failed", "cancelled"].includes(payload.status)) {
        setRuntimeConnection("idle");
        return payload;
      }
    }
    setRuntimeConnection("idle");
    throw new Error("工作流轮询超时。");
  }

  async function applyWorkflowOutcome(run: WorkflowRun) {
    const finalText = readPayloadString(run.output_payload ?? null, "final_text") || readPayloadString(run.output_payload ?? null, "partial_text");
    if (finalText) {
      setGeneratedDraft(finalText);
      setGeneratedNotes([workflowSafeToApply ? "工作流已产出可用草稿。" : "结果被守门拦截，系统已阻止自动回填正文。"]);
      if (readPayloadBoolean(run.output_payload ?? null, "auto_applied") === true) {
        setDraft(finalText);
        setStatus("draft");
        await loadVersions();
      }
    }
    await runConsistencyScan(finalText || draft, false);
  }

  async function runWorkflow() {
    if (!sceneId.trim()) return setErrorMessage("请先填写 scene_id");
    setBusyKey("runWorkflow");
    setMessage(null);
    try {
      const queued = await queueSceneWorkflow<WorkflowRun>({ scene_id: sceneId.trim(), length: lengthMode, guidance, auto_apply: applyMode === "strict", provider_mode: workflowProviderMode, fixture_scenario: fixtureScenario });
      setWorkflow(queued);
      setSelectedWorkflowStepId("");
      setPlannerOverrideDraft("");
      const completed = ["completed", "partial_success", "failed", "cancelled"].includes(queued.status) ? queued : await pollWorkflow(queued.id);
      await applyWorkflowOutcome(completed);
      await Promise.all([loadRuntimeReadiness(), loadProviderRuntimeState()]);
      if (completed.status === "failed") setErrorMessage(completed.error_message ?? "工作流失败");
      else setMessage("工作流执行完毕。");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "启动工作流失败");
    } finally {
      setBusyKey("");
    }
  }

  async function retryWorkflow() {
    if (!workflow?.id) return;
    setBusyKey("retryWorkflow");
    setMessage(null);
    try {
      const queued = await resumeWorkflowRun<WorkflowRun>(workflow.id, { idempotency_key: `resume-${Date.now()}`, expected_step_version: getResumeVersion(workflow), resume_from_step: workflow.resume_from_step ?? undefined });
      setWorkflow(queued);
      const completed = ["completed", "partial_success", "failed", "cancelled"].includes(queued.status) ? queued : await pollWorkflow(queued.id);
      await applyWorkflowOutcome(completed);
      await Promise.all([loadRuntimeReadiness(), loadProviderRuntimeState()]);
      setMessage("工作流已重新排队。");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "重试工作流失败");
    } finally {
      setBusyKey("");
    }
  }

  async function overridePlannerStep() {
    if (!workflow?.id || !selectedWorkflowStep || selectedWorkflowStep.step_key !== "plan") return;
    setBusyKey("retryWorkflow");
    setMessage(null);
    try {
      const version = selectedWorkflowStep.version ?? 0;
      const snapshot = (() => {
        try {
          const parsed = JSON.parse(plannerOverrideDraft);
          return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : { summary: plannerOverrideDraft.split("\n")[0] || "人工覆写规划", raw_plan: plannerOverrideDraft };
        } catch {
          return { summary: plannerOverrideDraft.split("\n")[0] || "人工覆写规划", raw_plan: plannerOverrideDraft };
        }
      })();
      const queued = await overrideWorkflowStep<WorkflowRun>(workflow.id, selectedWorkflowStep.step_key, { idempotency_key: `override-${Date.now()}`, expected_step_version: version, derived_from_version: version, edited_reason: "编辑器中的人工 Planner Override", effective_output_snapshot: snapshot });
      setWorkflow(queued);
      const completed = ["completed", "partial_success", "failed", "cancelled"].includes(queued.status) ? queued : await pollWorkflow(queued.id);
      await applyWorkflowOutcome(completed);
      await Promise.all([loadRuntimeReadiness(), loadProviderRuntimeState()]);
      setMessage("规划步骤已覆写并继续执行。");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "覆写规划步骤失败");
    } finally {
      setBusyKey("");
    }
  }

  async function cancelWorkflow() {
    if (!workflow?.id) return;
    setBusyKey("cancelWorkflow");
    setMessage(null);
    try {
      setWorkflow(await cancelWorkflowRun<WorkflowRun>(workflow.id));
      setRuntimeConnection("idle");
      setMessage("工作流已取消。");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "取消工作流失败");
    } finally {
      setBusyKey("");
    }
  }

  async function exportVn() {
    if (!draft.trim()) return setErrorMessage("请先输入正文。");
    setBusyKey("exportVn");
    setMessage(null);
    try {
      setVnExport(await exportVnRequest<VnExportState>({ draft_text: draft, scene_title: title.trim() || undefined, include_image_prompts: true }));
      setMessage("VN 脚本已生成。");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "导出 VN 失败");
    } finally {
      setBusyKey("");
    }
  }

  async function copyGuidance() {
    if (!guidance.length) return;
    await navigator.clipboard.writeText(guidance.join("\n"));
    setMessage("已复制已选提示。");
  }

  return (
    <main className="min-h-screen bg-[#171717] text-zinc-100">
      <div className="mx-auto flex max-w-[1600px] flex-col gap-6 px-4 py-6">
        <WorkspaceHeader sceneStatusLabel={sceneLabel[status]} workflowStatusLabel={workflowStatusText(workflow?.status)} issueCount={issues.length} sceneId={sceneId} title={title} onSceneIdChange={setSceneId} onTitleChange={setTitle} onReload={() => void loadScene()} onSave={() => void saveScene()} tab={tab} onTabChange={setTab} busyKey={busyKey} statusMessage={statusMessage} errorMessage={errorMessage} loadingContent={busyKey ? <LoadingDots label={busyLabel[busyKey] ?? "正在处理，请稍候…"} /> : null} buttonClass={buttonClass} />
        <div className="grid gap-6 xl:grid-cols-[1.7fr_0.95fr]">
          <section className="space-y-6">
            {tab === "writing" ? (
              <WritingPane contextSummary={contextSummary} lengthMode={lengthMode} reviseMode={reviseMode} applyMode={applyMode} workflowProviderMode={workflowProviderMode} fixtureScenario={fixtureScenario} draft={draft} generatedDraft={generatedDraft} generatedNotes={generatedNotes} revisedDraft={revisedDraft} revisionBase={revisionBase} revisionNotes={revisionNotes} busyKey={busyKey} onLengthModeChange={setLengthMode} onReviseModeChange={setReviseMode} onApplyModeChange={setApplyMode} onWorkflowProviderModeChange={setWorkflowProviderMode} onFixtureScenarioChange={setFixtureScenario} onDraftChange={setDraft} onAnalyze={() => void analyzeScene()} onWrite={() => void writeScene()} onRevise={() => void reviseScene()} onRunWorkflow={() => void runWorkflow()} onScanConsistency={() => void runConsistencyScan(draft, true)} onExportVn={() => void exportVn()} onAcceptGeneratedDraft={acceptGeneratedDraft} onRejectGeneratedDraft={rejectGeneratedDraft} onApplyRevision={() => void applyRevision()} onDiscardRevision={discardRevision} buttonClass={buttonClass} />
            ) : (
              <VersionsPane busyKey={busyKey} selectedVersionId={selectedVersionId} compareVersionId={compareVersionId} versions={versions} selectedVersion={selectedVersion} compareVersion={compareVersion} versionDiffRows={versionDiffRows} branchName={branchName} branchDescription={branchDescription} selectedBranchId={selectedBranchId} branches={branches} branchDiff={branchDiff} onSelectedVersionIdChange={setSelectedVersionId} onCompareVersionIdChange={setCompareVersionId} onRestoreVersion={() => void restoreVersion()} onBranchNameChange={setBranchName} onBranchDescriptionChange={setBranchDescription} onCreateBranch={() => void createBranch()} onSelectedBranchIdChange={(value) => { setSelectedBranchId(value); void loadBranchDiffState(value); }} onAdoptBranch={() => void adoptBranch()} buttonClass={buttonClass} displayVersionLabel={displayVersionLabel} formatTime={fmt} lineClass={lineClass} looksGarbledText={looksGarbledText} />
            )}
          </section>
          <SidebarPanels sideTab={sideTab} analysis={analysis} analysisStore={analysisStore} issueSummary={issueSummary} visibleIssues={visibleIssues} issues={issues} showAllIssues={showAllIssues} runtimeConnection={runtimeConnection} workflow={workflow} runtimeSelfCheck={runtimeSelfCheck} workflowRuntimeEvents={workflowRuntimeEvents} workflowEventCounts={workflowEventCounts} busyKey={busyKey} workflowPreview={workflowPreview} workflowAutoApplied={workflowAutoApplied} workflowSafeToApply={workflowSafeToApply} rejectedPreview={rejectedPreview} selectedWorkflowStep={selectedWorkflowStep} selectedWorkflowStepDiffRows={selectedWorkflowStepDiffRows} selectedStyleHardHits={selectedStyleHardHits} selectedStyleSoftHits={selectedStyleSoftHits} selectedRewriteSuggestions={selectedRewriteSuggestions} selectedNegativeMatches={selectedNegativeMatches} selectedGuardSafeToApply={selectedGuardSafeToApply} selectedGuardNeedsRewrite={selectedGuardNeedsRewrite} selectedGuardNeedsUserReview={selectedGuardNeedsUserReview} activeContextSnapshot={workflow?.context_compile_snapshot ?? contextSnapshot} workflowViolations={workflowViolations} plannerOverrideDraft={plannerOverrideDraft} providerSettings={providerSettings} providerRuntime={providerRuntime} latestBackendSmoke={latestBackendSmoke} latestFrontendSmoke={latestFrontendSmoke} smokeReports={smokeReports} selectedSmokeReportFilename={selectedSmokeReportFilename} selectedSmokeReport={selectedSmokeReport} selectedSmokeRegression={selectedSmokeRegression} backendSmokeReports={backendSmokeReports} frontendSmokeReports={frontendSmokeReports} timeline={timeline} memories={memories} knowledgeHits={knowledgeHits} recentScenes={recentScenes} vnExport={vnExport} providerMatrix={providerMatrix} onSideTabChange={setSideTab} onCopyGuidance={() => void copyGuidance()} onToggleAnalysisItem={(itemId, nextSelected) => void toggleAnalysisItem(itemId, nextSelected)} onToggleShowAllIssues={() => setShowAllIssues((current) => !current)} onRetryWorkflow={() => void retryWorkflow()} onCancelWorkflow={() => void cancelWorkflow()} onSelectedWorkflowStepIdChange={setSelectedWorkflowStepId} onPlannerOverrideDraftChange={setPlannerOverrideDraft} onOverridePlannerStep={() => void overridePlannerStep()} onRefreshRuntime={() => { void loadRuntimeReadiness(); void loadProviderRuntimeState(); }} onUpdateProviderField={updateProviderField} onSaveProviderSettings={() => void saveProviderSettingsState()} onRefreshProviderRuntime={() => void loadProviderRuntimeState()} onRefreshSmokeConsole={() => { void loadSmokeLatestState(); void loadSmokeReportsState(); }} onSelectedSmokeReportFilenameChange={setSelectedSmokeReportFilename} buttonClass={buttonClass} displaySeverityLabel={severityLabel} displayIssueLabel={issueLabel} displayIssueSource={displayIssueSource} deriveIssueSuggestion={deriveIssueSuggestion} workflowStatusText={workflowStatusText} displayStepTitle={displayStepTitle} snapshotToText={snapshotToText} formatTime={fmt} lineClass={lineClass} smokeReportTypeLabel={smokeReportTypeLabel} smokeScenarioOutcomeLabel={smokeScenarioOutcomeLabel} />
        </div>
      </div>
    </main>
  );
}
