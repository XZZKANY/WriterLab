"use client";

import type { ReactNode } from "react";

type Tab = "writing" | "versions";

type WorkspaceHeaderProps = {
  sceneStatusLabel: string;
  workflowStatusLabel: string;
  issueCount: number;
  sceneId: string;
  title: string;
  onSceneIdChange: (value: string) => void;
  onTitleChange: (value: string) => void;
  onReload: () => void;
  onSave: () => void;
  tab: Tab;
  onTabChange: (tab: Tab) => void;
  busyKey: string;
  statusMessage: string | null;
  errorMessage: string | null;
  loadingContent: ReactNode;
  buttonClass: (base: string, busy?: boolean) => string;
};

export function WorkspaceHeader({
  sceneStatusLabel,
  workflowStatusLabel,
  issueCount,
  sceneId,
  title,
  onSceneIdChange,
  onTitleChange,
  onReload,
  onSave,
  tab,
  onTabChange,
  busyKey,
  statusMessage,
  errorMessage,
  loadingContent,
  buttonClass,
}: WorkspaceHeaderProps) {
  return (
    <section className="rounded-[30px] border border-white/8 bg-[#1b1b1b] p-5 shadow-[0_24px_60px_rgba(0,0,0,0.24)]">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl">
          <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-zinc-500">WriterLab</p>
          <h1 className="mt-3 text-[2rem] font-semibold tracking-[-0.05em] text-zinc-100">写作台与分支工作区</h1>
          <p className="mt-3 text-sm leading-7 text-zinc-500">编辑器入口现在只保留写作、版本和上下文辅助，运行诊断能力已经迁往独立入口。</p>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-2xl border border-amber-400/15 bg-amber-500/10 px-4 py-3">
            <div className="text-[11px] uppercase tracking-[0.24em] text-amber-200/80">Scene</div>
            <div className="mt-2 text-lg font-semibold text-amber-50">{sceneStatusLabel}</div>
          </div>
          <div className="rounded-2xl border border-sky-400/15 bg-sky-500/10 px-4 py-3">
            <div className="text-[11px] uppercase tracking-[0.24em] text-sky-200/80">Workflow</div>
            <div className="mt-2 text-lg font-semibold text-sky-50">{workflowStatusLabel}</div>
          </div>
          <div className="rounded-2xl border border-emerald-400/15 bg-emerald-500/10 px-4 py-3">
            <div className="text-[11px] uppercase tracking-[0.24em] text-emerald-200/80">Issues</div>
            <div className="mt-2 text-lg font-semibold text-emerald-50">{issueCount}</div>
          </div>
        </div>
      </div>

      <div className="mt-5 grid gap-3 lg:grid-cols-[1.4fr_1fr]">
        <input
          className="rounded-2xl border border-white/10 bg-[#232323] px-4 py-3 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-500 focus:border-zinc-500"
          value={sceneId}
          onChange={(event) => onSceneIdChange(event.target.value)}
          placeholder="scene_id"
        />
        <input
          className="rounded-2xl border border-white/10 bg-[#232323] px-4 py-3 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-500 focus:border-zinc-500"
          value={title}
          onChange={(event) => onTitleChange(event.target.value)}
          placeholder="场景标题"
        />
      </div>

      <div className="mt-5 flex flex-wrap gap-3">
        <button
          className={buttonClass("rounded-full bg-zinc-100 px-4 py-2 text-sm font-medium text-black", busyKey === "loadScene")}
          onClick={onReload}
          disabled={busyKey === "loadScene"}
          type="button"
        >
          {busyKey === "loadScene" ? "加载中..." : "重新加载场景"}
        </button>
        <button
          className={buttonClass("rounded-full border border-white/10 px-4 py-2 text-sm text-zinc-200", busyKey === "saveScene")}
          onClick={onSave}
          disabled={busyKey === "saveScene"}
          type="button"
        >
          {busyKey === "saveScene" ? "保存中..." : "保存正文"}
        </button>

        <div className="ml-auto flex overflow-hidden rounded-full border border-white/10 bg-[#202020]">
          <button className={`px-4 py-2 text-sm transition ${tab === "writing" ? "bg-zinc-100 text-black" : "text-zinc-400 hover:text-zinc-100"}`} onClick={() => onTabChange("writing")} type="button">
            写作台
          </button>
          <button className={`px-4 py-2 text-sm transition ${tab === "versions" ? "bg-zinc-100 text-black" : "text-zinc-400 hover:text-zinc-100"}`} onClick={() => onTabChange("versions")} type="button">
            版本与分支
          </button>
        </div>
      </div>

      {statusMessage ? <div className="mt-4 rounded-2xl border border-emerald-400/15 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">{statusMessage}</div> : null}
      {errorMessage ? <div className="mt-4 rounded-2xl border border-rose-400/15 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">{errorMessage}</div> : null}
      {loadingContent ? <div className="mt-4">{loadingContent}</div> : null}
    </section>
  );
}
