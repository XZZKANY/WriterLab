# WriterLab phase-3 时间线与版本联动 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 先补齐 Timeline 最小后端合同与前端最小查看入口，再收口 SceneVersion / StoryBranch 的验证链路，形成 phase-3 第一轮稳定地基。

**Architecture:** 延续现有后端优先策略，先用 pytest 锁定 Timeline 与版本/分支回归，再在 `router + repository + service + schema` 分层内补齐 Timeline 资源接口。前端继续复用 `editor-workspace` 的版本/分支链路，不重写 `versions-pane`，只新增 Timeline 共享 client 与最小项目级查看页。

**Tech Stack:** FastAPI、SQLAlchemy、Pydantic、pytest、Next.js 16、TypeScript、node:test

---

## 范围与 Gate

### 本计划覆盖

- `WriterLab-v1/fastapi/backend/app/api/*`
- `WriterLab-v1/fastapi/backend/app/api/routers/*`
- `WriterLab-v1/fastapi/backend/app/repositories/*`
- `WriterLab-v1/fastapi/backend/app/services/*`
- `WriterLab-v1/fastapi/backend/app/schemas/*`
- `WriterLab-v1/fastapi/backend/tests/*`
- `WriterLab-v1/Next.js/frontend/app/project/[projectId]/timeline/*`
- `WriterLab-v1/Next.js/frontend/features/project/*`
- `WriterLab-v1/Next.js/frontend/features/timeline/*`
- `WriterLab-v1/Next.js/frontend/lib/api/*`
- `WriterLab-v1/Next.js/frontend/tests/features/*`
- `docs/superpowers/*`
- `.codex/*`

### 本计划不覆盖

- `knowledge_scope` 扩表或 timeline 高级权限模型
- 满意样本 / style_sample 正式落地
- workflow / runtime 深层联动改造
- `versions-pane.tsx` 的大规模重构
- 炫酷时间轴、拖拽排序、多视图筛选等增强 UI

### Gate 决策

- Timeline 第一轮只做结构化事件列表，不做复杂可视化时间轴。
- SceneVersion / StoryBranch 以“契约收口 + 回归验证”为目标，不重写现有主逻辑。
- 前端 Timeline 使用项目级页面 `app/project/[projectId]/timeline/page.tsx`，通过共享 API client 读取数据。

## 文件职责

- `WriterLab-v1/fastapi/backend/app/api/timeline_events.py`
  - 新增 Timeline 资源路由，提供 CRUD 与过滤入口。
- `WriterLab-v1/fastapi/backend/app/api/routers/story.py`
  - 把 timeline router 纳入 story 聚合入口。
- `WriterLab-v1/fastapi/backend/app/repositories/timeline_repository.py`
  - 承接 Timeline 的 list/get/create/update/delete 查询与写操作。
- `WriterLab-v1/fastapi/backend/app/services/timeline_service.py`
  - 统一 Timeline 的 payload 清理、项目过滤和更新逻辑。
- `WriterLab-v1/fastapi/backend/app/schemas/timeline_event.py`
  - 补齐 Timeline update 与 delete response 所需 schema。
- `WriterLab-v1/fastapi/backend/tests/test_timeline_domain_contracts.py`
  - 新建，锁定 Timeline CRUD、404 与 `project_id` 过滤契约。
- `WriterLab-v1/fastapi/backend/tests/test_story_version_branch_contracts.py`
  - 新建，锁定 SceneVersion 列表/恢复与 StoryBranch 列表/diff/adopt 的 API 回归。
- `WriterLab-v1/Next.js/frontend/lib/api/timeline.ts`
  - 新增 Timeline 共享 client，避免页面层散落请求。
- `WriterLab-v1/Next.js/frontend/features/timeline/timeline-library-page.tsx`
  - 新增项目级 Timeline 列表页，复用现有暗色 `AppShell + InfoCard` 语言。
- `WriterLab-v1/Next.js/frontend/app/project/[projectId]/timeline/page.tsx`
  - 提供 Timeline 页薄路由入口。
- `WriterLab-v1/Next.js/frontend/features/project/project-detail.tsx`
  - 给项目工作台补一个 Timeline 入口链接。
- `WriterLab-v1/Next.js/frontend/tests/features/timeline-domain-contract.test.mjs`
  - 新建，锁定 Timeline 页面通过共享 client 消费数据，且不直连 `/api`。
