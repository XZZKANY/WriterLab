# WriterLab 阶段一后端数据基础收口 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 稳定 WriterLab 的项目、书籍、章节、场景四层核心数据链路，为前端项目入口和后续资料域迭代提供可靠后端契约。

**Architecture:** 以 FastAPI 现有 `router + repository + schema + service` 分层为基础，先用 pytest 锁定后端契约，再增加项目概览聚合接口，随后让前端 `project` 工作区消费这个稳定接口，最后补齐前后端结构验证和文档留痕。该计划只覆盖中期蓝图的阶段一，资料域、时间线/版本、workflow/context 后续单独起 plan。

**Tech Stack:** FastAPI、SQLAlchemy、Pydantic、pytest、Next.js 16、React 19、TypeScript、node:test

---

## 文件结构与职责

- `D:/WritierLab/WriterLab-v1/fastapi/backend/app/api/projects.py`
  - 增加项目概览读取接口，保留项目创建、列表、删除入口。
- `D:/WritierLab/WriterLab-v1/fastapi/backend/app/repositories/project_repository.py`
  - 增加项目结构聚合查询，继续作为项目、书籍、章节聚合读取和删除清理的主仓储。
- `D:/WritierLab/WriterLab-v1/fastapi/backend/app/schemas/project.py`
  - 新增项目概览响应模型。
- `D:/WritierLab/WriterLab-v1/fastapi/backend/tests/test_project_scene_contracts.py`
  - 新建。锁定项目概览、项目删除、场景更新与版本冲突的后端契约。
- `D:/WritierLab/WriterLab-v1/Next.js/frontend/lib/api/projects.ts`
  - 新增项目概览 API 客户端。
- `D:/WritierLab/WriterLab-v1/Next.js/frontend/features/project/project-detail.tsx`
  - 从多次串行读取改为优先消费项目概览接口。
- `D:/WritierLab/WriterLab-v1/Next.js/frontend/features/project/project-hub.tsx`
  - 与新的项目概览和删除契约对齐，确保入口提示与错误语义一致。
- `D:/WritierLab/WriterLab-v1/Next.js/frontend/tests/features/project-detail-contract.test.mjs`
  - 新建。锁定前端项目详情页必须消费概览 API，而不是继续在页面里做 books/chapters/scenes 的 N+1 读取。
- `D:/WritierLab/docs/superpowers/specs/2026-04-06-writerlab-multi-track-backend-first-design.md`
  - 作为本计划的规格输入。
- `D:/WritierLab/.codex/operations-log.md`
  - 记录实现决策和验证结果。

## Scope Check

当前中期蓝图覆盖多个独立子系统，不适合一次性写成一个可直接执行的超级计划。本计划只实现蓝图的“阶段一：项目与场景主数据稳定化”。资料域、时间线/版本、workflow/context 应分别产出后续计划。

### Task 1: 先锁定阶段一后端契约

**Files:**
- Create: `D:/WritierLab/WriterLab-v1/fastapi/backend/tests/test_project_scene_contracts.py`
- Reference: `D:/WritierLab/WriterLab-v1/fastapi/backend/tests/test_api_routes.py`
- Reference: `D:/WritierLab/WriterLab-v1/fastapi/backend/app/api/projects.py`
- Reference: `D:/WritierLab/WriterLab-v1/fastapi/backend/app/api/scenes.py`

- [ ] **Step 1: 写失败测试，锁定项目概览、删除和场景版本冲突契约**

