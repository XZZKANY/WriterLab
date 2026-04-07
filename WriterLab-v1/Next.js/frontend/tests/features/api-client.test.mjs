import test from "node:test";
import assert from "node:assert/strict";

import { apiDelete, apiGet, getApiBaseUrl } from "../../lib/api/client.ts";

test("apiGet extracts detail from JSON error payloads", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ detail: "Project not found" }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });

  try {
    await assert.rejects(
      () => apiGet("/api/projects/404"),
      (error) => error instanceof Error && error.message === "Project not found",
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("apiDelete tolerates empty success bodies", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(null, {
      status: 204,
    });

  try {
    const payload = await apiDelete("/api/projects/empty");
    assert.equal(payload, undefined);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("apiDelete wraps network failures with api base context", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new TypeError("Failed to fetch");
  };

  try {
    await assert.rejects(
      () => apiDelete("/api/projects/network-error", "删除项目失败"),
      (error) =>
        error instanceof Error &&
        error.message.includes("删除项目失败") &&
        error.message.includes("http://127.0.0.1:8000") &&
        error.message.includes("请确认后端服务已启动"),
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("getApiBaseUrl uses same-origin proxy in browser runtime by default", () => {
  const originalWindow = globalThis.window;
  globalThis.window = {};

  try {
    assert.equal(getApiBaseUrl(), "");
  } finally {
    if (originalWindow === undefined) {
      delete globalThis.window;
    } else {
      globalThis.window = originalWindow;
    }
  }
});
