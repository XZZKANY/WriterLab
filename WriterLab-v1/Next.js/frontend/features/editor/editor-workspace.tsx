"use client";

import { useEffect, useMemo, useState } from "react";
import { ContextSidebar } from "@/features/editor/context-sidebar";
import {
  type SceneStatus,
  useAuthoringWorkspace,
} from "@/features/editor/hooks/use-authoring-workspace";
import {
  type AnalysisResult,
  type AnalysisStore,
  type ConsistencyPayload,
  type IssueItem,
  type SceneContextPayload,
  type VnExportState,
  useSceneContext,
} from "@/features/editor/hooks/use-scene-context";
import {
  type Branch,
  type BranchDiff,
  type DiffRow,
  type SceneVersion,
  useVersioningWorkspace,
} from "@/features/editor/hooks/use-versioning-workspace";
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
  exportVn as exportVnRequest,
  fetchSceneAnalyses,
  reviseScene as reviseSceneRequest,
  scanConsistency as scanConsistencyRequest,
  updateAnalysisSelection,
  writeScene as writeSceneRequest,
} from "@/lib/api/workflow";

type Tab = "writing" | "versions";

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
type AdoptBranchPayload = { current_text: string };

const sceneLabel: Record<SceneStatus, string> = {
  "": "未记录",
  draft: "草稿",
  generated: "已生成",
  analyzed: "已分析",
  revision_ready: "待确认润色稿",
};
const issueLabel: Record<string, string> = {
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
const severityLabel: Record<string, string> = {
  high: "高",
  medium: "中",
  low: "低",
};
const busyLabel: Record<string, string> = {
  loadScene: "正在加载场景...",
  saveScene: "正在保存正文...",
  analyzeScene: "正在分析场景...",
  writeScene: "正在生成草稿...",
  reviseScene: "正在润色正文...",
  scanConsistency: "正在扫描一致性...",
  exportVn: "正在导出 VN...",
  applyRevision: "正在采纳润色稿...",
  restoreVersion: "正在恢复版本...",
  createBranch: "正在创建分支...",
  adoptBranch: "正在采纳支线版本...",
  toggleAnalysis: "正在更新分析项状态...",
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
const normalizeText = (value: string) => value.replace(/\r\n/g, "\n").trim();
const displayIssueSource = (value?: string | null) =>
  !value?.trim() ? "规则检查 / LLM 复核" : value === "LLM复核" ? "LLM 复核" : value;
const deriveIssueSuggestion = (issue: IssueItem) =>
  issue.fix_suggestion?.trim() || "根据提示回看正文，优先修正会影响剧情理解的部分。";
const lineClass = (type: DiffRow["type"]) =>
  type === "add"
    ? "bg-emerald-500/10 text-emerald-200"
    : type === "remove"
      ? "bg-rose-500/10 text-rose-200"
      : "bg-[#232323] text-zinc-300";
const buttonClass = (base: string, busy = false) =>
  `${base} transition disabled:cursor-not-allowed disabled:opacity-50 ${busy ? "cursor-wait opacity-60 grayscale" : ""}`;
const displayVersionLabel = (item: SceneVersion) => item.label || item.source;
const looksGarbledText = (value?: string | null) => {
  const text = value?.trim() ?? "";
  return text.length > 0 && /[�]|锟|鈥|鏂|鍦|姝/.test(text);
};

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

export default function EditorWorkspace() {
  const [tab, setTab] = useState<Tab>("writing");
  const [busyKey, setBusyKey] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const {
    sceneId,
    title,
    status,
    draft,
    lengthMode,
    reviseMode,
    applyMode,
    analysis,
    analysisStore,
    generatedDraft,
    generatedNotes,
    revisedDraft,
    revisionBase,
    revisionNotes,
    setSceneId,
    setTitle,
    setStatus,
    setDraft,
    setLengthMode,
    setReviseMode,
    setApplyMode,
    setAnalysis,
    setAnalysisStore,
    setGeneratedDraft,
    setGeneratedNotes,
    setRevisedDraft,
    setRevisionBase,
    setRevisionNotes,
  } = useAuthoringWorkspace();
  const {
    versions,
    selectedVersionId,
    compareVersionId,
    branches,
    selectedBranchId,
    branchDiff,
    branchName,
    branchDescription,
    selectedVersion,
    compareVersion,
    versionDiffRows,
    setVersions,
    setSelectedVersionId,
    setCompareVersionId,
    setBranches,
    setSelectedBranchId,
    setBranchDiff,
    setBranchName,
    setBranchDescription,
  } = useVersioningWorkspace();
  const {
    sideTab,
    issues,
    issueSummary,
    showAllIssues,
    timeline,
    memories,
    knowledgeHits,
    recentScenes,
    vnExport,
    visibleIssues,
    setSideTab,
    setShowAllIssues,
    setVnExport,
    applySceneContext,
    applyConsistencyResult,
    resetSceneContext,
  } = useSceneContext();

  const guidance = (analysisStore?.items ?? [])
    .filter((item) => item.is_selected)
    .map((item) => item.content);
  const contextSummary = useMemo(
    () =>
      [
        `提示 ${guidance.length}`,
        `时间线 ${timeline.length}`,
        `风格记忆 ${memories.length}`,
        `近期场景 ${recentScenes.length}`,
      ].join(" · "),
    [guidance.length, memories.length, recentScenes.length, timeline.length],
  );

  useEffect(() => {
    void loadScene();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
    resetSceneContext();
  }

  async function loadVersions(targetSceneId = sceneId.trim()) {
    const payload = await fetchSceneVersions<SceneVersion[]>(targetSceneId);
    setVersions(payload);
    setSelectedVersionId((current) =>
      payload.some((item) => item.id === current) ? current : payload[0]?.id ?? "",
    );
    setCompareVersionId((current) =>
      payload.some((item) => item.id === current) ? current : payload[1]?.id ?? "",
    );
  }

  async function loadAnalyses(targetSceneId = sceneId.trim()) {
    const payload = await fetchSceneAnalyses<AnalysisStore[]>(targetSceneId);
    setAnalysisStore(payload[0] ?? null);
  }

  async function loadBranchDiffState(branchId: string) {
    if (!branchId) {
      setBranchDiff(null);
      return;
    }
    setBranchDiff(await fetchBranchDiff<BranchDiff>(branchId));
  }

  async function loadBranches(targetSceneId = sceneId.trim()) {
    const payload = await fetchBranchesByScene<Branch[]>(targetSceneId);
    setBranches(payload);
    const nextId = payload.some((item) => item.id === selectedBranchId)
      ? selectedBranchId
      : payload[0]?.id ?? "";
    setSelectedBranchId(nextId);
    await loadBranchDiffState(nextId);
  }

  async function loadScene() {
    if (!sceneId.trim()) {
      setErrorMessage("请先填写 scene_id");
      return;
    }
    setBusyKey("loadScene");
    setMessage(null);
    try {
      const payload = await fetchSceneContext<SceneContextPayload>(sceneId.trim());
      setTitle(payload.scene?.title ?? "");
      setStatus(payload.scene_status ?? payload.scene?.status ?? "draft");
      setDraft(payload.scene?.draft_text ?? "");
      applySceneContext(payload);
      clearDerived();
      await Promise.all([
        loadVersions(sceneId.trim()),
        loadAnalyses(sceneId.trim()),
        loadBranches(sceneId.trim()),
      ]);
      setMessage("场景已加载。");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "读取场景失败");
    } finally {
      setBusyKey("");
    }
  }

  async function patchScene(nextDraft = draft, source = "manual", label = "manual update") {
    const payload = await updateScene<UpdateScenePayload>(sceneId.trim(), {
      title: title.trim() || undefined,
      draft_text: nextDraft,
      version_source: source,
      version_label: label,
    });
    setStatus(payload.scene_status ?? payload.status ?? status);
  }

  async function saveScene() {
    if (!sceneId.trim()) {
      setErrorMessage("请先填写 scene_id");
      return;
    }
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
    if (!sceneId.trim()) {
      setErrorMessage("请先填写 scene_id");
      return;
    }
    if (!draft.trim()) {
      setErrorMessage("请先输入正文。");
      return;
    }
    setBusyKey("analyzeScene");
    setMessage(null);
    try {
      await patchScene(draft, "manual", "analyze source");
      const payload = await analyzeSceneRequest<AnalyzeScenePayload>({
        scene_id: sceneId.trim(),
      });
      if (!payload.success || !payload.data) {
        setErrorMessage(payload.message ?? "分析失败");
        return;
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
      const selectedIds = (analysisStore.items ?? [])
        .filter((item) => item.is_selected)
        .map((item) => item.id);
      const nextIds = nextSelected
        ? [...new Set([...selectedIds, itemId])]
        : selectedIds.filter((id) => id !== itemId);
      setAnalysisStore(
        await updateAnalysisSelection<AnalysisStore>(analysisStore.id, {
          selected_item_ids: nextIds,
        }),
      );
      setMessage(nextIds.length ? "已更新写作提示。" : "已清空写作提示。");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "更新分析选择失败");
    } finally {
      setBusyKey("");
    }
  }

  async function writeScene() {
    if (!sceneId.trim()) {
      setErrorMessage("请先填写 scene_id");
      return;
    }
    setBusyKey("writeScene");
    setMessage(null);
    try {
      await patchScene(draft, "manual", "write source");
      const payload = await writeSceneRequest<WriteScenePayload>({
        scene_id: sceneId.trim(),
        length: lengthMode,
        analysis_id: analysisStore?.id ?? null,
        guidance,
      });
      if (!payload.success || !payload.data) {
        setErrorMessage(payload.message ?? "扩写失败");
        return;
      }
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
    if (!sceneId.trim()) {
      setErrorMessage("请先填写 scene_id");
      return;
    }
    if (!draft.trim()) {
      setErrorMessage("请先输入正文。");
      return;
    }
    setBusyKey("reviseScene");
    setMessage(null);
    try {
      await patchScene(draft, "manual", "revise source");
      const payload = await reviseSceneRequest<ReviseScenePayload>({
        scene_id: sceneId.trim(),
        mode: reviseMode,
      });
      if (!payload.success || !payload.data) {
        setErrorMessage(payload.message ?? "润色失败");
        return;
      }
      if (
        !payload.data.changed ||
        normalizeText(payload.data.revised_text) === normalizeText(draft)
      ) {
        setRevisionNotes(payload.data.notes ?? []);
        setMessage(payload.data.message ?? "当前正文无需额外修改。");
        return;
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
      const payload = await restoreSceneVersion<RestoreVersionPayload>(
        sceneId.trim(),
        selectedVersionId,
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
    if (!sceneId.trim()) {
      setErrorMessage("请先填写 scene_id");
      return;
    }
    if (!branchName.trim()) {
      setErrorMessage("请填写分支名称。");
      return;
    }
    setBusyKey("createBranch");
    setMessage(null);
    try {
      const payload = await createBranchRequest<Branch>({
        name: branchName.trim(),
        description: branchDescription.trim() || undefined,
        source_scene_id: sceneId.trim(),
        source_version_id: selectedVersionId || undefined,
        metadata_json: { created_from: "editor" },
      });
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
      const payload = await scanConsistencyRequest<ConsistencyPayload>({
        scene_id: sceneId.trim(),
        draft_text: nextDraft,
      });
      applyConsistencyResult(payload);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "一致性扫描失败");
    } finally {
      if (showBusy) setBusyKey("");
    }
  }

  async function adoptBranch() {
    if (!selectedBranchId) {
      setErrorMessage("请先选择要采纳的分支。");
      return;
    }
    setBusyKey("adoptBranch");
    setMessage(null);
    try {
      const payload = await adoptBranchRequest<AdoptBranchPayload>(selectedBranchId);
      setDraft(payload.current_text);
      clearDerived();
      setStatus("draft");
      await Promise.all([
        loadVersions(),
        loadBranches(),
        runConsistencyScan(payload.current_text, false),
      ]);
      setMessage("分支已采纳并回填正文。");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "采纳分支失败");
    } finally {
      setBusyKey("");
    }
  }

  async function exportVn() {
    if (!draft.trim()) {
      setErrorMessage("请先输入正文。");
      return;
    }
    setBusyKey("exportVn");
    setMessage(null);
    try {
      setVnExport(
        await exportVnRequest<VnExportState>({
          draft_text: draft,
          scene_title: title.trim() || undefined,
          include_image_prompts: true,
        }),
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
    <main className="min-h-screen bg-[#171717] text-zinc-100">
      <div className="mx-auto flex max-w-[1600px] flex-col gap-6 px-4 py-6">
        <WorkspaceHeader
          sceneStatusLabel={sceneLabel[status]}
          workflowStatusLabel="已迁往诊断台"
          issueCount={issues.length}
          sceneId={sceneId}
          title={title}
          onSceneIdChange={setSceneId}
          onTitleChange={setTitle}
          onReload={() => void loadScene()}
          onSave={() => void saveScene()}
          tab={tab}
          onTabChange={setTab}
          busyKey={busyKey}
          statusMessage={statusMessage}
          errorMessage={errorMessage}
          loadingContent={
            busyKey ? (
              <LoadingDots label={busyLabel[busyKey] ?? "正在处理，请稍候..."} />
            ) : null
          }
          buttonClass={buttonClass}
        />

        <div className="grid gap-6 xl:grid-cols-[1.7fr_0.95fr]">
          <section className="space-y-6">
            {tab === "writing" ? (
              <WritingPane
                contextSummary={contextSummary}
                lengthMode={lengthMode}
                reviseMode={reviseMode}
                applyMode={applyMode}
                draft={draft}
                generatedDraft={generatedDraft}
                generatedNotes={generatedNotes}
                revisedDraft={revisedDraft}
                revisionBase={revisionBase}
                revisionNotes={revisionNotes}
                busyKey={busyKey}
                onLengthModeChange={setLengthMode}
                onReviseModeChange={setReviseMode}
                onApplyModeChange={setApplyMode}
                onDraftChange={setDraft}
                onAnalyze={() => void analyzeScene()}
                onWrite={() => void writeScene()}
                onRevise={() => void reviseScene()}
                onAcceptGeneratedDraft={acceptGeneratedDraft}
                onRejectGeneratedDraft={rejectGeneratedDraft}
                onApplyRevision={() => void applyRevision()}
                onDiscardRevision={discardRevision}
                buttonClass={buttonClass}
              />
            ) : (
              <VersionsPane
                busyKey={busyKey}
                selectedVersionId={selectedVersionId}
                compareVersionId={compareVersionId}
                versions={versions}
                selectedVersion={selectedVersion}
                compareVersion={compareVersion}
                versionDiffRows={versionDiffRows}
                branchName={branchName}
                branchDescription={branchDescription}
                selectedBranchId={selectedBranchId}
                branches={branches}
                branchDiff={branchDiff}
                onSelectedVersionIdChange={setSelectedVersionId}
                onCompareVersionIdChange={setCompareVersionId}
                onRestoreVersion={() => void restoreVersion()}
                onBranchNameChange={setBranchName}
                onBranchDescriptionChange={setBranchDescription}
                onCreateBranch={() => void createBranch()}
                onSelectedBranchIdChange={(value) => {
                  setSelectedBranchId(value);
                  void loadBranchDiffState(value);
                }}
                onAdoptBranch={() => void adoptBranch()}
                buttonClass={buttonClass}
                displayVersionLabel={displayVersionLabel}
                formatTime={fmt}
                lineClass={lineClass}
                looksGarbledText={looksGarbledText}
              />
            )}
          </section>

          <ContextSidebar
            sideTab={sideTab}
            analysis={analysis}
            analysisStore={analysisStore}
            issueSummary={issueSummary}
            visibleIssues={visibleIssues}
            issues={issues}
            showAllIssues={showAllIssues}
            timeline={timeline}
            memories={memories}
            knowledgeHits={knowledgeHits}
            recentScenes={recentScenes}
            vnExport={vnExport}
            busyKey={busyKey}
            onSideTabChange={setSideTab}
            onCopyGuidance={() => void copyGuidance()}
            onToggleAnalysisItem={(itemId, nextSelected) =>
              void toggleAnalysisItem(itemId, nextSelected)
            }
            onToggleShowAllIssues={() => setShowAllIssues((current) => !current)}
            onRunConsistencyScan={() => void runConsistencyScan(draft, true)}
            onExportVn={() => void exportVn()}
            buttonClass={buttonClass}
            displaySeverityLabel={severityLabel}
            displayIssueLabel={issueLabel}
            displayIssueSource={displayIssueSource}
            deriveIssueSuggestion={deriveIssueSuggestion}
          />
        </div>
      </div>
    </main>
  );
}
