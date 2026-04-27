"use client";

import { useEffect, useState } from "react";
import {
  fetchHealth,
  fetchLatestSmokeReports,
  fetchProviderState,
  fetchRuntimeSelfCheck,
  fetchSmokeReportDetail,
  fetchSmokeReportRegression,
  fetchSmokeReports,
} from "@/lib/api/runtime";
import { fetchProviderSettings, updateProviderSettings } from "@/lib/api/settings";
import { fetchProviderMatrix } from "@/lib/api/workflow";

export type ProviderKind = "openai" | "deepseek" | "xai";
export type SmokeReportType = "backend_full_smoke" | "frontend_live_smoke";

type RuntimeSelfCheckState = {
  backend_root: { message: string };
  health: { status: string; schema_ready: boolean; provider_runtime_ready: boolean; version: string };
  workflow_runtime: {
    workflow_runner_started: boolean;
    recovery_scan_completed: boolean;
    last_startup_stage: string;
    startup_error?: string | null;
  };
  knowledge: { pgvector_ready: boolean; retrieval_mode: string; retrieval_reason: string };
  provider_matrix: { rule_count: number; steps: string[] };
  provider_runtime: {
    ok: boolean;
    blocked_steps: string[];
    providers_with_open_circuit: string[];
    providers_disabled: string[];
  };
  recommended_checks: Record<string, string[]>;
} | null;

type ProviderRuntimeState = {
  providers: {
    provider: string;
    enabled: boolean;
    consecutive_failures: number;
    remaining_cooldown_seconds: number;
    open_until?: string | null;
    enabled_reason?: string | null;
    last_error?: string | null;
  }[];
  steps: {
    step: string;
    ready: boolean;
    candidate_profiles: string[];
    blocking_reasons: string[];
  }[];
  profiles: {
    profile_name: string;
    provider: string;
    model: string;
    task_type?: string | null;
    workflow_step?: string | null;
    spent_usd: number;
    monthly_budget_usd?: number | null;
    requests_per_minute?: number | null;
    enabled: boolean;
    skip_reason?: string | null;
  }[];
} | null;

type SelectedSmokeReportState = {
  report_type: SmokeReportType;
  provider_mode?: string | null;
  effective_provider_mode?: string | null;
  success: boolean;
  failure_stage?: string | null;
  scenario_count: number;
  created_at: string;
  blocking_reasons: string[];
  provider_preflight?: unknown;
  scenarios: {
    name: string;
    fixture_scenario?: string | null;
    expected_status?: string | null;
    actual_status?: string | null;
    resume_checkpoint?: string | null;
    event_summary?: { count?: number; counts?: Record<string, number> };
    assertions: { name: string; ok: boolean; detail?: string | null }[];
    step_statuses: {
      step_key: string;
      status: string;
      provider_mode?: string | null;
      provider?: string | null;
      model?: string | null;
      profile_name?: string | null;
    }[];
  }[];
  frontend_summary?: {
    url?: string | null;
    status_code?: number | null;
    created_at?: string | null;
    markers: Record<string, boolean>;
  } | null;
} | null;

type SelectedSmokeRegressionState = {
  comparable: boolean;
  regression_free: boolean;
  findings: {
    scope: string;
    key: string;
    message: string;
    baseline_value?: unknown;
    current_value?: unknown;
  }[];
  current_report: {
    filename: string;
    provider_mode?: string | null;
    success: boolean;
    failure_stage?: string | null;
  };
  baseline_report?: {
    filename: string;
    provider_mode?: string | null;
    success: boolean;
    created_at: string;
  } | null;
} | null;

type ProviderMatrixRule = {
  step: string;
  default_provider: string;
  default_model: string;
  timeout_ms: number;
  retry_count: number;
  fallback_targets: { provider: string; model: string }[];
  fallback_to_ollama_when: string;
  quality_degraded_on_fallback: boolean;
};

export type ProviderSettingsItem = {
  provider: ProviderKind;
  api_base: string;
  has_api_key: boolean;
  api_key_masked?: string | null;
  api_key?: string;
};

export type SmokeReportSummary = {
  report_type: SmokeReportType;
  filename: string;
  created_at: string;
  provider_mode?: string | null;
  failure_stage?: string | null;
  success: boolean;
  scenario_count: number;
};

export type SmokeLatest = {
  backend_full_smoke: SmokeReportSummary | null;
  frontend_live_smoke: SmokeReportSummary | null;
};

type UseRuntimeDiagnosticsOptions = {
  setBusyKey: (value: string) => void;
  setMessage: (ok: string | null, error?: string | null) => void;
};

