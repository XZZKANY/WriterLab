"use client";

type LengthMode = "short" | "medium" | "long";
type ReviseMode = "trim" | "literary" | "unify";
type ApplyMode = "strict" | "manual";
type WorkflowProviderMode = "live" | "smoke_fixture";

type WritingPaneProps = {
  contextSummary: string;
  lengthMode: LengthMode;
  reviseMode: ReviseMode;
  applyMode: ApplyMode;
  workflowProviderMode: WorkflowProviderMode;
  fixtureScenario: string;
  draft: string;
  generatedDraft: string;
  generatedNotes: string[];
  revisedDraft: string;
  revisionBase: string;
  revisionNotes: string[];
  busyKey: string;
  onLengthModeChange: (value: LengthMode) => void;
  onReviseModeChange: (value: ReviseMode) => void;
  onApplyModeChange: (value: ApplyMode) => void;
  onWorkflowProviderModeChange: (value: WorkflowProviderMode) => void;
  onFixtureScenarioChange: (value: string) => void;
  onDraftChange: (value: string) => void;
  onAnalyze: () => void;
  onWrite: () => void;
  onRevise: () => void;
  onRunWorkflow: () => void;
  onScanConsistency: () => void;
  onExportVn: () => void;
  onAcceptGeneratedDraft: () => void;
  onRejectGeneratedDraft: () => void;
  onApplyRevision: () => void;
  onDiscardRevision: () => void;
  buttonClass: (base: string, busy?: boolean) => string;
};

