import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const loreApiPath = new URL("../../lib/api/lore.ts", import.meta.url);
const loreLibraryPagePath = new URL("../../features/lore/lore-library-page.tsx", import.meta.url);
const loreHubPath = new URL("../../features/lore/lore-hub.tsx", import.meta.url);

test("lore api exposes shared detail update delete contracts for three lore domains", async () => {
  const apiSource = await readFile(loreApiPath, "utf8");

  assert.equal(apiSource.includes("apiPatch"), true);
  assert.equal(apiSource.includes("apiDelete"), true);
  assert.equal(apiSource.includes("fetchCharacterDetail"), true);
  assert.equal(apiSource.includes("updateCharacter"), true);
  assert.equal(apiSource.includes("deleteCharacter"), true);
  assert.equal(apiSource.includes("fetchLocationDetail"), true);
  assert.equal(apiSource.includes("updateLocation"), true);
  assert.equal(apiSource.includes("deleteLocation"), true);
  assert.equal(apiSource.includes("fetchLoreEntryDetail"), true);
  assert.equal(apiSource.includes("updateLoreEntry"), true);
  assert.equal(apiSource.includes("deleteLoreEntry"), true);
});

test("lore pages keep consuming shared lore api instead of direct page-level fetch", async () => {
  const [librarySource, hubSource] = await Promise.all([
    readFile(loreLibraryPagePath, "utf8"),
    readFile(loreHubPath, "utf8"),
  ]);

  assert.equal(librarySource.includes("@/lib/api/lore"), true);
  assert.equal(hubSource.includes("@/lib/api/lore"), true);
  assert.equal(librarySource.includes("fetch('/api/"), false);
  assert.equal(hubSource.includes("fetch('/api/"), false);
});

test("lore library page provides selected detail editing through shared update contracts", async () => {
  const librarySource = await readFile(loreLibraryPagePath, "utf8");

  assert.equal(librarySource.includes("selectedItemId"), true);
  assert.equal(librarySource.includes("isEditing"), true);
  assert.equal(librarySource.includes("updateCharacter"), true);
  assert.equal(librarySource.includes("updateLocation"), true);
  assert.equal(librarySource.includes("updateLoreEntry"), true);
  assert.equal(librarySource.includes("资料详情"), true);
  assert.equal(librarySource.includes("开始编辑"), true);
});

test("lore library page provides minimal create delete flows through shared contracts", async () => {
  const librarySource = await readFile(loreLibraryPagePath, "utf8");

  assert.equal(librarySource.includes("isCreating"), true);
  assert.equal(librarySource.includes("deleting"), true);
  assert.equal(librarySource.includes("createCharacter"), true);
  assert.equal(librarySource.includes("createLocation"), true);
  assert.equal(librarySource.includes("createLoreEntry"), true);
  assert.equal(librarySource.includes("deleteCharacter"), true);
  assert.equal(librarySource.includes("deleteLocation"), true);
  assert.equal(librarySource.includes("deleteLoreEntry"), true);
  assert.equal(librarySource.includes("window.confirm"), true);
  assert.equal(librarySource.includes("新建资料"), true);
  assert.equal(librarySource.includes("删除当前"), true);
});

test("lore library page exposes more character fields and lore priority through shared contracts", async () => {
  const librarySource = await readFile(loreLibraryPagePath, "utf8");

  assert.equal(librarySource.includes("appearance"), true);
  assert.equal(librarySource.includes("background"), true);
  assert.equal(librarySource.includes("motivation"), true);
  assert.equal(librarySource.includes("speaking_style"), true);
  assert.equal(librarySource.includes("secrets"), true);
  assert.equal(librarySource.includes("priority"), true);
  assert.equal(librarySource.includes("外观"), true);
  assert.equal(librarySource.includes("背景"), true);
  assert.equal(librarySource.includes("动机"), true);
  assert.equal(librarySource.includes("说话风格"), true);
  assert.equal(librarySource.includes("秘密"), true);
  assert.equal(librarySource.includes("优先级"), true);
});
