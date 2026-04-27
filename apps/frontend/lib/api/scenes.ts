import { apiGet, apiPatch, apiPost } from "@/lib/api/client";

export function fetchSceneContext<T>(sceneId: string) {
  return apiGet<T>(`/api/scenes/${sceneId}/context`, "读取场景失败");
}

export function fetchScenesByChapter<T>(chapterId: string) {
  return apiGet<T>(`/api/scenes?chapter_id=${chapterId}`, "读取场景列表失败");
}

export function updateScene<T>(sceneId: string, body: unknown) {
  return apiPatch<T>(`/api/scenes/${sceneId}`, body, "保存正文失败");
}

export function fetchSceneVersions<T>(sceneId: string) {
  return apiGet<T>(`/api/scenes/${sceneId}/versions`, "读取版本失败");
}

export function restoreSceneVersion<T>(sceneId: string, versionId: string) {
  return apiPost<T>(
    `/api/scenes/${sceneId}/versions/${versionId}/restore`,
    undefined,
    "恢复版本失败",
  );
}

export function fetchBranchesByScene<T>(sceneId: string) {
  return apiGet<T>(`/api/branches?scene_id=${sceneId}`, "读取分支失败");
}

export function fetchBranchDiff<T>(branchId: string) {
  return apiGet<T>(`/api/branches/${branchId}/diff`, "读取分支差异失败");
}

export function createBranch<T>(body: unknown) {
  return apiPost<T>("/api/branches", body, "创建分支失败");
}

export function adoptBranch<T>(branchId: string) {
  return apiPost<T>(`/api/branches/${branchId}/adopt`, undefined, "采纳分支失败");
}
