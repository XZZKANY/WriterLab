from app.services.vn_export_service import export_vn_script


def test_export_vn_script_extracts_dialogue_and_image_prompt():
    payload = "Ava(smile): Welcome home.\nThe room glows with warm lantern light."
    exported = export_vn_script(payload, scene_title="Homecoming", include_image_prompts=True)
    assert exported.lines[0].kind == "dialogue"
    assert exported.lines[0].character == "Ava"
    assert exported.lines[0].expression == "smile"
    assert exported.lines[1].kind == "narration"
    assert exported.image_prompts
    assert "Homecoming" in exported.image_prompts[0]


def test_export_vn_script_handles_empty_text():
    exported = export_vn_script("", scene_title=None)
    assert exported.lines == []
    assert exported.markdown_script == ""
    assert exported.image_prompts == []
    assert exported.title is None


def test_export_vn_script_skips_blank_lines():
    exported = export_vn_script("\n   \n\nA: hi\n\n", include_image_prompts=False)
    assert len(exported.lines) == 1
    assert exported.lines[0].kind == "dialogue"
    assert exported.lines[0].character == "A"
    assert exported.lines[0].text == "hi"


def test_export_vn_script_supports_chinese_colon_separator():
    # 全角冒号必须与 ASCII ':' 等价工作。
    exported = export_vn_script("林雨：你回来了。", include_image_prompts=False)
    assert exported.lines[0].kind == "dialogue"
    assert exported.lines[0].character == "林雨"
    assert exported.lines[0].text == "你回来了。"


def test_export_vn_script_supports_bracket_expression_marker():
    # `[expression]` 与 `(expression)` 两种写法都应能识别为 expression。
    exported = export_vn_script("Ava[angry]: stop it.", include_image_prompts=False)
    assert exported.lines[0].kind == "dialogue"
    assert exported.lines[0].expression == "angry"
    assert exported.lines[0].text == "stop it."


def test_export_vn_script_pure_narration_has_no_dialogue():
    exported = export_vn_script("The wind howled outside.\nA candle flickered.", include_image_prompts=False)
    assert all(item.kind == "narration" for item in exported.lines)
    assert "NARRATION: The wind howled outside." in exported.markdown_script


def test_export_vn_script_skips_image_prompts_when_flag_false():
    payload = "Ava: Hello.\nA quiet hallway."
    exported = export_vn_script(payload, scene_title="Doorway", include_image_prompts=False)
    assert exported.image_prompts == []


def test_export_vn_script_image_prompt_includes_first_three_narrations():
    # 当 narration 多于 3 条时，image_prompt 仅引用前 3 条。
    lines = "\n".join(f"narration line {i}" for i in range(5)) + "\nAva: hi"
    exported = export_vn_script(lines, scene_title="Many", include_image_prompts=True)
    prompt = exported.image_prompts[0]
    assert "narration line 0" in prompt
    assert "narration line 2" in prompt
    assert "narration line 4" not in prompt
    assert "Ava" in prompt


def test_export_vn_script_image_prompt_skipped_when_no_payload():
    # 即使 include_image_prompts=True，没有可用片段时也不应硬塞空字符串。
    exported = export_vn_script("", include_image_prompts=True)
    assert exported.image_prompts == []


def test_export_vn_script_markdown_includes_expression_prefix():
    exported = export_vn_script("Ava(smile): hello", include_image_prompts=False)
    assert "[Ava][smile] hello" in exported.markdown_script
