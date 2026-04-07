"use client";

import { useEffect, useMemo, useState } from "react";
import {
  createCharacter,
  createLocation,
  createLoreEntry,
  deleteCharacter,
  deleteLocation,
  deleteLoreEntry,
  fetchLoreEntries,
  fetchCharacters,
  fetchLocations,
  updateCharacter,
  updateLocation,
  updateLoreEntry,
  type CharacterResponse,
  type LocationResponse,
  type LoreEntryResponse,
} from "@/lib/api/lore";
import { fetchProjects, type ProjectResponse } from "@/lib/api/projects";
import { AppShell } from "@/shared/ui/app-shell";
import { InfoCard } from "@/shared/ui/info-card";

type LoreMode = "characters" | "locations" | "entries";

type LoreLibraryPageProps = {
  mode: LoreMode;
};

type DetailDraft = {
  name: string;
  aliases: string;
  personality: string;
  status: string;
  description: string;
  title: string;
  category: string;
  content: string;
  canonical: boolean;
};

const modeMeta: Record<LoreMode, { title: string; description: string; emptyLabel: string }> = {
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

const inputClassName =
  "rounded-2xl border border-white/8 bg-[#212121] px-4 py-3 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-zinc-600";
const textareaClassName =
  "min-h-32 rounded-2xl border border-white/8 bg-[#212121] px-4 py-3 text-sm leading-7 text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-zinc-600";
const primaryButtonClassName =
  "rounded-xl bg-zinc-100 px-4 py-2.5 text-sm font-medium tracking-[-0.01em] text-black transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:bg-zinc-500";
const secondaryButtonClassName =
  "rounded-xl border border-white/10 px-4 py-2.5 text-sm font-medium tracking-[-0.01em] text-zinc-200 transition hover:border-zinc-500 hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-60";

const emptyDetailDraft: DetailDraft = {
  name: "",
  aliases: "",
  personality: "",
  status: "",
  description: "",
  title: "",
  category: "",
  content: "",
  canonical: true,
};

function makeDraftFromCharacter(item: CharacterResponse): DetailDraft {
  return {
    ...emptyDetailDraft,
    name: item.name,
    aliases: item.aliases || "",
    personality: item.personality || "",
    status: item.status || "",
  };
}

function makeDraftFromLocation(item: LocationResponse): DetailDraft {
  return {
    ...emptyDetailDraft,
    name: item.name,
    description: item.description || "",
  };
}

function makeDraftFromLoreEntry(item: LoreEntryResponse): DetailDraft {
  return {
    ...emptyDetailDraft,
    title: item.title,
    category: item.category,
    content: item.content,
    canonical: item.canonical,
  };
}

function normalizeOptionalText(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

export default function LoreLibraryPage({ mode }: LoreLibraryPageProps) {
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [preferredProjectId, setPreferredProjectId] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [selectedItemId, setSelectedItemId] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [draft, setDraft] = useState<DetailDraft | null>(null);
  const [characters, setCharacters] = useState<CharacterResponse[]>([]);
  const [locations, setLocations] = useState<LocationResponse[]>([]);
  const [entries, setEntries] = useState<LoreEntryResponse[]>([]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    setPreferredProjectId(new URLSearchParams(window.location.search).get("projectId") ?? "");
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadProjects() {
      try {
        const payload = await fetchProjects<ProjectResponse[]>();
        if (!cancelled) {
          setProjects(payload);
          setSelectedProjectId((current) => current || preferredProjectId || payload[0]?.id || "");
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "读取项目失败");
          setLoading(false);
        }
      }
    }

    void loadProjects();
    return () => {
      cancelled = true;
    };
  }, [preferredProjectId]);

  useEffect(() => {
    if (!preferredProjectId) {
      return;
    }

    setSelectedProjectId(preferredProjectId);
  }, [preferredProjectId]);

  useEffect(() => {
    if (!selectedProjectId) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    setDetailError(null);
    setMessage(null);
    setIsEditing(false);
    setIsCreating(false);
    setDraft(null);
    setSelectedItemId("");

    async function loadData() {
      try {
        if (mode === "characters") {
          setCharacters(await fetchCharacters(selectedProjectId));
        } else if (mode === "locations") {
          setLocations(await fetchLocations(selectedProjectId));
        } else {
          setEntries(await fetchLoreEntries(selectedProjectId));
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "读取设定库失败");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadData();
    return () => {
      cancelled = true;
    };
  }, [mode, selectedProjectId]);

  const selectedCharacter = useMemo(
    () => characters.find((item) => item.id === selectedItemId) ?? null,
    [characters, selectedItemId],
  );
  const selectedLocation = useMemo(
    () => locations.find((item) => item.id === selectedItemId) ?? null,
    [locations, selectedItemId],
  );
  const selectedEntry = useMemo(
    () => entries.find((item) => item.id === selectedItemId) ?? null,
    [entries, selectedItemId],
  );

  const currentItems = mode === "characters" ? characters : mode === "locations" ? locations : entries;
  const hasItems = currentItems.length > 0;
  const selectedTitle =
    mode === "characters"
      ? selectedCharacter?.name
      : mode === "locations"
        ? selectedLocation?.name
        : selectedEntry?.title;
  const detailDescription = isCreating
    ? `正在新建${modeMeta[mode].emptyLabel}资料。`
    : selectedTitle
      ? `${selectedTitle} · 可在当前页进行最小编辑。`
      : "先从左侧选择一条资料。";

  useEffect(() => {
    if (!currentItems.length) {
      setSelectedItemId("");
      setIsEditing(false);
      setIsCreating(false);
      setDraft(null);
      return;
    }

    setSelectedItemId((current) =>
      currentItems.some((item) => item.id === current) ? current : currentItems[0]?.id || "",
    );
  }, [currentItems]);

  function handleSelectItem(itemId: string) {
    setSelectedItemId(itemId);
    setIsEditing(false);
    setIsCreating(false);
    setDraft(null);
    setDetailError(null);
    setMessage(null);
  }

  function updateDraft(patch: Partial<DetailDraft>) {
    setDraft((current) => ({ ...(current ?? emptyDetailDraft), ...patch }));
  }

  function startEditing() {
    if (mode === "characters" && selectedCharacter) {
      setDraft(makeDraftFromCharacter(selectedCharacter));
    } else if (mode === "locations" && selectedLocation) {
      setDraft(makeDraftFromLocation(selectedLocation));
    } else if (selectedEntry) {
      setDraft(makeDraftFromLoreEntry(selectedEntry));
    }
    setIsCreating(false);
    setIsEditing(true);
    setDetailError(null);
    setMessage(null);
  }

  function startCreating() {
    setDraft({ ...emptyDetailDraft });
    setIsEditing(false);
    setIsCreating(true);
    setDetailError(null);
    setMessage(null);
  }

  function cancelEditing() {
    setIsEditing(false);
    setIsCreating(false);
    setDraft(null);
    setDetailError(null);
  }

  async function saveSelectedItem() {
    if (!draft) {
      return;
    }
    if (isCreating && !selectedProjectId) {
      setDetailError("请先选择项目，再创建资料。");
      return;
    }

    setSaving(true);
    setDetailError(null);
    setMessage(null);

    try {
      if (mode === "characters") {
        const nextName = draft.name.trim();
        if (!nextName) {
          setDetailError("角色名称不能为空。");
          return;
        }

        if (isCreating) {
          const created = await createCharacter({
            project_id: selectedProjectId,
            name: nextName,
            aliases: normalizeOptionalText(draft.aliases),
            personality: normalizeOptionalText(draft.personality),
            status: normalizeOptionalText(draft.status),
          });
          setCharacters((current) => [created, ...current]);
          setSelectedItemId(created.id);
          setMessage("已创建资料。");
        } else if (selectedCharacter) {
          const updated = await updateCharacter(selectedCharacter.id, {
            name: nextName,
            aliases: normalizeOptionalText(draft.aliases),
            personality: normalizeOptionalText(draft.personality),
            status: normalizeOptionalText(draft.status),
          });
          setCharacters((current) => current.map((item) => (item.id === updated.id ? updated : item)));
          setMessage("已保存资料。");
        }
      } else if (mode === "locations") {
        const nextName = draft.name.trim();
        if (!nextName) {
          setDetailError("地点名称不能为空。");
          return;
        }

        if (isCreating) {
          const created = await createLocation({
            project_id: selectedProjectId,
            name: nextName,
            description: normalizeOptionalText(draft.description),
          });
          setLocations((current) => [created, ...current]);
          setSelectedItemId(created.id);
          setMessage("已创建资料。");
        } else if (selectedLocation) {
          const updated = await updateLocation(selectedLocation.id, {
            name: nextName,
            description: normalizeOptionalText(draft.description),
          });
          setLocations((current) => current.map((item) => (item.id === updated.id ? updated : item)));
          setMessage("已保存资料。");
        }
      } else {
        const nextTitle = draft.title.trim();
        const nextCategory = draft.category.trim();
        const nextContent = draft.content.trim();
        if (!nextTitle || !nextCategory || !nextContent) {
          setDetailError("词条标题、分类和正文不能为空。");
          return;
        }

        if (isCreating) {
          const created = await createLoreEntry({
            project_id: selectedProjectId,
            title: nextTitle,
            category: nextCategory,
            content: nextContent,
            canonical: draft.canonical,
          });
          setEntries((current) => [created, ...current]);
          setSelectedItemId(created.id);
          setMessage("已创建资料。");
        } else if (selectedEntry) {
          const updated = await updateLoreEntry(selectedEntry.id, {
            title: nextTitle,
            category: nextCategory,
            content: nextContent,
            canonical: draft.canonical,
          });
          setEntries((current) => current.map((item) => (item.id === updated.id ? updated : item)));
          setMessage("已保存资料。");
        }
      }

      setIsEditing(false);
      setIsCreating(false);
      setDraft(null);
    } catch (saveError) {
      setDetailError(
        saveError instanceof Error ? saveError.message : isCreating ? "创建资料失败" : "保存资料失败",
      );
    } finally {
      setSaving(false);
    }
  }

  async function deleteSelectedItem() {
    if (!selectedItemId) {
      return;
    }

    const confirmed = window.confirm("确认删除当前资料吗？删除后不会保留兼容数据。");
    if (!confirmed) {
      return;
    }

    setDeleting(true);
    setDetailError(null);
    setMessage(null);

    try {
      if (mode === "characters") {
        await deleteCharacter(selectedItemId);
        setCharacters((current) => current.filter((item) => item.id !== selectedItemId));
      } else if (mode === "locations") {
        await deleteLocation(selectedItemId);
        setLocations((current) => current.filter((item) => item.id !== selectedItemId));
      } else {
        await deleteLoreEntry(selectedItemId);
        setEntries((current) => current.filter((item) => item.id !== selectedItemId));
      }

      setSelectedItemId("");
      setIsEditing(false);
      setIsCreating(false);
      setDraft(null);
      setMessage("已删除资料。");
    } catch (deleteError) {
      setDetailError(deleteError instanceof Error ? deleteError.message : "删除资料失败");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <AppShell
      title={modeMeta[mode].title}
      description={modeMeta[mode].description}
      actions={
        <select
          className="rounded-2xl border border-white/8 bg-[#212121] px-4 py-2.5 text-sm text-zinc-100 outline-none transition focus:border-zinc-600"
          value={selectedProjectId}
          onChange={(event) => setSelectedProjectId(event.target.value)}
        >
          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>
      }
    >
      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <InfoCard title="设定清单" description="点击左侧条目后，可在当前页查看详情并进行最小编辑。">
          {loading ? (
            <div className="text-sm text-zinc-500">正在读取数据…</div>
          ) : error ? (
            <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-4 text-sm text-rose-100">
              {error}
            </div>
          ) : !hasItems ? (
            <div className="rounded-2xl border border-dashed border-white/10 bg-[#1a1a1a] px-4 py-8 text-sm text-zinc-500">
              当前项目下还没有可展示的{modeMeta[mode].emptyLabel}数据。
            </div>
          ) : mode === "characters" ? (

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-1">
              {characters.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleSelectItem(item.id)}
                  className={`rounded-[24px] border px-5 py-5 text-left transition ${
                    item.id === selectedItemId
                      ? "border-amber-300/30 bg-amber-500/10"
                      : "border-white/8 bg-[#1d1d1d] hover:border-zinc-600"
                  }`}
                >
                  <div className="text-lg font-semibold tracking-[-0.02em] text-zinc-100">{item.name}</div>
                  <div className="mt-2 text-sm leading-7 text-zinc-400">{item.personality || "暂无角色描述。"}</div>
                  <div className="mt-3 text-xs tracking-[0.01em] text-zinc-500">
                    别名：{item.aliases || "无"} | 状态：{item.status || "未标记"}
                  </div>
                </button>
              ))}
            </div>
          ) : mode === "locations" ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-1">
              {locations.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleSelectItem(item.id)}
                  className={`rounded-[24px] border px-5 py-5 text-left transition ${
                    item.id === selectedItemId
                      ? "border-sky-300/30 bg-sky-500/10"
                      : "border-white/8 bg-[#1d1d1d] hover:border-zinc-600"
                  }`}
                >
                  <div className="text-lg font-semibold tracking-[-0.02em] text-zinc-100">{item.name}</div>
                  <div className="mt-2 text-sm leading-7 text-zinc-400">{item.description || "暂无地点描述。"}</div>
                </button>
              ))}
            </div>
          ) : (
            <div className="space-y-4">
              {entries.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleSelectItem(item.id)}
                  className={`w-full rounded-[24px] border px-5 py-5 text-left transition ${
                    item.id === selectedItemId
                      ? "border-emerald-300/30 bg-emerald-500/10"
                      : "border-white/8 bg-[#1d1d1d] hover:border-zinc-600"
                  }`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="text-lg font-semibold tracking-[-0.02em] text-zinc-100">{item.title}</div>
                      <div className="mt-1 text-xs tracking-[0.01em] text-zinc-500">分类：{item.category}</div>
                    </div>
                    <span
                      className={`rounded-full border px-3 py-1 text-xs ${
                        item.canonical
                          ? "border-amber-400/20 bg-amber-500/10 text-amber-200"
                          : "border-white/8 bg-[#171717] text-zinc-500"
                      }`}
                    >
                      {item.canonical ? "正典" : "非正典"}
                    </span>
                  </div>
                  <div className="mt-3 text-sm leading-7 text-zinc-400">{item.content}</div>
                </button>
              ))}
            </div>
          )}
        </InfoCard>

        <InfoCard title="资料详情" description={detailDescription}>
          {loading ? (
            <div className="text-sm text-zinc-500">正在准备详情面板…</div>
          ) : (
            <div className="space-y-4">
              {message ? (
                <div className="rounded-2xl border border-emerald-400/20 bg-emerald-500/10 px-4 py-4 text-sm text-emerald-100">
                  {message}
                </div>
              ) : null}
              {detailError ? (
                <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-4 text-sm text-rose-100">
                  {detailError}
                </div>
              ) : null}
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="text-xs tracking-[0.01em] text-zinc-500">当前模式：{modeMeta[mode].title}</div>
                <div className="flex flex-wrap gap-3">
                  {isEditing || isCreating ? (
                    <>
                      <button
                        type="button"
                        className={secondaryButtonClassName}
                        onClick={cancelEditing}
                        disabled={saving || deleting}
                      >
                        取消
                      </button>
                      <button
                        type="button"
                        className={primaryButtonClassName}
                        onClick={() => void saveSelectedItem()}
                        disabled={saving || deleting}
                      >
                        {saving ? (isCreating ? "创建中…" : "保存中…") : isCreating ? "创建资料" : "保存修改"}
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        type="button"
                        className={secondaryButtonClassName}
                        onClick={startCreating}
                        disabled={deleting || !selectedProjectId}
                      >
                        新建资料
                      </button>
                      {selectedItemId ? (
                        <button
                          type="button"
                          className={secondaryButtonClassName}
                          onClick={() => void deleteSelectedItem()}
                          disabled={deleting}
                        >
                          {deleting ? "删除中…" : "删除当前"}
                        </button>
                      ) : null}
                      {hasItems && selectedTitle ? (
                        <button type="button" className={primaryButtonClassName} onClick={startEditing} disabled={deleting}>
                          开始编辑
                        </button>
                      ) : null}
                    </>
                  )}
                </div>
              </div>

              {isCreating && draft ? (
                mode === "characters" ? (
                  <div className="grid gap-3">
                    <input className={inputClassName} value={draft.name} onChange={(event) => updateDraft({ name: event.target.value })} placeholder="角色名称" />
                    <input className={inputClassName} value={draft.aliases} onChange={(event) => updateDraft({ aliases: event.target.value })} placeholder="别名" />
                    <textarea className={textareaClassName} value={draft.personality} onChange={(event) => updateDraft({ personality: event.target.value })} placeholder="角色性格或当前描述" />
                    <input className={inputClassName} value={draft.status} onChange={(event) => updateDraft({ status: event.target.value })} placeholder="状态" />
                  </div>
                ) : mode === "locations" ? (
                  <div className="grid gap-3">
                    <input className={inputClassName} value={draft.name} onChange={(event) => updateDraft({ name: event.target.value })} placeholder="地点名称" />
                    <textarea className={textareaClassName} value={draft.description} onChange={(event) => updateDraft({ description: event.target.value })} placeholder="地点描述" />
                  </div>
                ) : (
                  <div className="grid gap-3">
                    <input className={inputClassName} value={draft.title} onChange={(event) => updateDraft({ title: event.target.value })} placeholder="词条标题" />
                    <input className={inputClassName} value={draft.category} onChange={(event) => updateDraft({ category: event.target.value })} placeholder="分类" />
                    <textarea className={textareaClassName} value={draft.content} onChange={(event) => updateDraft({ content: event.target.value })} placeholder="词条正文" />
                    <label className="flex items-center gap-3 rounded-2xl border border-white/8 bg-[#212121] px-4 py-3 text-sm text-zinc-200">
                      <input type="checkbox" checked={draft.canonical} onChange={(event) => updateDraft({ canonical: event.target.checked })} />
                      作为正典词条保留
                    </label>
                  </div>
                )
              ) : !hasItems ? (
                <div className="rounded-2xl border border-dashed border-white/10 bg-[#1a1a1a] px-4 py-8 text-sm text-zinc-500">
                  当前项目还没有可编辑的{modeMeta[mode].emptyLabel}资料。你可以直接点击上方“新建资料”开始创建。
                </div>
              ) : !selectedTitle ? (
                <div className="rounded-2xl border border-dashed border-white/10 bg-[#1a1a1a] px-4 py-8 text-sm text-zinc-500">
                  请先从左侧列表选择一条资料，或点击上方“新建资料”。
                </div>
              ) : mode === "characters" && selectedCharacter ? (
                isEditing && draft ? (
                  <div className="grid gap-3">
                    <input className={inputClassName} value={draft.name} onChange={(event) => updateDraft({ name: event.target.value })} placeholder="角色名称" />
                    <input className={inputClassName} value={draft.aliases} onChange={(event) => updateDraft({ aliases: event.target.value })} placeholder="别名" />
                    <textarea className={textareaClassName} value={draft.personality} onChange={(event) => updateDraft({ personality: event.target.value })} placeholder="角色性格或当前描述" />
                    <input className={inputClassName} value={draft.status} onChange={(event) => updateDraft({ status: event.target.value })} placeholder="状态" />
                  </div>
                ) : (
                  <div className="space-y-4 text-sm leading-7 text-zinc-300">
                    <div><span className="text-zinc-500">别名：</span>{selectedCharacter.aliases || "无"}</div>
                    <div><span className="text-zinc-500">性格：</span>{selectedCharacter.personality || "暂无角色描述。"}</div>
                    <div><span className="text-zinc-500">状态：</span>{selectedCharacter.status || "未标记"}</div>
                  </div>
                )
              ) : mode === "locations" && selectedLocation ? (
                isEditing && draft ? (
                  <div className="grid gap-3">
                    <input className={inputClassName} value={draft.name} onChange={(event) => updateDraft({ name: event.target.value })} placeholder="地点名称" />
                    <textarea className={textareaClassName} value={draft.description} onChange={(event) => updateDraft({ description: event.target.value })} placeholder="地点描述" />
                  </div>
                ) : (
                  <div className="space-y-4 text-sm leading-7 text-zinc-300">
                    <div><span className="text-zinc-500">地点名称：</span>{selectedLocation.name}</div>
                    <div><span className="text-zinc-500">地点描述：</span>{selectedLocation.description || "暂无地点描述。"}</div>
                  </div>
                )
              ) : selectedEntry ? (
                isEditing && draft ? (
                  <div className="grid gap-3">
                    <input className={inputClassName} value={draft.title} onChange={(event) => updateDraft({ title: event.target.value })} placeholder="词条标题" />
                    <input className={inputClassName} value={draft.category} onChange={(event) => updateDraft({ category: event.target.value })} placeholder="分类" />
                    <textarea className={textareaClassName} value={draft.content} onChange={(event) => updateDraft({ content: event.target.value })} placeholder="词条正文" />
                    <label className="flex items-center gap-3 rounded-2xl border border-white/8 bg-[#212121] px-4 py-3 text-sm text-zinc-200">
                      <input type="checkbox" checked={draft.canonical} onChange={(event) => updateDraft({ canonical: event.target.checked })} />
                      作为正典词条保留
                    </label>
                  </div>
                ) : (
                  <div className="space-y-4 text-sm leading-7 text-zinc-300">
                    <div><span className="text-zinc-500">分类：</span>{selectedEntry.category}</div>
                    <div><span className="text-zinc-500">正文：</span>{selectedEntry.content}</div>
                    <div><span className="text-zinc-500">正典状态：</span>{selectedEntry.canonical ? "正典" : "非正典"}</div>
                  </div>
                )
              ) : null}
            </div>
          )}
        </InfoCard>
      </div>
    </AppShell>
  );
}
