import re

from app.schemas.vn_export import VNDialogueLine, VNExportResponse


LINE_PATTERN = re.compile(r"^\s*([^\s:：\[\(]+?)\s*(?:\(([^)]+)\)|\[([^\]]+)\])?\s*[:：]\s*(.+)$")


def export_vn_script(draft_text: str, *, scene_title: str | None = None, include_image_prompts: bool = True) -> VNExportResponse:
    lines: list[VNDialogueLine] = []
    markdown_lines: list[str] = []

    for raw_line in (draft_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = LINE_PATTERN.match(line)
        if match:
            character = match.group(1)
            expression = match.group(2) or match.group(3)
            text = match.group(4).strip()
            lines.append(VNDialogueLine(kind="dialogue", character=character, expression=expression, text=text))
            prefix = f"[{character}]"
            if expression:
                prefix = f"{prefix}[{expression}]"
            markdown_lines.append(f"{prefix} {text}")
        else:
            lines.append(VNDialogueLine(kind="narration", text=line))
            markdown_lines.append(f"NARRATION: {line}")

    image_prompts: list[str] = []
    if include_image_prompts:
        narration = [item.text for item in lines if item.kind == "narration"][:3]
        dialogue_characters = [item.character for item in lines if item.kind == "dialogue" and item.character][:3]
        scene_bits = [bit for bit in [scene_title, ", ".join(dialogue_characters), " ".join(narration)] if bit]
        if scene_bits:
            image_prompts.append(
                "cinematic visual novel illustration, " + ", ".join(scene_bits)
            )

    return VNExportResponse(
        title=scene_title,
        lines=lines,
        markdown_script="\n".join(markdown_lines),
        image_prompts=image_prompts,
    )
