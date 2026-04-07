## 项目上下文摘要（阶段二 / 资料域）

生成时间：2026-04-07

### 1. 相似实现分析

- **实现 1**: `D:/WritierLab/WriterLab-v1/fastapi/backend/app/api/characters.py:10-35`
  - 模式：独立 `APIRouter` 文件，直接在路由中完成 create + list。
  - 可复用：`prefix + tags + Depends(get_db)` 的 FastAPI 路由骨架。
  - 缺口：没有 get detail、update、delete，也没有 repository 级写操作封装。

- **实现 2**: `D:/WritierLab/WriterLab-v1/fastapi/backend/app/api/locations.py:10-51`
  - 模式：资料域里最完整的一组，已具备 create、list、get detail、patch update。
  - 可复用：404 错误语义、`payload.model_dump(exclude_unset=True)` 的更新模式。
  - 缺口：仍未下沉到 repository/service，delete 缺失。

- **实现 3**: `D:/WritierLab/WriterLab-v1/fastapi/backend/app/api/lore_entries.py:10-31`
  - 模式：与角色路由相似，仅有 create + list。
  - 可复用：以 `LoreEntryCreate / LoreEntryResponse` 作为最小 schema 契约。
  - 缺口：没有 get、update、delete，也没有词条引用关系契约。

- **实现 4**: `D:/WritierLab/WriterLab-v1/fastapi/backend/app/api/routers/lore.py:1-10`
  - 模式：用聚合 router 统一挂载角色、地点、词条三组 API。
  - 可复用：阶段二首轮应继续沿用这个 lore 聚合入口，而不是新造平行总线。
  - 缺口：当前没有 Terminology 独立 router。

- **实现 5**: `D:/WritierLab/WriterLab-v1/Next.js/frontend/features/lore/lore-library-page.tsx:42-227`
  - 模式：前端 lore 子页面使用同一个 `mode` 组件承接三类资料列表视图。
  - 可复用：`characters / locations / entries` 三态切换和只读浏览布局。
  - 缺口：页面目前只读，不具备资料域 CRUD 入口，也未消费场景引用链路。

### 2. 项目约定

- **后端边界**：继续沿用 `app/main.py:37-43` 的 `include_router()` 模式，把资料域挂在 `lore_router` 下。
- **共享查询层**：当前 `app/repositories/lore_repository.py:8-17` 只有 list 查询，阶段二应优先扩展这一层，而不是让路由继续内嵌全部 CRUD。
- **前端边界**：继续沿用 `lib/api/lore.ts:3-13` + `features/lore/*` 的分层，避免页面直接拼接请求。
- **测试约定**：后端沿用 `pytest + TestClient`，前端沿用 `node:test` 的结构契约测试。
- **官方依据**：Context7 中 FastAPI 0.128.0 推荐用 `APIRouter` 组织 bigger applications，并用 `TestClient` 做本地测试；SQLAlchemy ORM 文档支持以 `Session` 承接简单 CRUD 和查询。

### 3. 当前缺口

- 资料域能力不对称：Character / LoreEntry 仅有 create + list，Location 额外有 get + patch。
- 未找到 `/api/characters`、`/api/locations`、`/api/lore-entries` 的专用 pytest 契约测试。
- 未找到 lore 前端的结构测试或 smoke。
- 蓝图写有 `Terminology`，但当前代码中未找到独立 model / schema / router / API client。

### 4. Gate 决策

- **事实**：代码里已有 `LoreEntry / entries / 词条`，但没有 `Terminology` 独立实现。
- **建议**：阶段二首轮先统一 `Character / Location / LoreEntry` 三域 CRUD 与契约测试，把 Terminology 作为显式 Gate 决策记录在计划中。
- **理由**：前端当前已经稳定消费 `/lore/entries`，若无证据直接拆新模型，会引入平行命名和额外返工。

### 5. 本地验证出口

- 后端：新增资料域 pytest 契约文件，走 `D:/WritierLab/WriterLab-v1/.venv/Scripts/python.exe -m pytest ...`
- 前端：新增 `features/lore/*` 结构契约测试，走 `node .../tests/features/*.mjs`
- 类型：`npm.cmd run typecheck`

### 6. 关键风险点

- Terminology 命名决策若不先冻结，后端和前端很容易各自扩展出两套词条体系。
- 若先改前端编辑交互而后端契约未统一，会重演阶段一之前的接线返工问题。
- 资料域查询当前都是按项目全量读取，若后续直接叠加场景引用聚合，必须先在 repository 层集中处理查询。