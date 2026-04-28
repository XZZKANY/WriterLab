import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const projectsApiPath = new URL("../../lib/api/projects.ts", import.meta.url);
const settingsApiPath = new URL("../../lib/api/settings.ts", import.meta.url);

test("lib/api/projects 暴露项目 CRUD、overview 与层级列表契约", async () => {
  const source = await readFile(projectsApiPath, "utf8");

  assert.equal(source.includes("@/lib/api/client"), true, "projects.ts 必须复用 client.ts");
  assert.equal(source.includes("apiGet"), true);
  assert.equal(source.includes("apiPost"), true);
  assert.equal(source.includes("apiDelete"), true);
  assert.equal(source.includes("fetch('/api"), false, "projects.ts 不应直接调 fetch");

  for (const symbol of [
    "fetchProjects",
    "createProject",
    "deleteProject",
    "fetchProjectOverview",
    "fetchBooksByProject",
    "fetchChaptersByBook",
  ]) {
    assert.equal(
      source.includes(`export function ${symbol}`),
      true,
      `缺少 export function ${symbol}`,
    );
  }

  for (const symbol of [
    "ProjectCreatePayload",
    "ProjectResponse",
    "ProjectDeleteResponse",
    "ProjectOverviewResponse",
  ]) {
    assert.equal(
      source.includes(`export type ${symbol}`),
      true,
      `缺少 export type ${symbol}`,
    );
  }

  assert.equal(source.includes('"/api/projects"'), true);
  assert.equal(source.includes('`/api/projects/${projectId}`'), true);
  assert.equal(source.includes('`/api/projects/${projectId}/overview`'), true);
  assert.equal(source.includes('`/api/books?project_id=${projectId}`'), true);
  assert.equal(source.includes('`/api/chapters?book_id=${bookId}`'), true);

  assert.equal(source.includes("读取项目失败"), true);
  assert.equal(source.includes("创建项目失败"), true);
  assert.equal(source.includes("删除项目失败"), true);
  assert.equal(source.includes("读取项目概览失败"), true);
  assert.equal(source.includes("读取书籍失败"), true);
  assert.equal(source.includes("读取章节失败"), true);
});

test("lib/api/settings 暴露 provider settings 读写契约", async () => {
  const source = await readFile(settingsApiPath, "utf8");

  assert.equal(source.includes("@/lib/api/client"), true, "settings.ts 必须复用 client.ts");
  assert.equal(source.includes("apiGet"), true);
  assert.equal(source.includes("apiPut"), true);
  assert.equal(source.includes("fetch('/api"), false, "settings.ts 不应直接调 fetch");

  assert.equal(source.includes("export function fetchProviderSettings"), true);
  assert.equal(source.includes("export function updateProviderSettings"), true);
  assert.equal(source.includes('"/api/settings/providers"'), true);
  assert.equal(source.includes("读取 API 配置失败"), true);
  assert.equal(source.includes("保存 API 配置失败"), true);
});
