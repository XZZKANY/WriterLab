# WriterLab phase-3 时间线与版本联动设计

生成时间：2026-04-07

## 1. 设计目标

本设计文档定义 WriterLab 在 phase-3 的第一轮实施范围：优先建立 Timeline / SceneVersion / StoryBranch 的稳定联动层，而不是一次性做完整的版本中心或复杂时间轴工作台。

本轮目标是把“剧情事实”和“写作历史”收口为可追溯、可恢复、可验证的稳定基础层，并为后续 workflow / context / runtime 消费提供更可靠的数据支点。

## 2. 范围边界

### 2.1 本轮纳入范围

- Timeline 最小后端合同与数据维护入口
- SceneVersion / StoryBranch 现有合同的收口与回归验证
- 前端最小时间线查看接线
- 版本对比 / 恢复 / 分支采纳现有链路的继续复用
- `.codex`、spec、plan、verification 的阶段留痕

### 2.2 本轮明确不做

- 炫酷时间轴或复杂可视化拖拽 UI
- 重写现有 `versions-pane` 或 editor 工作台结构
- 满意样本、style_sample 向量库正式落地
- workflow / context / runtime 的深层回写重构
- 超出 phase-3 第一轮所需的大面积前端翻新

## 3. 当前实现基线

### 3.1 已存在的版本能力

当前仓库已经存在以下 SceneVersion 基础实现：

- `fastapi/backend/app/api/scenes.py`
- `fastapi/backend/app/services/scene_version_service.py`
- `fastapi/backend/app/repositories/scene_repository.py`
- `fastapi/backend/app/schemas/scene_version.py`

现状证据表明：

- 已有场景版本列表接口：`GET /api/scenes/{scene_id}/versions`
- 已有版本恢复接口：`POST /api/scenes/{scene_id}/versions/{version_id}/restore`
- 已有版本创建与恢复 service 逻辑

### 3.2 已存在的分支能力

当前仓库已经存在以下 StoryBranch 基础实现：

- `fastapi/backend/app/api/branches.py`
- `fastapi/backend/app/services/branch_service.py`
- `fastapi/backend/app/models/story_branch.py`
- `fastapi/backend/app/schemas/branch.py`
- `fastapi/backend/tests/test_branch_service.py`

现状证据表明：

- 已有分支创建、列表、diff、adopt 接口
- 已有最小服务测试
- 已有前端分支列表、差异展示和采纳 UI 基座

### 3.3 Timeline 的真实缺口

当前 Timeline 只存在：

- `fastapi/backend/app/models/timeline_event.py`
- `fastapi/backend/app/schemas/timeline_event.py`

尚未发现：

- timeline repository
- timeline service
- timeline router
- timeline pytest 契约
- timeline 前端 API client 与页面接线

### 3.4 前端现状基线

当前前端已经存在：

- `Next.js/frontend/features/editor/hooks/use-versioning-workspace.ts`
- `Next.js/frontend/features/editor/versions-pane.tsx`
- `Next.js/frontend/lib/api/scenes.ts`
- `Next.js/frontend/features/editor/editor-workspace.tsx`

这说明 phase-3 并不需要重写版本页，而应继续沿用现有 editor 内的版本/分支工作区。

### 3.5 上下文消费现状

`fastapi/backend/app/services/context/context_service.py` 已经消费 `TimelineEvent`，把它作为 scene context 的一部分返回。这意味着 Timeline 并不是孤立新功能，而是现有上下文链路中已经预留了消费入口，只缺正式维护与验证接口。

## 4. 设计原则

### 4.1 真实缺口优先

phase-3 第一轮优先补 Timeline 这个真实缺口，而不是重复建设已经存在的 SceneVersion / StoryBranch 页面与接口。

### 4.2 后端优先于前端扩张

延续既有“后端优先”策略，先冻结 Timeline / Version / Branch 的稳定合同，再补前端最小接线，降低返工。

### 4.3 继续复用 editor 版本工作区

前端继续复用 `editor-workspace`、`use-versioning-workspace` 和 `versions-pane`，不引入新的平行版本中心。

### 4.4 时间线第一版保持结构化列表

