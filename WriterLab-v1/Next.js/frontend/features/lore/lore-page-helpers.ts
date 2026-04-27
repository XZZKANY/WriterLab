import type {
  CharacterResponse,
  LocationResponse,
  LoreEntryResponse,
} from "@/lib/api/lore";

export type LoreMode = "characters" | "locations" | "entries";

export type DetailDraft = {
  name: string;
  aliases: string;
  appearance: string;
  personality: string;
  background: string;
  motivation: string;
  speaking_style: string;
  status: string;
  secrets: string;
  description: string;
  title: string;
  category: string;
  content: string;
  priority: string;
  canonical: boolean;
};

// 三种 lore 视图（角色 / 地点 / 词条）的页眉文案与空态标签集中维护。
export const modeMeta: Record<LoreMode, { title: string; description: string; emptyLabel: string }> = {
  characters: {
    title: "角色库",
    description: "角色视图聚焦姓名、别名、性格和状态。",
    emptyLabel: "角色",
  },
  locations: {
    title: "地点库",
    description: "地点视图聚焦地理节点和描述。",
    emptyLabel: "地点",
  },
  entries: {
    title: "设定词条库",
    description: "词条视图聚焦分类、正文和 canonical 标记。",
    emptyLabel: "词条",
  },
};

// 表单控件的视觉一致性由这组 Tailwind 类名集中保证。
export const inputClassName =
  "rounded-2xl border border-white/8 bg-[#212121] px-4 py-3 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-zinc-600";
export const textareaClassName =
  "min-h-32 rounded-2xl border border-white/8 bg-[#212121] px-4 py-3 text-sm leading-7 text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-zinc-600";
export const primaryButtonClassName =
  "rounded-xl bg-zinc-100 px-4 py-2.5 text-sm font-medium tracking-[-0.01em] text-black transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:bg-zinc-500";
export const secondaryButtonClassName =
  "rounded-xl border border-white/10 px-4 py-2.5 text-sm font-medium tracking-[-0.01em] text-zinc-200 transition hover:border-zinc-500 hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-60";

export const emptyDetailDraft: DetailDraft = {
  name: "",
  aliases: "",
  appearance: "",
  personality: "",
  background: "",
  motivation: "",
  speaking_style: "",
  status: "",
  secrets: "",
  description: "",
  title: "",
  category: "",
  content: "",
  priority: "50",
  canonical: true,
};

export function makeDraftFromCharacter(item: CharacterResponse): DetailDraft {
  return {
    ...emptyDetailDraft,
    name: item.name,
    aliases: item.aliases || "",
    appearance: item.appearance || "",
    personality: item.personality || "",
    background: item.background || "",
    motivation: item.motivation || "",
    speaking_style: item.speaking_style || "",
    status: item.status || "",
    secrets: item.secrets || "",
  };
}

export function makeDraftFromLocation(item: LocationResponse): DetailDraft {
  return {
    ...emptyDetailDraft,
    name: item.name,
    description: item.description || "",
  };
}

export function makeDraftFromLoreEntry(item: LoreEntryResponse): DetailDraft {
  return {
    ...emptyDetailDraft,
    title: item.title,
    category: item.category,
    content: item.content,
    priority: String(item.priority),
    canonical: item.canonical,
  };
}

export function normalizeOptionalText(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}
