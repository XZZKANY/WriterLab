from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SceneProblem(BaseModel):
    type: Literal["pacing", "consistency", "character", "logic"]
    severity: Literal["low", "medium", "high"]
    message: str


class SceneAnalysisResult(BaseModel):
    summary: str = ""
    scene_goal_detected: str | None = None
    emotional_flow: list[str] = Field(default_factory=list)
    problems: list[SceneProblem] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class AnalyzeSceneRequest(BaseModel):
    scene_id: UUID


class AnalyzeSceneSuccessResponse(BaseModel):
    success: Literal[True] = True
    data: SceneAnalysisResult
    run_id: UUID


class AnalyzeSceneErrorResponse(BaseModel):
    success: Literal[False] = False
    error_type: str
    message: str
    run_id: UUID | None = None


class AnalyzeSceneResponse(BaseModel):
    success: bool
    data: SceneAnalysisResult | None = None
    run_id: UUID | None = None
    analysis_id: UUID | None = None
    error_type: str | None = None
    message: str | None = None
