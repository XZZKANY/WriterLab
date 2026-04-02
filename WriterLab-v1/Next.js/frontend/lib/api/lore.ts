import { apiGet } from "@/lib/api/client";

export function fetchCharacters<T>(projectId: string) {
  return apiGet<T>(`/api/characters?project_id=${projectId}`, "读取角色失败");
}

export function fetchLocations<T>(projectId: string) {
  return apiGet<T>(`/api/locations?project_id=${projectId}`, "读取地点失败");
}

export function fetchLoreEntries<T>(projectId: string) {
  return apiGet<T>(`/api/lore-entries?project_id=${projectId}`, "读取设定词条失败");
}