```python
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_project_overview_returns_books_chapters_scenes_summary():
    project = client.post(
        "/api/projects",
        json={"name": "阶段一项目", "default_language": "zh-CN"},
    ).json()
    book = client.post(
        "/api/books",
        json={"project_id": project["id"], "title": "卷一", "status": "draft"},
    ).json()
    chapter = client.post(
        "/api/chapters",
        json={"book_id": book["id"], "chapter_no": 1, "title": "第一章", "status": "draft"},
    ).json()
    scene = client.post(
        "/api/scenes",
        json={"chapter_id": chapter["id"], "scene_no": 1, "title": "开场", "status": "draft"},
    ).json()

    response = client.get(f"/api/projects/{project['id']}/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["id"] == project["id"]
    assert payload["counts"] == {"books": 1, "chapters": 1, "scenes": 1}
    assert payload["books"][0]["id"] == book["id"]
    assert payload["chapters_by_book"][book["id"]][0]["id"] == chapter["id"]
    assert payload["scenes_by_chapter"][chapter["id"]][0]["id"] == scene["id"]


def test_delete_missing_project_returns_404():
    response = client.delete(f"/api/projects/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}


def test_scene_update_rejects_stale_scene_version():
    project = client.post(
        "/api/projects",
        json={"name": "冲突项目", "default_language": "zh-CN"},
    ).json()
    book = client.post(
        "/api/books",
        json={"project_id": project["id"], "title": "卷一", "status": "draft"},
    ).json()
    chapter = client.post(
        "/api/chapters",
        json={"book_id": book["id"], "chapter_no": 1, "title": "第一章", "status": "draft"},
    ).json()
    scene = client.post(
        "/api/scenes",
        json={"chapter_id": chapter["id"], "scene_no": 1, "title": "开场", "status": "draft", "draft_text": "初稿"},
    ).json()

    response = client.patch(
        f"/api/scenes/{scene['id']}",
        json={"draft_text": "新版本", "expected_scene_version": scene["scene_version"] - 1},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Scene version mismatch"}
```

- [ ] **Step 2: 运行测试，确认当前至少因缺少概览接口而失败**

Run:

```powershell
D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_project_scene_contracts.py -q
```

Expected:

```text
FAILED test_project_overview_returns_books_chapters_scenes_summary
```

- [ ] **Step 3: 提交失败基线**

```bash
git add D:/WritierLab/WriterLab-v1/fastapi/backend/tests/test_project_scene_contracts.py
git commit -m "test: lock phase-1 project scene contracts"
```

### Task 2: 实现项目概览聚合接口

**Files:**
- Modify: `D:/WritierLab/WriterLab-v1/fastapi/backend/app/repositories/project_repository.py`
- Modify: `D:/WritierLab/WriterLab-v1/fastapi/backend/app/schemas/project.py`
- Modify: `D:/WritierLab/WriterLab-v1/fastapi/backend/app/api/projects.py`
- Test: `D:/WritierLab/WriterLab-v1/fastapi/backend/tests/test_project_scene_contracts.py`

- [ ] **Step 1: 在 schema 中定义项目概览响应模型**

```python
class ProjectCountsResponse(BaseModel):
    books: int
    chapters: int
    scenes: int


class ProjectOverviewResponse(BaseModel):
    project: ProjectResponse
    books: list[BookResponse]
    chapters_by_book: dict[str, list[ChapterResponse]]
    scenes_by_chapter: dict[str, list[SceneResponse]]
    counts: ProjectCountsResponse
```

- [ ] **Step 2: 在 repository 中增加聚合查询函数**

```python
def get_project_overview(db: Session, project_id: UUID) -> dict | None:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        return None

    books = list_books_by_project(db, project_id)
    chapters_by_book = {
        str(book.id): list_chapters_by_book(db, book.id)
        for book in books
    }
    scenes_by_chapter = {
        str(chapter.id): list_scenes_by_chapter(db, chapter.id)
        for chapters in chapters_by_book.values()
        for chapter in chapters
    }
    return {
        "project": project,
        "books": books,
        "chapters_by_book": chapters_by_book,
        "scenes_by_chapter": scenes_by_chapter,
        "counts": {
            "books": len(books),
            "chapters": sum(len(items) for items in chapters_by_book.values()),
            "scenes": sum(len(items) for items in scenes_by_chapter.values()),
        },
    }
```

- [ ] **Step 3: 在 projects router 暴露概览接口**

```python
@router.get("/{project_id}/overview", response_model=ProjectOverviewResponse)
def get_project_overview_api(project_id: UUID, db: Session = Depends(get_db)):
    payload = get_project_overview(db, project_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return payload
```

- [ ] **Step 4: 运行后端契约测试，确认通过**

Run:

```powershell
D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_project_scene_contracts.py -q
```

Expected:

```text
3 passed
```

- [ ] **Step 5: 提交后端接口实现**

