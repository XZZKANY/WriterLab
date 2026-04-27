import type { SceneStatus } from "@/features/editor/hooks/use-authoring-workspace";
import type {
  IssueItem,
} from "@/features/editor/hooks/use-scene-context";
import type {
  DiffRow,
  SceneVersion,
} from "@/features/editor/hooks/use-versioning-workspace";

// 场景状态、问题类型、严重度、忙碌阶段在 UI 各处展示，集中维护避免文案漂移。
export const sceneLabel: Record<SceneStatus, string> = {
  "": "未记录",
  draft: "草稿",
  generated: "已生成",
  analyzed: "已分析",
  revision_ready: "待确认润色稿",
};

export const issueLabel: Record<string, string> = {
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

export const severityLabel: Record<string, string> = {
  high: "高",
  medium: "中",
  low: "低",
};

export const busyLabel: Record<string, string> = {
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

export const fmt = (value?: string | null) =>
  value
    ? new Date(value).toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "未记录";

export const normalizeText = (value: string) => value.replace(/\r\n/g, "\n").trim();

export const displayIssueSource = (value?: string | null) =>
  !value?.trim() ? "规则检查 / LLM 复核" : value === "LLM复核" ? "LLM 复核" : value;

export const deriveIssueSuggestion = (issue: IssueItem) =>
  issue.fix_suggestion?.trim() || "根据提示回看正文，优先修正会影响剧情理解的部分。";

export const lineClass = (type: DiffRow["type"]) =>
  type === "add"
    ? "bg-emerald-500/10 text-emerald-200"
    : type === "remove"
      ? "bg-rose-500/10 text-rose-200"
      : "bg-[#232323] text-zinc-300";

export const buttonClass = (base: string, busy = false) =>
  `${base} transition disabled:cursor-not-allowed disabled:opacity-50 ${busy ? "cursor-wait opacity-60 grayscale" : ""}`;

export const displayVersionLabel = (item: SceneVersion) => item.label || item.source;

// 用于识别历史导入数据中的乱码（GB18030/UTF-8 串扰留下的特征字符）。
export const looksGarbledText = (value?: string | null) => {
  const text = value?.trim() ?? "";
  return text.length > 0 && /[�]|锟|鈥|鏂|鍦|姝/.test(text);
};