- `.codex/operations-log.md`
  - 记录 phase-3 第一轮决策、验证结果与提交信息。

### Task 1: 锁定 Timeline 后端失败基线

**Files:**
- Create: `WriterLab-v1/fastapi/backend/tests/test_timeline_domain_contracts.py`
- Reference: `WriterLab-v1/fastapi/backend/tests/test_project_scene_contracts.py`
- Reference: `WriterLab-v1/fastapi/backend/app/schemas/timeline_event.py`

- [ ] **Step 1: 写 Timeline 失败测试**

```python
from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db.session import get_db
```

```python
def test_list_timeline_events_filters_by_project(monkeypatch):
    app = FastAPI()
    app.include_router(timeline_router)
    project_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    other_project_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    now = datetime.utcnow()
    rows = [
        SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"), project_id=project_id, title="事故", event_type="incident", description="北站事故", participants=["林岚"], event_time_label="第0天", canonical=True, metadata_json=None, chapter_id=None, scene_id=None, created_at=now, updated_at=now),
        SimpleNamespace(id=UUID("22222222-2222-2222-2222-222222222222"), project_id=other_project_id, title="无关事件", event_type="note", description="忽略", participants=[], event_time_label=None, canonical=True, metadata_json=None, chapter_id=None, scene_id=None, created_at=now, updated_at=now),
    ]
    monkeypatch.setattr("app.api.timeline_events.list_timeline_events", lambda db, project_id, chapter_id=None, scene_id=None: [row for row in rows if row.project_id == project_id])
    app.dependency_overrides[get_db] = lambda: object()
    client = TestClient(app)
    response = client.get(f"/api/timeline-events?project_id={project_id}")
    assert response.status_code == 200
    assert len(response.json()) == 1
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_timeline_domain_contracts.py -q`
Expected: FAIL，提示 `app.api.timeline_events` 不存在或 Timeline 路由/更新 schema 缺失。

- [ ] **Step 3: 扩展测试到完整 CRUD 与 404 语义**

```python
def test_get_missing_timeline_event_returns_404():
    response = client.get(f"/api/timeline-events/{missing_event_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Timeline event not found"}
```

```python
def test_delete_timeline_event_returns_deleted_payload():
    response = client.delete(f"/api/timeline-events/{event_id}")
    assert response.status_code == 200
    assert response.json() == {"deleted": True, "timeline_event_id": str(event_id)}
```

- [ ] **Step 4: 再次运行 Timeline 测试，确认红灯稳定**

Run: `D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_timeline_domain_contracts.py -q`
Expected: FAIL，且失败原因只指向 Timeline 实现缺失，不是测试拼写错误。

- [ ] **Step 5: 提交红灯基线**

```bash
git add WriterLab-v1/fastapi/backend/tests/test_timeline_domain_contracts.py
git commit -m "新增 phase-3 timeline 合同失败基线"
```

### Task 2: 实现 Timeline 后端最小合同

**Files:**
- Create: `WriterLab-v1/fastapi/backend/app/api/timeline_events.py`
- Create: `WriterLab-v1/fastapi/backend/app/repositories/timeline_repository.py`
- Create: `WriterLab-v1/fastapi/backend/app/services/timeline_service.py`
- Modify: `WriterLab-v1/fastapi/backend/app/api/routers/story.py`
- Modify: `WriterLab-v1/fastapi/backend/app/schemas/timeline_event.py`
- Test: `WriterLab-v1/fastapi/backend/tests/test_timeline_domain_contracts.py`

- [ ] **Step 1: 先补 schema 缺口**

```python
class TimelineEventUpdate(BaseModel):
    chapter_id: UUID | None = None
    scene_id: UUID | None = None
    title: str | None = None
    event_type: str | None = None
    description: str | None = None
    participants: list[str] | None = None
    event_time_label: str | None = None
    canonical: bool | None = None
    metadata_json: dict | None = None

class TimelineEventDeleteResponse(BaseModel):
    deleted: bool
    timeline_event_id: UUID
```

- [ ] **Step 2: 写最小 repository**

```python
def list_timeline_events(db: Session, *, project_id, chapter_id=None, scene_id=None):
    query = db.query(TimelineEvent).filter(TimelineEvent.project_id == project_id)
    if chapter_id is not None:
        query = query.filter(TimelineEvent.chapter_id == chapter_id)
    if scene_id is not None:
        query = query.filter(TimelineEvent.scene_id == scene_id)
    return query.order_by(TimelineEvent.created_at.desc()).all()
```

