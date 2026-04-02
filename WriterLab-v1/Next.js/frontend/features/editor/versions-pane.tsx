"use client";

type DiffRow = { type: "add" | "remove" | "context"; text: string };

type SceneVersion = {
  id: string;
  content: string;
  label: string | null;
  source: "manual" | "write" | "revise" | "restore" | "workflow";
  created_at: string;
};

type Branch = {
  id: string;
  name: string;
  updated_at: string;
};

type BranchDiff = {
  branch_name?: string | null;
  base_text?: string | null;
  branch_text?: string | null;
  source_chapter_id?: string | null;
  source_version_label?: string | null;
  latest_version_label?: string | null;
  diff_rows?: DiffRow[];
};

type VersionsPaneProps = {
  busyKey: string;
  selectedVersionId: string;
  compareVersionId: string;
  versions: SceneVersion[];
  selectedVersion: SceneVersion | null;
  compareVersion: SceneVersion | null;
  versionDiffRows: DiffRow[];
  branchName: string;
  branchDescription: string;
  selectedBranchId: string;
  branches: Branch[];
  branchDiff: BranchDiff | null;
  onSelectedVersionIdChange: (value: string) => void;
  onCompareVersionIdChange: (value: string) => void;
  onRestoreVersion: () => void;
  onBranchNameChange: (value: string) => void;
  onBranchDescriptionChange: (value: string) => void;
  onCreateBranch: () => void;
  onSelectedBranchIdChange: (value: string) => void;
  onAdoptBranch: () => void;
  buttonClass: (base: string, busy?: boolean) => string;
  displayVersionLabel: (item: SceneVersion) => string;
  formatTime: (value?: string | null) => string;
  lineClass: (type: DiffRow["type"]) => string;
  looksGarbledText: (value?: string | null) => boolean;
};

