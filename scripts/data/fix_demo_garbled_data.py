from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any
from uuid import UUID


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "fastapi" / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.db.base  # noqa: F401,E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.character import Character  # noqa: E402
from app.models.location import Location  # noqa: E402
from app.models.scene import Scene  # noqa: E402


MOJIBAKE_MARKERS = set("聛聙聜聮聼聺聴聦聧茫盲氓莽猫忙茅镛驴麓卤虏露聢")

DEMO_SCENE_ID = UUID("b816b1bd-96b8-486e-a56b-4a26b396b562")
DEMO_CHARACTER_ID = UUID("f9f170ce-df53-4bc4-b3b8-b2d1f6f1eb26")
DEMO_LOCATION_ID = UUID("dba545f5-ae17-4ef3-88d1-e17e4557bc26")


SCENE_FIX = {
    "title": "雾港旧站夜巡",
    "time_label": "第三纪元·雨夜",
    "goal": "米拉在夜巡中确认异常回响的来源。",
    "conflict": "旧站深处不断传来回声，她必须在暴露之前判断那是不是诱饵。",
    "outcome": "米拉锁定了异响来自站台下层，也意识到有人先一步埋伏在旧站。",
    "must_include": ["旧站站台", "潮湿铁轨", "异常回响"],
    "must_avoid": ["现代热武器", "脱离视角的上帝旁白"],
    "draft_text": (
        "雾港旧站的雨水顺着锈轨往下淌，站台边缘积着一层冷亮的薄光。米拉沿着湿滑的警戒线慢慢前行，"
        "靴底每一次落下，都能听见铁轨深处传来迟钝的回声。那声音不像风，也不像空站常见的管道震颤，"
        "更像是有人故意敲出来给她听的信号。\n\n"
        "她停在塌陷的候车棚前，没有立刻下判断，只是把呼吸压得更稳。雨声之外，回响又一次从站台下层翻上来，"
        "带着短促而克制的节奏。米拉意识到自己不是在追一场偶然的异动，而是在一步步走进别人提前布好的局。"
    ),
}

CHARACTER_FIX = {
    "name": "米拉",
    "aliases": "守夜人米拉",
    "appearance": "黑色短发，常穿防雨长外套，右手手背有一道浅色旧伤。",
    "personality": "冷静、克制、警觉，习惯先观察再行动。",
    "background": "长期负责雾港外围夜巡，熟悉旧站与港区的隐蔽路线。",
    "motivation": "她想先一步查清异常信号背后的埋伏者，避免同伴被卷入。",
    "speaking_style": "简短、直接，不轻易泄露判断。",
    "status": "执行夜巡任务中",
    "secrets": "她比任何人都更熟悉旧站下层曾经发生过什么。",
}

LOCATION_FIX = {
    "name": "雾港旧站",
    "description": "一座长期废弃的临海旧站，站台塌陷、铁轨生锈，雨夜里回声格外清晰。",
}


def looks_garbled(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if "\ufffd" in value:
        return True
    return any(ch in MOJIBAKE_MARKERS for ch in value)


def should_replace(current: Any) -> bool:
    if current is None:
        return True
    if isinstance(current, list):
        return not current or any(looks_garbled(item) for item in current if isinstance(item, str))
    if isinstance(current, str):
        return current.strip() == "" or looks_garbled(current)
    return False


def apply_mapping(obj: Any, mapping: dict[str, Any]) -> list[str]:
    changed: list[str] = []
    for field, replacement in mapping.items():
        current = getattr(obj, field)
        if should_replace(current):
            setattr(obj, field, replacement)
            changed.append(field)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix known garbled demo records without touching general user data.")
    parser.add_argument("--apply", action="store_true", help="Persist the demo-data fixes.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        scene = db.query(Scene).filter(Scene.id == DEMO_SCENE_ID).first()
        character = db.query(Character).filter(Character.id == DEMO_CHARACTER_ID).first()
        location = db.query(Location).filter(Location.id == DEMO_LOCATION_ID).first()

        if scene is None or character is None or location is None:
            print("Demo records not found. No changes made.")
            return 1

        changes = {
          "scene": apply_mapping(scene, SCENE_FIX),
          "character": apply_mapping(character, CHARACTER_FIX),
          "location": apply_mapping(location, LOCATION_FIX),
        }

        if not any(changes.values()):
            print("Demo records already look readable. No changes needed.")
            db.rollback()
            return 0

        for key, fields in changes.items():
            if fields:
                print(f"{key}: {', '.join(fields)}")

        if args.apply:
            db.add(scene)
            db.add(character)
            db.add(location)
            db.commit()
            print("Applied demo data fixes.")
        else:
            db.rollback()
            print("Dry run only. Re-run with --apply to persist these fixes.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
