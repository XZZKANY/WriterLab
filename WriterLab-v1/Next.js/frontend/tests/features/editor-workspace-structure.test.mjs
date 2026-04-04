import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const sidebarPanelsPath = new URL("../../features/editor/sidebar-panels.tsx", import.meta.url);
const workspaceHeaderPath = new URL("../../features/editor/workspace-header.tsx", import.meta.url);

const authoringMarkers = ["写作台与分支工作区", "分析与一致性", "记忆上下文与 VN 导出"];
const oldDiagnosticTitles = [
  "Workflow Debug",
  "Provider Runtime",
  "Smoke Console",
  "Provider Matrix",
  "Context Compiler",
  "Runtime Self-Check Alert",
];

// 这是为后续重构建立的失败基线测试，直到 editor 侧栏真正移除旧诊断区块前都应保持失败。
test("editor 入口应保留作者工作台契约，同时侧栏不应再出现旧诊断区块标题", async () => {
  const [sidebarSource, headerSource] = await Promise.all([
    readFile(sidebarPanelsPath, "utf8"),
    readFile(workspaceHeaderPath, "utf8"),
  ]);

  assert.equal(headerSource.includes(authoringMarkers[0]), true, `作者工作台标题缺少标记: ${authoringMarkers[0]}`);
  assert.equal(sidebarSource.includes(authoringMarkers[1]), true, `侧栏缺少标记: ${authoringMarkers[1]}`);
  assert.equal(sidebarSource.includes(authoringMarkers[2]), true, `侧栏缺少标记: ${authoringMarkers[2]}`);

  for (const title of oldDiagnosticTitles) {
    assert.equal(
      sidebarSource.includes(title),
      false,
      `sidebar-panels.tsx 仍包含旧诊断区块标题: ${title}`,
    );
  }
});