```python
def get_timeline_event(db: Session, event_id):
    return db.query(TimelineEvent).filter(TimelineEvent.id == event_id).first()
```

- [ ] **Step 3: 写最小 service**

```python
def create_timeline_event(db: Session, payload: TimelineEventCreate) -> TimelineEvent:
    row = TimelineEvent(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
```

```python
def update_timeline_event(db: Session, row: TimelineEvent, payload: TimelineEventUpdate) -> TimelineEvent:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row
```

- [ ] **Step 4: 接入 router 与 story 聚合**

```python
router = APIRouter(prefix="/api/timeline-events", tags=["timeline"])

@router.get("", response_model=list[TimelineEventResponse])
def get_timeline_events(project_id: UUID, chapter_id: UUID | None = None, scene_id: UUID | None = None, db: Session = Depends(get_db)):
    return list_timeline_events(db, project_id=project_id, chapter_id=chapter_id, scene_id=scene_id)
```

```python
@router.delete("/{event_id}", response_model=TimelineEventDeleteResponse)
def delete_timeline_event_api(event_id: UUID, db: Session = Depends(get_db)):
    row = get_timeline_event(db, event_id)
    if not row:
        raise HTTPException(status_code=404, detail="Timeline event not found")
    delete_timeline_event(db, row)
    return TimelineEventDeleteResponse(deleted=True, timeline_event_id=event_id)
```

```python
# app/api/routers/story.py
from app.api.timeline_events import router as timeline_events_router
router.include_router(timeline_events_router)
```

- [ ] **Step 5: 运行 Timeline 测试转绿并提交**

Run: `D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_timeline_domain_contracts.py -q`
Expected: PASS

```bash
git add WriterLab-v1/fastapi/backend/app/api/timeline_events.py WriterLab-v1/fastapi/backend/app/api/routers/story.py WriterLab-v1/fastapi/backend/app/repositories/timeline_repository.py WriterLab-v1/fastapi/backend/app/services/timeline_service.py WriterLab-v1/fastapi/backend/app/schemas/timeline_event.py WriterLab-v1/fastapi/backend/tests/test_timeline_domain_contracts.py
git commit -m "实现 phase-3 timeline 最小后端合同"
```

### Task 3: 收口版本与分支 API 回归

**Files:**
- Create: `WriterLab-v1/fastapi/backend/tests/test_story_version_branch_contracts.py`
- Reference: `WriterLab-v1/fastapi/backend/app/api/scenes.py`
- Reference: `WriterLab-v1/fastapi/backend/app/api/branches.py`
- Reference: `WriterLab-v1/fastapi/backend/tests/test_branch_service.py`

- [ ] **Step 1: 为 SceneVersion API 写失败测试**

```python
def test_get_scene_versions_returns_latest_first(monkeypatch):
    app = FastAPI()
    app.include_router(scenes_router)
    monkeypatch.setattr("app.api.scenes.get_scene_record", lambda db, scene_id: SimpleNamespace(id=scene_id))
    monkeypatch.setattr("app.api.scenes.list_scene_version_records", lambda db, scene_id: [SimpleNamespace(id=version_id, scene_id=scene_id, content="v2", source="manual", label="manual update", created_at=now)])
    response = TestClient(app).get(f"/api/scenes/{scene_id}/versions")
    assert response.status_code == 200
    assert response.json()[0]["id"] == str(version_id)
```

- [ ] **Step 2: 为 Branch API 写失败测试**

```python
def test_adopt_branch_returns_current_text(monkeypatch):
    app = FastAPI()
    app.include_router(branches_router)
    monkeypatch.setattr("app.api.branches.adopt_story_branch", lambda db, branch: (SimpleNamespace(id=scene_id, draft_text="采纳后的正文"), SimpleNamespace(id=version_id)))
    response = TestClient(app).post(f"/api/branches/{branch_id}/adopt")
    assert response.status_code == 200
    assert response.json()["current_text"] == "采纳后的正文"
```

- [ ] **Step 3: 运行回归测试并确认缺口**

Run: `D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_story_version_branch_contracts.py -q`
Expected: 先红灯，若已有实现与预期不一致，则暴露具体契约差异。