```bash
git add D:/WritierLab/WriterLab-v1/fastapi/backend/app/repositories/project_repository.py D:/WritierLab/WriterLab-v1/fastapi/backend/app/schemas/project.py D:/WritierLab/WriterLab-v1/fastapi/backend/app/api/projects.py D:/WritierLab/WriterLab-v1/fastapi/backend/tests/test_project_scene_contracts.py
git commit -m "feat: add project overview contract"
```

### Task 3: 收口项目详情前端到稳定概览接口

**Files:**
- Modify: `D:/WritierLab/WriterLab-v1/Next.js/frontend/lib/api/projects.ts`
- Modify: `D:/WritierLab/WriterLab-v1/Next.js/frontend/features/project/project-detail.tsx`
- Create: `D:/WritierLab/WriterLab-v1/Next.js/frontend/tests/features/project-detail-contract.test.mjs`

- [ ] **Step 1: 写失败测试，锁定项目详情页必须消费概览 API**

```js
import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const projectApiPath = new URL("../../lib/api/projects.ts", import.meta.url);
const projectDetailPath = new URL("../../features/project/project-detail.tsx", import.meta.url);

test("project detail reads project overview instead of manual nested fetch chain", async () => {
  const [apiSource, detailSource] = await Promise.all([
    readFile(projectApiPath, "utf8"),
    readFile(projectDetailPath, "utf8"),
  ]);

  assert.equal(apiSource.includes("fetchProjectOverview"), true);
  assert.equal(detailSource.includes("fetchProjectOverview"), true);
  assert.equal(detailSource.includes("fetchBooksByProject"), false);
  assert.equal(detailSource.includes("fetchChaptersByBook"), false);
  assert.equal(detailSource.includes("fetchScenesByChapter"), false);
});
```

- [ ] **Step 2: 运行前端结构测试，确认当前失败**

Run:

```powershell
node --test D:\WritierLab\WriterLab-v1\Next.js\frontend\tests\features\project-detail-contract.test.mjs
```

Expected:

```text
FAIL project detail reads project overview instead of manual nested fetch chain
```

- [ ] **Step 3: 在前端 API 客户端增加概览读取函数**

```ts
export type ProjectOverviewResponse = {
  project: ProjectResponse;
  books: { id: string; title: string; summary?: string | null; status: string }[];
  chapters_by_book: Record<string, { id: string; book_id: string; chapter_no: number; title: string; summary?: string | null; status: string }[]>;
  scenes_by_chapter: Record<string, { id: string; chapter_id: string; scene_no: number; title: string; status?: string | null }[]>;
  counts: { books: number; chapters: number; scenes: number };
};

export function fetchProjectOverview<T>(projectId: string) {
  return apiGet<T>(`/api/projects/${projectId}/overview`, "读取项目概览失败");
}
```

- [ ] **Step 4: 改造项目详情页，使用概览接口单次读取**

```tsx
const overview = await fetchProjectOverview<ProjectOverviewResponse>(projectId);

if (!cancelled) {
  setProject(overview.project);
  setBooks(overview.books);
  setChaptersByBook(overview.chapters_by_book);
  setScenesByChapter(overview.scenes_by_chapter);
  setError(null);
}
```

- [ ] **Step 5: 运行结构测试与类型检查**

Run:

```powershell
node --test D:\WritierLab\WriterLab-v1\Next.js\frontend\tests\features\project-detail-contract.test.mjs
Set-Location D:\WritierLab\WriterLab-v1\Next.js\frontend
npm.cmd run typecheck
```

Expected:

```text
PASS project detail reads project overview instead of manual nested fetch chain
typecheck exits 0
```

- [ ] **Step 6: 提交前端接入**

```bash
git add D:/WritierLab/WriterLab-v1/Next.js/frontend/lib/api/projects.ts D:/WritierLab/WriterLab-v1/Next.js/frontend/features/project/project-detail.tsx D:/WritierLab/WriterLab-v1/Next.js/frontend/tests/features/project-detail-contract.test.mjs
git commit -m "feat: align project detail with overview contract"
```

### Task 4: 收口项目列表与删除语义

**Files:**
- Modify: `D:/WritierLab/WriterLab-v1/Next.js/frontend/features/project/project-hub.tsx`
- Modify: `D:/WritierLab/WriterLab-v1/Next.js/frontend/lib/api/projects.ts`
- Test: `D:/WritierLab/WriterLab-v1/Next.js/frontend/tests/features/api-client.test.mjs`

