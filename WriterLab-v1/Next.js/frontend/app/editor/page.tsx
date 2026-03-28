"use client";

import { useEffect, useMemo, useState } from "react";

const API = "http://127.0.0.1:8000";

type Tab = "writing" | "versions";
type SideTab = "analysis" | "warnings";
type LengthMode = "short" | "medium" | "long";
type ReviseMode = "trim" | "literary" | "unify";
type ApplyMode = "strict" | "manual";
type SceneStatus = "" | "draft" | "generated" | "analyzed" | "revision_ready";
type VersionSource = "manual" | "write" | "revise" | "restore" | "workflow";
type DiffRow = { type: "add" | "remove" | "context"; text: string };

type SceneContextResponse = {
  scene: { title: string; status: SceneStatus; draft_text: string | null };
  timeline_events?: { id: string; title: string; event_time_label?: string | null }[];
  style_memories?: { id: string; content: string; status: string }[];
  knowledge_hits?: {
    chunk_id: string;
    document_title: string;
    score: number;
    content: string;
    source_label?: string | null;
    confirmed?: boolean | null;
  }[];
  recent_scenes?: { scene_id: string; title: string; scene_no: number }[];
};

type AnalysisItem = {
  id: string;
  item_type: string;
  title?: string | null;
  severity?: string | null;
  content: string;
  is_selected: boolean;
};

type AnalysisStore = { id: string; items: AnalysisItem[] };

type AnalysisResult = {
  summary?: string;
  problems?: { type: string; severity: string; message: string }[];
};

type SceneVersion = {
  id: string;
  content: string;
  source: VersionSource;
  label: string | null;
  created_at: string;
};

type WorkflowStep = {
  id: string;
  step_key: string;
  status: string;
  provider?: string | null;
  model?: string | null;
  error_message?: string | null;
  fallback_used?: boolean | null;
  guardrail_blocked?: boolean | null;
  duration_ms?: number | null;
  output_payload?: Record<string, unknown> | null;
};

type WorkflowRun = {
  id: string;
  status: string;
  retry_count?: number;
  output_payload?: Record<string, unknown> | null;
  error_message?: string | null;
  steps: WorkflowStep[];
};

type Branch = {
  id: string;
  name: string;
  description?: string | null;
  source_chapter_id?: string | null;
  latest_version_label?: string | null;
  updated_at: string;
};

type BranchDiff = {
  branch_id: string;
  branch_name?: string | null;
  source_chapter_id?: string | null;
  source_version_label?: string | null;
  latest_version_label?: string | null;
  base_text: string;
  branch_text: string;
  diff_rows: DiffRow[];
};

type ConsistencyIssue = {
  id: string;
  issue_type: string;
  severity: string;
  message: string;
  evidence_json?: Record<string, unknown> | null;
  source?: string | null;
  fix_suggestion?: string | null;
};

type VnExport = { markdown_script: string; image_prompts: string[] };

type ProviderSettingsItem = {
  provider: "openai" | "deepseek" | "xai";
  api_base: string;
  has_api_key: boolean;
  api_key_masked?: string | null;
  api_key?: string;
};

const sceneLabel: Record<SceneStatus, string> = {
  "": "未加载",
  draft: "草稿",
  generated: "已生成初稿",
  analyzed: "已分析",
  revision_ready: "待确认润色",
};

const versionLabel: Record<VersionSource, string> = {
  manual: "手动保存",
  write: "AI生成初稿",
  revise: "AI润色稿",
  restore: "恢复版本",
  workflow: "工作流结果",
};

const workflowLabel: Record<string, string> = {
  queued: "排队中",
  running: "执行中",
  completed: "已完成",
  partial_success: "部分完成",
  failed: "失败",
  cancelled: "已取消",
};

const stepLabel: Record<string, string> = {
  bootstrap: "初始化",
  queued: "排队中",
  analyze: "分析",
  plan: "规划",
  write: "写作",
  style: "润色",
  check: "检查",
  store: "入库",
  done: "完成",
};

const issueLabel: Record<string, string> = {
  must_include_missing: "缺少必写元素",
  must_avoid_violation: "触发禁写内容",
  location_anchor: "地点锚点不足",
  time_label_missing: "时间标签缺失",
  timeline_conflict: "时间线冲突",
  appearance_conflict: "人物外貌冲突",
  title_drift: "标题与正文偏移",
  motivation_drift: "人物动机漂移",
  lore_conflict: "设定冲突",
  llm_review: "模型复核提醒",
};

const severityLabel: Record<string, string> = { high: "高", medium: "中", low: "低" };

const busyLabel: Record<string, string> = {
  loadScene: "正在加载场景…",
  saveScene: "正在保存正文…",
  analyzeScene: "正在分析场景…",
  writeScene: "正在生成草稿…",
  reviseScene: "正在润色正文…",
  runWorkflow: "正在执行完整工作流…",
  scanConsistency: "正在扫描一致性问题…",
  exportVn: "正在导出 VN 脚本…",
  applyRevision: "正在采纳润色稿…",
  restoreVersion: "正在恢复版本…",
  createBranch: "正在创建分支…",
  adoptBranch: "正在采纳支线版本…",
  retryWorkflow: "正在重试工作流…",
  cancelWorkflow: "正在取消工作流…",
  toggleAnalysis: "正在更新写作提示…",
};

const cleanStepLabel: Record<string, string> = {
  bootstrap: "启动准备",
  queued: "等待执行",
  analyze: "分析场景",
  plan: "整理计划",
  write: "生成正文",
  style: "润色文风",
  check: "一致性检查",
  guard: "守门复核",
  store: "写回存档",
  memory: "整理记忆",
  done: "流程完成",
};

const stepAgentLabel: Record<string, string> = {
  bootstrap: "流程调度 Agent",
  queued: "流程调度 Agent",
  analyze: "规划 Agent",
  plan: "规划 Agent",
  write: "写作 Agent",
  style: "文风 Agent",
  check: "一致性 Agent",
  guard: "守门 Agent",
  store: "存储 Agent",
  memory: "记忆整理 Agent",
  done: "流程调度 Agent",
};

const isTerminal = (status?: string | null) =>
  ["completed", "partial_success", "failed", "cancelled"].includes(status ?? "");

const uiSceneLabel: Record<SceneStatus, string> = {
  "": "未记录",
  draft: "草稿",
  generated: "已生成",
  analyzed: "已分析",
  revision_ready: "待采纳润色稿",
};

const uiVersionLabel: Record<VersionSource, string> = {
  manual: "手动保存",
  write: "AI 生成稿",
  revise: "AI 润色稿",
  restore: "恢复版本",
  workflow: "工作流结果",
};

const uiWorkflowLabel: Record<string, string> = {
  queued: "排队中",
  running: "执行中",
  completed: "已完成",
  partial_success: "部分完成",
  failed: "失败",
  cancelled: "已取消",
};

const uiIssueLabel: Record<string, string> = {
  must_include_missing: "缺少必写项",
  must_avoid_violation: "命中禁写项",
  location_anchor: "地点锚点缺失",
  time_label_missing: "时间标签缺失",
  timeline_conflict: "时间线冲突",
  appearance_conflict: "外貌设定冲突",
  title_drift: "称谓漂移",
  motivation_drift: "动机漂移",
  lore_conflict: "设定冲突",
  llm_review: "LLM 复核问题",
};

const uiSeverityLabel: Record<string, string> = { high: "高", medium: "中", low: "低" };

