"use client";

import { useEffect, useState } from "react";
import {
  fetchHealth,
  fetchLatestSmokeReports,
  fetchProviderState,
  fetchRuntimeSelfCheck,
  fetchSmokeReports,
} from "@/lib/api/runtime";
import { AppShell } from "@/shared/ui/app-shell";
import { InfoCard } from "@/shared/ui/info-card";

type HealthResponse = {
  status: string;
  service: string;
  schema_ready: boolean;
  workflow_runner_started: boolean;
  recovery_scan_completed: boolean;
  pgvector_ready: boolean;
  provider_matrix_loaded: boolean;
  provider_runtime_ready: boolean;
  version: string;
  last_startup_stage: string;
  startup_error?: string | null;
};

type ProviderRuntimeStateResponse = {
  providers: { provider: string; enabled: boolean; remaining_cooldown_seconds: number; last_error?: string | null }[];
  steps: { step: string; ready: boolean; blocking_reasons: string[] }[];
};

type RuntimeSelfCheck = {
  workflow_runtime: {
    workflow_runner_started: boolean;
    recovery_scan_completed: boolean;
    recovered_runs: number;
    last_startup_stage: string;
    startup_error?: string | null;
  };
  provider_matrix: { rule_count: number; steps: string[] };
};

type SmokeReportSummary = {
  filename: string;
  report_type: "backend_full_smoke" | "frontend_live_smoke";
  success: boolean;
  created_at: string;
};

type SmokeLatest = {
  backend_full_smoke: SmokeReportSummary | null;
  frontend_live_smoke: SmokeReportSummary | null;
};

export default function RuntimeHub() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [providerState, setProviderState] = useState<ProviderRuntimeStateResponse | null>(null);
  const [selfCheck, setSelfCheck] = useState<RuntimeSelfCheck | null>(null);
  const [smokeLatest, setSmokeLatest] = useState<SmokeLatest | null>(null);
  const [smokeReports, setSmokeReports] = useState<SmokeReportSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [nextHealth, nextProviderState, nextSelfCheck, nextSmokeLatest, nextSmokeReports] =
          await Promise.all([
            fetchHealth<HealthResponse>(),
            fetchProviderState<ProviderRuntimeStateResponse>(),
            fetchRuntimeSelfCheck<RuntimeSelfCheck>(),
            fetchLatestSmokeReports<SmokeLatest>(),
            fetchSmokeReports<SmokeReportSummary[]>(),
          ]);
        if (!cancelled) {
          setHealth(nextHealth);
          setProviderState(nextProviderState);
          setSelfCheck(nextSelfCheck);
          setSmokeLatest(nextSmokeLatest);
          setSmokeReports(nextSmokeReports);
          setError(null);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "读取运行时信息失败");
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
      title="运行时诊断"
      description="运行时诊断从编辑器中迁出，集中展示健康状态、Provider Runtime、自检结果与 smoke 基线。"
    >
      {error ? (
        <InfoCard title="读取失败">
          <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-4 text-sm text-rose-100">
            {error}
          </div>
        </InfoCard>
        ) : null}

      <div className="grid gap-6 xl:grid-cols-[1.05fr_1.35fr]">
        <InfoCard title="运行时就绪度" description="保留前台可读摘要，详细问题都集中在这个诊断页。">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-amber-400/15 bg-amber-500/8 px-4 py-4">
              <div className="text-xs text-amber-300">健康状态</div>
              <div className="mt-2 text-xl font-semibold text-zinc-100">{health?.status || "unknown"}</div>
            </div>
            <div className="rounded-2xl border border-sky-400/15 bg-sky-500/8 px-4 py-4">
              <div className="text-xs text-sky-300">启动阶段</div>
              <div className="mt-2 text-xl font-semibold text-zinc-100">
                {health?.last_startup_stage || "unknown"}
              </div>
            </div>
            <div className="rounded-2xl border border-emerald-400/15 bg-emerald-500/8 px-4 py-4 text-sm text-zinc-200">
              schema_ready：{health?.schema_ready ? "true" : "false"}
            </div>
            <div className="rounded-2xl border border-white/8 bg-[#1d1d1d] px-4 py-4 text-sm text-zinc-200">
              pgvector_ready：{health?.pgvector_ready ? "true" : "false"}
            </div>
          </div>
          <div className="mt-4 rounded-2xl border border-white/8 bg-[#1d1d1d] px-4 py-4 text-sm text-zinc-200">
            运行时自检告警：{selfCheck?.workflow_runtime.startup_error || "无"}
          </div>
        </InfoCard>

        <InfoCard title="Provider 运行态与 Smoke" description="统一查看 Provider 状态和最近的本地回归报告。">
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-3">
              {(providerState?.providers ?? []).map((provider) => (
                <div
                  key={provider.provider}
                  className="rounded-2xl border border-white/8 bg-[#1d1d1d] px-4 py-4 text-sm text-zinc-200"
                >
                  <div className="font-semibold text-zinc-100">{provider.provider}</div>
                  <div className="mt-1">
                    可用：{provider.enabled ? "是" : "否"} | 冷却：{provider.remaining_cooldown_seconds}s
                  </div>
                  <div className="mt-1 text-xs text-zinc-500">{provider.last_error || "无最近错误"}</div>
                </div>
              ))}
            </div>

            <div className="space-y-3">
              <div className="rounded-2xl border border-white/8 bg-[#1d1d1d] px-4 py-4 text-sm text-zinc-200">
                最新 backend smoke：{smokeLatest?.backend_full_smoke?.filename || "暂无"}
              </div>
              <div className="rounded-2xl border border-white/8 bg-[#1d1d1d] px-4 py-4 text-sm text-zinc-200">
                最新 frontend smoke：{smokeLatest?.frontend_live_smoke?.filename || "暂无"}
              </div>
              <div className="rounded-2xl border border-white/8 bg-[#1d1d1d] px-4 py-4 text-xs text-zinc-500">
                {(smokeReports ?? []).slice(0, 5).map((item) => (
                  <div key={item.filename}>
                    {item.report_type} | {item.success ? "通过" : "失败"} | {item.filename}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </InfoCard>
      </div>
    </AppShell>
  );
}