export function VersionsPane({
  busyKey,
  selectedVersionId,
  compareVersionId,
  versions,
  selectedVersion,
  compareVersion,
  versionDiffRows,
  branchName,
  branchDescription,
  selectedBranchId,
  branches,
  branchDiff,
  onSelectedVersionIdChange,
  onCompareVersionIdChange,
  onRestoreVersion,
  onBranchNameChange,
  onBranchDescriptionChange,
  onCreateBranch,
  onSelectedBranchIdChange,
  onAdoptBranch,
  buttonClass,
  displayVersionLabel,
  formatTime,
  lineClass,
  looksGarbledText,
}: VersionsPaneProps) {
  return (
    <>
      <section className="rounded-[30px] border border-white/8 bg-[#1b1b1b] p-5 shadow-[0_24px_60px_rgba(0,0,0,0.24)]">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-zinc-100">版本快照</h2>
          <button
            className={buttonClass(
              "rounded-full border border-white/10 px-4 py-2 text-sm text-zinc-200",
              busyKey === "restoreVersion",
            )}
            onClick={onRestoreVersion}
            disabled={!selectedVersionId || busyKey === "restoreVersion"}
          >
            {busyKey === "restoreVersion" ? "恢复中..." : "恢复当前选中版本"}
          </button>
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
          <div className="space-y-3">
            <select
              className="w-full rounded-2xl border border-white/10 bg-[#232323] px-3 py-3 text-sm text-zinc-100 outline-none"
              value={selectedVersionId}
              onChange={(event) => onSelectedVersionIdChange(event.target.value)}
            >
              {versions.map((item) => (
                <option key={item.id} value={item.id}>
                  {displayVersionLabel(item)} · {formatTime(item.created_at)}
                </option>
              ))}
            </select>
            <select
              className="w-full rounded-2xl border border-white/10 bg-[#232323] px-3 py-3 text-sm text-zinc-100 outline-none"
              value={compareVersionId}
              onChange={(event) => onCompareVersionIdChange(event.target.value)}
            >
              <option value="">不对比</option>
              {versions.map((item) => (
                <option key={item.id} value={item.id}>
                  {displayVersionLabel(item)} · {formatTime(item.created_at)}
                </option>
              ))}
            </select>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <pre className="min-h-[240px] whitespace-pre-wrap rounded-2xl border border-white/8 bg-[#151515] px-4 py-4 text-sm leading-7 text-zinc-100">
              {compareVersion?.content || "选择对比版本后显示旧文本。"}
            </pre>
            <pre className="min-h-[240px] whitespace-pre-wrap rounded-2xl border border-white/8 bg-[#151515] px-4 py-4 text-sm leading-7 text-zinc-100">
              {selectedVersion?.content || "选择主版本后显示当前文本。"}
            </pre>
          </div>
        </div>

        {versionDiffRows.length ? (
          <div className="mt-4 space-y-1">
            {versionDiffRows.map((row, index) => (
              <div
                key={`${row.type}-${index}`}
                className={`rounded-xl px-3 py-2 text-sm ${lineClass(row.type)}`}
              >
                {row.type === "add" ? "+ " : row.type === "remove" ? "- " : "  "}
                {row.text || " "}
              </div>
            ))}
          </div>
        ) : null}
      </section>

      <section className="rounded-[30px] border border-white/8 bg-[#1b1b1b] p-5 shadow-[0_24px_60px_rgba(0,0,0,0.24)]">
        <div className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
          <div className="space-y-3">
            <h2 className="text-xl font-semibold text-zinc-100">剧情分支</h2>
            <input
              className="w-full rounded-2xl border border-white/10 bg-[#232323] px-3 py-3 text-sm text-zinc-100 outline-none placeholder:text-zinc-500"
              value={branchName}
              onChange={(event) => onBranchNameChange(event.target.value)}
              placeholder="分支名称"
            />
            <textarea
              className="min-h-[120px] w-full rounded-2xl border border-white/10 bg-[#232323] px-3 py-3 text-sm text-zinc-100 outline-none placeholder:text-zinc-500"
              value={branchDescription}
              onChange={(event) => onBranchDescriptionChange(event.target.value)}
              placeholder="分支说明"
            />
            <button
              className={buttonClass(
                "w-full rounded-full bg-zinc-100 px-4 py-2 text-sm font-medium text-black",
                busyKey === "createBranch",
              )}
              onClick={onCreateBranch}
              disabled={busyKey === "createBranch"}
            >
              {busyKey === "createBranch" ? "创建中..." : "创建剧情分支"}
            </button>
            <select
              className="w-full rounded-2xl border border-white/10 bg-[#232323] px-3 py-3 text-sm text-zinc-100 outline-none"
              value={selectedBranchId}
              onChange={(event) => onSelectedBranchIdChange(event.target.value)}
            >
              <option value="">请选择分支</option>
              {branches.map((item) => (
                <option key={item.id} value={item.id}>
                  {looksGarbledText(item.name) ? "剧情分支" : item.name} ·{" "}
                  {formatTime(item.updated_at)}
                </option>
              ))}
            </select>
            <div className="rounded-2xl border border-white/8 bg-[#232323] px-4 py-3 text-sm text-zinc-300">
              <div>来源章节：{branchDiff?.source_chapter_id || "未记录"}</div>
              <div className="mt-1">起点版本：{branchDiff?.source_version_label || "未记录"}</div>
              <div className="mt-1">最新支线版本：{branchDiff?.latest_version_label || "未记录"}</div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-zinc-100">
                  {branchDiff?.branch_name || "主线 vs 支线"}
                </h3>
                <p className="text-sm text-zinc-500">左侧是主线正文，右侧是支线正文。</p>
              </div>
              <button
                className={buttonClass(
                  "rounded-full bg-amber-400 px-4 py-2 text-sm font-medium text-black",
                  busyKey === "adoptBranch",
                )}
                onClick={onAdoptBranch}
                disabled={!selectedBranchId || busyKey === "adoptBranch"}
              >
                {busyKey === "adoptBranch" ? "采纳中..." : "采纳这条支线"}
              </button>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <pre className="min-h-[260px] whitespace-pre-wrap rounded-2xl border border-white/8 bg-[#151515] px-4 py-4 text-sm leading-7 text-zinc-100">
                {branchDiff?.base_text || "这里显示主线正文。"}
              </pre>
              <pre className="min-h-[260px] whitespace-pre-wrap rounded-2xl border border-white/8 bg-[#151515] px-4 py-4 text-sm leading-7 text-zinc-100">
                {branchDiff?.branch_text || "这里显示支线正文。"}
              </pre>
            </div>

            <div className="space-y-1">
              {(branchDiff?.diff_rows ?? []).length ? (
                branchDiff?.diff_rows?.map((row, index) => (
                  <div
                    key={`${row.type}-${index}`}
                    className={`rounded-xl px-3 py-2 text-sm ${lineClass(row.type)}`}
                  >
                    {row.type === "add" ? "+ " : row.type === "remove" ? "- " : "  "}
                    {row.text || " "}
                  </div>
                ))
              ) : (
                <div className="rounded-xl border border-dashed border-white/10 bg-[#202020] px-3 py-2 text-sm text-zinc-500">
                  选择分支后显示差异。
                </div>
              )}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