const uiBusyLabel: Record<string, string> = {
  loadScene: "正在加载场景…",
  saveScene: "正在保存正文…",
  analyzeScene: "正在分析场景…",
  writeScene: "正在生成草稿…",
  reviseScene: "正在润色正文…",
  runWorkflow: "正在执行完整工作流…",
  scanConsistency: "正在扫描一致性…",
  exportVn: "正在导出 VN 脚本…",
  applyRevision: "正在采纳润色稿…",
  restoreVersion: "正在恢复版本…",
  createBranch: "正在创建剧情分支…",
  adoptBranch: "正在采纳支线版本…",
  retryWorkflow: "正在重试工作流…",
  cancelWorkflow: "正在取消工作流…",
  toggleAnalysis: "正在更新分析选项…",
};

const fmt = (value?: string | null) =>
  value
    ? new Date(value).toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "未记录";

const fmtDuration = (value?: number | null) =>
  !value ? "未记录" : value < 1000 ? `${value} ms` : `${(value / 1000).toFixed(value >= 10000 ? 0 : 1)} s`;

const normalizeText = (value: string) => value.replace(/\r\n/g, "\n").trim();

const readPayloadString = (payload: Record<string, unknown> | null | undefined, key: string) => {
  const value = payload?.[key];
  return typeof value === "string" ? value : "";
};

const displaySceneLabel: Record<SceneStatus, string> = {
  "": "未记录",
  draft: "草稿",
  generated: "已生成",
  analyzed: "已分析",
  revision_ready: "待确认润色稿",
};

const displayVersionSourceLabel: Record<VersionSource, string> = {
  manual: "手动保存",
  write: "AI 生成稿",
  revise: "AI 润色稿",
  restore: "恢复版本",
  workflow: "工作流结果",
};

const displayWorkflowLabel: Record<string, string> = {
  queued: "排队中",
  running: "执行中",
  completed: "已完成",
  partial_success: "部分完成",
  failed: "失败",
  cancelled: "已取消",
};

const displayIssueLabel: Record<string, string> = {
  must_include_missing: "缺少必写项",
  must_avoid_violation: "命中禁写项",
  location_anchor: "地点锚点缺失",
  time_label_missing: "时间标记缺失",
  timeline_conflict: "时间线冲突",
  appearance_conflict: "外貌设定冲突",
  title_drift: "称谓漂移",
  motivation_drift: "动机漂移",
  lore_conflict: "设定冲突",
  llm_review: "LLM 复核问题",
};

const displaySeverityLabel: Record<string, string> = { high: "高", medium: "中", low: "低" };

const displayBusyLabel: Record<string, string> = {
  loadScene: "正在加载场景…",
  saveScene: "正在保存正文…",
  analyzeScene: "正在分析场景…",
  writeScene: "正在生成草稿…",
  reviseScene: "正在润色正文…",
  runWorkflow: "正在执行工作流…",
  scanConsistency: "正在扫描一致性…",
  exportVn: "正在导出 VN…",
  saveProviderSettings: "正在保存 API 配置…",
  applyRevision: "正在采纳润色稿…",
  restoreVersion: "正在恢复版本…",
  createBranch: "正在创建分支…",
  adoptBranch: "正在采纳支线版本…",
  retryWorkflow: "正在重试工作流…",
  cancelWorkflow: "正在取消工作流…",
  toggleAnalysis: "正在更新分析项状态…",
};

const readPayloadBoolean = (payload: Record<string, unknown> | null | undefined, key: string) => {
  const value = payload?.[key];
  return typeof value === "boolean" ? value : null;
};

const formatIssueSource = (value?: string | null) => {
  if (!value?.trim()) return "规则检查 / LLM复核";
  if (value === "LLM复核") return "LLM复核";
  if (value === "规则检查") return "规则检查";
  return value;
};

const formatWorkflowError = (value?: string | null) => {
  const text = (value ?? "").trim();
  if (!text) return "";
  if (text.includes("timed out")) return "模型响应超时，系统已停止等待这一步。";
  if (text.includes("generic commentary")) return "这一步产出了分析腔或说明腔文本，已被守门拦截。";
  if (text.includes("length too aggressively")) return "这一步改动幅度过大，系统没有采纳。";
  if (text.includes("drifted too far")) return "这一步与原稿偏离过大，系统没有采纳。";
  if (text.includes("Japanese-heavy")) return "这一步语言明显漂移，系统已拦截。";
  if (text.includes("drifted away from the source language")) return "这一步偏离了原文语言，系统已拦截。";
  if (text.includes("Provider not configured")) return "当前步骤没有可用模型配置。";
  return text;
};

const formatStepTitle = (step: WorkflowStep) => {
  const stepName = cleanStepLabel[step.step_key] ?? stepLabel[step.step_key] ?? step.step_key;
  const payload = step.output_payload ?? {};
  const payloadAgentLabel = typeof payload.agent_label === "string" ? payload.agent_label : "";
  const agentLabel = payloadAgentLabel || stepAgentLabel[step.step_key] || "流程 Agent";
  return `${agentLabel} · ${stepName}`;
};

const displayIssueSource = (value?: string | null) => {
  if (!value?.trim()) return "规则检查 / LLM 复核";
  if (value === "LLM复核") return "LLM 复核";
  if (value === "规则检查") return "规则检查";
  return value;
};

const displayWorkflowError = (value?: string | null) => {
  const text = (value ?? "").trim();
  if (!text) return "";
  if (text.includes("timed out")) return "模型响应超时，系统已停止等待这一步。";
  if (text.includes("generic commentary")) return "这一步产出了分析腔或说明腔文本，已被守门拦截。";
  if (text.includes("length too aggressively")) return "这一步改动幅度过大，系统没有采纳。";
  if (text.includes("drifted too far")) return "这一步与原稿偏离过大，系统没有采纳。";
  if (text.includes("Japanese-heavy")) return "这一步语言明显漂移，系统已拦截。";
  if (text.includes("drifted away from the source language")) return "这一步偏离了原文语言，系统已拦截。";
  if (text.includes("Provider not configured")) return "当前步骤没有可用模型配置。";
  if (text.includes("rate limit")) return "模型触发了限流，系统已尝试切换到降级路径。";
  if (text.includes("circuit breaker")) return "该模型最近连续失败，系统暂时停用了这一路径。";
  return text;
};

const displayStepTitle = (step: WorkflowStep) => {
  const stepName = cleanStepLabel[step.step_key] ?? step.step_key;
  const payload = step.output_payload ?? {};
  const payloadAgentLabel = typeof payload.agent_label === "string" ? payload.agent_label : "";
  const agentLabel = payloadAgentLabel || stepAgentLabel[step.step_key] || "流程 Agent";
  return `${agentLabel} · ${stepName}`;
};

const deriveIssueSuggestion = (issue: ConsistencyIssue) => {
  if (issue.fix_suggestion?.trim()) return issue.fix_suggestion;
  switch (issue.issue_type) {
    case "must_include_missing":
      return "把缺失的关键设定、物件或动作明确补回正文。";
    case "must_avoid_violation":
      return "删掉命中的禁写内容，或改写成符合当前设定的表达。";
    case "location_anchor":
      return "补一到两处地点细节，让读者知道人物此刻身在何处。";
    case "time_label_missing":
      return "补上时间标签或时间线线索，避免读者分不清先后顺序。";
    case "timeline_conflict":
      return "统一这段文字里的时间线索，避免同一场景同时出现彼此冲突的时段描述。";
    case "appearance_conflict":
      return "回看人物设定，把外貌描述改回既有设定，或明确交代外貌变化的原因。";
    case "lore_conflict":
      return "对照世界观设定修正文中的冲突点，避免引入未解释的新规则。";
    default:
      return "根据提示回看正文，优先修正会影响剧情理解的部分。";
  }
};

