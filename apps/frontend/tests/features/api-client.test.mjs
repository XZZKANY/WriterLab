import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const clientPath = new URL("../../lib/api/client.ts", import.meta.url);

test("api client 源码契约：保留 base URL 解析、错误体提取、空响应容忍与网络错误包装", async () => {
  const source = await readFile(clientPath, "utf8");

  // 浏览器同源回落：默认在浏览器中走相对路径，让 Next 的同源代理生效。
  assert.equal(source.includes('return isBrowserRuntime() ? "" : DEFAULT_BACKEND_ORIGIN;'), true);
  assert.equal(source.includes('const DEFAULT_BACKEND_ORIGIN = "http://127.0.0.1:8000";'), true);

  // JSON 错误体提取：优先 detail，其次 message。
  assert.equal(source.includes('if (typeof parsed.detail === "string" && parsed.detail.trim())'), true);
  assert.equal(source.includes('if (typeof parsed.message === "string" && parsed.message.trim())'), true);

  // 204 空响应容忍：apiDelete 等返回 undefined 而不是抛 JSON parse 错。
  assert.equal(source.includes('if (response.status === 204)'), true);
  assert.equal(source.includes('if (!rawText)'), true);
  assert.equal(source.includes('return undefined as T;'), true);

  // 网络错误包装：必须把 base URL 与启动提示告诉用户。
  assert.equal(source.includes("formatNetworkErrorMessage"), true);
  assert.equal(source.includes("请确认后端服务已启动"), true);
  assert.equal(source.includes("NEXT_PUBLIC_API_BASE_URL"), true);

  // 关键导出：4 个 HTTP 方法 + base URL 探测。
  for (const symbol of ["getApiBaseUrl", "apiGet", "apiPost", "apiPut", "apiPatch", "apiDelete"]) {
    assert.equal(source.includes(`export function ${symbol}`) || source.includes(`export async function ${symbol}`), true, `缺少导出：${symbol}`);
  }
});
