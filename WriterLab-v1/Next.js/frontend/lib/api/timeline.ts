import { apiGet } from "@/lib/api/client";

export type TimelineEventResponse = {
  id: string;
  project_id: string;
  chapter_id?: string | null;
  scene_id?: string | null;
  title: string;
  event_type: string;
  description: string;
  participants?: string[] | null;
  event_time_label?: string | null;
  canonical: boolean;
  metadata_json?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export function fetchTimelineEvents<T = TimelineEventResponse[]>(projectId: string) {
  return apiGet<T>(`/api/timeline-events?project_id=${projectId}`, "读取时间线失败");
}
