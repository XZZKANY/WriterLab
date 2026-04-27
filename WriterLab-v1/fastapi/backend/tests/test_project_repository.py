"""project_repository 直测。

聚焦低复杂度 / 高价值的入口：
- _collect_ids 收集主键的查询代理
- get_project_overview 的 dict 组装与 counts 求和
- delete_project 在 project 不存在时的提前 return False

`delete_project` 的级联清理涉及十多个 model + SQLAlchemy `or_` / `.in_` /
`.delete(synchronize_session=False)` 等内部机制，FakeDB 难以忠实模拟，价值
有限，故不在此覆盖；可由集成测试或 `tests/api/api_routes_suite.py` 中
现有的 `test_project_delete_endpoint` 间接守护。
"""

from types import SimpleNamespace
from uuid import UUID

from app.repositories import project_repository as repo


# ---------- 辅助 fake ----------

class _Query:
    def __init__(self, items):
        self._items = list(items)

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._items[0] if self._items else None

    def all(self):
        return list(self._items)


class _RoutingDB:
    """根据 model.__name__ 路由到预备列表。"""

    def __init__(self, by_model: dict | None = None):
        self._by_model = by_model or {}

    def query(self, model_or_column):
        # 处理 column（如 Book.id）：取其 class 名
        target = getattr(model_or_column, "__name__", None)
        if target is None:
            target = type(model_or_column).__name__
            # 还是不行就走对象的 class.parent 名
            if target == "InstrumentedAttribute":
                target = model_or_column.parent.entity.__name__
        return _Query(self._by_model.get(target, []))

    def delete(self, obj):
        pass

    def commit(self):
        pass


# ---------- _collect_ids ----------

def test_collect_ids_extracts_first_tuple_element():
    """_collect_ids 期望 query.all() 返回 [(id,), ...] 形式，提取每行第 0 元素。"""
    rows = [
        (UUID("11111111-1111-1111-1111-111111111111"),),
        (UUID("22222222-2222-2222-2222-222222222222"),),
    ]

    class _StubDB:
        def query(self, column):
            return _Query(rows)

    out = repo._collect_ids(_StubDB(), object())
    assert out == [
        UUID("11111111-1111-1111-1111-111111111111"),
        UUID("22222222-2222-2222-2222-222222222222"),
    ]


def test_collect_ids_handles_empty_result():
    class _StubDB:
        def query(self, column):
            return _Query([])

    assert repo._collect_ids(_StubDB(), object()) == []


# ---------- get_project_overview ----------

def test_get_project_overview_returns_none_when_project_missing():
    db = _RoutingDB()  # Project 列表空
    assert repo.get_project_overview(db, UUID("11111111-1111-1111-1111-111111111111")) is None


def test_get_project_overview_assembles_full_dict_with_counts():
    project_id = UUID("11111111-1111-1111-1111-111111111111")
    book_id = UUID("22222222-2222-2222-2222-222222222222")
    chapter_id = UUID("33333333-3333-3333-3333-333333333333")
    scene_id = UUID("44444444-4444-4444-4444-444444444444")

    project = SimpleNamespace(
        id=project_id, name="P", description=None, genre=None,
        default_language="zh-CN",
        created_at=__import__("datetime").datetime.utcnow(),
        updated_at=__import__("datetime").datetime.utcnow(),
    )
    book = SimpleNamespace(id=book_id, project_id=project_id, title="B")
    chapter = SimpleNamespace(id=chapter_id, book_id=book_id, chapter_no=1, title="C")
    scene = SimpleNamespace(id=scene_id, chapter_id=chapter_id, scene_no=1, title="S")

    db = _RoutingDB(
        by_model={
            "Project": [project],
            "Book": [book],
            "Chapter": [chapter],
            "Scene": [scene],
        }
    )
    out = repo.get_project_overview(db, project_id)
    assert out is not None
    assert out["project"] is project
    assert out["books"] == [book]
    assert out["chapters_by_book"][str(book_id)] == [chapter]
    assert out["scenes_by_chapter"][str(chapter_id)] == [scene]
    assert out["counts"] == {"books": 1, "chapters": 1, "scenes": 1}


