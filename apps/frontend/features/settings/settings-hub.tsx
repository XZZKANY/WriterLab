"use client";

import { useEffect, useState } from "react";
import { fetchProviderSettings, updateProviderSettings } from "@/lib/api/settings";
import { AppShell } from "@/shared/ui/app-shell";
import { InfoCard } from "@/shared/ui/info-card";

type ProviderSettingsItem = {
  provider: "openai" | "deepseek" | "xai";
  api_base: string;
  has_api_key: boolean;
  api_key_masked?: string | null;
  api_key?: string;
};

export default function SettingsHub() {
  const [providers, setProviders] = useState<ProviderSettingsItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const payload = await fetchProviderSettings<{ providers: ProviderSettingsItem[] }>();
        if (!cancelled) {
          setProviders(payload.providers.map((item) => ({ ...item, api_key: "" })));
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "读取配置失败");
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  function updateField(provider: ProviderSettingsItem["provider"], field: "api_base" | "api_key", value: string) {
    setProviders((current) =>
      current.map((item) => (item.provider === provider ? { ...item, [field]: value } : item)),
    );
  }

  async function save() {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const payload = await updateProviderSettings<{
        message: string;
        providers: ProviderSettingsItem[];
      }>(
        providers.reduce<Record<string, { api_key: string | null; api_base: string }>>((acc, item) => {
          acc[item.provider] = {
            api_key: item.api_key?.trim() ? item.api_key : null,
            api_base: item.api_base,
          };
          return acc;
        }, {}),
      );
      setProviders(payload.providers.map((item) => ({ ...item, api_key: "" })));
      setMessage(payload.message || "已保存配置");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "保存配置失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell
      title="模型设置"
      description="云 API 与模型 Provider 配置统一在独立设置页维护，并沿用同一套暗色工作区视觉语言。"
      actions={
        <button
          className="rounded-xl bg-zinc-100 px-4 py-2.5 text-sm font-medium tracking-[-0.01em] text-black transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:bg-zinc-500"
          onClick={() => void save()}
          disabled={busy}
        >
          {busy ? "保存中…" : "保存配置"}
        </button>
      }
    >
      <InfoCard title="Provider 配置" description="保留现有后端接口与返回语义，只调整展示方式与控件层级。">
        <div className="space-y-4">
          {providers.length === 0 && !error ? (
            <div className="rounded-2xl border border-dashed border-white/10 bg-[#1a1a1a] px-4 py-6 text-sm text-zinc-500">
              还没有可配置的 Provider 数据。
            </div>
          ) : null}
          {providers.map((item) => (
            <article
              key={item.provider}
              className="rounded-[24px] border border-white/8 bg-[#1d1d1d] px-5 py-5"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="text-lg font-semibold capitalize tracking-[-0.02em] text-zinc-100">
                    {item.provider}
                  </div>
                  <div className="mt-2 text-sm leading-7 text-zinc-500">
                    调整 API Base 与密钥后，当前工作区会继续复用既有后端设置接口。
                  </div>
                </div>
                <span
                  className={`rounded-full border px-3 py-1 text-xs ${
                    item.has_api_key
                      ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-200"
                      : "border-white/8 bg-[#171717] text-zinc-500"
                  }`}
                >
                  {item.has_api_key ? "已配置密钥" : "未配置密钥"}
                </span>
              </div>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <input
                  className="rounded-2xl border border-white/8 bg-[#212121] px-4 py-3 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-zinc-600"
                  value={item.api_base}
                  onChange={(event) => updateField(item.provider, "api_base", event.target.value)}
                  placeholder="API Base"
                />
                <input
                  className="rounded-2xl border border-white/8 bg-[#212121] px-4 py-3 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-zinc-600"
                  value={item.api_key || ""}
                  onChange={(event) => updateField(item.provider, "api_key", event.target.value)}
                  placeholder={item.api_key_masked || "输入新的 API Key"}
                />
              </div>
              <div className="mt-3 text-xs tracking-[0.01em] text-zinc-500">
                当前 API Base：{item.api_base || "未配置"}
              </div>
            </article>
          ))}
          {message ? (
            <div className="rounded-2xl border border-emerald-400/20 bg-emerald-500/10 px-4 py-4 text-sm text-emerald-100">
              {message}
            </div>
          ) : null}
          {error ? (
            <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-4 text-sm text-rose-100">
              {error}
            </div>
          ) : null}
        </div>
      </InfoCard>
    </AppShell>
  );
}
