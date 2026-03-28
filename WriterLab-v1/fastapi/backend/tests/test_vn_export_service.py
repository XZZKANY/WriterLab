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