依据 `guidance.md`，Timeline 第一版只做结构化事件列表，不做炫酷时间轴，确保实现简单、可验证、可迭代。

## 5. 推荐方案 A

### 5.1 第一轮实施顺序

1. **先补 Timeline 最小后端合同**
   - 列表读取
   - 单项读取
   - 创建
   - 更新
   - 删除
   - 404 与项目过滤语义

2. **再收口 SceneVersion / StoryBranch 契约**
   - 锁定版本列表与恢复回归
   - 锁定分支 diff 与采纳回归
   - 统一错误语义与结构测试入口

3. **最后做前端最小时间线查看接线**
   - 通过共享 API client 读取 timeline
   - 以列表方式展示到 editor 或独立 feature 容器
   - 不重写版本/分支 pane

### 5.2 后端设计

#### Timeline

新增稳定资源接口：

- `POST /api/timeline-events`
- `GET /api/timeline-events?project_id=...`
- `GET /api/timeline-events/{event_id}`
- `PATCH /api/timeline-events/{event_id}`
- `DELETE /api/timeline-events/{event_id}`

第一轮字段优先复用现有模型与 schema：

- `title`
- `event_type`
- `description`
- `participants`
- `event_time_label`
- `canonical`
- `metadata_json`
- `chapter_id / scene_id / project_id`

#### SceneVersion / StoryBranch

本轮不重写主逻辑，只做契约收口：

- SceneVersion：继续复用 `scenes.py` 与 `scene_version_service.py`
- StoryBranch：继续复用 `branches.py` 与 `branch_service.py`
- 把 phase-3 验证重点放在“可列出 / 可恢复 / 可 diff / 可采纳 / 可本地回归”

### 5.3 前端设计

- `lib/api/scenes.ts` 继续保留 SceneVersion / StoryBranch 请求
- Timeline 新增独立前端 client（建议放在 `lib/api/timeline.ts` 或按项目既有命名收敛）
- 前端时间线第一轮以列表态为主，可挂到 editor 侧栏或独立 feature 容器
- `versions-pane.tsx` 继续承接版本与分支 UI，不拆平行页面

## 6. 测试与验证设计

### 6.1 后端验证

新增或补齐 phase-3 后端测试，至少锁定：

- Timeline CRUD
- Timeline 的 `project_id` 过滤
- Timeline 不存在资源的 404 语义
- SceneVersion 列表与恢复路径
- StoryBranch diff 与采纳路径

### 6.2 前端验证

新增 phase-3 前端结构验证，至少锁定：

- Timeline 页面或容器通过共享 API client 读取数据
- 版本/分支仍继续复用 `lib/api/scenes.ts`
- 不在页面层散落 `fetch('/api/...')`
- `npm.cmd run typecheck` 通过

### 6.3 推荐验证命令

```powershell
D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_timeline_domain_contracts.py -q
D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_project_scene_contracts.py -q
D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_branch_service.py -q
node D:\WritierLab\WriterLab-v1\Next.js\frontend\tests\features\editor-workspace-structure.test.mjs
Set-Location D:\WritierLab\WriterLab-v1\Next.js\frontend
npm.cmd run typecheck
```

## 7. 风险与约束

- Timeline 已被 context service 消费，因此本轮要优先保证字段与查询语义稳定，避免后续 context 输出漂移。
- `guidance.md` 中的 `knowledge_scope` 尚未在当前 model/schema 中正式落地，第一轮不应无证据强行扩表。
- SceneVersion / StoryBranch 当前已有基础实现，本轮若重写版本页或分支流，会放大返工范围。
- phase-3 第一轮应继续保持最小落地，不把 workflow / runtime 深层联动混入同一轮。

## 8. 交付结论

phase-3 第一轮完成后，应得到以下结果：

- WriterLab 拥有可维护的 Timeline 数据入口与稳定后端契约
- SceneVersion / StoryBranch 的已有链路得到测试收口
- 前端可最小查看 Timeline，且继续沿用现有版本/分支工作区
- phase-3 的验证命令、设计与留痕文档齐全

该设计已明确采用方案 A：先补 Timeline 后端合同，再收口版本/分支契约，最后做前端最小接线。后续 implementation plan 应在这个边界内展开，而不是重新定义 phase-3。
