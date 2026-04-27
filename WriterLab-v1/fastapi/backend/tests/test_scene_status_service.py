"""scene_status_service 直测。

该模块极小（11 行）：4 个 status 常量 + 1 个 mark 函数。被 api/ai.py 等调用方依赖
"SCENE_STATUS_*" 这些字面量与 Scene.status 字段对齐。
"""

from types import SimpleNamespace

from app.services import scene_status_service as ss


def test_status_constants_are_lowercased_known_values():
    # 这些字面量是前端 sceneLabel / 后端各处共用的 contract，不应该乱改。
    assert ss.SCENE_STATUS_DRAFT == "draft"
    assert ss.SCENE_STATUS_GENERATED == "generated"
    assert ss.SCENE_STATUS_ANALYZED == "analyzed"
    assert ss.SCENE_STATUS_REVISION_READY == "revision_ready"


def test_mark_scene_status_writes_to_scene_status_attribute():
    scene = SimpleNamespace(status="")
    ss.mark_scene_status(scene, ss.SCENE_STATUS_GENERATED)
    assert scene.status == "generated"


def test_mark_scene_status_overwrites_existing_value():
    scene = SimpleNamespace(status="draft")
    ss.mark_scene_status(scene, ss.SCENE_STATUS_REVISION_READY)
    assert scene.status == "revision_ready"


def test_mark_scene_status_does_not_persist_internally():
    # 本函数只改对象属性，不维护任何模块级缓存；多次调用相互独立。
    scene_a = SimpleNamespace(status="")
    scene_b = SimpleNamespace(status="")
    ss.mark_scene_status(scene_a, "draft")
    ss.mark_scene_status(scene_b, "analyzed")
    assert scene_a.status == "draft"
    assert scene_b.status == "analyzed"
