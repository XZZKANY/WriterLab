import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const runtimeWorkbenchPath = new URL("../../features/runtime/runtime-debug-workbench.tsx", import.meta.url);
const runtimePagePath = new URL("../../app/runtime/page.tsx", import.meta.url);
const runtimeHubPath = new URL("../../features/runtime/runtime-hub.tsx", import.meta.url);
const editorRuntimeHookPath = new URL("../../features/editor/use-editor-runtime-workbench.ts", import.meta.url);
const runtimeDiagnosticsHookPath = new URL("../../features/runtime/hooks/use-runtime-diagnostics.ts", import.meta.url);

test("runtime debug workbench 的源码契约覆盖关键交互与状态回收", async () => {
  const [source, pageSource, hubSource, editorHookSource, runtimeHookSource] = await Promise.all([
    readFile(runtimeWorkbenchPath, "utf8"),
    readFile(runtimePagePath, "utf8"),
    readFile(runtimeHubPath, "utf8"),
    readFile(editorRuntimeHookPath, "utf8"),
    readFile(runtimeDiagnosticsHookPath, "utf8"),
  ]);

  assert.equal(source.includes("Workflow Debug"), true);
  assert.equal(source.includes("运行时就绪度"), true);
  assert.equal(source.includes("Smoke Console"), true);
  assert.equal(source.includes("Provider Matrix"), true);
  assert.equal(source.includes("Context Compiler"), true);

  assert.equal(source.includes("Resume / Retry"), true);
  assert.equal(source.includes("Cancel"), true);
  assert.equal(source.includes("输入 workflow id 后加载运行态"), true);
  assert.equal(source.includes("加载 Workflow Run"), true);

  assert.equal(
    source.includes("Planner Override") || source.includes("selectedWorkflowStepDiffRows") || source.includes("diff"),
    true,
  );

  const loadWorkflowBlock = sliceBetween(
    source,
    "async function loadWorkflowRun",
    "async function pollWorkflow",
  );
  assert.equal(loadWorkflowBlock.includes('setBusyKey("loadWorkflow");'), true);
  assert.equal(loadWorkflowBlock.includes("try {"), true);
  assert.equal(loadWorkflowBlock.includes("finally {"), true);
  assert.equal(loadWorkflowBlock.includes('if (showBusy) setBusyKey("");'), true);
  assert.equal(
    source.includes('onClick={() => void loadWorkflowRun().catch((nextError) => setError(toErrorMessage(nextError, "读取工作流失败")))}'),
    true,
  );

  const pollWorkflowBlock = sliceBetween(
    source,
    "async function pollWorkflow",
    "async function retryWorkflow",
  );
  assert.equal(pollWorkflowBlock.includes('setRuntimeConnection("connected");'), true);
  assert.equal(pollWorkflowBlock.includes("try {"), true);
  assert.equal(pollWorkflowBlock.includes("finally {"), true);
  assert.equal(pollWorkflowBlock.includes('setRuntimeConnection("idle");'), true);
  assert.equal(pollWorkflowBlock.includes('throw new Error("工作流轮询超时");'), true);

  assert.equal(
    pageSource.includes('import RuntimeDebugWorkbench from "@/features/runtime/runtime-debug-workbench";'),
    true,
  );
  assert.equal(pageSource.includes("return <RuntimeDebugWorkbench />;"), true);

  assert.equal(
    hubSource.includes('import RuntimeDebugWorkbench from "@/features/runtime/runtime-debug-workbench";'),
    true,
  );
  assert.equal(hubSource.includes("return <RuntimeDebugWorkbench />;"), true);
  assert.equal(hubSource.includes("fetchHealth"), false);
  assert.equal(hubSource.includes("fetchProviderState"), false);

  assert.equal(editorHookSource.includes("export {"), true);
  assert.equal(
    editorHookSource.includes('useRuntimeDiagnostics as useEditorRuntimeWorkbench'),
    true,
  );
  assert.equal(editorHookSource.includes("fetchHealth"), false);
  assert.equal(editorHookSource.includes("fetchProviderState"), false);

  assert.equal(runtimeHookSource.includes("SidebarPanels"), false);
  assert.equal(runtimeHookSource.includes('from "@/features/editor/sidebar-panels"'), false);
  assert.equal(runtimeHookSource.includes("export type SmokeReportType"), true);
  assert.equal(runtimeHookSource.includes("type RuntimeSelfCheckState = {"), true);
});

function sliceBetween(source, startMarker, endMarker) {
  const start = source.indexOf(startMarker);
  const end = source.indexOf(endMarker);

  assert.notEqual(start, -1, `未找到起始标记: ${startMarker}`);
  assert.notEqual(end, -1, `未找到结束标记: ${endMarker}`);
  assert.ok(end > start, `标记顺序异常: ${startMarker} -> ${endMarker}`);

  return source.slice(start, end);
}
