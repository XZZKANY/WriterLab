"use client";

import type {
  AnalysisResult,
  AnalysisStore,
  IssueItem,
  KnowledgeHitItem,
  MemoryItem,
  RecentSceneItem,
  SideTab,
  TimelineItem,
  VnExportState,
} from "@/features/editor/hooks/use-scene-context";

type ContextSidebarProps = {
  sideTab: SideTab;
  analysis: AnalysisResult | null;
  analysisStore: AnalysisStore | null;
  issueSummary: string | null;
  visibleIssues: IssueItem[];
  issues: IssueItem[];
  showAllIssues: boolean;
  timeline: TimelineItem[];
  memories: MemoryItem[];
  knowledgeHits: KnowledgeHitItem[];
  recentScenes: RecentSceneItem[];
  vnExport: VnExportState;
  busyKey: string;
  onSideTabChange: (value: SideTab) => void;
  onCopyGuidance: () => void;
  onToggleAnalysisItem: (itemId: string, nextSelected: boolean) => void;
  onToggleShowAllIssues: () => void;
  onRunConsistencyScan: () => void;
  onExportVn: () => void;
  buttonClass: (base: string, busy?: boolean) => string;
  displaySeverityLabel: Record<string, string>;
  displayIssueLabel: Record<string, string>;
  displayIssueSource: (value?: string | null) => string;
  deriveIssueSuggestion: (issue: IssueItem) => string;
};