- [ ] **Step 4: 做最小修复，不重写主逻辑**

```python
# app/api/branches.py
return BranchAdoptResponse(
    branch_id=branch.id,
    scene_id=scene.id,
    version_id=version.id if version else None,
    adopted_version_id=version.id if version else None,
    current_text=scene.draft_text or "",
    adopted_at=datetime.utcnow(),
)
```

```python
# app/api/scenes.py
return RestoreVersionResponse(
    success=True,
    version_id=restored.id,
    restored_to_scene_id=scene.id,
    current_text=scene.draft_text or "",
)
```

- [ ] **Step 5: 运行三组后端测试并提交**

Run: `D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_timeline_domain_contracts.py D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_story_version_branch_contracts.py D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_project_scene_contracts.py -q`
Expected: PASS

```bash
git add WriterLab-v1/fastapi/backend/tests/test_story_version_branch_contracts.py WriterLab-v1/fastapi/backend/app/api/scenes.py WriterLab-v1/fastapi/backend/app/api/branches.py
git commit -m "收口 phase-3 版本与分支 API 回归"
```

### Task 4: 接入前端 Timeline 最小查看页

**Files:**
- Create: `WriterLab-v1/Next.js/frontend/lib/api/timeline.ts`
- Create: `WriterLab-v1/Next.js/frontend/features/timeline/timeline-library-page.tsx`
- Create: `WriterLab-v1/Next.js/frontend/app/project/[projectId]/timeline/page.tsx`
- Create: `WriterLab-v1/Next.js/frontend/tests/features/timeline-domain-contract.test.mjs`
- Modify: `WriterLab-v1/Next.js/frontend/features/project/project-detail.tsx`
- Reference: `WriterLab-v1/Next.js/frontend/features/lore/lore-library-page.tsx`
- Reference: `WriterLab-v1/Next.js/frontend/shared/ui/info-card.tsx`

- [ ] **Step 1: 先写前端结构测试**

```javascript
test("timeline page consumes shared timeline api and project workbench exposes entry", async () => {
  const [apiSource, pageSource, projectDetailSource] = await Promise.all([
    readFile(timelineApiPath, "utf8"),
    readFile(timelinePagePath, "utf8"),
    readFile(projectDetailPath, "utf8"),
  ]);
  assert.equal(apiSource.includes("fetchTimelineEvents"), true);
  assert.equal(pageSource.includes("@/lib/api/timeline"), true);
  assert.equal(pageSource.includes("fetch('/api/"), false);
  assert.equal(projectDetailSource.includes("时间线"), true);
});
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `node D:\WritierLab\WriterLab-v1\Next.js\frontend\tests\features\timeline-domain-contract.test.mjs`
Expected: FAIL，缺少 `timeline.ts`、timeline page 或项目入口链接。

- [ ] **Step 3: 写最小前端 client 与页面**

```typescript
export function fetchTimelineEvents<T>(projectId: string) {
  return apiGet<T>(`/api/timeline-events?project_id=${projectId}`, "读取时间线失败");
}
```

```tsx
import { use } from "react";
import TimelineLibraryPage from "@/features/timeline/timeline-library-page";

