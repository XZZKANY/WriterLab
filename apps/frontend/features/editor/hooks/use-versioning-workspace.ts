"use client";

import { useMemo, useState } from "react";

export type DiffRow = { type: "add" | "remove" | "context"; text: string };

export type SceneVersion = {
  id: string;
  content: string;
  source: "manual" | "write" | "revise" | "restore" | "workflow";
  label: string | null;
  created_at: string;
};

export type Branch = { id: string; name: string; updated_at: string };

export type BranchDiff = {
  branch_name?: string | null;
  source_chapter_id?: string | null;
  source_version_label?: string | null;
  latest_version_label?: string | null;
  base_text?: string | null;
  branch_text?: string | null;
  diff_rows?: DiffRow[];
};

function makeDiffRows(beforeText: string, afterText: string) {
  const before = beforeText.split("\n");
  const after = afterText.split("\n");
  const rows: DiffRow[] = [];
  const max = Math.max(before.length, after.length);

  for (let index = 0; index < max; index += 1) {
    if ((before[index] ?? "") === (after[index] ?? "")) {
      rows.push({ type: "context", text: before[index] ?? "" });
    } else {
      if (before[index] !== undefined) rows.push({ type: "remove", text: before[index] });
      if (after[index] !== undefined) rows.push({ type: "add", text: after[index] });
    }
  }

  return rows;
}

export function useVersioningWorkspace() {
  const [versions, setVersions] = useState<SceneVersion[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState("");
  const [compareVersionId, setCompareVersionId] = useState("");
  const [branches, setBranches] = useState<Branch[]>([]);
  const [selectedBranchId, setSelectedBranchId] = useState("");
  const [branchDiff, setBranchDiff] = useState<BranchDiff | null>(null);
  const [branchName, setBranchName] = useState("");
  const [branchDescription, setBranchDescription] = useState("");

  const selectedVersion = useMemo(
    () => versions.find((item) => item.id === selectedVersionId) ?? null,
    [selectedVersionId, versions],
  );
  const compareVersion = useMemo(
    () => versions.find((item) => item.id === compareVersionId) ?? null,
    [compareVersionId, versions],
  );
  const versionDiffRows = useMemo(
    () =>
      selectedVersion && compareVersion
        ? makeDiffRows(compareVersion.content, selectedVersion.content)
        : [],
    [compareVersion, selectedVersion],
  );

  return {
    versions,
    selectedVersionId,
    compareVersionId,
    branches,
    selectedBranchId,
    branchDiff,
    branchName,
    branchDescription,
    selectedVersion,
    compareVersion,
    versionDiffRows,
    setVersions,
    setSelectedVersionId,
    setCompareVersionId,
    setBranches,
    setSelectedBranchId,
    setBranchDiff,
    setBranchName,
    setBranchDescription,
  };
}
