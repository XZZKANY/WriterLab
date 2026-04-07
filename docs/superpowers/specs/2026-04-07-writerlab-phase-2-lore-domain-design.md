# WriterLab phase-2 资料域收口设计

生成时间：2026-04-07

## 1. 设计目标

本设计文档定义 WriterLab 在 phase-2 的第一轮实施范围：只收口资料域本身，不扩展到场景侧展示、知识库重构或时间线联动。

本轮目标是把以下四类资料做成稳定基础层：

- `Character`
- `Location`
- `LoreEntry`
- `Terminology`

资料域第一轮验收标准是：可录入、可读取、可更新、可删除、可验证，并且为后续 scene/context 消费保留稳定契约。

## 2. 范围边界

### 2.1 本轮纳入范围

- 后端四类资料资源的 CRUD 契约收口
- 前端资料库页面的统一读写入口
- `Terminology` 资源从无到有补齐
- 资料域的后端契约测试、前端结构验证与 typecheck
- `.codex`、spec、plan、verification 的阶段留痕

### 2.2 本轮明确不做

- scene 页面中的资料展示或交互改造
- context / knowledge 检索体系重构
- timeline / version / branch 联动
- 搜索、分页、标签体系等增强功能
- 超出资料域第一轮收口所需的 UI 大改

## 3. 当前实现基线

### 3.1 已存在的后端基础

当前仓库已经存在以下资料域基础实现：

- `app/api/characters.py`
- `app/api/locations.py`
- `app/api/lore_entries.py`
- `app/models/character.py`
- `app/models/location.py`
- `app/models/lore_entry.py`
- `app/schemas/character.py`
- `app/schemas/location.py`
- `app/schemas/lore_entry.py`
- `app/repositories/lore_repository.py`

这些实现目前只覆盖了部分 create/list/update 能力，尚未形成四类资源一致、完整、可验证的 phase-2 契约。

### 3.2 已存在的前端基础

当前前端已经存在：

- `app/lore/page.tsx`
- `app/lore/characters/page.tsx`
- `app/lore/locations/page.tsx`
- `app/lore/entries/page.tsx`
- `features/lore/lore-hub.tsx`
- `features/lore/lore-library-page.tsx`
- `lib/api/lore.ts`

这些页面与 client 目前以只读消费为主，尚未收口为统一资料库工作页。

### 3.3 已确认的关键缺口

- `Terminology` 资源缺失
- `Character / Location / LoreEntry` 没有完整 CRUD 对齐
- 前端没有统一的创建、编辑、删除入口
- 缺少 phase-2 专属契约测试与前端结构验证

## 4. 设计原则

### 4.1 资源级收口优先

phase-2 第一轮优先把资料资源本身做稳定，而不是提前引入聚合查询、复杂筛选或知识库统一映射。

### 4.2 契约一致优先于功能扩展

四类资料资源必须尽量使用一致的 API 形状、错误语义和前端调用方式，降低后续 scene/context 接入成本。

### 4.3 复用现有路由与页面骨架

前端继续保留现有 `lore` 路由族与 `lore-hub` / `lore-library-page` 主结构，只做资料库能力增强，不进行无关重写。

### 4.4 不越界到 phase-3

本轮不处理 timeline、scene version、branch、context pipeline 的联动增强，避免资料域收口再次扩大范围。

## 5. 后端设计

### 5.1 资源清单

phase-2 第一轮后端覆盖以下四类资源：

- `Character`
- `Location`
- `LoreEntry`
- `Terminology`

### 5.2 分层方式

每个资源保持清晰边界：

- `model`
- `schema`
- `repository`
- `api router`

不再继续把全部 phase-2 行为堆入单一 `lore_repository.py`。随着 CRUD 和 terminology 落地，资料域应拆为资源级 repository，避免文件退化为杂物仓库。

### 5.3 API 契约

#### Character

- `POST /api/characters`
- `GET /api/characters?project_id=...`
- `GET /api/characters/{character_id}`
- `PATCH /api/characters/{character_id}`
- `DELETE /api/characters/{character_id}`

#### Location

- `POST /api/locations`
- `GET /api/locations?project_id=...`
- `GET /api/locations/{location_id}`
- `PATCH /api/locations/{location_id}`
- `DELETE /api/locations/{location_id}`

#### LoreEntry

