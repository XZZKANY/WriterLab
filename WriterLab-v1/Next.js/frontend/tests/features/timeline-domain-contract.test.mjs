import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const timelineApiPath = new URL("../../lib/api/timeline.ts", import.meta.url);
const timelinePagePath = new URL("../../features/timeline/timeline-library-page.tsx", import.meta.url);
const projectTimelineRoutePath = new URL("../../app/project/[projectId]/timeline/page.tsx", import.meta.url);
const projectDetailPath = new URL("../../features/project/project-detail.tsx", import.meta.url);

test("timeline api exposes shared timeline fetch contract", async () => {
  const apiSource = await readFile(timelineApiPath, "utf8");

  assert.equal(apiSource.includes("apiGet"), true);
  assert.equal(apiSource.includes("fetchTimelineEvents"), true);
  assert.equal(apiSource.includes("/api/timeline-events?project_id="), true);
  assert.equal(apiSource.includes("读取时间线失败"), true);
});

test("timeline page consumes shared timeline api instead of direct page-level fetch", async () => {
  const pageSource = await readFile(timelinePagePath, "utf8");

  assert.equal(pageSource.includes("@/lib/api/timeline"), true);
  assert.equal(pageSource.includes("fetchTimelineEvents"), true);
  assert.equal(pageSource.includes("fetch('/api/"), false);
  assert.equal(pageSource.includes("项目时间线"), true);
  assert.equal(pageSource.includes("时间线事件"), true);
});

test("project timeline route passes dynamic projectId into timeline feature page", async () => {
  const routeSource = await readFile(projectTimelineRoutePath, "utf8");

  assert.equal(routeSource.includes("params: Promise<{ projectId: string }>"), true);
  assert.equal(routeSource.includes("const { projectId } = await params"), true);
  assert.equal(routeSource.includes("TimelineLibraryPage projectId={projectId}"), true);
});

test("project detail exposes timeline workbench entry", async () => {
  const detailSource = await readFile(projectDetailPath, "utf8");

  assert.equal(detailSource.includes("/project/${projectId}/timeline"), true);
  assert.equal(detailSource.includes("项目时间线"), true);
  assert.equal(detailSource.includes("剧情事实"), true);
});
