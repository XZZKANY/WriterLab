import { apiDelete, apiGet, apiPost } from "@/lib/api/client";

export type ProjectCreatePayload = {
  name: string;
  description?: string;
  genre?: string;
  default_language?: string;
};

export type ProjectResponse = {
  id: string;
  name: string;
  description?: string | null;
  genre?: string | null;
  default_language: string;
  created_at: string;
  updated_at: string;
};

export type ProjectDeleteResponse = {
  deleted: boolean;
  project_id: string;
};

export type ProjectBookSummary = {
  id: string;
  project_id: string;
  title: string;
  summary?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type ProjectChapterSummary = {
  id: string;
  book_id: string;
  chapter_no: number;
  title: string;
  summary?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type ProjectSceneSummary = {
  id: string;
  chapter_id: string;
  scene_no: number;
  title: string;
  status?: string | null;
  created_at: string;
  updated_at: string;
};

export type ProjectOverviewResponse = {
  project: ProjectResponse;
  books: ProjectBookSummary[];
  chapters_by_book: Record<string, ProjectChapterSummary[]>;
  scenes_by_chapter: Record<string, ProjectSceneSummary[]>;
  counts: {
    books: number;
    chapters: number;
    scenes: number;
  };
};

export function fetchProjects<T>() {
  return apiGet<T>("/api/projects", "读取项目失败");
}

export function createProject<T>(body: ProjectCreatePayload) {
  return apiPost<T>("/api/projects", body, "创建项目失败");
}

export function deleteProject<T>(projectId: string) {
  return apiDelete<T>(`/api/projects/${projectId}`, "删除项目失败");
}

export function fetchProjectOverview<T>(projectId: string) {
  return apiGet<T>(`/api/projects/${projectId}/overview`, "读取项目概览失败");
}

export function fetchBooksByProject<T>(projectId: string) {
  return apiGet<T>(`/api/books?project_id=${projectId}`, "读取书籍失败");
}

export function fetchChaptersByBook<T>(bookId: string) {
  return apiGet<T>(`/api/chapters?book_id=${bookId}`, "读取章节失败");
}
