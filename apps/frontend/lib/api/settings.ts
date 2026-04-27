import { apiGet, apiPut } from "@/lib/api/client";

export function fetchProviderSettings<T>() {
  return apiGet<T>("/api/settings/providers", "读取 API 配置失败");
}

export function updateProviderSettings<T>(body: unknown) {
  return apiPut<T>("/api/settings/providers", body, "保存 API 配置失败");
}
