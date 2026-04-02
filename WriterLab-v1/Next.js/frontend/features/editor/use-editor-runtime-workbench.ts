"use client";

import { type ComponentProps, useEffect, useState } from "react";
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
import { SidebarPanels } from "@/features/editor/sidebar-panels";

export type ProviderKind = "openai" | "deepseek" | "xai";
export type SmokeReportType = ComponentProps<typeof SidebarPanels>["latestBackendSmoke"] extends {
  report_type: infer T;
}
  ? T
  : "backend_full_smoke" | "frontend_live_smoke";
type SidebarPanelsProps = ComponentProps<typeof SidebarPanels>;
type RuntimeSelfCheckState = SidebarPanelsProps["runtimeSelfCheck"];
type ProviderRuntimeState = SidebarPanelsProps["providerRuntime"];
type SelectedSmokeReportState = SidebarPanelsProps["selectedSmokeReport"];
type SelectedSmokeRegressionState = SidebarPanelsProps["selectedSmokeRegression"];
type ProviderMatrixRule = SidebarPanelsProps["providerMatrix"][number];

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

type UseEditorRuntimeWorkbenchOptions = {
  setBusyKey: (value: string) => void;
  setMessage: (ok: string | null, error?: string | null) => void;
};

export function useEditorRuntimeWorkbench({
  setBusyKey,
  setMessage,
}: UseEditorRuntimeWorkbenchOptions) {
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
    void loadProviderSettingsState();
    void loadRuntimeReadiness();
    void loadProviderRuntimeState();
    void loadSmokeLatestState();
    void loadSmokeReportsState();
    void loadProviderMatrixState();
  }, []);

  useEffect(() => {
    if (!selectedSmokeReportFilename) return;

    void Promise.all([
      fetchSmokeReportDetail<SelectedSmokeReportState>(selectedSmokeReportFilename),
      fetchSmokeReportRegression<SelectedSmokeRegressionState>(selectedSmokeReportFilename),
    ])
      .then(([detail, regression]) => {
        setSelectedSmokeReport(detail);
        setSelectedSmokeRegression(regression);
      })
      .catch(() => {
        setSelectedSmokeReport(null);
        setSelectedSmokeRegression(null);
      });
  }, [selectedSmokeReportFilename]);

  async function loadProviderSettingsState() {
    try {
      const payload = await fetchProviderSettings<{ providers: ProviderSettingsItem[] }>();
      setProviderSettings(payload.providers.map((item) => ({ ...item, api_key: "" })));
    } catch {}
  }

  async function loadRuntimeReadiness() {
    try {
      const [health, selfCheck] = await Promise.all([
        fetchHealth<NonNullable<RuntimeSelfCheckState>["health"]>(),
        fetchRuntimeSelfCheck<Omit<NonNullable<RuntimeSelfCheckState>, "health">>(),
      ]);
      setRuntimeSelfCheck({ ...selfCheck, health });
    } catch {}
  }

  async function loadProviderRuntimeState() {
    try {
      setProviderRuntime(await fetchProviderState<ProviderRuntimeState>());
    } catch {}
  }

  async function loadSmokeLatestState() {
    try {
      setSmokeLatest(await fetchLatestSmokeReports<SmokeLatest>());
    } catch {}
  }

  async function loadSmokeReportsState() {
    try {
      const payload = await fetchSmokeReports<SmokeReportSummary[]>();
      setSmokeReports(payload);
      setSelectedSmokeReportFilename((current) =>
        payload.some((item) => item.filename === current) ? current : payload[0]?.filename ?? "",
      );
    } catch {}
  }

  async function loadProviderMatrixState() {
    try {
      const payload = await fetchProviderMatrix<{ rules?: ProviderMatrixRule[] }>();
      setProviderMatrix(payload.rules ?? []);
    } catch {}
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
      setMessage(payload.message || "API 配置已保存");
      await Promise.all([loadRuntimeReadiness(), loadProviderRuntimeState()]);
    } catch (error) {
      setMessage(null, error instanceof Error ? error.message : "保存 API 配置失败");
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
    loadProviderRuntimeState,
    loadRuntimeReadiness,
    loadSmokeLatestState,
    loadSmokeReportsState,
    setSelectedSmokeReportFilename,
  };
}
