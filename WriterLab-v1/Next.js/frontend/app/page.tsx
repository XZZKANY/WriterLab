"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type HealthResponse = {
  status?: string;
  service?: string;
  message?: string;
};

export default function Home() {
  const [data, setData] = useState<HealthResponse | null>(null);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/health")
      .then((res) => res.json())
      .then((res) => setData(res));
  }, []);

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#f8f1e5_0%,#f1e8da_45%,#ebe0d0_100%)] px-6 py-10 text-stone-900">
      <div className="mx-auto flex max-w-5xl flex-col gap-6">
        <section className="rounded-[32px] border border-stone-200/80 bg-white/88 p-8 shadow-[0_24px_90px_rgba(120,93,53,0.1)] backdrop-blur">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-stone-500">
            WriterLab
          </p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-stone-900">
            WriterLab 🚀
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-8 text-stone-600">
            后端已经连通。现在可以直接进入场景编辑器，调用“分析当前场景”来联调
            `analyze-scene`。
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href="/editor"
              className="rounded-2xl bg-stone-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-stone-700"
            >
              打开编辑器
            </Link>
            <a
              href="http://127.0.0.1:8000/docs#/ai/analyze_scene_api_api_ai_analyze_scene_post"
              target="_blank"
              rel="noreferrer"
              className="rounded-2xl border border-stone-300 px-5 py-3 text-sm font-medium text-stone-700 transition hover:border-stone-500 hover:bg-stone-50"
            >
              打开 API Docs
            </a>
          </div>
        </section>

        <section className="rounded-[28px] border border-stone-200 bg-white/80 p-6 shadow-[0_18px_60px_rgba(120,93,53,0.08)]">
          <h2 className="text-lg font-semibold text-stone-900">Backend Status</h2>
          <pre className="mt-4 overflow-x-auto rounded-2xl bg-stone-100 p-4 text-sm leading-7 text-stone-700">
            {JSON.stringify(data, null, 2)}
          </pre>
        </section>
      </div>
    </main>
  );
}
