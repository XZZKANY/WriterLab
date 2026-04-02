"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchHealth } from "@/lib/api/runtime";
import { AppShell } from "@/shared/ui/app-shell";
import { InfoCard } from "@/shared/ui/info-card";

type HealthResponse = {
  status?: string;
  service?: string;
  message?: string;
  schema_ready?: boolean;
  workflow_runner_started?: boolean;
};

export default function HomeDashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const payload = await fetchHealth<HealthResponse>();
        if (!cancelled) {
          setHealth(payload);
        }
      } catch {
        if (!cancelled) {
          setHealth(null);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <AppShell
      title="WriterLab 正式工作区"
      description="前端入口已从单页调试台过渡到按领域分层的正式应用。你可以从这里进入项目工作台、编辑器、设定库、运行时和设置。"
      actions={
        <>
          <Link
            href="/editor"
            className="rounded-xl bg-zinc-100 px-4 py-2.5 text-sm font-medium tracking-[-0.01em] text-black transition hover:bg-zinc-200"
          >
            打开编辑器
          </Link>
          <a
            href="http://127.0.0.1:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="rounded-xl border border-white/8 bg-[#212121] px-4 py-2.5 text-sm text-zinc-200 transition hover:border-zinc-600 hover:bg-[#262626]"
          >
            打开 API Docs
          </a>
        </>
      }
    >
      <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <InfoCard title="迁移重点" description="当前版本已经补齐正式一级入口，并把 editor 变成路由装配层。">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-amber-400/15 bg-amber-500/8 px-4 py-4 text-sm text-amber-100">
              `/project`：项目列表和项目详情
            </div>
            <div className="rounded-2xl border border-sky-400/15 bg-sky-500/8 px-4 py-4 text-sm text-sky-100">
              `/lore`：角色、地点、词条子视图
            </div>
            <div className="rounded-2xl border border-emerald-400/15 bg-emerald-500/8 px-4 py-4 text-sm text-emerald-100">
              `/runtime`：运行时诊断与 smoke 摘要
            </div>
            <div className="rounded-2xl border border-white/8 bg-[#1d1d1d] px-4 py-4 text-sm text-zinc-300">
              `/settings`：模型设置入口
            </div>
          </div>
        </InfoCard>
        <InfoCard title="后端状态" description="继续展示后端健康状态，便于确认本地环境就绪。">
          <pre className="overflow-x-auto rounded-2xl border border-white/8 bg-[#1d1d1d] p-4 text-sm leading-7 text-zinc-300">
            {JSON.stringify(health, null, 2)}
          </pre>
        </InfoCard>
      </div>
    </AppShell>
  );
}