export function WritingPane({
  contextSummary,
  lengthMode,
  reviseMode,
  applyMode,
  workflowProviderMode,
  fixtureScenario,
  draft,
  generatedDraft,
  generatedNotes,
  revisedDraft,
  revisionBase,
  revisionNotes,
  busyKey,
  onLengthModeChange,
  onReviseModeChange,
  onApplyModeChange,
  onWorkflowProviderModeChange,
  onFixtureScenarioChange,
  onDraftChange,
  onAnalyze,
  onWrite,
  onRevise,
  onRunWorkflow,
  onScanConsistency,
  onExportVn,
  onAcceptGeneratedDraft,
  onRejectGeneratedDraft,
  onApplyRevision,
  onDiscardRevision,
  buttonClass,
}: WritingPaneProps) {
  return (
    <>
      <section className="rounded-[30px] border border-white/8 bg-[#1b1b1b] p-5 shadow-[0_24px_60px_rgba(0,0,0,0.24)]">
        <div className="flex flex-wrap gap-3 text-sm text-zinc-500">
          <span>{contextSummary}</span>
        </div>

        <div className="mt-4 flex flex-wrap gap-3">
          <select
            className="rounded-full border border-white/10 bg-[#232323] px-4 py-2 text-sm text-zinc-100 outline-none"
            value={lengthMode}
            onChange={(event) => onLengthModeChange(event.target.value as LengthMode)}
          >
            <option value="short">短</option>
            <option value="medium">中</option>
            <option value="long">长</option>
          </select>
          <select
            className="rounded-full border border-white/10 bg-[#232323] px-4 py-2 text-sm text-zinc-100 outline-none"
            value={reviseMode}
            onChange={(event) => onReviseModeChange(event.target.value as ReviseMode)}
          >
            <option value="trim">精简节奏</option>
            <option value="literary">文学润色</option>
            <option value="unify">统一文风</option>
          </select>
          <select
            className="rounded-full border border-white/10 bg-[#232323] px-4 py-2 text-sm text-zinc-100 outline-none"
            value={applyMode}
            onChange={(event) => onApplyModeChange(event.target.value as ApplyMode)}
          >
            <option value="strict">严格回填</option>
            <option value="manual">手动确认</option>
          </select>
          <select
            className="rounded-full border border-white/10 bg-[#232323] px-4 py-2 text-sm text-zinc-100 outline-none"
            value={workflowProviderMode}
            onChange={(event) =>
              onWorkflowProviderModeChange(event.target.value as WorkflowProviderMode)
            }
          >
            <option value="live">live provider</option>
            <option value="smoke_fixture">smoke fixture</option>
          </select>
          {workflowProviderMode === "smoke_fixture" ? (
            <select
              className="rounded-full border border-white/10 bg-[#232323] px-4 py-2 text-sm text-zinc-100 outline-none"
              value={fixtureScenario}
              onChange={(event) => onFixtureScenarioChange(event.target.value)}
            >
              <option value="happy_path">happy_path</option>
              <option value="style_fail">style_fail</option>
              <option value="planner_wait_review">planner_wait_review</option>
              <option value="guard_block">guard_block</option>
              <option value="check_issue">check_issue</option>
              <option value="malformed_planner">malformed_planner</option>
            </select>
          ) : null}
        </div>

        <textarea
          className="mt-4 min-h-[420px] w-full rounded-[28px] border border-white/10 bg-[#151515] px-5 py-4 text-sm leading-7 text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-zinc-500"
          value={draft}
          onChange={(event) => onDraftChange(event.target.value)}
          placeholder="在这里编辑当前主正文。生成草稿、润色稿和工作流输出会在独立区域中显示。"
        />

        <div className="mt-4 flex flex-wrap gap-3">
          <button
            className={buttonClass(
              "rounded-full bg-zinc-100 px-4 py-2 text-sm font-medium text-black",
              busyKey === "analyzeScene",
            )}
            onClick={onAnalyze}
            disabled={busyKey === "analyzeScene"}
          >
            {busyKey === "analyzeScene" ? "分析中..." : "分析场景"}
          </button>
          <button
            className={buttonClass(
              "rounded-full bg-amber-400 px-4 py-2 text-sm font-medium text-black",
              busyKey === "writeScene",
            )}
            onClick={onWrite}
            disabled={busyKey === "writeScene"}
          >
            {busyKey === "writeScene" ? "生成中..." : "扩写正文"}
          </button>
          <button
            className={buttonClass(
              "rounded-full bg-sky-500 px-4 py-2 text-sm font-medium text-white",
              busyKey === "reviseScene",
            )}
            onClick={onRevise}
            disabled={busyKey === "reviseScene"}
          >
            {busyKey === "reviseScene" ? "润色中..." : "润色正文"}
          </button>
          <button
            className={buttonClass(
              "rounded-full bg-emerald-500 px-4 py-2 text-sm font-medium text-white",
              busyKey === "runWorkflow",
            )}
            onClick={onRunWorkflow}
            disabled={busyKey === "runWorkflow"}
          >
            {busyKey === "runWorkflow" ? "执行中..." : "一键跑全流程"}
          </button>
          <button
            className={buttonClass(
              "rounded-full border border-white/10 px-4 py-2 text-sm text-zinc-200",
              busyKey === "scanConsistency",
            )}
            onClick={onScanConsistency}
            disabled={busyKey === "scanConsistency"}
          >
            {busyKey === "scanConsistency" ? "扫描中..." : "一致性扫描"}
          </button>
          <button
            className={buttonClass(
              "rounded-full border border-white/10 px-4 py-2 text-sm text-zinc-200",
              busyKey === "exportVn",
            )}
            onClick={onExportVn}
            disabled={busyKey === "exportVn"}
          >
            {busyKey === "exportVn" ? "导出中..." : "导出 VN"}
          </button>
        </div>
      </section>

      {generatedDraft ? (
        <section className="rounded-[30px] border border-amber-400/15 bg-amber-500/10 p-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h2 className="text-xl font-semibold text-amber-50">生成草稿</h2>
              <p className="mt-1 text-sm text-amber-100/75">
                这是候选内容，不会自动覆盖当前正文。
              </p>
            </div>
            <div className="flex gap-3">
              <button
                className="rounded-full bg-zinc-100 px-4 py-2 text-sm font-medium text-black"
                onClick={onAcceptGeneratedDraft}
              >
                放入正文编辑区
              </button>
              <button
                className="rounded-full border border-amber-200/20 px-4 py-2 text-sm text-amber-50"
                onClick={onRejectGeneratedDraft}
              >
                丢弃
              </button>
            </div>
          </div>

          <pre className="mt-4 whitespace-pre-wrap rounded-2xl border border-white/8 bg-[#171717] px-4 py-4 text-sm leading-7 text-zinc-100">
            {generatedDraft}
          </pre>

          {generatedNotes.length ? (
            <ul className="mt-4 space-y-2 text-sm text-amber-50">
              {generatedNotes.map((note, index) => (
                <li key={`${note}-${index}`}>• {note}</li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}

      {revisedDraft ? (
        <section className="rounded-[30px] border border-sky-400/15 bg-sky-500/10 p-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h2 className="text-xl font-semibold text-sky-50">待确认润色稿</h2>
              <p className="mt-1 text-sm text-sky-100/75">
                左侧是原正文，右侧是润色建议，确认后才会覆盖正文。
              </p>
            </div>
            <div className="flex gap-3">
              <button
                className={buttonClass(
                  "rounded-full bg-zinc-100 px-4 py-2 text-sm font-medium text-black",
                  busyKey === "applyRevision",
                )}
                onClick={onApplyRevision}
                disabled={busyKey === "applyRevision"}
              >
                {busyKey === "applyRevision" ? "采纳中..." : "采纳润色稿"}
              </button>
              <button
                className="rounded-full border border-sky-200/20 px-4 py-2 text-sm text-sky-50"
                onClick={onDiscardRevision}
              >
                丢弃
              </button>
            </div>
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <pre className="min-h-[220px] whitespace-pre-wrap rounded-2xl border border-white/8 bg-[#171717] px-4 py-4 text-sm leading-7 text-zinc-100">
              {revisionBase}
            </pre>
            <pre className="min-h-[220px] whitespace-pre-wrap rounded-2xl border border-white/8 bg-[#171717] px-4 py-4 text-sm leading-7 text-zinc-100">
              {revisedDraft}
            </pre>
          </div>

          {revisionNotes.length ? (
            <ul className="mt-4 space-y-2 text-sm text-sky-50">
              {revisionNotes.map((note, index) => (
                <li key={`${note}-${index}`}>• {note}</li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}
    </>
  );
}