def test_get_project_overview_counts_zero_when_empty():
    project_id = UUID("11111111-1111-1111-1111-111111111111")
    project = SimpleNamespace(
        id=project_id,
        created_at=__import__("datetime").datetime.utcnow(),
        updated_at=__import__("datetime").datetime.utcnow(),
    )
    db = _RoutingDB(by_model={"Project": [project]})
    out = repo.get_project_overview(db, project_id)
    assert out is not None
    assert out["counts"] == {"books": 0, "chapters": 0, "scenes": 0}
    assert out["chapters_by_book"] == {}
    assert out["scenes_by_chapter"] == {}


def test_get_project_overview_aggregates_multiple_books_and_chapters():
    project_id = UUID("11111111-1111-1111-1111-111111111111")
    book_a = SimpleNamespace(id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
    book_b = SimpleNamespace(id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"))
    chapter_1 = SimpleNamespace(id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"))
    chapter_2 = SimpleNamespace(id=UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"))
    chapter_3 = SimpleNamespace(id=UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"))

    project = SimpleNamespace(
        id=project_id,
        created_at=__import__("datetime").datetime.utcnow(),
        updated_at=__import__("datetime").datetime.utcnow(),
    )

    # 简化：两个 books 共享同一份 chapters 列表（fake DB 不区分 filter），
    # 共享同一份 scenes（每个 chapter 复用同一份 scenes 列表）。
    # counts 验证：books=2, chapters=2*3=6, scenes 取决于每章 scene 数。
    scenes = [SimpleNamespace(id=UUID(f"00000000-0000-0000-0000-{i:012d}")) for i in range(2)]
    db = _RoutingDB(
        by_model={
            "Project": [project],
            "Book": [book_a, book_b],
            "Chapter": [chapter_1, chapter_2, chapter_3],
            "Scene": scenes,
        }
    )
    out = repo.get_project_overview(db, project_id)
    assert out["counts"]["books"] == 2
    # 每个 book 都拿到 3 个 chapter（fake 简化）→ 总 6（chapters_by_book 是按 book.id 分的）
    assert out["counts"]["chapters"] == 6
    # scenes_by_chapter 用 chapter.id 做 key，不同 book 下相同 chapter.id 会去重，
    # 所以 fake 共用 chapters 时 scene 总数 = unique_chapters * scenes_per_chapter = 3 * 2 = 6
    assert out["counts"]["scenes"] == 6


# ---------- delete_project：仅测 not-found 短路 ----------

def test_delete_project_returns_false_when_project_missing():
    """级联清理逻辑由集成测试守护；这里只测 project 不存在时安全 short-circuit。"""

    class _StubDB:
        def query(self, model):
            return _Query([])

        def delete(self, obj):
            raise AssertionError("不应进入 delete 分支")

        def commit(self):
            raise AssertionError("不应触发 commit")

    assert repo.delete_project(_StubDB(), UUID("99999999-9999-9999-9999-999999999999")) is False


# ---------- list_books_by_project / list_chapters_by_book ----------

def test_list_books_by_project_proxies_query():
    book = SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"))
    db = _RoutingDB(by_model={"Book": [book]})
    out = repo.list_books_by_project(db, UUID("99999999-9999-9999-9999-999999999999"))
    assert out == [book]


def test_list_chapters_by_book_proxies_query():
    chapter = SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"))
    db = _RoutingDB(by_model={"Chapter": [chapter]})
    out = repo.list_chapters_by_book(db, UUID("99999999-9999-9999-9999-999999999999"))
    assert out == [chapter]


# ---------- list_projects ----------

def test_list_projects_returns_query_results():
    proj = SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"))
    db = _RoutingDB(by_model={"Project": [proj]})
    out = repo.list_projects(db)
    assert out == [proj]