export function useRuntimeDiagnostics({
  setBusyKey,
  setMessage,
}: UseRuntimeDiagnosticsOptions) {
  const [runtimeSelfCheck, setRuntimeSelfCheck] = useState<RuntimeSelfCheckState>(null);
  const [providerRuntime, setProviderRuntime] = useState<ProviderRuntimeState>(null);
  const [smokeLatest, setSmokeLatest] = useState<SmokeLatest | null>(null);
  const [smokeReports, setSmokeReports] = useState<SmokeReportSummary[]>([]);
  const [selectedSmokeReportFilename, setSelectedSmokeReportFilename] = useState("");
  const [selectedSmokeReport, setSelectedSmokeReport] = useState<SelectedSmokeReportState>(null);
  const [selectedSmokeRegression, setSelectedSmokeRegression] = useState<SelectedSmokeRegressionState>(null);
  const [providerMatrix, setProviderMatrix] = useState<ProviderMatrixRule[]>([]);
  const [providerSettings, setProviderSettings] = useState<ProviderSettingsItem[]>([
    { provider: "openai", api_base: "https://api.openai.com/v1", has_api_key: false, api_key: "" },
    { provider: "deepseek", api_base: "https://api.deepseek.com/v1", has_api_key: false, api_key: "" },
    { provider: "xai", api_base: "https://api.x.ai/v1", has_api_key: false, api_key: "" },
  ]);

  useEffect(() => {
    let active = true;

    void Promise.allSettled([
      loadProviderSettingsState(),
      loadRuntimeReadiness(),
      loadProviderRuntimeState(),
      loadSmokeLatestState(),
      loadSmokeReportsState(),
      loadProviderMatrixState(),
    ]).then((results) => {
      if (!active) return;
      const rejected = results.find((item) => item.status === "rejected");
      if (rejected?.status === "rejected") {
        setMessage(null, toErrorMessage(rejected.reason, "初始化运行诊断失败"));
      }
    });

    return () => {
      active = false;
    };
    // 该 effect 只在挂载时跑一次以拉初始诊断；setMessage 来自父组件的内联回调，
    // 每次 render 都是新闭包；把它放进依赖会让初始化反复触发。这里有意保持空依赖。
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    let active = true;

    if (!selectedSmokeReportFilename) {
      setSelectedSmokeReport(null);
      setSelectedSmokeRegression(null);
      return () => {
        active = false;
      };
    }

    void Promise.all([
      fetchSmokeReportDetail<SelectedSmokeReportState>(selectedSmokeReportFilename),
      fetchSmokeReportRegression<SelectedSmokeRegressionState>(selectedSmokeReportFilename),
    ])
      .then(([detail, regression]) => {
        if (!active) return;
        setSelectedSmokeReport(detail);
        setSelectedSmokeRegression(regression);
      })
      .catch((error) => {
        if (!active) return;
        setSelectedSmokeReport(null);
        setSelectedSmokeRegression(null);
        setMessage(null, toErrorMessage(error, "读取 smoke 报告详情失败"));
      });

    return () => {
      active = false;
    };
  }, [selectedSmokeReportFilename, setMessage]);

  async function loadProviderSettingsState() {
    const payload = await fetchProviderSettings<{ providers: ProviderSettingsItem[] }>();
    setProviderSettings(payload.providers.map((item) => ({ ...item, api_key: "" })));
    return payload;
  }

  async function loadRuntimeReadiness() {
    const [health, selfCheck] = await Promise.all([
      fetchHealth<NonNullable<RuntimeSelfCheckState>["health"]>(),
      fetchRuntimeSelfCheck<Omit<NonNullable<RuntimeSelfCheckState>, "health">>(),
    ]);
    const nextState = { ...selfCheck, health };
    setRuntimeSelfCheck(nextState);
    return nextState;
  }

  async function loadProviderRuntimeState() {
    const payload = await fetchProviderState<ProviderRuntimeState>();
    setProviderRuntime(payload);
    return payload;
  }

  async function loadSmokeLatestState() {
    const payload = await fetchLatestSmokeReports<SmokeLatest>();
    setSmokeLatest(payload);
    return payload;
  }

  async function loadSmokeReportsState() {
    const payload = await fetchSmokeReports<SmokeReportSummary[]>();
    setSmokeReports(payload);
    setSelectedSmokeReportFilename((current) =>
      payload.some((item) => item.filename === current) ? current : payload[0]?.filename ?? "",
    );
    return payload;
  }

  async function loadProviderMatrixState() {
    const payload = await fetchProviderMatrix<{ rules?: ProviderMatrixRule[] }>();
    const nextRules = payload.rules ?? [];
    setProviderMatrix(nextRules);
    return nextRules;
  }

  async function refreshAllDiagnostics() {
    return Promise.all([
      loadProviderSettingsState(),
      loadRuntimeReadiness(),
      loadProviderRuntimeState(),
      loadSmokeLatestState(),
      loadSmokeReportsState(),
      loadProviderMatrixState(),
    ]);
  }

  function updateProviderField(provider: ProviderKind, field: "api_key" | "api_base", value: string) {
    setProviderSettings((current) =>
      current.map((item) => (item.provider === provider ? { ...item, [field]: value } : item)),
    );
  }

  async function saveProviderSettingsState() {
    setBusyKey("saveProviderSettings");
    setMessage(null);

    try {
      const payload = await updateProviderSettings<{
        message: string;
        providers: ProviderSettingsItem[];
      }>(
        providerSettings.reduce<Record<string, { api_key: string | null; api_base: string }>>(
          (acc, item) => {
            acc[item.provider] = {
              api_key: item.api_key?.trim() ? item.api_key : null,
              api_base: item.api_base,
            };
            return acc;
          },
          {},
        ),
      );

      setProviderSettings(payload.providers.map((item) => ({ ...item, api_key: "" })));
      await Promise.all([loadProviderSettingsState(), loadRuntimeReadiness(), loadProviderRuntimeState()]);
      setMessage(payload.message || "API 配置已保存");
      return payload;
    } catch (error) {
      const nextError = toErrorMessage(error, "保存 API 配置失败");
      setMessage(null, nextError);
      throw error;
    } finally {
      setBusyKey("");
    }
  }

  return {
    providerSettings,
    providerRuntime,
    providerMatrix,
    runtimeSelfCheck,
    selectedSmokeRegression,
    selectedSmokeReport,
    selectedSmokeReportFilename,
    smokeLatest,
    smokeReports,
    updateProviderField,
    saveProviderSettingsState,
    loadProviderSettingsState,
    loadProviderMatrixState,
    loadProviderRuntimeState,
    loadRuntimeReadiness,
    loadSmokeLatestState,
    loadSmokeReportsState,
    refreshAllDiagnostics,
    setSelectedSmokeReportFilename,
  };
}

function toErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}
