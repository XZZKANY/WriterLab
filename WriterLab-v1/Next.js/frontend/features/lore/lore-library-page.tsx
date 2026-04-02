"use client";

import { useEffect, useState } from "react";
import { fetchLoreEntries, fetchCharacters, fetchLocations } from "@/lib/api/lore";
import { fetchProjects } from "@/lib/api/projects";
import { AppShell } from "@/shared/ui/app-shell";
import { InfoCard } from "@/shared/ui/info-card";

type LoreMode = "characters" | "locations" | "entries";

type Project = {
  id: string;
  name: string;
};

type Character = {
  id: string;
  name: string;
  aliases?: string | null;
  personality?: string | null;
  status?: string | null;
};

type Location = {
  id: string;
  name: string;
  description?: string | null;
};

type LoreEntry = {
  id: string;
  title: string;
  category: string;
  content: string;
  canonical: boolean;
};

type LoreLibraryPageProps = {
  mode: LoreMode;
};

const modeMeta: Record<LoreMode, { title: string; description: string }> = {
  characters: {
    title: "角色库",
    description: "角色视图聚焦姓名、别名、性格和状态。",
  },
  locations: {
    title: "地点库",
    description: "地点视图聚焦地理节点和描述。",
  },
  entries: {
    title: "设定词条库",
    description: "词条视图聚焦分类、正文和 canonical 标记。",
  },
};

export default function LoreLibraryPage({ mode }: LoreLibraryPageProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [preferredProjectId, setPreferredProjectId] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [entries, setEntries] = useState<LoreEntry[]>([]);

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
        const payload = await fetchProjects<Project[]>();
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

    async function loadData() {
      try {
        if (mode === "characters") {
          setCharacters(await fetchCharacters<Character[]>(selectedProjectId));
        } else if (mode === "locations") {
          setLocations(await fetchLocations<Location[]>(selectedProjectId));
        } else {
          setEntries(await fetchLoreEntries<LoreEntry[]>(selectedProjectId));
        }
        if (!cancelled) {
          setError(null);
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

  const hasItems =
    mode === "characters" ? characters.length > 0 : mode === "locations" ? locations.length > 0 : entries.length > 0;

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
      <InfoCard title="设定清单" description="子路由现在承接正式浏览视图，不再停留在占位页。">
        {loading ? (
          <div className="text-sm text-zinc-500">正在读取数据…</div>
        ) : error ? (
          <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-4 text-sm text-rose-100">
            {error}
          </div>
        ) : !hasItems ? (
          <div className="rounded-2xl border border-dashed border-white/10 bg-[#1a1a1a] px-4 py-8 text-sm text-zinc-500">
            当前项目下还没有可展示的{mode === "characters" ? "角色" : mode === "locations" ? "地点" : "词条"}数据。
          </div>
        ) : mode === "characters" ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {characters.map((item) => (
              <article
                key={item.id}
                className="rounded-[24px] border border-white/8 bg-[#1d1d1d] px-5 py-5"
              >
                <div className="text-lg font-semibold tracking-[-0.02em] text-zinc-100">{item.name}</div>
                <div className="mt-2 text-sm leading-7 text-zinc-400">{item.personality || "暂无角色描述。"}</div>
                <div className="mt-3 text-xs tracking-[0.01em] text-zinc-500">
                  别名：{item.aliases || "无"} | 状态：{item.status || "未标记"}
                </div>
              </article>
            ))}
          </div>
        ) : mode === "locations" ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {locations.map((item) => (
              <article
                key={item.id}
                className="rounded-[24px] border border-white/8 bg-[#1d1d1d] px-5 py-5"
              >
                <div className="text-lg font-semibold tracking-[-0.02em] text-zinc-100">{item.name}</div>
                <div className="mt-2 text-sm leading-7 text-zinc-400">{item.description || "暂无地点描述。"}</div>
              </article>
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            {entries.map((item) => (
              <article key={item.id} className="rounded-[24px] border border-white/8 bg-[#1d1d1d] px-5 py-5">
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
              </article>
            ))}
          </div>
        )}
      </InfoCard>
    </AppShell>
  );
}
