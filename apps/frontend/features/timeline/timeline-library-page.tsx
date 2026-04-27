"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { fetchTimelineEvents, type TimelineEventResponse } from "@/lib/api/timeline";
import { AppShell } from "@/shared/ui/app-shell";
import { InfoCard } from "@/shared/ui/info-card";

type TimelineLibraryPageProps = {
  projectId: string;
};

export default function TimelineLibraryPage({ projectId }: TimelineLibraryPageProps) {
  const [events, setEvents] = useState<TimelineEventResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!projectId) {
        setEvents([]);
        setError("项目标识缺失，无法读取时间线。");
        setLoading(false);
        return;
      }

      try {
        const payload = await fetchTimelineEvents(projectId);
        if (!cancelled) {
          setEvents(payload);
          setError(null);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "读取时间线失败");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const canonicalCount = useMemo(() => events.filter((item) => item.canonical).length, [events]);

  return (
    <AppShell
      title="项目时间线"
      description="以结构化事件列表查看当前项目的关键剧情事实。"
      actions={
        <>
          <Link
            href={`/project/${projectId}`}
            className="rounded-xl border border-white/8 bg-[#212121] px-4 py-2 text-sm text-zinc-200 transition hover:border-zinc-600 hover:bg-[#262626]"
          >
            返回项目详情
          </Link>
          <Link
            href={`/editor?projectId=${projectId}`}
            className="rounded-xl bg-zinc-100 px-4 py-2 text-sm font-medium text-black transition hover:bg-zinc-200"
          >
            进入写作编辑
          </Link>
        </>
      }
    >
      <div className="grid gap-6 xl:grid-cols-[0.82fr_1.18fr]">
        <InfoCard title="时间线摘要" description="第一轮只做结构化列表，不做复杂时间轴。">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-amber-400/15 bg-amber-500/8 px-4 py-4">
              <div className="text-xs text-amber-300">事件总数</div>
              <div className="mt-2 text-2xl font-semibold text-zinc-100">{events.length}</div>
            </div>
            <div className="rounded-2xl border border-emerald-400/15 bg-emerald-500/8 px-4 py-4">
              <div className="text-xs text-emerald-300">正典事件</div>
              <div className="mt-2 text-2xl font-semibold text-zinc-100">{canonicalCount}</div>
            </div>
          </div>
        </InfoCard>

        <InfoCard title="时间线事件" description="按结构化事件列表回看剧情推进、参与角色和时间标签。">
          {loading ? (
            <div className="text-sm text-zinc-500">正在读取时间线…</div>
          ) : error ? (
            <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-4 text-sm text-rose-100">{error}</div>
          ) : events.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/10 bg-[#1a1a1a] px-4 py-8 text-sm text-zinc-500">
              当前项目还没有时间线事件。
            </div>
          ) : (
            <div className="space-y-4">
              {events.map((item) => (
                <article key={item.id} className="rounded-[24px] border border-white/8 bg-[#1d1d1d] px-5 py-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="text-lg font-semibold tracking-[-0.02em] text-zinc-100">{item.title}</div>
                      <div className="mt-1 text-xs tracking-[0.01em] text-zinc-500">
                        {item.event_type} · {item.event_time_label || "未标记时间"}
                      </div>
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
                  <div className="mt-3 text-sm leading-7 text-zinc-300">{item.description}</div>
                  <div className="mt-3 text-xs tracking-[0.01em] text-zinc-500">
                    参与者：{item.participants?.length ? item.participants.join("、") : "未记录"}
                  </div>
                </article>
              ))}
            </div>
          )}
        </InfoCard>
      </div>
    </AppShell>
  );
}
