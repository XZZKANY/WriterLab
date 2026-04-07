# WriterLab 阶段二资料域稳定化 Implementation Plan

**Goal:** 稳定 WriterLab 的角色、地点、词条三组资料域后端契约，并为后续场景资料引用与前端资料库接线提供可靠基础。

**Architecture:** 延续现有 `router + repository + schema + model` 分层，先锁后端 pytest 契约，再统一 Character / Location / LoreEntry 三域 CRUD 与错误语义，随后补前端最小 API 客户端和结构契约，最后同步文档与留痕。Terminology 暂列为阶段二 Gate 决策，不在首轮无证据新增平行数据域。

**Tech Stack:** FastAPI、SQLAlchemy、Pydantic、pytest、Next.js 16、TypeScript、node:test

---

## 范围与 Gate

### 本计划覆盖

- `WriterLab-v1/fastapi/backend/app/api/*`
- `WriterLab-v1/fastapi/backend/app/repositories/*`
- `WriterLab-v1/fastapi/backend/app/schemas/*`
- `WriterLab-v1/fastapi/backend/tests/*`
- `WriterLab-v1/Next.js/frontend/lib/api/*`
- `WriterLab-v1/Next.js/frontend/features/lore/*`
- `WriterLab-v1/Next.js/frontend/tests/features/*`
- `docs/superpowers/*`
- `.codex/*`

### 本计划不覆盖

- 时间线 / 版本 / 分支能力
- workflow、context compiler、runtime 深层联动
- 全量视觉翻新

### Gate 决策

- 阶段二首轮默认以 `Character / Location / LoreEntry` 为落地对象。
- `Terminology` 当前仅存在于蓝图和旧文档，不存在独立代码实现。
- 若后续确认 Terminology 必须独立建模，再单独起补充计划，不在首轮与 LoreEntry 同时并行改造。

## 文件职责

- `app/api/characters.py`
  - 从 create/list 扩展为统一 CRUD 路由，保持角色域错误语义一致。
- `app/api/locations.py`
  - 作为资料域最完整样板，对齐统一 CRUD 与错误格式。
- `app/api/lore_entries.py`
  - 补齐词条 get/update/delete，并与前端 `entries` 命名保持一致。
- `app/repositories/lore_repository.py`
  - 承接三域 list/get/create/update/delete 的共享查询与写操作。
- `app/schemas/character.py`
  - 增加 update 与 detail 所需 schema。
- `app/schemas/location.py`
  - 维持现有 update 契约，并在必要时补 delete 响应等共享 schema。
- `app/schemas/lore_entry.py`
  - 增加 update 与 detail 所需 schema。
- `fastapi/backend/tests/test_lore_domain_contracts.py`
  - 新建，锁定三域 CRUD、404 语义与项目过滤契约。
- `Next.js/frontend/lib/api/lore.ts`
  - 从只读 fetch 扩展为最小资料域 API 客户端。
- `Next.js/frontend/features/lore/lore-library-page.tsx`
  - 首轮仍以只读为主，只对齐稳定契约和空态/错误态，不直接扩成复杂编辑工作台。
- `Next.js/frontend/tests/features/lore-domain-contract.test.mjs`
  - 新建，锁定前端 lore 页面仍通过共享 API 客户端消费稳定资料域接口。
- `.codex/operations-log.md`
  - 记录阶段二决策、Gate 选择和验证结果。

## Task 1：先锁资料域后端失败基线

- 新建 `test_lore_domain_contracts.py`
- 覆盖：
  - Character CRUD
  - Location CRUD
  - LoreEntry CRUD
  - 非存在 ID 的 404 语义
  - 按 `project_id` 过滤
- 先运行 pytest，确认当前因 Character/LoreEntry 缺失 get/update/delete 而失败

## Task 2：统一三域后端 CRUD 与错误语义

- 以 `locations.py` 为样板，对齐 Character 与 LoreEntry。
- 在 `lore_repository.py` 增加共享函数：
  - `list_*_by_project`
  - `get_*`
  - `create_*`
  - `update_*`
  - `delete_*`
- 路由层只保留：参数解析、404 抛错、返回 schema。
- 统一错误语义：
  - `Character not found`
  - `Location not found`
  - `Lore entry not found`

## Task 3：补最小前端契约与接线

- 在 `lib/api/lore.ts` 补 create/update/delete 或 detail 读取接口。
- 新建 `lore-domain-contract.test.mjs`，锁定：
  - `features/lore/lore-library-page.tsx` 继续通过 `lib/api/lore.ts` 取数
  - 不在页面层直接散落 `fetch('/api/...')`
- 第一轮前端目标不是完整编辑器，而是：
  - 资料页继续可读
  - 空态与错误态稳定
  - 若后端新增 detail/read API，前端能最小接线

## Task 4：阶段二留痕与验证

- 更新 `.codex/operations-log.md`
- 追加阶段二资料域收口记录
- 更新本计划和蓝图中的阶段二实施状态

### 推荐验证命令

```powershell
D:\WritierLab\WriterLab-v1\.venv\Scripts\python.exe -m pytest D:\WritierLab\WriterLab-v1\fastapi\backend\tests\test_lore_domain_contracts.py -q
node D:\WritierLab\WriterLab-v1\Next.js\frontend\tests\features\lore-domain-contract.test.mjs
Set-Location D:\WritierLab\WriterLab-v1\Next.js\frontend
npm.cmd run typecheck
```
## 风险与约束

- 如果 Terminology 决策未冻结，就不要同时引入 `terminologies` 与 `lore_entries` 两套并行 API。
- 如果前端先行扩编辑能力，会在后端契约不稳定时产生返工。
- 如果继续把写操作堆在路由层，Character / Location / LoreEntry 三域会再次漂移。

## 完成标准

- 后端存在统一的资料域 pytest 契约测试，并能本地通过。
- Character / Location / LoreEntry 三域 CRUD 能力与 404 语义对齐。
- 前端 lore 页面继续通过共享 API 客户端消费资料域，不新增页面内直连请求。
- 阶段二 Gate 决策与验证命令已写入文档和 `.codex` 留痕。

## 下一步执行建议

- 先执行 Task 1：写 `test_lore_domain_contracts.py` 失败基线。
- 若你要我继续，下一轮我会直接从这个失败测试开始进入 TDD 实施，而不是再重复写计划。