const getReviseLabel = (mode: ReviseMode) =>
  ({ trim: "精简节奏", literary: "文学润色", unify: "统一文风" })[mode];

const lineClass = (type: DiffRow["type"]) =>
  type === "add"
    ? "bg-emerald-50 text-emerald-900"
    : type === "remove"
      ? "bg-rose-50 text-rose-900"
      : "bg-neutral-50 text-neutral-700";

const buttonClass = (base: string, busy = false) =>
  `${base} transition disabled:cursor-not-allowed disabled:opacity-50 ${busy ? "cursor-wait opacity-60 grayscale" : ""}`;

const looksGarbledText = (value?: string | null) => {
  const text = (value ?? "").trim();
  if (!text) return false;
  return /[\u00C0-\u017F]|�/.test(text) || /\?{2,}/.test(text);
};

const displayVersionLabel = (item: SceneVersion) => {
  const raw = (item.label ?? "").trim();
  if (!raw) return displayVersionSourceLabel[item.source];
  if (/adopt branch/i.test(raw)) return "采纳支线版本";
  if (looksGarbledText(raw)) return displayVersionSourceLabel[item.source];
  return raw;
};

function LoadingDots({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl bg-neutral-100 px-4 py-3 text-sm text-neutral-700">
      <span className="inline-flex gap-1">
        <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-neutral-500 [animation-delay:-0.2s]" />
        <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-neutral-500 [animation-delay:-0.1s]" />
        <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-neutral-500" />
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
  for (let i = 0; i < max; i += 1) {
    if ((before[i] ?? "") === (after[i] ?? "")) {
      rows.push({ type: "context", text: before[i] ?? "" });
    } else {
      if (before[i] !== undefined) rows.push({ type: "remove", text: before[i] });
      if (after[i] !== undefined) rows.push({ type: "add", text: after[i] });
    }
  }
  return rows;
}

export default function EditorPage() {
  const [tab, setTab] = useState<Tab>("writing");
  const [sideTab, setSideTab] = useState<SideTab>("analysis");
  const [sceneId, setSceneId] = useState("b816b1bd-96b8-486e-a56b-4a26b396b562");
  const [title, setTitle] = useState("");
  const [status, setStatus] = useState<SceneStatus>("");
  const [draft, setDraft] = useState("");
  const [lengthMode, setLengthMode] = useState<LengthMode>("medium");
  const [reviseMode, setReviseMode] = useState<ReviseMode>("trim");
  const [applyMode, setApplyMode] = useState<ApplyMode>("strict");
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
  const [timeline, setTimeline] = useState<NonNullable<SceneContextResponse["timeline_events"]>>([]);
  const [memories, setMemories] = useState<NonNullable<SceneContextResponse["style_memories"]>>([]);
  const [knowledgeHits, setKnowledgeHits] = useState<NonNullable<SceneContextResponse["knowledge_hits"]>>([]);
  const [recentScenes, setRecentScenes] = useState<NonNullable<SceneContextResponse["recent_scenes"]>>([]);
  const [workflow, setWorkflow] = useState<WorkflowRun | null>(null);
  const [issues, setIssues] = useState<ConsistencyIssue[]>([]);
  const [issueSummary, setIssueSummary] = useState<string | null>(null);
  const [showAllIssues, setShowAllIssues] = useState(false);
  const [vnExport, setVnExport] = useState<VnExport | null>(null);
  const [busyKey, setBusyKey] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [providerSettings, setProviderSettings] = useState<ProviderSettingsItem[]>([
    { provider: "openai", api_base: "https://api.openai.com/v1", has_api_key: false, api_key_masked: null, api_key: "" },
    { provider: "deepseek", api_base: "https://api.deepseek.com/v1", has_api_key: false, api_key_masked: null, api_key: "" },
    { provider: "xai", api_base: "https://api.x.ai/v1", has_api_key: false, api_key_masked: null, api_key: "" },
  ]);

  const selectedVersion = versions.find((item) => item.id === selectedVersionId) ?? null;
  const compareVersion = versions.find((item) => item.id === compareVersionId) ?? null;
  const selectedItems = (analysisStore?.items ?? []).filter((item) => item.is_selected);
  const guidance = selectedItems.map((item) => item.content);
  const workflowPreview = readPayloadString(workflow?.output_payload ?? null, "final_text")
    || readPayloadString(workflow?.output_payload ?? null, "partial_text");
  const workflowAutoApplied = readPayloadBoolean(workflow?.output_payload ?? null, "auto_applied") === true;
  const workflowSafeToApply = readPayloadBoolean(workflow?.output_payload ?? null, "safe_to_apply") !== false;
  const rejectedPreview = (() => {
    const blockedStep = workflow?.steps.find((step) => step.guardrail_blocked);
    const preview = blockedStep?.output_payload?.rejected_text_preview;
    return typeof preview === "string" ? preview : "";
  })();
  const versionDiffRows = selectedVersion && compareVersion ? makeDiffRows(compareVersion.content, selectedVersion.content) : [];
  const visibleIssues = showAllIssues
    ? issues
    : issues.filter((item) => item.severity === "high").length
      ? issues.filter((item) => item.severity === "high")
      : issues.slice(0, 3);
  const contextSummary = useMemo(
    () => [`提示 ${guidance.length}`, `时间线 ${timeline.length}`, `风格记忆 ${memories.length}`, `近期场景 ${recentScenes.length}`].join(" · "),
    [guidance.length, memories.length, recentScenes.length, timeline.length],
  );

  useEffect(() => {
    void loadScene();
    void loadProviderSettings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function jsonFetch<T>(url: string, init?: RequestInit, fallback = "请求失败") {
    const response = await fetch(url, init);
    if (!response.ok) {
      try {
        const payload = (await response.json()) as { detail?: string };
        throw new Error(payload.detail ?? fallback);
      } catch {
        throw new Error(fallback);
      }
    }
    return (await response.json()) as T;
  }

  async function loadProviderSettings() {
    try {
      const payload = await jsonFetch<{ providers: ProviderSettingsItem[] }>(
        `${API}/api/settings/providers`,
        undefined,
        "读取 API 配置失败",
      );
      setProviderSettings(payload.providers.map((item) => ({ ...item, api_key: "" })));
    } catch (error) {
      console.error(error);
    }
  }

  function updateProviderField(provider: ProviderSettingsItem["provider"], field: "api_key" | "api_base", value: string) {
    setProviderSettings((current) =>
      current.map((item) => (item.provider === provider ? { ...item, [field]: value } : item)),
    );
  }

  async function saveProviderSettings() {
    setBusyKey("saveProviderSettings");
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      const payload = await jsonFetch<{ message: string; providers: ProviderSettingsItem[] }>(
        `${API}/api/settings/providers`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(
            providerSettings.reduce<Record<string, { api_key: string | null; api_base: string }>>((acc, item) => {
              acc[item.provider] = {
                api_key: item.api_key?.trim() ? item.api_key : null,
                api_base: item.api_base ?? "",
              };
              return acc;
            }, {}),
          ),
        },
        "保存 API 配置失败",
      );
      setProviderSettings(payload.providers.map((item) => ({ ...item, api_key: "" })));
      setStatusMessage(payload.message || "API 配置已保存");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "保存 API 配置失败");
    } finally {
      setBusyKey("");
    }
  }

  function setMessage(ok: string | null, error: string | null = null) {
    setStatusMessage(ok);
    setErrorMessage(error);
  }

  function clearDerived() {
    setGeneratedDraft("");
    setGeneratedNotes([]);
    setRevisedDraft("");
    setRevisionBase("");
    setRevisionNotes([]);
    setWorkflow(null);
    setVnExport(null);
  }

  async function loadVersions(targetSceneId = sceneId.trim()) {
    const payload = await jsonFetch<SceneVersion[]>(`${API}/api/scenes/${targetSceneId}/versions`, undefined, "读取版本失败");
    setVersions(payload);
    setSelectedVersionId((current) => (payload.some((item) => item.id === current) ? current : payload[0]?.id ?? ""));
    setCompareVersionId((current) => (payload.some((item) => item.id === current) ? current : payload[1]?.id ?? ""));
  }

  async function loadAnalyses(targetSceneId = sceneId.trim()) {
    const payload = await jsonFetch<AnalysisStore[]>(`${API}/api/ai/scenes/${targetSceneId}/analyses`, undefined, "读取分析记录失败");
    setAnalysisStore(payload[0] ?? null);
  }

  async function loadBranchDiff(branchId: string) {
    if (!branchId) {
      setBranchDiff(null);
      return;
    }
    setBranchDiff(await jsonFetch<BranchDiff>(`${API}/api/branches/${branchId}/diff`, undefined, "读取分支差异失败"));
  }

  async function loadBranches(targetSceneId = sceneId.trim()) {
    const payload = await jsonFetch<Branch[]>(`${API}/api/branches?scene_id=${targetSceneId}`, undefined, "读取分支失败");
    setBranches(payload);
    const nextId = payload.some((item) => item.id === selectedBranchId) ? selectedBranchId : payload[0]?.id ?? "";
    setSelectedBranchId(nextId);
    await loadBranchDiff(nextId);
  }

  async function loadScene() {
    if (!sceneId.trim()) {
      setErrorMessage("请先填写 scene_id");
      return;
    }
    setBusyKey("loadScene");
    setMessage(null);
    try {
      const payload = await jsonFetch<SceneContextResponse>(`${API}/api/scenes/${sceneId.trim()}/context`, undefined, "读取场景失败");
      setTitle(payload.scene.title ?? "");
      setStatus(payload.scene.status ?? "draft");
      setDraft(payload.scene.draft_text ?? "");
      setTimeline(payload.timeline_events ?? []);
      setMemories(payload.style_memories ?? []);
      setKnowledgeHits(payload.knowledge_hits ?? []);
      setRecentScenes(payload.recent_scenes ?? []);
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
    const payload = await jsonFetch<{ status?: SceneStatus }>(
      `${API}/api/scenes/${sceneId.trim()}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title.trim() || undefined,
          draft_text: nextDraft,
          version_source: source,
          version_label: label,
        }),
      },
      "保存场景失败",
    );
    setStatus(payload.status ?? status);
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
      const payload = await jsonFetch<{
        success: boolean;
        data?: AnalysisResult | null;
        error_type?: string | null;
        message?: string | null;
      }>(
        `${API}/api/ai/analyze-scene`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ scene_id: sceneId.trim() }),
        },
        "分析失败",
      );
      if (!payload.success || !payload.data) {
        return setErrorMessage(payload.message ?? "分析失败");
      }
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
      const ids = nextSelected
        ? [...new Set([...selectedItems.map((item) => item.id), itemId])]
        : selectedItems.map((item) => item.id).filter((id) => id !== itemId);
      const payload = await jsonFetch<AnalysisStore>(
        `${API}/api/ai/analyses/${analysisStore.id}/selection`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ selected_item_ids: ids }),
        },
        "更新分析选择失败",
      );
      setAnalysisStore(payload);
      setMessage(ids.length ? "已更新工作流提示。" : "已清空工作流提示。");
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
      const payload = await jsonFetch<{
        success: boolean;
        data?: { draft_text: string; notes: string[]; message?: string | null } | null;
        error_type?: string | null;
        message?: string | null;
      }>(
        `${API}/api/ai/write-scene`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ scene_id: sceneId.trim(), length: lengthMode, analysis_id: analysisStore?.id ?? null, guidance }),
        },
        "扩写失败",
      );
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
      const payload = await jsonFetch<{
        success: boolean;
        data?: { revised_text: string; notes: string[]; changed: boolean; message?: string | null } | null;
        error_type?: string | null;
        message?: string | null;
      }>(
        `${API}/api/ai/revise-scene`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ scene_id: sceneId.trim(), mode: reviseMode }),
        },
        "润色失败",
      );
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
      await patchScene(revisedDraft, "revise", `apply ${getReviseLabel(reviseMode)}`);
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
      const payload = await jsonFetch<{ current_text: string }>(
        `${API}/api/scenes/${sceneId.trim()}/versions/${selectedVersionId}/restore`,
        { method: "POST" },
        "恢复版本失败",
      );
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
      const payload = await jsonFetch<Branch>(
        `${API}/api/branches`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: branchName.trim(),
            description: branchDescription.trim() || undefined,
            source_scene_id: sceneId.trim(),
            source_version_id: selectedVersionId || undefined,
            metadata_json: { created_from: "editor" },
          }),
        },
        "创建分支失败",
      );
      setBranchName("");
      setBranchDescription("");
      await loadBranches(sceneId.trim());
      setSelectedBranchId(payload.id);
      await loadBranchDiff(payload.id);
      setTab("versions");
      setMessage("分支已创建。");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "创建分支失败");
    } finally {
      setBusyKey("");
    }
  }

  async function adoptBranch() {
    if (!selectedBranchId) return setErrorMessage("请先选择要采纳的分支。");
    setBusyKey("adoptBranch");
    setMessage(null);
    try {
      const payload = await jsonFetch<{ current_text: string }>(`${API}/api/branches/${selectedBranchId}/adopt`, { method: "POST" }, "采纳分支失败");
      setDraft(payload.current_text);
      clearDerived();
      setStatus("draft");
      await Promise.all([loadVersions(), loadBranches(), scanConsistency(payload.current_text)]);
      setMessage("分支已采纳并回填正文。");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "采纳分支失败");
    } finally {
      setBusyKey("");
    }
  }

  async function pollWorkflow(id: string) {
    for (let i = 0; i < 60; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, 1500));
      const payload = await jsonFetch<WorkflowRun>(`${API}/api/ai/workflows/${id}`, undefined, "读取工作流失败");
      setWorkflow(payload);
      if (isTerminal(payload.status)) return payload;
    }
    throw new Error("工作流轮询超时。");
  }

  async function scanConsistency(nextDraft = draft) {
    const payload = await jsonFetch<{ issues: ConsistencyIssue[]; summary: string }>(
      `${API}/api/consistency/scan`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scene_id: sceneId.trim(), draft_text: nextDraft }),
      },
      "一致性扫描失败",
    );
    setIssues(payload.issues ?? []);
    setIssueSummary(payload.summary ?? null);
    setShowAllIssues(false);
    if ((payload.issues ?? []).length) setSideTab("warnings");
  }

  async function applyWorkflowOutcome(run: WorkflowRun) {
    const autoApplied = readPayloadBoolean(run.output_payload ?? null, "auto_applied") === true;
    const safeToApply = readPayloadBoolean(run.output_payload ?? null, "safe_to_apply") !== false;
    const finalText = readPayloadString(run.output_payload ?? null, "final_text")
      || readPayloadString(run.output_payload ?? null, "partial_text");
    if (finalText && autoApplied) {
      setDraft(finalText);
      setGeneratedDraft(finalText);
      setGeneratedNotes([
        run.status === "partial_success"
          ? "工作流虽然有失败步骤，但系统只保留了安全正文，没有把坏结果写回主文。"
          : "工作流结果已经通过安全校验，并自动回填到正文。",
      ]);
      setStatus("draft");
      await loadVersions();
    } else if (finalText) {
      setGeneratedDraft(finalText);
      setGeneratedNotes([
        applyMode === "manual"
          ? "当前是手动模式，这份结果只会进入生成草稿区，不会自动覆盖正文。"
          : safeToApply
            ? "工作流已经产出可用草稿，但还没有自动写回正文，请人工确认。"
            : "结果被守门拦截，系统已经阻止自动回填正文。",
      ]);
    }
    await scanConsistency(finalText || draft);
  }

  async function runWorkflow() {
    if (!sceneId.trim()) return setErrorMessage("请先填写 scene_id");
    setBusyKey("runWorkflow");
    setMessage(null);
    try {
      const queued = await jsonFetch<WorkflowRun>(
        `${API}/api/ai/workflows/scene`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            scene_id: sceneId.trim(),
            length: lengthMode,
            guidance,
            auto_apply: applyMode === "strict",
          }),
        },
        "启动工作流失败",
      );
      setWorkflow(queued);
      setMessage("工作流已进入队列。");
      const completed = isTerminal(queued.status) ? queued : await pollWorkflow(queued.id);
      await applyWorkflowOutcome(completed);
      if (completed.status === "completed") {
        setMessage(applyMode === "strict" ? "工作流完成，结果已回填。" : "工作流完成，结果保存在建议稿区。");
      } else if (completed.status === "partial_success") {
        setMessage("工作流部分完成，已保留可用内容。");
      } else if (completed.status === "cancelled") {
        setMessage("工作流已取消。");
      } else {
        setErrorMessage(
          typeof completed.output_payload?.error_summary === "string"
            ? completed.output_payload.error_summary
            : completed.error_message ?? "工作流失败",
        );
      }
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
      const queued = await jsonFetch<WorkflowRun>(`${API}/api/ai/workflows/${workflow.id}/retry`, { method: "POST" }, "重试工作流失败");
      setWorkflow(queued);
      setMessage("工作流已重新排队。");
      await applyWorkflowOutcome(await pollWorkflow(queued.id));
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "重试工作流失败");
    } finally {
      setBusyKey("");
    }
  }

  async function cancelWorkflow() {
    if (!workflow?.id) return;
    setBusyKey("cancelWorkflow");
    setMessage(null);
    try {
      setWorkflow(await jsonFetch<WorkflowRun>(`${API}/api/ai/workflows/${workflow.id}/cancel`, { method: "POST" }, "取消工作流失败"));
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
      setVnExport(
        await jsonFetch<VnExport>(
          `${API}/api/vn/export`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ draft_text: draft, scene_title: title.trim() || undefined, include_image_prompts: true }),
          },
          "导出 VN 失败",
        ),
      );
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
    <main className="min-h-screen bg-neutral-100 text-neutral-900">
      <div className="mx-auto flex max-w-[1600px] flex-col gap-6 px-4 py-6">
        <section className="rounded-3xl bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-amber-700">WriterLab</p>
              <h1 className="mt-2 text-3xl font-semibold">写作台与分支工作区</h1>
              <p className="mt-2 text-sm text-neutral-600">版本是时间快照，分支是剧情支线。当前页面同时处理正文、工作流、版本和分支。</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl bg-amber-50 px-4 py-3"><div className="text-xs text-amber-700">场景状态</div><div className="mt-1 text-lg font-semibold">{displaySceneLabel[status]}</div></div>
              <div className="rounded-2xl bg-sky-50 px-4 py-3"><div className="text-xs text-sky-700">工作流状态</div><div className="mt-1 text-lg font-semibold">{displayWorkflowLabel[workflow?.status ?? ""] ?? "未运行"}</div></div>
              <div className="rounded-2xl bg-emerald-50 px-4 py-3"><div className="text-xs text-emerald-700">一致性问题</div><div className="mt-1 text-lg font-semibold">{issues.length}</div></div>
            </div>
          </div>
          <div className="mt-4 grid gap-3 lg:grid-cols-[2fr_1fr]">
            <input className="rounded-2xl border border-neutral-200 px-4 py-3 text-sm" value={sceneId} onChange={(e) => setSceneId(e.target.value)} />
            <input className="rounded-2xl border border-neutral-200 px-4 py-3 text-sm" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <button className={buttonClass("rounded-full bg-neutral-900 px-4 py-2 text-sm text-white", busyKey === "loadScene")} onClick={() => void loadScene()} disabled={busyKey === "loadScene"}>{busyKey === "loadScene" ? "加载中…" : "重新加载场景"}</button>
            <button className={buttonClass("rounded-full border border-neutral-300 px-4 py-2 text-sm", busyKey === "saveScene")} onClick={() => void saveScene()} disabled={busyKey === "saveScene"}>{busyKey === "saveScene" ? "保存中…" : "保存正文"}</button>
            <div className="ml-auto flex overflow-hidden rounded-full border border-neutral-300">
              <button className={`px-4 py-2 text-sm ${tab === "writing" ? "bg-neutral-900 text-white" : ""}`} onClick={() => setTab("writing")}>写作台</button>
              <button className={`px-4 py-2 text-sm ${tab === "versions" ? "bg-neutral-900 text-white" : ""}`} onClick={() => setTab("versions")}>版本与分支</button>
            </div>
          </div>
          {statusMessage ? <div className="mt-4 rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-900">{statusMessage}</div> : null}
          {errorMessage ? <div className="mt-4 rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-900">{errorMessage}</div> : null}
          {busyKey ? <div className="mt-4"><LoadingDots label={displayBusyLabel[busyKey] ?? "正在处理，请稍候…"} /></div> : null}
        </section>

        <div className="grid gap-6 xl:grid-cols-[1.7fr_0.95fr]">
          <section className="space-y-6">
            {tab === "writing" ? (
              <>
                <section className="rounded-3xl bg-white p-5 shadow-sm">
                  <div className="flex flex-wrap gap-3 text-sm text-neutral-600"><span>{contextSummary}</span></div>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <select className="rounded-full border border-neutral-300 px-4 py-2 text-sm" value={lengthMode} onChange={(e) => setLengthMode(e.target.value as LengthMode)}><option value="short">短</option><option value="medium">中</option><option value="long">长</option></select>
                    <select className="rounded-full border border-neutral-300 px-4 py-2 text-sm" value={reviseMode} onChange={(e) => setReviseMode(e.target.value as ReviseMode)}><option value="trim">精简节奏</option><option value="literary">文学润色</option><option value="unify">统一文风</option></select>
                    <select className="rounded-full border border-neutral-300 px-4 py-2 text-sm" value={applyMode} onChange={(e) => setApplyMode(e.target.value as ApplyMode)}><option value="strict">严格回填</option><option value="manual">手动确认</option></select>
                  </div>
                  <textarea className="mt-4 min-h-[420px] w-full rounded-3xl border border-neutral-200 px-5 py-4 text-sm leading-7" value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="在这里写当前正文。这个编辑区只代表主正文，不代表生成草稿或分支文本。" />
                  <div className="mt-4 flex flex-wrap gap-3">
                    <button className={buttonClass("rounded-full bg-neutral-900 px-4 py-2 text-sm text-white", busyKey === "analyzeScene")} onClick={() => void analyzeScene()} disabled={busyKey === "analyzeScene"}>{busyKey === "analyzeScene" ? "分析中…" : "分析场景"}</button>
                    <button className={buttonClass("rounded-full bg-amber-500 px-4 py-2 text-sm text-white", busyKey === "writeScene")} onClick={() => void writeScene()} disabled={busyKey === "writeScene"}>{busyKey === "writeScene" ? "生成中…" : "扩写正文"}</button>
                    <button className={buttonClass("rounded-full bg-sky-600 px-4 py-2 text-sm text-white", busyKey === "reviseScene")} onClick={() => void reviseScene()} disabled={busyKey === "reviseScene"}>{busyKey === "reviseScene" ? "润色中…" : "润色正文"}</button>
                    <button className={buttonClass("rounded-full bg-emerald-600 px-4 py-2 text-sm text-white", busyKey === "runWorkflow")} onClick={() => void runWorkflow()} disabled={busyKey === "runWorkflow"}>{busyKey === "runWorkflow" ? "执行中…" : "一键跑全流程"}</button>
                    <button className={buttonClass("rounded-full border border-neutral-300 px-4 py-2 text-sm", busyKey === "scanConsistency")} onClick={() => void scanConsistency()} disabled={busyKey === "scanConsistency"}>{busyKey === "scanConsistency" ? "扫描中…" : "一致性扫描"}</button>
                    <button className={buttonClass("rounded-full border border-neutral-300 px-4 py-2 text-sm", busyKey === "exportVn")} onClick={() => void exportVn()} disabled={busyKey === "exportVn"}>{busyKey === "exportVn" ? "导出中…" : "导出 VN"}</button>
                  </div>
                </section>

                {generatedDraft ? <section className="rounded-3xl bg-amber-50 p-5"><div className="flex justify-between gap-4"><div><h2 className="text-xl font-semibold">生成草稿</h2><p className="mt-1 text-sm text-amber-900/80">这是候选内容，不会自动等同于当前正文。</p></div><div className="flex gap-3"><button className="rounded-full bg-neutral-900 px-4 py-2 text-sm text-white" onClick={acceptGeneratedDraft}>放入正文编辑区</button><button className="rounded-full border border-neutral-300 px-4 py-2 text-sm" onClick={rejectGeneratedDraft}>丢弃</button></div></div><pre className="mt-4 whitespace-pre-wrap rounded-2xl bg-white px-4 py-4 text-sm leading-7">{generatedDraft}</pre>{generatedNotes.length ? <ul className="mt-4 space-y-2 text-sm">{generatedNotes.map((note, index) => <li key={`${note}-${index}`}>• {note}</li>)}</ul> : null}</section> : null}
                {revisedDraft ? <section className="rounded-3xl bg-sky-50 p-5"><div className="flex justify-between gap-4"><div><h2 className="text-xl font-semibold">待确认润色稿</h2><p className="mt-1 text-sm text-sky-900/80">左侧是原正文，右侧是润色建议。确认后才会覆盖正文。</p></div><div className="flex gap-3"><button className="rounded-full bg-neutral-900 px-4 py-2 text-sm text-white" onClick={() => void applyRevision()} disabled={busyKey === "applyRevision"}>采纳润色稿</button><button className="rounded-full border border-neutral-300 px-4 py-2 text-sm" onClick={discardRevision}>丢弃</button></div></div><div className="mt-4 grid gap-4 lg:grid-cols-2"><pre className="min-h-[220px] whitespace-pre-wrap rounded-2xl bg-white px-4 py-4 text-sm leading-7">{revisionBase}</pre><pre className="min-h-[220px] whitespace-pre-wrap rounded-2xl bg-white px-4 py-4 text-sm leading-7">{revisedDraft}</pre></div>{revisionNotes.length ? <ul className="mt-4 space-y-2 text-sm">{revisionNotes.map((note, index) => <li key={`${note}-${index}`}>• {note}</li>)}</ul> : null}</section> : null}
                {workflow ? <section className="rounded-3xl bg-white p-5 shadow-sm"><div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between"><div><h2 className="text-xl font-semibold">工作流结果区</h2><p className="mt-1 text-sm text-neutral-600">这里专门区分已自动回填结果、可用草稿，以及被守门拦截的结果。</p></div><div className="text-sm text-neutral-500">{displayWorkflowLabel[workflow.status] ?? workflow.status}</div></div>{workflowPreview ? <div className="mt-4 grid gap-4"><div className="rounded-2xl bg-neutral-50 px-4 py-3 text-sm text-neutral-700">{workflowAutoApplied ? "这份结果已经安全回填到正文。" : workflowSafeToApply ? "这份结果可用，但目前仍停留在草稿区。" : "这份结果未通过安全校验，系统没有自动回填正文。"}</div><pre className="min-h-[220px] whitespace-pre-wrap rounded-2xl bg-white px-4 py-4 text-sm leading-7 ring-1 ring-neutral-200">{workflowPreview}</pre></div> : null}{rejectedPreview ? <div className="mt-4 rounded-2xl bg-rose-50 px-4 py-4"><div className="text-sm font-semibold text-rose-900">被守门拦截的结果预览</div><p className="mt-1 text-sm text-rose-800">下面的内容被系统判定为不安全，因此没有进入正文。</p><pre className="mt-3 whitespace-pre-wrap rounded-2xl bg-white px-4 py-4 text-sm leading-7 text-neutral-800">{rejectedPreview}</pre></div> : null}</section> : null}
              </>
            ) : (
              <>
                <section className="rounded-3xl bg-white p-5 shadow-sm">
                  <div className="flex items-center justify-between"><h2 className="text-xl font-semibold">版本快照</h2><button className={buttonClass("rounded-full border border-neutral-300 px-4 py-2 text-sm", busyKey === "restoreVersion")} onClick={() => void restoreVersion()} disabled={!selectedVersionId || busyKey === "restoreVersion"}>{busyKey === "restoreVersion" ? "恢复中…" : "恢复当前选中版本"}</button></div>
                  <div className="mt-4 grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
                    <div className="space-y-3">
                      <select className="w-full rounded-2xl border border-neutral-200 px-3 py-3 text-sm" value={selectedVersionId} onChange={(e) => setSelectedVersionId(e.target.value)}>{versions.map((item) => <option key={item.id} value={item.id}>{displayVersionLabel(item)} · {fmt(item.created_at)}</option>)}</select>
                      <select className="w-full rounded-2xl border border-neutral-200 px-3 py-3 text-sm" value={compareVersionId} onChange={(e) => setCompareVersionId(e.target.value)}><option value="">不对比</option>{versions.map((item) => <option key={item.id} value={item.id}>{displayVersionLabel(item)} · {fmt(item.created_at)}</option>)}</select>
                    </div>
                    <div className="grid gap-4 lg:grid-cols-2"><pre className="min-h-[240px] whitespace-pre-wrap rounded-2xl bg-white px-4 py-4 text-sm leading-7 ring-1 ring-neutral-200">{compareVersion?.content || "选择对比版本后显示旧文本。"}</pre><pre className="min-h-[240px] whitespace-pre-wrap rounded-2xl bg-white px-4 py-4 text-sm leading-7 ring-1 ring-neutral-200">{selectedVersion?.content || "选择主版本后显示当前文本。"}</pre></div>
                  </div>
                  {versionDiffRows.length ? <div className="mt-4 space-y-1">{versionDiffRows.map((row, index) => <div key={`${row.type}-${index}`} className={`rounded-xl px-3 py-2 text-sm ${lineClass(row.type)}`}>{row.type === "add" ? "+ " : row.type === "remove" ? "- " : "  "}{row.text || " "}</div>)}</div> : null}
                </section>

                <section className="rounded-3xl bg-white p-5 shadow-sm">
                  <div className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
                    <div className="space-y-3">
                      <h2 className="text-xl font-semibold">剧情分支</h2>
                      <input className="w-full rounded-2xl border border-neutral-200 px-3 py-3 text-sm" value={branchName} onChange={(e) => setBranchName(e.target.value)} placeholder="分支名称" />
                      <textarea className="min-h-[120px] w-full rounded-2xl border border-neutral-200 px-3 py-3 text-sm" value={branchDescription} onChange={(e) => setBranchDescription(e.target.value)} placeholder="分支说明" />
                      <button className={buttonClass("w-full rounded-full bg-neutral-900 px-4 py-2 text-sm text-white", busyKey === "createBranch")} onClick={() => void createBranch()} disabled={busyKey === "createBranch"}>{busyKey === "createBranch" ? "创建中…" : "创建剧情分支"}</button>
                      <select className="w-full rounded-2xl border border-neutral-200 px-3 py-3 text-sm" value={selectedBranchId} onChange={(e) => { setSelectedBranchId(e.target.value); void loadBranchDiff(e.target.value); }}><option value="">请选择分支</option>{branches.map((item) => <option key={item.id} value={item.id}>{looksGarbledText(item.name) ? "剧情分支" : item.name} · {fmt(item.updated_at)}</option>)}</select>
                      <div className="rounded-2xl bg-neutral-50 px-4 py-3 text-sm text-neutral-700"><div>来源章节：{branchDiff?.source_chapter_id || "未记录"}</div><div className="mt-1">起点版本：{branchDiff?.source_version_label || "未记录"}</div><div className="mt-1">最新支线版本：{branchDiff?.latest_version_label || "未记录"}</div></div>
                    </div>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between"><div><h3 className="text-lg font-semibold">{branchDiff?.branch_name || "主线 vs 支线"}</h3><p className="text-sm text-neutral-600">左侧是主线正文，右侧是支线正文。</p></div><button className={buttonClass("rounded-full bg-amber-500 px-4 py-2 text-sm text-white", busyKey === "adoptBranch")} onClick={() => void adoptBranch()} disabled={!selectedBranchId || busyKey === "adoptBranch"}>{busyKey === "adoptBranch" ? "采纳中…" : "采纳这条支线"}</button></div>
                      <div className="grid gap-4 lg:grid-cols-2"><pre className="min-h-[260px] whitespace-pre-wrap rounded-2xl bg-white px-4 py-4 text-sm leading-7 ring-1 ring-neutral-200">{branchDiff?.base_text || "这里显示主线正文。"}</pre><pre className="min-h-[260px] whitespace-pre-wrap rounded-2xl bg-white px-4 py-4 text-sm leading-7 ring-1 ring-neutral-200">{branchDiff?.branch_text || "这里显示支线正文。"}</pre></div>
                      <div className="space-y-1">{(branchDiff?.diff_rows ?? []).length ? branchDiff?.diff_rows.map((row, index) => <div key={`${row.type}-${index}`} className={`rounded-xl px-3 py-2 text-sm ${lineClass(row.type)}`}>{row.type === "add" ? "+ " : row.type === "remove" ? "- " : "  "}{row.text || " "}</div>) : <div className="rounded-xl bg-neutral-50 px-3 py-2 text-sm text-neutral-500">选择分支后显示差异。</div>}</div>
                    </div>
                  </div>
                </section>
              </>
            )}
          </section>

          <aside className="space-y-6">
            <section className="rounded-3xl bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between"><h2 className="text-xl font-semibold">工作流</h2><div className="text-right text-sm text-neutral-500"><div>{displayWorkflowLabel[workflow?.status ?? ""] ?? "未运行"}</div><div>重试 {workflow?.retry_count ?? 0} 次</div></div></div>
              <div className="mt-4 flex flex-wrap gap-3"><button className={buttonClass("rounded-full border border-neutral-300 px-4 py-2 text-sm", busyKey === "retryWorkflow")} onClick={() => void retryWorkflow()} disabled={!workflow?.id || busyKey === "retryWorkflow"}>{busyKey === "retryWorkflow" ? "重试中…" : "重试工作流"}</button><button className={buttonClass("rounded-full border border-neutral-300 px-4 py-2 text-sm", busyKey === "cancelWorkflow")} onClick={() => void cancelWorkflow()} disabled={!workflow?.id || busyKey === "cancelWorkflow"}>{busyKey === "cancelWorkflow" ? "取消中…" : "取消工作流"}</button></div>
              <div className="mt-4 space-y-3">{(workflow?.steps ?? []).length ? workflow?.steps.map((step) => <div key={step.id} className="rounded-2xl bg-neutral-50 px-4 py-3"><div className="flex items-start justify-between gap-4"><div><div className="text-sm font-semibold">{displayStepTitle(step)}</div><div className="mt-1 text-xs text-neutral-500">{step.provider || "未记录模型提供方"} · {step.model || "未记录模型"} · {fmtDuration(step.duration_ms)}</div></div><div className="text-right text-xs text-neutral-500"><div>{displayWorkflowLabel[step.status] ?? step.status}</div><div>{step.fallback_used ? "已走降级" : "未走降级"}</div></div></div>{step.guardrail_blocked ? <div className="mt-2 text-xs text-rose-700">守门已拦截这一步的输出，因此没有继续写回正文。</div> : null}{step.error_message ? <div className="mt-2 text-xs text-rose-700">{displayWorkflowError(step.error_message)}</div> : null}</div>) : <div className="rounded-2xl border border-dashed border-neutral-300 px-4 py-6 text-sm text-neutral-500">还没有工作流记录。</div>}</div>
              {workflowPreview ? <pre className="mt-4 whitespace-pre-wrap rounded-2xl bg-neutral-50 px-4 py-4 text-sm leading-7">{workflowPreview}</pre> : null}
            </section>

            <section className="rounded-3xl bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between"><h2 className="text-xl font-semibold">分析与一致性</h2><div className="flex overflow-hidden rounded-full border border-neutral-300"><button className={`px-4 py-2 text-sm ${sideTab === "analysis" ? "bg-neutral-900 text-white" : ""}`} onClick={() => setSideTab("analysis")}>分析</button><button className={`px-4 py-2 text-sm ${sideTab === "warnings" ? "bg-neutral-900 text-white" : ""}`} onClick={() => setSideTab("warnings")}>一致性</button></div></div>
              {sideTab === "analysis" ? <div className="mt-4 space-y-4">{analysis?.summary ? <div className="rounded-2xl bg-neutral-50 px-4 py-3 text-sm leading-7">{analysis.summary}</div> : null}<div className="flex items-center justify-between"><div className="text-sm font-medium">已选写作提示</div><button className="rounded-full border border-neutral-300 px-3 py-1.5 text-xs" onClick={() => void copyGuidance()}>复制已选提示</button></div><div className="space-y-2">{(analysisStore?.items ?? []).length ? analysisStore?.items.map((item) => <label key={item.id} className="flex gap-3 rounded-2xl bg-neutral-50 px-3 py-3 text-sm"><input type="checkbox" className="mt-1" checked={item.is_selected} onChange={(e) => void toggleAnalysisItem(item.id, e.target.checked)} /><div><div className="font-medium">{item.title || item.item_type}{item.severity ? ` · ${displaySeverityLabel[item.severity] ?? item.severity}` : ""}</div><div className="mt-1">{item.content}</div></div></label>) : <div className="rounded-2xl border border-dashed border-neutral-300 px-3 py-6 text-sm text-neutral-500">先跑一次分析，才能选择提示。</div>}</div></div> : <div className="mt-4 space-y-3"><div className="rounded-2xl bg-neutral-50 px-4 py-3 text-sm">{issueSummary || "还没有扫描结果。"}</div>{visibleIssues.length ? visibleIssues.map((issue) => <div key={issue.id} className={`rounded-2xl px-4 py-3 ${issue.severity === "high" ? "bg-rose-50" : "bg-neutral-50"}`}><div className="flex items-start justify-between gap-4"><div><div className="text-sm font-semibold">{displayIssueLabel[issue.issue_type] ?? issue.issue_type}</div><div className="mt-1 text-xs text-neutral-500">严重度：{displaySeverityLabel[issue.severity] ?? issue.severity}</div></div><div className="rounded-full bg-white px-3 py-1 text-xs text-neutral-600">{displayIssueSource(issue.source)}</div></div><div className="mt-3 text-sm leading-6">{issue.message}</div>{issue.evidence_json ? <pre className="mt-3 whitespace-pre-wrap rounded-xl bg-white px-3 py-3 text-xs leading-6">{JSON.stringify(issue.evidence_json, null, 2)}</pre> : null}<div className="mt-3 text-xs text-neutral-500">建议动作：{deriveIssueSuggestion(issue)}</div></div>) : <div className="rounded-2xl border border-dashed border-neutral-300 px-4 py-6 text-sm text-neutral-500">还没有一致性问题。</div>}{issues.length > visibleIssues.length ? <button className="rounded-full border border-neutral-300 px-4 py-2 text-sm" onClick={() => setShowAllIssues((current) => !current)}>{showAllIssues ? "收起其余问题" : `查看更多 (${issues.length - visibleIssues.length})`}</button> : null}</div>}
            </section>
            <section className="rounded-3xl bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="text-xl font-semibold">Cloud API Config</h2>
                  <p className="mt-1 text-sm text-neutral-600">Save your OpenAI, DeepSeek, and xAI API keys here. After saving, workflow calls will prefer these cloud settings.</p>
                </div>
                <button
                  className={buttonClass("rounded-full bg-neutral-900 px-4 py-2 text-sm text-white", busyKey === "saveProviderSettings")}
                  onClick={() => void saveProviderSettings()}
                  disabled={busyKey === "saveProviderSettings"}
                >
                  {busyKey === "saveProviderSettings" ? "Saving..." : "Save API Config"}
                </button>
              </div>
              <div className="mt-4 space-y-4">
                {providerSettings.map((item) => (
                  <div key={item.provider} className="rounded-2xl bg-neutral-50 px-4 py-4">
                    <div className="flex items-center justify-between gap-4">
                      <div className="text-sm font-semibold text-neutral-900">
                        {item.provider === "openai" ? "OpenAI" : item.provider === "deepseek" ? "DeepSeek" : "xAI / Grok"}
                      </div>
                      <div className="text-xs text-neutral-500">
                        {item.has_api_key ? `Saved: ${item.api_key_masked ?? "configured"}` : "No API key saved yet"}
                      </div>
                    </div>
                    <div className="mt-3 grid gap-3">
                      <input
                        className="w-full rounded-2xl border border-neutral-200 bg-white px-3 py-3 text-sm"
                        value={item.api_base}
                        onChange={(e) => updateProviderField(item.provider, "api_base", e.target.value)}
                        placeholder="API Base URL"
                      />
                      <input
                        className="w-full rounded-2xl border border-neutral-200 bg-white px-3 py-3 text-sm"
                        type="password"
                        value={item.api_key ?? ""}
                        onChange={(e) => updateProviderField(item.provider, "api_key", e.target.value)}
                        placeholder={item.has_api_key ? "Leave blank to keep the saved key; enter a new value to replace it" : "Paste API key here"}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </section>



            <section className="rounded-3xl bg-white p-5 shadow-sm">
              <h2 className="text-xl font-semibold">记忆上下文与 VN 导出</h2>
              <div className="mt-4 space-y-4 text-sm text-neutral-700">
                <div className="rounded-2xl bg-neutral-50 px-4 py-3"><div className="font-medium text-neutral-900">时间线</div><div className="mt-2 space-y-2">{timeline.length ? timeline.map((item) => <div key={item.id}>• {item.title} {item.event_time_label ? `· ${item.event_time_label}` : ""}</div>) : <div>暂无。</div>}</div></div>
                <div className="rounded-2xl bg-neutral-50 px-4 py-3"><div className="font-medium text-neutral-900">风格记忆</div><div className="mt-2 space-y-2">{memories.length ? memories.map((item) => <div key={item.id}>• [{item.status}] {item.content}</div>) : <div>暂无。</div>}</div></div>
                <div className="rounded-2xl bg-neutral-50 px-4 py-3"><div className="font-medium text-neutral-900">设定命中</div><div className="mt-2 space-y-3">{knowledgeHits.length ? knowledgeHits.map((item) => <div key={item.chunk_id}><div className="font-medium text-neutral-900">{item.document_title} · {item.source_label || "记忆片段"}</div><div className="mt-1 text-xs text-neutral-500">分数 {item.score.toFixed(3)} · {item.confirmed ? "已确认" : "未确认/通用"}</div><div className="mt-1">{item.content}</div></div>) : <div>暂无。</div>}</div></div>
                <div className="rounded-2xl bg-neutral-50 px-4 py-3"><div className="font-medium text-neutral-900">近期场景</div><div className="mt-2 space-y-2">{recentScenes.length ? recentScenes.map((item) => <div key={item.scene_id}>• 第 {item.scene_no} 场 {item.title}</div>) : <div>暂无。</div>}</div></div>
                {vnExport ? <div className="rounded-2xl bg-emerald-50 px-4 py-3"><div className="font-medium text-emerald-900">VN 导出预览</div><pre className="mt-3 max-h-[220px] overflow-auto whitespace-pre-wrap rounded-xl bg-white px-3 py-3 text-sm leading-6 text-neutral-800">{vnExport.markdown_script}</pre>{vnExport.image_prompts.length ? <div className="mt-3 space-y-2">{vnExport.image_prompts.map((item, index) => <div key={`${item}-${index}`}>• {item}</div>)}</div> : null}</div> : null}
              </div>
            </section>
          </aside>
        </div>
      </div>
    </main>
  );
}