export default function ProjectTimelinePage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = use(params);
  return <TimelineLibraryPage projectId={projectId} />;
}
```

```tsx
export default function TimelineLibraryPage({ projectId }: { projectId: string }) {
  const [events, setEvents] = useState<TimelineEventResponse[]>([]);

  useEffect(() => {
    void fetchTimelineEvents<TimelineEventResponse[]>(projectId).then(setEvents);
  }, [projectId]);

  return (
    <AppShell title="项目时间线" description="以结构化事件列表查看当前项目的关键剧情事实。">
      <InfoCard title="时间线事件" description="第一轮只做结构化列表，不做复杂时间轴。">
        <div className="space-y-3">
          {events.map((item) => (
            <article key={item.id} className="rounded-[24px] border border-white/8 bg-[#1d1d1d] px-4 py-4">
              <div className="text-sm font-medium text-zinc-100">{item.title}</div>
              <div className="mt-1 text-xs text-zinc-500">{item.event_type} · {item.event_time_label || "未标记时间"}</div>
              <div className="mt-2 text-sm text-zinc-300">{item.description}</div>
            </article>
          ))}
        </div>
      </InfoCard>
    </AppShell>
  );
}
```

- [ ] **Step 4: 给项目工作台补 Timeline 入口并跑绿**

Run: `node D:\WritierLab\WriterLab-v1\Next.js\frontend\tests\features\timeline-domain-contract.test.mjs`
Expected: PASS

Run: `Set-Location D:\WritierLab\WriterLab-v1\Next.js\frontend; npm.cmd run typecheck`
Expected: PASS

- [ ] **Step 5: 提交前端 Timeline 接线**

```bash
git add WriterLab-v1/Next.js/frontend/lib/api/timeline.ts WriterLab-v1/Next.js/frontend/features/timeline/timeline-library-page.tsx WriterLab-v1/Next.js/frontend/app/project/[projectId]/timeline/page.tsx WriterLab-v1/Next.js/frontend/features/project/project-detail.tsx WriterLab-v1/Next.js/frontend/tests/features/timeline-domain-contract.test.mjs
git commit -m "接入 phase-3 timeline 最小前端查看页"
```

### Task 5: 留痕、总验证与收口

**Files:**
- Modify: `.codex/operations-log.md`
- Modify: `.codex/verification-report.md`
- Modify: `docs/superpowers/specs/2026-04-07-writerlab-phase-3-timeline-version-design.md`
- Modify: `docs/superpowers/plans/2026-04-07-writerlab-phase-3-timeline-version-plan.md`

- [ ] **Step 1: 更新 `.codex/operations-log.md`**

```markdown
## 2026-04-07 phase-3 第一轮实施
- Timeline 合同已落地
- SceneVersion / StoryBranch 回归已收口
- Timeline 前端最小查看页已接入
```

- [ ] **Step 2: 更新 `.codex/verification-report.md`**

```markdown
## 2026-04-07 phase-3 第一轮审查报告

Scoring
score: 92

summary: 'phase-3 第一轮已形成 Timeline / Version / Branch 的稳定联动地基。'
```

- [ ] **Step 3: 运行总验证**

Run: `D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_timeline_domain_contracts.py D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_story_version_branch_contracts.py D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_project_scene_contracts.py D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_branch_service.py -q`
Expected: PASS

Run: `node D:\WritierLab\WriterLab-v1\Next.js\frontend\tests\features\timeline-domain-contract.test.mjs`
Expected: PASS

Run: `node D:\WritierLab\WriterLab-v1\Next.js\frontend\tests\features\editor-workspace-structure.test.mjs`
Expected: PASS

Run: `Set-Location D:\WritierLab\WriterLab-v1\Next.js\frontend; npm.cmd run typecheck`
Expected: PASS

- [ ] **Step 4: 提交留痕与计划更新**

```bash
git add .codex/operations-log.md .codex/verification-report.md docs/superpowers/specs/2026-04-07-writerlab-phase-3-timeline-version-design.md docs/superpowers/plans/2026-04-07-writerlab-phase-3-timeline-version-plan.md
git commit -m "完成 phase-3 第一轮 timeline version branch 收口"
```

- [ ] **Step 5: 推送并记录结果**

```bash
git push origin master
```

Expected: 远端包含 phase-3 第一轮提交链路。

## 完成标准

- Timeline 后端存在稳定 CRUD 合同与本地 pytest 入口。
- SceneVersion / StoryBranch 现有 API 有独立回归验证。
- 前端存在最小 Timeline 查看入口，并继续通过共享 API client 读取数据。
- `versions-pane` 未被重写，editor 版本/分支链路保持可用。
- `.codex`、spec、plan、verification 留痕完整。

## 2026-04-09 实施回填

- [x] Task 1：Timeline 失败基线已提交（`1f8c2d0`）
- [x] Task 2：Timeline 后端最小合同已提交（`2da22e2`）
- [x] Task 3：版本与分支 API 回归已提交（`aafb554`）
- [x] Task 4：前端 Timeline 最小查看页已提交（`4a69a1e`）
- [x] Task 5：已完成总验证与留痕收口

### 总验证结果
- 后端：`pytest tests/test_timeline_domain_contracts.py tests/test_story_version_branch_contracts.py tests/test_project_scene_contracts.py tests/test_branch_service.py -q` → `15 passed`
- 前端：`node tests/features/timeline-domain-contract.test.mjs` → `4 passed`
- 前端：`node tests/features/editor-workspace-structure.test.mjs` → `1 passed`
- 前端：`npm.cmd run typecheck` → 通过