export function ContextSidebar({
  sideTab,
  analysis,
  analysisStore,
  issueSummary,
  visibleIssues,
  issues,
  showAllIssues,
  timeline,
  memories,
  knowledgeHits,
  recentScenes,
  vnExport,
  busyKey,
  onSideTabChange,
  onCopyGuidance,
  onToggleAnalysisItem,
  onToggleShowAllIssues,
  onRunConsistencyScan,
  onExportVn,
  buttonClass,
  displaySeverityLabel,
  displayIssueLabel,
  displayIssueSource,
  deriveIssueSuggestion,
}: ContextSidebarProps) {
  return (
    <aside className="space-y-6">
      <section className="rounded-3xl border border-white/8 bg-zinc-900/80 p-5 shadow-2xl">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">分析与一致性</h2>
          <div className="flex overflow-hidden rounded-full border border-white/10">
            <button
              className={`px-4 py-2 text-sm ${sideTab === "analysis" ? "bg-zinc-100 text-black" : ""}`}
              onClick={() => onSideTabChange("analysis")}
              type="button"
            >
              分析
            </button>
            <button
              className={`px-4 py-2 text-sm ${sideTab === "warnings" ? "bg-zinc-100 text-black" : ""}`}
              onClick={() => onSideTabChange("warnings")}
              type="button"
            >
              一致性
            </button>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          <button
            className={buttonClass("rounded-full border border-white/10 px-4 py-2 text-sm text-zinc-200", busyKey === "scanConsistency")}
            onClick={onRunConsistencyScan}
            disabled={busyKey === "scanConsistency"}
            type="button"
          >
            {busyKey === "scanConsistency" ? "扫描中..." : "一致性扫描"}
          </button>
        </div>
        {sideTab === "analysis" ? (
          <div className="mt-4 space-y-4">
            {analysis?.summary ? (
              <div className="rounded-2xl bg-zinc-900/70 px-4 py-3 text-sm leading-7">
                {analysis.summary}
              </div>
            ) : null}
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium">已选写作提示</div>
              <button
                className="rounded-full border border-white/10 px-3 py-1.5 text-xs"
                onClick={onCopyGuidance}
                type="button"
              >
                复制已选提示
              </button>
            </div>
            <div className="space-y-2">
              {(analysisStore?.items ?? []).length ? (
                analysisStore?.items.map((item) => (
                  <label
                    key={item.id}
                    className="flex gap-3 rounded-2xl bg-zinc-900/70 px-3 py-3 text-sm"
                  >
                    <input
                      type="checkbox"
                      className="mt-1"
                      checked={item.is_selected}
                      onChange={(event) => onToggleAnalysisItem(item.id, event.target.checked)}
                    />
                    <div>
                      <div className="font-medium">
                        {item.title || item.item_type}
                        {item.severity
                          ? ` · ${displaySeverityLabel[item.severity] ?? item.severity}`
                          : ""}
                      </div>
                      <div className="mt-1">{item.content}</div>
                    </div>
                  </label>
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-white/10 px-3 py-6 text-sm text-zinc-500">
                  先跑一次分析，才能选择提示。
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="mt-4 space-y-3">
            <div className="rounded-2xl bg-zinc-900/70 px-4 py-3 text-sm">
              {issueSummary || "还没有扫描结果。"}
            </div>
            {visibleIssues.length ? (
              visibleIssues.map((issue) => (
                <div
                  key={issue.id}
                  className={`rounded-2xl px-4 py-3 ${
                    issue.severity === "high"
                      ? "border border-rose-400/15 bg-rose-500/10 text-rose-100"
                      : "bg-zinc-900/70"
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="text-sm font-semibold">
                        {displayIssueLabel[issue.issue_type] ?? issue.issue_type}
                      </div>
                      <div className="mt-1 text-xs text-zinc-500">
                        严重度：{displaySeverityLabel[issue.severity] ?? issue.severity}
                      </div>
                    </div>
                    <div className="rounded-full bg-zinc-950 px-3 py-1 text-xs text-zinc-500">
                      {displayIssueSource(issue.source)}
                    </div>
                  </div>
                  <div className="mt-3 text-sm leading-6">{issue.message}</div>
                  {issue.evidence_json ? (
                    <pre className="mt-3 whitespace-pre-wrap rounded-xl bg-zinc-950 px-3 py-3 text-xs leading-6">
                      {JSON.stringify(issue.evidence_json, null, 2)}
                    </pre>
                  ) : null}
                  <div className="mt-3 text-xs text-zinc-500">
                    建议动作：{deriveIssueSuggestion(issue)}
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-white/10 px-4 py-6 text-sm text-zinc-500">
                还没有一致性问题。
              </div>
            )}
            {issues.length > visibleIssues.length ? (
              <button
                className="rounded-full border border-white/10 px-4 py-2 text-sm"
                onClick={onToggleShowAllIssues}
                type="button"
              >
                {showAllIssues ? "收起其余问题" : `查看更多 (${issues.length - visibleIssues.length})`}
              </button>
            ) : null}
          </div>
        )}
      </section>

      <section className="rounded-3xl border border-white/8 bg-zinc-900/80 p-5 shadow-2xl">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-xl font-semibold">记忆上下文与 VN 导出</h2>
          <button
            className={buttonClass("rounded-full border border-white/10 px-4 py-2 text-sm text-zinc-200", busyKey === "exportVn")}
            onClick={onExportVn}
            disabled={busyKey === "exportVn"}
            type="button"
          >
            {busyKey === "exportVn" ? "导出中..." : "导出 VN"}
          </button>
        </div>
        <div className="mt-4 space-y-4 text-sm text-zinc-300">
          <div className="rounded-2xl bg-zinc-900/70 px-4 py-3">
            <div className="font-medium text-zinc-100">时间线</div>
            <div className="mt-2 space-y-2">
              {timeline.length ? (
                timeline.map((item) => (
                  <div key={item.id}>
                    • {item.title}
                    {item.event_time_label ? ` · ${item.event_time_label}` : ""}
                  </div>
                ))
              ) : (
                <div>暂无。</div>
              )}
            </div>
          </div>
          <div className="rounded-2xl bg-zinc-900/70 px-4 py-3">
            <div className="font-medium text-zinc-100">风格记忆</div>
            <div className="mt-2 space-y-2">
              {memories.length ? (
                memories.map((item) => <div key={item.id}>• [{item.status}] {item.content}</div>)
              ) : (
                <div>暂无。</div>
              )}
            </div>
          </div>
          <div className="rounded-2xl bg-zinc-900/70 px-4 py-3">
            <div className="font-medium text-zinc-100">设定命中</div>
            <div className="mt-2 space-y-3">
              {knowledgeHits.length ? (
                knowledgeHits.map((item) => (
                  <div key={item.chunk_id}>
                    <div className="font-medium text-zinc-100">
                      {item.document_title} · {item.source_label || "记忆片段"}
                    </div>
                    <div className="mt-1 text-xs text-zinc-500">
                      分数 {item.score.toFixed(3)} · {item.confirmed ? "已确认" : "未确认 / 通用"}
                    </div>
                    <div className="mt-1">{item.content}</div>
                  </div>
                ))
              ) : (
                <div>暂无。</div>
              )}
            </div>
          </div>
          <div className="rounded-2xl bg-zinc-900/70 px-4 py-3">
            <div className="font-medium text-zinc-100">近期场景</div>
            <div className="mt-2 space-y-2">
              {recentScenes.length ? (
                recentScenes.map((item) => (
                  <div key={item.scene_id}>• 第 {item.scene_no} 场 {item.title}</div>
                ))
              ) : (
                <div>暂无。</div>
              )}
            </div>
          </div>
          {vnExport ? (
            <div className="rounded-2xl border border-emerald-400/15 bg-emerald-500/10 px-4 py-3 text-emerald-100">
              <div className="font-medium text-emerald-100">VN 导出预览</div>
              <pre className="mt-3 max-h-[220px] overflow-auto whitespace-pre-wrap rounded-xl bg-zinc-950 px-3 py-3 text-sm leading-6 text-zinc-200">
                {vnExport.markdown_script}
              </pre>
              {vnExport.image_prompts.length ? (
                <div className="mt-3 space-y-2">
                  {vnExport.image_prompts.map((item, index) => (
                    <div key={`${item}-${index}`}>• {item}</div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </section>
    </aside>
  );
}
