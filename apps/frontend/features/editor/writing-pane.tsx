"use client";

type LengthMode = "short" | "medium" | "long";
type ReviseMode = "trim" | "literary" | "unify";
type ApplyMode = "strict" | "manual";

type WritingPaneProps = {
  contextSummary: string;
  lengthMode: LengthMode;
  reviseMode: ReviseMode;
  applyMode: ApplyMode;
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
  onDraftChange: (value: string) => void;
  onAnalyze: () => void;
  onWrite: () => void;
  onRevise: () => void;
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
  onDraftChange,
  onAnalyze,
  onWrite,
  onRevise,
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
            <option value="short">短稿</option>
            <option value="medium">中稿</option>
            <option value="long">长稿</option>
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
        </div>

        <textarea
          className="mt-4 min-h-[420px] w-full rounded-[28px] border border-white/10 bg-[#151515] px-5 py-4 text-sm leading-7 text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-zinc-500"
          value={draft}
          onChange={(event) => onDraftChange(event.target.value)}
          placeholder="在这里编辑当前主正文。生成草稿和润色稿会在下方候选区域显示。"
        />

        <div className="mt-4 flex flex-wrap gap-3">
          <button
            className={buttonClass("rounded-full bg-zinc-100 px-4 py-2 text-sm font-medium text-black", busyKey === "analyzeScene")}
            onClick={onAnalyze}
            disabled={busyKey === "analyzeScene"}
            type="button"
          >
            {busyKey === "analyzeScene" ? "分析中..." : "分析场景"}
          </button>
          <button
            className={buttonClass("rounded-full bg-amber-400 px-4 py-2 text-sm font-medium text-black", busyKey === "writeScene")}
            onClick={onWrite}
            disabled={busyKey === "writeScene"}
            type="button"
          >
            {busyKey === "writeScene" ? "生成中..." : "扩写正文"}
          </button>
          <button
            className={buttonClass("rounded-full bg-sky-500 px-4 py-2 text-sm font-medium text-white", busyKey === "reviseScene")}
            onClick={onRevise}
            disabled={busyKey === "reviseScene"}
            type="button"
          >
            {busyKey === "reviseScene" ? "润色中..." : "润色正文"}
          </button>
        </div>
      </section>

      {generatedDraft ? (
        <section className="rounded-[30px] border border-amber-400/15 bg-amber-500/10 p-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h2 className="text-xl font-semibold text-amber-50">生成草稿</h2>
              <p className="mt-1 text-sm text-amber-100/75">这是候选内容，不会自动覆盖当前正文。</p>
            </div>
            <div className="flex gap-3">
              <button className="rounded-full bg-zinc-100 px-4 py-2 text-sm font-medium text-black" onClick={onAcceptGeneratedDraft} type="button">
                放入正文编辑区
              </button>
              <button className="rounded-full border border-amber-200/20 px-4 py-2 text-sm text-amber-50" onClick={onRejectGeneratedDraft} type="button">
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
              <p className="mt-1 text-sm text-sky-100/75">左侧是原正文，右侧是润色建议，确认后才会覆盖正文。</p>
            </div>
            <div className="flex gap-3">
              <button
                className={buttonClass("rounded-full bg-zinc-100 px-4 py-2 text-sm font-medium text-black", busyKey === "applyRevision")}
                onClick={onApplyRevision}
                disabled={busyKey === "applyRevision"}
                type="button"
              >
                {busyKey === "applyRevision" ? "应用中..." : "应用润色稿"}
              </button>
              <button className="rounded-full border border-sky-200/20 px-4 py-2 text-sm text-sky-50" onClick={onDiscardRevision} type="button">
                丢弃
              </button>
            </div>
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <pre className="min-h-[240px] whitespace-pre-wrap rounded-2xl border border-white/8 bg-[#151515] px-4 py-4 text-sm leading-7 text-zinc-100">
              {revisionBase}
            </pre>
            <pre className="min-h-[240px] whitespace-pre-wrap rounded-2xl border border-white/8 bg-[#151515] px-4 py-4 text-sm leading-7 text-zinc-100">
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