- [ ] **Step 1: 为删除 404 和网络失败补前端 API 客户端断言**

```js
test("apiDelete surfaces backend detail for missing project", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ detail: "Project not found" }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });

  try {
    await assert.rejects(() => deleteProject("missing-id"), /Project not found/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
```

- [ ] **Step 2: 在 project hub 中统一删除成功与失败提示**

```tsx
try {
  const payload = await deleteProject<ProjectDeleteResponse>(project.id);
  if (!payload.deleted) {
    throw new Error("删除项目失败");
  }
  setProjects((current) => current.filter((item) => item.id !== project.id));
  setNotice(`已删除项目“${project.name}”。`);
} catch (deleteError) {
  setError(deleteError instanceof Error ? deleteError.message : "删除项目失败");
}
```

- [ ] **Step 3: 运行 API 客户端测试**

Run:

```powershell
node --test D:\WritierLab\WriterLab-v1\Next.js\frontend\tests\features\api-client.test.mjs
```

Expected:

```text
all tests pass
```

- [ ] **Step 4: 提交项目列表收口**

```bash
git add D:/WritierLab/WriterLab-v1/Next.js/frontend/features/project/project-hub.tsx D:/WritierLab/WriterLab-v1/Next.js/frontend/lib/api/projects.ts D:/WritierLab/WriterLab-v1/Next.js/frontend/tests/features/api-client.test.mjs
git commit -m "fix: align project deletion messaging with backend contract"
```

### Task 5: 阶段一验证与留痕

**Files:**
- Modify: `D:/WritierLab/.codex/operations-log.md`
- Modify: `D:/WritierLab/docs/superpowers/specs/2026-04-06-writerlab-multi-track-backend-first-design.md`
- Reference: `D:/WritierLab/docs/superpowers/plans/2026-04-06-writerlab-phase-1-backend-data-foundation-plan.md`

- [ ] **Step 1: 在 operations log 记录阶段一实现声明**

```md
## 阶段一实现声明 - 项目与场景主数据

时间：[实际执行时间]

- 新增 `/api/projects/{project_id}/overview` 作为阶段一稳定聚合契约
- 前端项目详情改为消费稳定概览接口，移除页面内嵌套读取链
- 删除语义与场景版本冲突已由自动测试锁定
```

- [ ] **Step 2: 运行阶段一完整验证**

Run:

```powershell
D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_project_scene_contracts.py -q
node --test D:\WritierLab\WriterLab-v1\Next.js\frontend\tests\features\project-detail-contract.test.mjs
node --test D:\WritierLab\WriterLab-v1\Next.js\frontend\tests\features\api-client.test.mjs
Set-Location D:\WritierLab\WriterLab-v1\Next.js\frontend
npm.cmd run typecheck
```

Expected:

```text
backend contract tests pass
frontend project detail contract test passes
frontend api client tests pass
typecheck exits 0
```

- [ ] **Step 3: 在规格文档中标记阶段一已落地**

```md
- 阶段一实施状态：已通过项目概览聚合接口、项目删除契约和场景版本冲突校验完成首轮收口。
```

- [ ] **Step 4: 提交验证与文档留痕**

```bash
git add D:/WritierLab/.codex/operations-log.md D:/WritierLab/docs/superpowers/specs/2026-04-06-writerlab-multi-track-backend-first-design.md D:/WritierLab/docs/superpowers/plans/2026-04-06-writerlab-phase-1-backend-data-foundation-plan.md
git commit -m "docs: record phase-1 backend data foundation delivery"
```

## 自检结论

- 规格覆盖：
  - 后端优先主线：Task 1、Task 2、Task 5 覆盖。
  - 前端跟随后端稳定契约接入：Task 3、Task 4 覆盖。
  - 测试先行与本地验证：Task 1、Task 2、Task 3、Task 4、Task 5 均带失败基线与通过验证。
  - 文档与留痕：Task 5 覆盖。
- 占位检查：
  - 无 `TODO`、`TBD`、`implement later`。
  - 所有任务都给出具体文件、命令和代码片段。
- 边界检查：
  - 该计划仅覆盖中期蓝图的阶段一，没有越界到资料域、时间线/版本和 workflow/context。
