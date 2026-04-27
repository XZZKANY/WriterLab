"""工作流 prompt 与候选文本拼接。

承接来自 workflow_service.py 的纯字符串组装函数：
- _planner_prompt: 给规划 step 喂的 prompt
- _style_prompt: 给 style step 喂的 prompt
- _build_memory_candidate: 风格记忆候选的正文与规则列表
"""

from __future__ import annotations

from app.models.scene import Scene
from app.schemas.workflow import WorkflowSceneRequest


def _planner_prompt(scene: Scene, bundle: dict, guidance: list[str]) -> str:
    return "\n".join(
        [
            f"Scene title: {scene.title}",
            f"Goal: {scene.goal or ''}",
            f"Conflict: {scene.conflict or ''}",
            f"Outcome target: {scene.outcome or ''}",
            f"Guidance: {guidance}",
            f"Recent scenes: {bundle.get('recent_scenes', [])}",
            f"Lore constraints: {[item.title for item in bundle.get('lore_constraints', [])]}",
            "Produce a concise plan.",
        ]
    )


def _style_prompt(scene: Scene, draft_text: str, bundle: dict) -> str:
    return "\n".join(
        [
            "Rewrite the following scene prose while preserving continuity.",
            f"Scene title: {scene.title}",
            f"Must include: {scene.must_include or []}",
            f"Must avoid: {scene.must_avoid or []}",
            f"Style memory: {[item.content for item in bundle.get('style_memories', [])]}",
            "Return only scene prose.",
            draft_text,
        ]
    )


def _build_memory_candidate(
    scene: Scene, payload: WorkflowSceneRequest, final_text: str
) -> tuple[str, list[str]]:
    guidance_rules = [item.strip() for item in payload.guidance if item and item.strip()]
    if guidance_rules:
        return (
            f"Workflow style candidate for {scene.title or 'scene'}: "
            + " | ".join(guidance_rules[:4]),
            guidance_rules[:6],
        )
    return (
        f"Workflow style candidate for {scene.title or 'scene'} based on accepted draft tone.",
        [
            "Use 中文小说正文 cadence instead of commentary.",
            "Avoid overexplaining motivations in narration.",
        ],
    )
