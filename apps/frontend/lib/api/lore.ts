import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api/client";

export type CharacterResponse = {
  id: string;
  project_id: string;
  name: string;
  aliases?: string | null;
  appearance?: string | null;
  personality?: string | null;
  background?: string | null;
  motivation?: string | null;
  speaking_style?: string | null;
  status?: string | null;
  secrets?: string | null;
  created_at: string;
  updated_at: string;
};

export type CharacterCreatePayload = {
  project_id: string;
  name: string;
  aliases?: string | null;
  appearance?: string | null;
  personality?: string | null;
  background?: string | null;
  motivation?: string | null;
  speaking_style?: string | null;
  status?: string | null;
  secrets?: string | null;
};

export type CharacterUpdatePayload = Partial<Omit<CharacterCreatePayload, "project_id">>;

export type CharacterDeleteResponse = {
  deleted: boolean;
  character_id: string;
};

export type LocationResponse = {
  id: string;
  project_id: string;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
};

export type LocationCreatePayload = {
  project_id: string;
  name: string;
  description?: string | null;
};

export type LocationUpdatePayload = Partial<Omit<LocationCreatePayload, "project_id">>;

export type LocationDeleteResponse = {
  deleted: boolean;
  location_id: string;
};

export type LoreEntryResponse = {
  id: string;
  project_id: string;
  category: string;
  title: string;
  content: string;
  priority: number;
  canonical: boolean;
  created_at: string;
  updated_at: string;
};

export type LoreEntryCreatePayload = {
  project_id: string;
  category: string;
  title: string;
  content: string;
  priority?: number;
  canonical?: boolean;
};

export type LoreEntryUpdatePayload = Partial<Omit<LoreEntryCreatePayload, "project_id">>;

export type LoreEntryDeleteResponse = {
  deleted: boolean;
  lore_entry_id: string;
};

export function fetchCharacters<T = CharacterResponse[]>(projectId: string) {
  return apiGet<T>(`/api/characters?project_id=${projectId}`, "读取角色失败");
}

export function fetchCharacterDetail<T = CharacterResponse>(characterId: string) {
  return apiGet<T>(`/api/characters/${characterId}`, "读取角色详情失败");
}

export function createCharacter<T = CharacterResponse>(body: CharacterCreatePayload) {
  return apiPost<T>("/api/characters", body, "创建角色失败");
}

export function updateCharacter<T = CharacterResponse>(characterId: string, body: CharacterUpdatePayload) {
  return apiPatch<T>(`/api/characters/${characterId}`, body, "更新角色失败");
}

export function deleteCharacter<T = CharacterDeleteResponse>(characterId: string) {
  return apiDelete<T>(`/api/characters/${characterId}`, "删除角色失败");
}

export function fetchLocations<T = LocationResponse[]>(projectId: string) {
  return apiGet<T>(`/api/locations?project_id=${projectId}`, "读取地点失败");
}

export function fetchLocationDetail<T = LocationResponse>(locationId: string) {
  return apiGet<T>(`/api/locations/${locationId}`, "读取地点详情失败");
}

export function createLocation<T = LocationResponse>(body: LocationCreatePayload) {
  return apiPost<T>("/api/locations", body, "创建地点失败");
}

export function updateLocation<T = LocationResponse>(locationId: string, body: LocationUpdatePayload) {
  return apiPatch<T>(`/api/locations/${locationId}`, body, "更新地点失败");
}

export function deleteLocation<T = LocationDeleteResponse>(locationId: string) {
  return apiDelete<T>(`/api/locations/${locationId}`, "删除地点失败");
}

export function fetchLoreEntries<T = LoreEntryResponse[]>(projectId: string) {
  return apiGet<T>(`/api/lore-entries?project_id=${projectId}`, "读取设定词条失败");
}

export function fetchLoreEntryDetail<T = LoreEntryResponse>(entryId: string) {
  return apiGet<T>(`/api/lore-entries/${entryId}`, "读取设定词条详情失败");
}

export function createLoreEntry<T = LoreEntryResponse>(body: LoreEntryCreatePayload) {
  return apiPost<T>("/api/lore-entries", body, "创建设定词条失败");
}

export function updateLoreEntry<T = LoreEntryResponse>(entryId: string, body: LoreEntryUpdatePayload) {
  return apiPatch<T>(`/api/lore-entries/${entryId}`, body, "更新设定词条失败");
}

export function deleteLoreEntry<T = LoreEntryDeleteResponse>(entryId: string) {
  return apiDelete<T>(`/api/lore-entries/${entryId}`, "删除设定词条失败");
}
