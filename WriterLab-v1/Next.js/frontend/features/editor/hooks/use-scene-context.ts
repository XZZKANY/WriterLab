"use client";

import { useMemo, useState } from "react";

export type SideTab = "analysis" | "warnings";

export type AnalysisItem = {
  id: string;
  item_type: string;
  title?: string | null;
  severity?: string | null;
  content: string;
  is_selected: boolean;
};

export type AnalysisStore = { id: string; items: AnalysisItem[] };
export type AnalysisResult = { summary?: string; problems?: { severity: string }[] };

export type IssueItem = {
  id: string;
  issue_type: string;
  severity: string;
  source?: string | null;
  message: string;
  evidence_json?: unknown;
  fix_suggestion?: string | null;
};

export type TimelineItem = { id: string; title: string; event_time_label?: string | null };
export type MemoryItem = { id: string; status: string; content: string };
export type KnowledgeHitItem = {
  chunk_id: string;
  document_title: string;
  source_label?: string | null;
  score: number;
  confirmed?: boolean | null;
  content: string;
};
export type RecentSceneItem = { scene_id: string; scene_no: number; title: string };
export type ActiveContextSnapshot = {
  hard_filters?: string[];
  hard_filter_result?: Record<string, unknown>;
  scope_resolution?: Record<string, unknown>;
  source_diversity_applied?: Record<string, unknown>;
  budget?: Record<string, unknown>;
  summary_reason?: string | null;
  deduped_sources?: string[];
  clipped_sources?: string[];
  candidates?: {
    source_type: string;
    source_id: string;
    title: string;
    score: number;
    diversity_slot?: string | null;
    summary_applied?: boolean;
  }[];
  summary_output?: unknown[];
} | null;
export type VnExportState = { markdown_script: string; image_prompts: string[] } | null;
type SceneStatus = "" | "draft" | "generated" | "analyzed" | "revision_ready";
export type SceneContextPayload = {
  scene?: { title?: string | null; draft_text?: string | null; status?: SceneStatus };
  scene_status?: SceneStatus;
  timeline_events?: TimelineItem[];
  style_memories?: MemoryItem[];
  knowledge_hits?: KnowledgeHitItem[];
  recent_scenes?: RecentSceneItem[];
  context_compile_snapshot?: ActiveContextSnapshot;
};
export type ConsistencyPayload = { issues?: IssueItem[]; summary?: string | null };

export function useSceneContext() {
  const [sideTab, setSideTab] = useState<SideTab>("analysis");
  const [issues, setIssues] = useState<IssueItem[]>([]);
  const [issueSummary, setIssueSummary] = useState<string | null>(null);
  const [showAllIssues, setShowAllIssues] = useState(false);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [knowledgeHits, setKnowledgeHits] = useState<KnowledgeHitItem[]>([]);
  const [recentScenes, setRecentScenes] = useState<RecentSceneItem[]>([]);
  const [contextSnapshot, setContextSnapshot] = useState<ActiveContextSnapshot>(null);
  const [vnExport, setVnExport] = useState<VnExportState>(null);

  const visibleIssues = useMemo(() => {
    if (showAllIssues) return issues;
    const highSeverityIssues = issues.filter((item) => item.severity === "high");
    return highSeverityIssues.length ? highSeverityIssues : issues.slice(0, 3);
  }, [issues, showAllIssues]);

  function applySceneContext(payload: SceneContextPayload) {
    setTimeline(payload.timeline_events ?? []);
    setMemories(payload.style_memories ?? []);
    setKnowledgeHits(payload.knowledge_hits ?? []);
    setRecentScenes(payload.recent_scenes ?? []);
    setContextSnapshot(payload.context_compile_snapshot ?? null);
  }

  function applyConsistencyResult(payload: ConsistencyPayload) {
    const nextIssues = payload.issues ?? [];
    setIssues(nextIssues);
    setIssueSummary(payload.summary ?? null);
    setShowAllIssues(false);
    if (nextIssues.length) setSideTab("warnings");
  }

  function resetSceneContext() {
    setIssues([]);
    setIssueSummary(null);
    setShowAllIssues(false);
    setVnExport(null);
  }

  return {
    sideTab,
    issues,
    issueSummary,
    showAllIssues,
    timeline,
    memories,
    knowledgeHits,
    recentScenes,
    contextSnapshot,
    vnExport,
    visibleIssues,
    setSideTab,
    setShowAllIssues,
    setVnExport,
    applySceneContext,
    applyConsistencyResult,
    resetSceneContext,
  };
}
