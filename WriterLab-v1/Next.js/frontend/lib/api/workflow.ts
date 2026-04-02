import { apiGet, apiPost } from "@/lib/api/client";

export function fetchProviderMatrix<T>() {
  return apiGet<T>("/api/ai/provider-matrix", "读取 provider matrix 失败");
}

export function fetchSceneAnalyses<T>(sceneId: string) {
  return apiGet<T>(`/api/ai/scenes/${sceneId}/analyses`, "读取分析记录失败");
}

export function updateAnalysisSelection<T>(analysisId: string, body: unknown) {
  return apiPost<T>(
    `/api/ai/analyses/${analysisId}/selection`,
    body,
    "更新分析项失败",
  );
}

export function analyzeScene<T>(body: unknown) {
  return apiPost<T>("/api/ai/analyze-scene", body, "分析场景失败");
}

export function writeScene<T>(body: unknown) {
  return apiPost<T>("/api/ai/write-scene", body, "扩写正文失败");
}

export function reviseScene<T>(body: unknown) {
  return apiPost<T>("/api/ai/revise-scene", body, "润色正文失败");
}

export function queueSceneWorkflow<T>(body: unknown) {
  return apiPost<T>("/api/ai/workflows/scene", body, "启动工作流失败");
}

export function runSceneWorkflowSync<T>(body: unknown) {
  return apiPost<T>("/api/ai/workflows/scene/run-sync", body, "同步执行工作流失败");
}

export function fetchWorkflowRun<T>(workflowId: string) {
  return apiGet<T>(`/api/ai/workflows/${workflowId}`, "读取工作流失败");
}

export function resumeWorkflowRun<T>(workflowId: string, body: unknown) {
  return apiPost<T>(
    `/api/ai/workflows/${workflowId}/resume`,
    body,
    "恢复工作流失败",
  );
}

export function overrideWorkflowStep<T>(
  workflowId: string,
  stepKey: string,
  body: unknown,
) {
  return apiPost<T>(
    `/api/ai/workflows/${workflowId}/steps/${stepKey}/override`,
    body,
    "覆盖工作流步骤失败",
  );
}

export function cancelWorkflowRun<T>(workflowId: string) {
  return apiPost<T>(
    `/api/ai/workflows/${workflowId}/cancel`,
    undefined,
    "取消工作流失败",
  );
}

export function scanConsistency<T>(body: unknown) {
  return apiPost<T>("/api/consistency/scan", body, "一致性扫描失败");
}

export function exportVn<T>(body: unknown) {
  return apiPost<T>("/api/vn/export", body, "导出 VN 失败");
}
