"use client";

import { useState } from "react";
import type { AnalysisResult, AnalysisStore } from "@/features/editor/hooks/use-scene-context";

export type LengthMode = "short" | "medium" | "long";
export type ReviseMode = "trim" | "literary" | "unify";
export type ApplyMode = "strict" | "manual";
export type SceneStatus = "" | "draft" | "generated" | "analyzed" | "revision_ready";

export function useAuthoringWorkspace() {
  const [sceneId, setSceneId] = useState("b816b1bd-96b8-486e-a56b-4a26b396b562");
  const [title, setTitle] = useState("");
  const [status, setStatus] = useState<SceneStatus>("");
  const [draft, setDraft] = useState("");
  const [lengthMode, setLengthMode] = useState<LengthMode>("medium");
  const [reviseMode, setReviseMode] = useState<ReviseMode>("trim");
  const [applyMode, setApplyMode] = useState<ApplyMode>("strict");
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [analysisStore, setAnalysisStore] = useState<AnalysisStore | null>(null);
  const [generatedDraft, setGeneratedDraft] = useState("");
  const [generatedNotes, setGeneratedNotes] = useState<string[]>([]);
  const [revisedDraft, setRevisedDraft] = useState("");
  const [revisionBase, setRevisionBase] = useState("");
  const [revisionNotes, setRevisionNotes] = useState<string[]>([]);

  return {
    sceneId,
    title,
    status,
    draft,
    lengthMode,
    reviseMode,
    applyMode,
    analysis,
    analysisStore,
    generatedDraft,
    generatedNotes,
    revisedDraft,
    revisionBase,
    revisionNotes,
    setSceneId,
    setTitle,
    setStatus,
    setDraft,
    setLengthMode,
    setReviseMode,
    setApplyMode,
    setAnalysis,
    setAnalysisStore,
    setGeneratedDraft,
    setGeneratedNotes,
    setRevisedDraft,
    setRevisionBase,
    setRevisionNotes,
  };
}
