import test from "node:test";
import assert from "node:assert/strict";

import { apiDelete, apiGet } from "../../lib/api/client.ts";

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
