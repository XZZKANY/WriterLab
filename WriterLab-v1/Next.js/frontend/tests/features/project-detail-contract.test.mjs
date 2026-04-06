import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const projectApiPath = new URL("../../lib/api/projects.ts", import.meta.url);
const projectDetailPath = new URL("../../features/project/project-detail.tsx", import.meta.url);

test("project detail reads project overview instead of manual nested fetch chain", async () => {
  const [apiSource, detailSource] = await Promise.all([
    readFile(projectApiPath, "utf8"),
    readFile(projectDetailPath, "utf8"),
  ]);

  assert.equal(apiSource.includes("fetchProjectOverview"), true);
  assert.equal(detailSource.includes("fetchProjectOverview"), true);
  assert.equal(detailSource.includes("fetchBooksByProject"), false);
  assert.equal(detailSource.includes("fetchChaptersByBook"), false);
  assert.equal(detailSource.includes("fetchScenesByChapter"), false);
});
