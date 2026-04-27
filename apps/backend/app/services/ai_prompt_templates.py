from app.models.character import Character
from app.models.location import Location
from app.models.scene import Scene
from app.schemas.scene_revise import ReviseMode

ANALYZE_SCENE_PROMPT_VERSION = "analyze-scene.v5"
WRITE_SCENE_PROMPT_VERSION = "write-scene.v5"
REVISE_SCENE_PROMPT_VERSION = "revise-scene.v4"

MODE_LABELS = {
    "trim": "精简节奏",
    "literary": "文学润色",
    "unify": "统一文风",
}

MODE_INSTRUCTIONS = {
    "trim": "删除重复表达和松散句子，保留情节推进、人物动作和必要情绪，不要改剧情事实。",
    "literary": "增强画面感、节奏和情绪感染力，但不要改剧情事实，不要加入解释性总结。",
    "unify": "统一叙述语气、措辞和视角，让文字更顺滑，但不要加入新设定或额外剧情。",
}

LENGTH_HINTS = {
    "short": "控制在 300 到 500 字，快速推进当前场景。",
    "medium": "控制在 600 到 900 字，兼顾推进、描写和对白。",
    "long": "控制在 1000 到 1500 字，充分展开动作、情绪和场景氛围。",
}


def stringify_list(value: list | None) -> str:
    if not value:
        return "无"
    items = [str(item).strip() for item in value if str(item).strip()]
    return "；".join(items) if items else "无"


def clip_context(value: str | None, fallback: str, limit: int) -> str:
    text = (value or "").strip()
    if not text:
        return fallback
    return " ".join(text.split())[:limit]


def build_context_block(pov: Character | None, location: Location | None) -> str:
    return "\n".join(
        [
            "人物与地点上下文：",
            f"- 视角人物：{clip_context(pov.name if pov else None, '未知', 40)}",
            f"- 人物性格：{clip_context(pov.personality if pov else None, '未知', 60)}",
            f"- 说话风格：{clip_context(pov.speaking_style if pov else None, '未知', 60)}",
            f"- 当前状态：{clip_context(pov.status if pov else None, '未知', 60)}",
            f"- 场景地点：{clip_context(location.name if location else None, '未知', 40)}",
            f"- 地点描述：{clip_context(location.description if location else None, '未知', 80)}",
        ]
    )


def build_analysis_prompt(scene: Scene) -> str:
    return f"""
你是小说场景分析 Agent，只能输出一个合法 JSON 对象。

硬性要求：
- 只能返回 JSON，不能返回解释、点评、前言、后记、Markdown、代码块或列表。
- 不要续写剧情，不要说“这个故事展现了”“如果需要可以继续”等泛化句子。
- 如果某项没有内容，也必须返回空数组或 null，而不是自然语言解释。

JSON 顶层字段必须严格是：
- summary: string
- scene_goal_detected: string | null
- emotional_flow: string[]
- problems: array
- suggestions: string[]

problems 每项必须严格包含：
- type: pacing | consistency | character | logic
- severity: low | medium | high
- message: string

返回格式示例：
{{
  "summary": "一句话概括当前场景在发生什么",
  "scene_goal_detected": "主角当前目标，没有则为 null",
  "emotional_flow": ["情绪1", "情绪2"],
  "problems": [
    {{
      "type": "logic",
      "severity": "medium",
      "message": "这里填写具体问题"
    }}
  ],
  "suggestions": ["这里填写具体可执行建议"]
}}

场景标题：
{scene.title or "未命名场景"}

场景正文：
{(scene.draft_text or "").strip() or "（空）"}
""".strip()


def build_write_prompt(
    scene: Scene,
    *,
    context_block: str,
    knowledge_block: str,
    length: str,
    guidance: list[str],
) -> str:
    return f"""
你是小说正文写作 Agent。你的任务是根据场景信息输出一段可直接放进正文的中文小说文本。

硬性要求：
- 只能输出正文，不要解释、总结、标题、列表、代码块或写作建议。
- 不要写“下面是正文”“这个故事展现了”“如果需要可以继续”等说明性句子。
- 必须遵守 must_include 和 must_avoid。
- 保持当前 POV、人物关系和场景事实，不要擅自补新设定。

写作上下文：
{context_block}

记忆检索结果：
{knowledge_block}

场景标题：{scene.title or "未命名场景"}
场景目标：{scene.goal or "未设置"}
场景冲突：{scene.conflict or "未设置"}
场景结果：{scene.outcome or "未设置"}
必须包含：{stringify_list(scene.must_include)}
必须避免：{stringify_list(scene.must_avoid)}
额外指导：{stringify_list(guidance)}
长度要求：{LENGTH_HINTS[length]}

当前草稿：
{(scene.draft_text or "").strip() or "（空）"}
""".strip()


def build_revise_prompt(scene: Scene, *, mode: ReviseMode, context_block: str) -> str:
    return f"""
你是小说润色 Agent。你的任务是在不改变剧情事实的前提下，对下面这段正文做最小必要润色。

润色模式：{MODE_LABELS[mode]}
润色要求：{MODE_INSTRUCTIONS[mode]}

硬性要求：
- 只能返回润色后的正文，不要解释、总结、标题、列表或改写说明。
- 不要新增剧情事实、人物设定、地点设定或世界观信息。
- 保持原 POV、时态和语言风格，不要跑偏成说明文。

上下文：
{context_block}

待润色正文：
{(scene.draft_text or "").strip() or "（空）"}
""".strip()
