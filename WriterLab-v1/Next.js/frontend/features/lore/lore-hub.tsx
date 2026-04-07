"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  fetchLoreEntries,
  fetchCharacters,
  fetchLocations,
  type CharacterResponse,
  type LocationResponse,
  type LoreEntryResponse,
} from "@/lib/api/lore";
import { fetchProjects, type ProjectResponse } from "@/lib/api/projects";
import { AppShell } from "@/shared/ui/app-shell";
import { InfoCard } from "@/shared/ui/info-card";

export default function LoreHub() {
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [preferredProjectId, setPreferredProjectId] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [characters, setCharacters] = useState<CharacterResponse[]>([]);
  const [locations, setLocations] = useState<LocationResponse[]>([]);
  const [entries, setEntries] = useState<LoreEntryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

    async function loadLore() {
      try {
        const [nextCharacters, nextLocations, nextEntries] = await Promise.all([
          fetchCharacters(selectedProjectId),
          fetchLocations(selectedProjectId),
          fetchLoreEntries(selectedProjectId),
        ]);
        if (!cancelled) {
          setCharacters(nextCharacters);
          setLocations(nextLocations);
          setEntries(nextEntries);
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

    void loadLore();
    return () => {
      cancelled = true;
    };
  }, [selectedProjectId]);

  const selectedProject = useMemo(
    () => projects.find((item) => item.id === selectedProjectId) ?? null,
    [projects, selectedProjectId],
  );

  return (
    <AppShell
      title="设定库"
      description="设定库已经并入统一项目工作区，角色、地点和词条以暗色浏览面板统一呈现。"
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
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.5fr]">
        <InfoCard
          title="项目上下文"
          description="角色、地点、词条共享同一个项目视角，先从这里选择上下文。"
        >
          {selectedProject ? (
            <div className="space-y-3 text-sm text-zinc-200">
              <div className="rounded-2xl border border-white/8 bg-[#1d1d1d] px-4 py-4">
                当前项目：<span className="font-semibold text-zinc-100">{selectedProject.name}</span>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <Link
                  href={`/lore/characters?projectId=${selectedProjectId}`}
                  className="rounded-2xl border border-amber-400/15 bg-amber-500/8 px-4 py-4 text-center text-amber-100 transition hover:border-amber-300/30 hover:bg-amber-500/12"
                >
                  角色
                </Link>
                <Link
                  href={`/lore/locations?projectId=${selectedProjectId}`}
                  className="rounded-2xl border border-sky-400/15 bg-sky-500/8 px-4 py-4 text-center text-sky-100 transition hover:border-sky-300/30 hover:bg-sky-500/12"
                >
                  地点
                </Link>
                <Link
                  href={`/lore/entries?projectId=${selectedProjectId}`}
                  className="rounded-2xl border border-emerald-400/15 bg-emerald-500/8 px-4 py-4 text-center text-emerald-100 transition hover:border-emerald-300/30 hover:bg-emerald-500/12"
                >
                  词条
                </Link>
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-white/10 bg-[#1a1a1a] px-4 py-6 text-sm text-zinc-500">
              暂无项目可供查看。
            </div>
          )}
        </InfoCard>
        <InfoCard title="设定摘要" description="这里保留总览，细项放到子路由。">
          {loading ? (
            <div className="text-sm text-zinc-500">正在读取设定库…</div>
          ) : error ? (
            <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-4 text-sm text-rose-100">
              {error}
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-[24px] border border-amber-400/15 bg-amber-500/8 px-5 py-5">
                <div className="text-xs text-amber-300">角色</div>
                <div className="mt-2 text-2xl font-semibold text-zinc-100">{characters.length}</div>
                <div className="mt-3 space-y-2 text-sm text-zinc-300">
                  {characters.slice(0, 4).map((item) => (
                    <div key={item.id}>• {item.name}</div>
                  ))}
                  {characters.length === 0 ? <div className="text-zinc-500">暂无角色资料</div> : null}
                </div>
              </div>
              <div className="rounded-[24px] border border-sky-400/15 bg-sky-500/8 px-5 py-5">
                <div className="text-xs text-sky-300">地点</div>
                <div className="mt-2 text-2xl font-semibold text-zinc-100">{locations.length}</div>
                <div className="mt-3 space-y-2 text-sm text-zinc-300">
                  {locations.slice(0, 4).map((item) => (
                    <div key={item.id}>• {item.name}</div>
                  ))}
                  {locations.length === 0 ? <div className="text-zinc-500">暂无地点资料</div> : null}
                </div>
              </div>
              <div className="rounded-[24px] border border-emerald-400/15 bg-emerald-500/8 px-5 py-5">
                <div className="text-xs text-emerald-300">词条</div>
                <div className="mt-2 text-2xl font-semibold text-zinc-100">{entries.length}</div>
                <div className="mt-3 space-y-2 text-sm text-zinc-300">
                  {entries.slice(0, 4).map((item) => (
                    <div key={item.id}>• {item.title}</div>
                  ))}
                  {entries.length === 0 ? <div className="text-zinc-500">暂无词条资料</div> : null}
                </div>
              </div>
            </div>
          )}
        </InfoCard>
      </div>
    </AppShell>
  );
}
