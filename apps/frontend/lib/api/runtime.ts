import { apiGet } from "@/lib/api/client";

export function fetchHealth<T>() {
  return apiGet<T>("/api/health", "读取健康状态失败");
}

export function fetchRuntimeSelfCheck<T>() {
  return apiGet<T>("/api/runtime/self-check", "读取 runtime self-check 失败");
}

export function fetchProviderState<T>() {
  return apiGet<T>("/api/runtime/provider-state", "读取 provider runtime 失败");
}

export function fetchLatestSmokeReports<T>() {
  return apiGet<T>("/api/runtime/smoke-reports/latest", "读取最新 smoke 报告失败");
}

export function fetchSmokeReports<T>() {
  return apiGet<T>("/api/runtime/smoke-reports", "读取 smoke 报告列表失败");
}

export function fetchSmokeReportDetail<T>(filename: string) {
  return apiGet<T>(
    `/api/runtime/smoke-reports/${filename}`,
    "读取 smoke 报告详情失败",
  );
}

export function fetchSmokeReportRegression<T>(filename: string) {
  return apiGet<T>(
    `/api/runtime/smoke-reports/${filename}/regression`,
    "读取 smoke 回归对比失败",
  );
}
