import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const sidebarPath = new URL("../../features/editor/sidebar-panels.tsx", import.meta.url);

test("sidebar panels avoids legacy light-surface classes in dark workspace", async () => {
  const source = await readFile(sidebarPath, "utf8");

  assert.equal(
    /bg-zinc-100[^\n]*text-white/.test(source),
    false,
    "亮底按钮不应再搭配白字",
  );
  assert.equal(/\bbg-rose-50\b/.test(source), false, "不应保留浅色红底卡片");
  assert.equal(/\bbg-amber-50\b/.test(source), false, "不应保留浅色黄底卡片");
  assert.equal(/\bbg-emerald-50\b/.test(source), false, "不应保留浅色绿底卡片");
  assert.equal(/\btext-neutral-800\b/.test(source), false, "VN 导出预览不应保留浅色正文");
});
