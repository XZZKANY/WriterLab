"""POST /api/scenes 路由的回归用例。

修复一个真实 bug：app/api/scenes.py 第 26 行用了 `Scene(...)` 但模块顶部没 import `Scene`；
任何创建场景的真实调用都会抛 `NameError: name 'Scene' is not defined`。
此用例守住"导入存在 + 路由能跑通到 db.add(scene)"这一最低契约。
"""

from datetime import datetime
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.scenes import router as scenes_router
from app.db.session import get_db


def test_post_scenes_resolves_scene_orm_class(monkeypatch):
    app = FastAPI()
    app.include_router(scenes_router)

    chapter_id = UUID("11111111-1111-1111-1111-111111111111")
    scene_id = UUID("22222222-2222-2222-2222-222222222222")

    captured: dict = {"added": None}

    class _FakeDB:
        def add(self, obj):
            captured["added"] = obj

        def commit(self):
            pass

        def refresh(self, obj):
            # 模拟 SQLAlchemy 给 ORM 行写回主键和时间戳。
            obj.id = scene_id
            obj.created_at = datetime.utcnow()
            obj.updated_at = datetime.utcnow()
            obj.scene_version = obj.scene_version or 1

    app.dependency_overrides[get_db] = lambda: _FakeDB()
    # 路由在创建场景后会顺手写一个版本快照；这里短路掉。
    monkeypatch.setattr("app.api.scenes.create_scene_version", lambda *args, **kwargs: None)

    client = TestClient(app)
    response = client.post(
        "/api/scenes",
        json={
            "chapter_id": str(chapter_id),
            "scene_no": 7,
            "title": "回归用场景",
            "draft_text": "正文内容",
        },
    )

    # 路由必须正常返回 200；之前 Scene 未导入会抛 NameError 直接变 500。
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["title"] == "回归用场景"
    assert payload["scene_no"] == 7
    # 确认 ORM 实例确实创建并持有传入字段。
    assert captured["added"] is not None
    assert captured["added"].title == "回归用场景"
    assert captured["added"].chapter_id == chapter_id