- `POST /api/lore-entries`
- `GET /api/lore-entries?project_id=...`
- `GET /api/lore-entries/{entry_id}`
- `PATCH /api/lore-entries/{entry_id}`
- `DELETE /api/lore-entries/{entry_id}`

#### Terminology

- `POST /api/terminology`
- `GET /api/terminology?project_id=...`
- `GET /api/terminology/{term_id}`
- `PATCH /api/terminology/{term_id}`
- `DELETE /api/terminology/{term_id}`

### 5.4 字段策略

`Character`、`Location`、`LoreEntry` 优先复用现有字段，避免无依据扩张。

`Terminology` 采用第一轮最小字段集：

- `term`
- `definition`
- `aliases`
- `usage_notes`
- `canonical`
- `status`

### 5.5 错误语义

资料域保持与 phase-1 一致的简单错误契约：

- 资源不存在：`404` + `{"detail": "... not found"}`
- 参数非法：`422`
- 删除成功：`200` + `{"deleted": true, "id": "..."}`

本轮不引入更复杂的错误码体系。

## 6. 前端设计

### 6.1 路由结构

继续保留并扩展现有资料域路由：

- `app/lore/page.tsx`
- `app/lore/characters/page.tsx`
- `app/lore/locations/page.tsx`
- `app/lore/entries/page.tsx`
- `app/lore/terminology/page.tsx`

### 6.2 页面职责

- `lore-hub.tsx` 继续作为资料域总览与项目切换入口
- `lore-library-page.tsx` 升级为统一资料库工作页，按 mode 驱动不同资源视图
- `lib/api/lore.ts` 继续作为资料域前端请求的唯一 client 入口

### 6.3 前端 client 契约

前端资料域 client 统一暴露：

- `fetchCharacters / createCharacter / updateCharacter / deleteCharacter`
- `fetchLocations / createLocation / updateLocation / deleteLocation`
- `fetchLoreEntries / createLoreEntry / updateLoreEntry / deleteLoreEntry`
- `fetchTerminology / createTerminology / updateTerminology / deleteTerminology`

页面层继续只展示 `Error.message`，不散落底层异常解释逻辑。

## 7. 测试与验证设计

### 7.1 后端验证

新增 phase-2 资料域契约测试，至少锁定：

- 四类资源的列表读取
- 四类资源的详情读取与 404 语义
- 更新成功路径
- 删除成功路径
- `Terminology` 已正确接入主应用路由

### 7.2 前端验证

新增资料域前端结构验证，至少锁定：

- `lib/api/lore.ts` 已提供四类资源 CRUD client
- `lore-library-page.tsx` 已支持统一资料库读写模式
- `app/lore/terminology/page.tsx` 已接上 terminology 视图
- `npm.cmd run typecheck` 通过

### 7.3 验证原则

- 继续优先使用源码级结构验证与后端契约测试
- 不把 scene/editor 的页面 smoke 混入本轮 phase-2 主验收
- 所有验证必须本地可重复执行并写入 `.codex` 留痕

## 8. 多 Subagent 执行设计

后续 implementation plan 通过后，采用多 subagent 并行执行：

- Worker 1：后端资料域 CRUD 与后端契约测试
- Worker 2：前端资料库页面与资料域 API client
- Worker 3：spec / plan / operations-log / verification-report 等文档留痕
- 主控：接口冻结、结果审查、最终验证、提交与推送

该拆分的核心目标是让后端、前端、文档三类改动尽量分离，降低并行冲突。

## 9. 风险与约束

- 当前资料域在仓库中存在后端基础和前端只读骨架，本轮要避免重复造第二套页面或第二套 API client。
- `Terminology` 是 phase-2 第一轮唯一新增资源，必须控制在最小字段与最小交互范围内。
- scene/context 已经存在对角色、地点、lore 的消费雏形，但本轮不以 scene 侧完成度作为验收条件。
- 如果实现过程中发现 `Character / Location / LoreEntry` 字段或行为存在历史不一致，应优先收口到统一契约，而不是继续扩散差异。

## 10. 交付结论

phase-2 第一轮完成后，应得到以下结果：

- WriterLab 拥有稳定的四类资料域资源接口
- 前端资料库具备统一的录入、读取、编辑、删除能力
- phase-2 的验证命令和留痕文档齐全
- scene/context 可以继续消费这些资料契约，但相关展示收口保留到后续阶段

该设计已明确限定 phase-2 第一轮只处理资料域本身，后续任何场景侧扩展都应在新的 spec / plan 中单独展开。
