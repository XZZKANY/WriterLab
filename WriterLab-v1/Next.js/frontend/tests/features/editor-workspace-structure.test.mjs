import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const contextSidebarPath = new URL("../../features/editor/context-sidebar.tsx", import.meta.url);
const workspaceHeaderPath = new URL("../../features/editor/workspace-header.tsx", import.meta.url);
const writingPanePath = new URL("../../features/editor/writing-pane.tsx", import.meta.url);

const authoringMarkers = ["写作台与分支工作区", "分析与一致性", "记忆上下文与 VN 导出"];
const oldDiagnosticTitles = [
  "Workflow Debug",
  "Provider Runtime",
  "Smoke Console",
  "Provider Matrix",
  "Context Compiler",
  "Runtime Self-Check Alert",
];

test("editor 入口应保留作者工作台契约，同时侧栏与写作区移除运行诊断泄漏", async () => {
  const [contextSidebarSource, headerSource, writingSource] = await Promise.all([
    readFile(contextSidebarPath, "utf8"),
    readFile(workspaceHeaderPath, "utf8"),
    readFile(writingPanePath, "utf8"),
  ]);

  assert.equal(headerSource.includes(authoringMarkers[0]), true, `作者工作台标题缺少标记: ${authoringMarkers[0]}`);
  assert.equal(contextSidebarSource.includes(authoringMarkers[1]), true, `侧栏缺少标记: ${authoringMarkers[1]}`);
  assert.equal(contextSidebarSource.includes(authoringMarkers[2]), true, `侧栏缺少标记: ${authoringMarkers[2]}`);

  for (const title of oldDiagnosticTitles) {
    assert.equal(
      contextSidebarSource.includes(title),
      false,
      `context-sidebar.tsx 仍包含旧诊断区块标题: ${title}`,
    );
  }

  assert.equal(writingSource.includes("onRunWorkflow"), false, "writing-pane.tsx 不应再暴露 onRunWorkflow");
  assert.equal(writingSource.includes("onScanConsistency"), false, "writing-pane.tsx 不应再暴露 onScanConsistency");
  assert.equal(writingSource.includes("onExportVn"), false, "writing-pane.tsx 不应再暴露 onExportVn");
  assert.equal(writingSource.includes("workflowProviderMode"), false, "writing-pane.tsx 不应再暴露 workflowProviderMode");
  assert.equal(writingSource.includes("fixtureScenario"), false, "writing-pane.tsx 不应再暴露 fixtureScenario");
});
