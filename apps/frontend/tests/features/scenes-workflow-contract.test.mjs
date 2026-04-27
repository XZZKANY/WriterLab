import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const scenesApiPath = new URL("../../lib/api/scenes.ts", import.meta.url);
const workflowApiPath = new URL("../../lib/api/workflow.ts", import.meta.url);
const settingsApiPath = new URL("../../lib/api/settings.ts", import.meta.url);

test("lib/api/scenes 暴露 scene/version/branch 完整 CRUD 与 diff/restore/adopt 路径", async () => {
  const source = await readFile(scenesApiPath, "utf8");

  // 必须复用统一 client，而不是直接调 fetch
  assert.equal(source.includes("@/lib/api/client"), true, "scenes.ts 必须从 client.ts import 统一封装");
  assert.equal(source.includes("apiGet"), true);
  assert.equal(source.includes("apiPost"), true);
  assert.equal(source.includes("apiPatch"), true);
  assert.equal(source.includes("fetch('/api"), false, "scenes.ts 不应再直接调 fetch（应走 apiRequest 封装）");

  // 场景核心 CRUD
  for (const symbol of [
    "fetchSceneContext",
    "fetchScenesByChapter",
    "updateScene",
  ]) {
    assert.equal(
      source.includes(`export function ${symbol}`),
      true,
      `缺少 export function ${symbol}`,
    );
  }

  // 版本流（fetch / restore）
  assert.equal(source.includes("fetchSceneVersions"), true);
  assert.equal(source.includes("restoreSceneVersion"), true);
  assert.equal(source.includes("/versions/"), true);
  assert.equal(source.includes("/restore"), true);

  // 分支流（list / diff / create / adopt）
  for (const symbol of [
    "fetchBranchesByScene",
    "fetchBranchDiff",
    "createBranch",
    "adoptBranch",
  ]) {
    assert.equal(
      source.includes(`export function ${symbol}`),
      true,
      `缺少 export function ${symbol}`,
    );
  }
  assert.equal(source.includes("/api/branches"), true);
  assert.equal(source.includes("/diff"), true);
  assert.equal(source.includes("/adopt"), true);
});


test("lib/api/workflow 覆盖 analyze/write/revise + workflow 编排 + scan/export 路径", async () => {
  const source = await readFile(workflowApiPath, "utf8");

  assert.equal(source.includes("@/lib/api/client"), true, "workflow.ts 必须复用 client.ts");
  assert.equal(source.includes("fetch('/api"), false);

  // provider matrix 与场景分析记录的获取/选择
  for (const symbol of [
    "fetchProviderMatrix",
    "fetchSceneAnalyses",
    "updateAnalysisSelection",
  ]) {
    assert.equal(
      source.includes(`export function ${symbol}`),
      true,
      `缺少 export function ${symbol}`,
    );
  }

  // 三个场景生成入口
  for (const symbol of ["analyzeScene", "writeScene", "reviseScene"]) {
    assert.equal(
      source.includes(`export function ${symbol}`),
      true,
      `缺少 export function ${symbol}`,
    );
  }
  assert.equal(source.includes("/api/ai/analyze-scene"), true);
  assert.equal(source.includes("/api/ai/write-scene"), true);
  assert.equal(source.includes("/api/ai/revise-scene"), true);

  // workflow 编排 5 入口
  for (const symbol of [
    "queueSceneWorkflow",
    "runSceneWorkflowSync",
    "fetchWorkflowRun",
    "resumeWorkflowRun",
    "overrideWorkflowStep",
    "cancelWorkflowRun",
  ]) {
    assert.equal(
      source.includes(`export function ${symbol}`),
      true,
      `缺少 export function ${symbol}`,
    );
  }
  assert.equal(source.includes("/api/ai/workflows/scene"), true);
  assert.equal(source.includes("/api/ai/workflows/scene/run-sync"), true);
  assert.equal(source.includes("/resume"), true);
  assert.equal(source.includes("/cancel"), true);
  assert.equal(source.includes("/override"), true);

  // 一致性扫描与 VN 导出（确保 URL 与后端 router 对齐）
  assert.equal(source.includes("scanConsistency"), true);
  assert.equal(source.includes("exportVn"), true);
  assert.equal(source.includes("/api/consistency/scan"), true);
  assert.equal(source.includes("/api/vn/export"), true);
});


test("lib/api/settings 暴露 provider settings 双向同步契约", async () => {
  const source = await readFile(settingsApiPath, "utf8");

  assert.equal(source.includes("@/lib/api/client"), true);
  assert.equal(source.includes("apiGet"), true);
  assert.equal(source.includes("apiPut"), true);
  assert.equal(source.includes("export function fetchProviderSettings"), true);
  assert.equal(source.includes("export function updateProviderSettings"), true);
  // 路径必须与 backend app/api/settings.py 注册的 router prefix 对齐
  assert.equal(source.includes("/api/settings/providers"), true);
});
