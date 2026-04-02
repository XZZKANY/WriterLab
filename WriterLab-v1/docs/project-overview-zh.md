# WriterLab v1 项目盘点文档

最后梳理时间：2026-04-01

本文基于当前工作区代码状态整理，目的是为后续“大改 / 重构 / 重写部分模块”提供统一参考。

## 1. 项目一句话说明

WriterLab v1 是一个面向中文小说创作的“场景级写作工作台”，采用：

- 前端：Next.js 16 + React 19 + TypeScript + Tailwind 4
- 后端：FastAPI + SQLAlchemy + PostgreSQL/Alembic
- AI 能力：多 Provider 路由、Fallback、工作流编排、上下文拼装、一致性检查
- 检索能力：知识文档切块 + 向量检索，优先 pgvector，不可用时回退到本地 embedding 相似度

当前前端更像“调试台 / 工作台”，不是完整的最终用户产品。

## 2. 已完成功能

### 2.1 核心写作链路

- 场景 `Scene` 的创建、读取、修改
- 场景正文保存与版本快照 `SceneVersion`
- AI 场景分析 `analyze-scene`
- AI 生成初稿 `write-scene`
- AI 润色改写 `revise-scene`
- 基于场景上下文的完整工作流执行 `workflow`
- 工作流支持异步排队和同步直跑两种模式
- 工作流支持恢复 `resume`、人工覆盖某一步 `override`、取消 `cancel`

### 2.2 上下文与记忆

- 场景上下文编译 `build_scene_context`
- 聚合 POV 角色、地点、时间线、近期场景、风格记忆、知识命中
- 记录上下文编译快照 `context_compile_snapshot`
- 风格记忆 `style_memories` 的新增、确认、按作用域使用
- 工作流结束后自动生成候选风格记忆

### 2.3 知识库 / 检索

- 知识文档录入 `knowledge_documents`
- 文档切块 `knowledge_chunks`
- embedding 生成与检索
- 优先使用 pgvector；数据库不满足时自动回退到本地向量相似度
- 知识库重建 / 重索引

### 2.4 一致性与守门

- 规则型一致性检查：
- `must_include` 缺失检查
- `must_avoid` 命中检查
- 地点锚点检查
- 时间标签检查
- 时间线冲突检查
- 角色外貌冲突检查
- LLM 二次复核一致性问题
- AI 输出 Guardrail：
- 拦截说明腔 / 分析腔输出
- 拦截语言漂移
- 拦截过度改写
- 风格负面规则 `style_negative_rules`

### 2.5 分支与版本采用

- 从场景版本创建剧情分支 `story_branches`
- 查看原文和分支文本差异
- 将分支版本采纳回主场景

### 2.6 运行时与可观测性

- `/api/health` 健康检查
- `/api/runtime/self-check` 自检聚合
- `/api/runtime/provider-state` Provider 运行状态
- `/api/runtime/events` WebSocket 运行时事件流
- smoke report 浏览、详情、回归比较
- 启动时：
- 校验 Alembic 管理状态
- 应用 schema upgrade
- 恢复过期工作流
- 启动后台 workflow runner

### 2.7 其他能力

- Provider API 设置保存与读取
- VN 脚本导出与图片提示词生成

## 3. 当前前端完成度

### 3.1 已有页面

- `/`
  首页，展示后端健康状态，并跳转到 `/editor`
- `/editor`
  当前核心页面，几乎所有业务功能都集中在这里
- `/project`
  占位页
- `/lore`
  占位页

### 3.2 `/editor` 页面现状

`app/editor/page.tsx` 是当前系统最核心的前端文件：

- 文件大小约 `133590` 字节
- 总行数约 `2255` 行
- 集中了状态定义、接口请求、工作流控制、版本管理、分支管理、运行时自检、Smoke 报告查看、VN 导出、Provider Matrix 查看、上下文快照查看等大量能力

这说明：

- 功能已经很丰富
- 但 UI 层和业务编排层高度耦合
- 后续大改时，前端应优先拆分

## 4. 项目结构

```text
WriterLab-v1/
├─ docs/
│  ├─ runtime-notes.md
│  └─ project-overview-zh.md
├─ fastapi/
│  └─ backend/
│     ├─ alembic/
│     ├─ app/
│     │  ├─ api/
│     │  ├─ db/
│     │  ├─ models/
│     │  ├─ schemas/
│     │  └─ services/
│     ├─ tests/
│     ├─ requirements.txt
│     └─ requirements.codex.txt
├─ Next.js/
│  └─ frontend/
│     ├─ app/
│     │  ├─ editor/
│     │  ├─ lore/
│     │  └─ project/
│     ├─ public/
│     └─ package.json
└─ scripts/
   ├─ start-backend.ps1
   ├─ start-frontend.ps1
   ├─ check-backend.ps1
   ├─ check-frontend.ps1
   ├─ backend_full_smoke.py
   └─ frontend_live_smoke.mjs
```

## 5. 后端结构说明

### 5.1 `app/api`

按资源和能力分路由：

- `projects.py` 项目
- `books.py` 书
- `chapters.py` 章节
- `scenes.py` 场景、场景上下文、场景版本
- `characters.py` 角色
- `locations.py` 地点
- `lore_entries.py` 世界观设定
- `knowledge.py` 知识文档、检索、风格记忆
- `ai.py` 分析、写作、润色、工作流
- `consistency.py` 一致性扫描
- `branches.py` 剧情分支
- `vn.py` VN 导出
- `settings.py` Provider 配置
- `health.py` 健康检查
- `runtime.py` 运行态、自检、事件流、Smoke 报告

### 5.2 `app/services`

这是后端真正的业务核心：

- `workflow_service.py`
  工作流引擎，负责排队、执行、恢复、覆盖、取消、事件发布、版本写回、记忆生成
- `ai_gateway_service.py`
  统一模型网关，负责 provider matrix、fallback、限流、预算、熔断、fixture 模式
- `context_service.py`
  负责为场景拼装上下文，并记录 compile snapshot
- `knowledge_service.py`
  负责知识文档切块、embedding、pgvector / fallback 检索
- `consistency_service.py`
  负责规则型一致性问题和 LLM 复核问题
- `scene_analysis_service.py`
  负责分析结果解析与兜底
- `scene_write_service.py`
  负责生成正文与约束补强
- `scene_revise_service.py`
  负责润色正文
- `scene_version_service.py`
  负责版本记录与恢复
- `branch_service.py`
  负责分支创建、diff、采纳
- `runtime_status_service.py`
  负责启动状态记录
- `runtime_events.py`
  负责运行时事件缓冲
- `smoke_report_service.py`
  负责 smoke 报告读取、摘要、回归比较

### 5.3 `app/models`

当前数据模型可以概括为 4 组：

- 内容主线：
- `Project` -> `Book` -> `Chapter` -> `Scene`
- 设定与上下文：
- `Character`
- `Location`
- `LoreEntry`
- `TimelineEvent`
- `KnowledgeDocument`
- `KnowledgeChunk`
- `StyleMemory`
- 创作过程资产：
- `SceneVersion`
- `StoryBranch`
- `ConsistencyIssue`
- 执行与路由：
- `ModelProfile`
- `AIRun`
- `WorkflowRun`
- `WorkflowStep`
- `WorkflowRequestDedup`
- `VRAMLock`
- `StyleNegativeRule`

## 6. 关键领域模型

### 6.1 内容层级

- `Project`
  最上层项目，包含名称、题材、默认语言
- `Book`
  隶属于项目，表示一本书或一个长篇主线
- `Chapter`
  隶属于书，包含章号、标题、摘要
- `Scene`
  当前系统最核心的创作单元，包含：
  标题、POV、地点、时间标签、目标、冲突、结果、必写项、禁写项、正文、状态、版本号

### 6.2 创作过程资产

- `SceneVersion`
  每次正文变化都会记录版本快照，可恢复
- `StoryBranch`
  用于“从某场景版本分叉出支线”
- `WorkflowRun`
  一次完整场景工作流的主记录
- `WorkflowStep`
  工作流中的单步执行记录，带 provider/model/耗时/输出快照/是否被人工覆盖等信息

### 6.3 设定与记忆

- `LoreEntry`
  项目级设定条目
- `KnowledgeDocument` + `KnowledgeChunk`
  文档化知识库与切块检索索引
- `StyleMemory`
  可确认、可作用域控制的写作风格记忆
- `TimelineEvent`
  项目 / 章节 / 场景级时间线事件

## 7. API 能力总览

### 7.1 内容资源

- `GET/POST /api/projects`
- `GET/POST /api/books`
- `GET/POST /api/chapters`
- `GET/POST/PATCH /api/scenes`
- `GET /api/scenes/{scene_id}/context`
- `GET /api/scenes/{scene_id}/bundle`
- `GET /api/scenes/{scene_id}/versions`
- `POST /api/scenes/{scene_id}/versions/{version_id}/restore`
- `GET/POST /api/characters`
- `GET/POST/PATCH /api/locations`
- `GET/POST /api/lore_entries`

### 7.2 AI 与工作流

- `GET /api/ai/provider-matrix`
- `POST /api/ai/analyze-scene`
- `POST /api/ai/write-scene`
- `POST /api/ai/revise-scene`
- `GET /api/ai/scenes/{scene_id}/analyses`
- `POST /api/ai/analyses/{analysis_id}/selection`
- `POST /api/ai/workflows/scene`
- `POST /api/ai/workflows/scene/run-sync`
- `GET /api/ai/workflows/{workflow_id}`
- `POST /api/ai/workflows/{workflow_id}/resume`
- `POST /api/ai/workflows/{workflow_id}/steps/{step_key}/override`
- `POST /api/ai/workflows/{workflow_id}/cancel`

### 7.3 设定、记忆、检索

- `POST /api/knowledge/documents`
- `POST /api/knowledge/retrieve`
- `GET /api/knowledge/search`
- `POST /api/knowledge/reindex`
- `GET/POST /api/knowledge/style-memories`
- `POST /api/knowledge/style-memories/{memory_id}/confirm`

### 7.4 审查、分支、导出、运行态

- `POST /api/consistency/scan`
- `GET/POST /api/branches`
- `GET /api/branches/{branch_id}/diff`
- `POST /api/branches/{branch_id}/adopt`
- `POST /api/vn/export`
- `GET /api/health`
- `GET /api/runtime/provider-state`
- `GET /api/runtime/self-check`
- `GET /api/runtime/smoke-reports`
- `GET /api/runtime/smoke-reports/latest`
- `GET /api/runtime/smoke-reports/{filename}`
- `GET /api/runtime/smoke-reports/{filename}/regression`
- `WS /api/runtime/events`

## 8. 工作流设计

当前工作流大致是：

1. `analyze`
2. `plan`
3. `write`
4. `style`
5. `check`
6. `guard`
7. `store`
8. `memory`

特点：

- 有后台 runner 轮询执行
- 有 lease / heartbeat / 恢复机制
- 支持 fixture smoke 场景
- 支持人工 review 后恢复
- 支持下游步骤失效与重跑
- 支持 request 去重
- 支持 VRAM 锁

这部分已经不只是“调用几个模型”，而是一个真正的后端编排器。

## 9. Provider 路由策略

在默认策略里：

- `analyze` / `planner`
  优先 `deepseek`，失败回退 `ollama`
- `write`
  优先 `openai`，失败回退 `ollama`
- `style` / `revise`
  优先 `xai`，失败回退 `ollama`
- `check`
  默认本地优先 `ollama`

另外还做了：

- 超时控制
- 重试次数
- 每分钟请求限制
- 月度预算控制
- Provider 熔断与冷却
- 运行时 readiness 汇总

## 10. 测试与验收现状

### 10.1 单元 / 接口测试

`fastapi/backend/tests` 已覆盖的重点包括：

- provider matrix、熔断、限流、预算、fallback
- AI 输出 guardrail
- workflow 恢复、override、等待人工 review、fixture 场景
- context compile snapshot
- consistency 规则检查
- branch diff / adopt
- VN export
- runtime smoke report 汇总与 regression compare
- 关键 API contract

### 10.2 Smoke 脚本

项目还提供了偏验收级的脚本：

- `scripts/check-backend.ps1`
  后端静态检查 + 健康检查 + 可选 full smoke
- `scripts/check-frontend.ps1`
  前端 typecheck + build 检查 + 可选 live UI smoke
- `scripts/backend_full_smoke.py`
  通过 API 走完整工作流链路
- `scripts/frontend_live_smoke.mjs`
  直接拉取 `/editor` HTML，校验关键标记是否存在

说明这套项目已经开始重视“可运行验收”，这对后续大改是好事。

## 11. 当前明显问题 / 风险

### 11.1 前端过于集中

- `app/editor/page.tsx` 超过 2200 行
- 业务状态、接口调用、展示层都混在一个页面里
- 不适合继续横向扩功能

### 11.2 前端产品形态不完整

- `/project` 和 `/lore` 还是占位页
- 没有完整的项目管理、章节管理、角色管理、地点管理专页
- 当前更像内部调试控制台

### 11.3 编码 / 文案乱码问题

- 多个页面和后端返回文案里出现明显乱码
- 例如首页、占位页、部分一致性提示、Provider 设置返回消息、fixture 文本
- 大改前建议先统一文件编码和文本来源

### 11.4 依赖声明有分裂

- `requirements.txt` 很精简
- `requirements.codex.txt` 才包含 `SQLAlchemy`、`alembic`、`httpx`、`python-dotenv`、`pytest`、`psycopg`
- 但实际后端代码和检查脚本明显依赖这些包

这意味着：

- 依赖管理还不够收敛
- 新环境部署时容易踩坑

### 11.5 Schema 管理存在“双轨”

- 有 Alembic
- 同时也有 `schema_upgrades.py` 在启动时直接执行 DDL

这在快速迭代期很实用，但后期会带来：

- 数据库状态来源不单一
- 迁移审计变难
- 环境差异更难排查

## 12. 适合大改的切入方式

如果你准备“大改”，我建议优先按下面顺序拆：

### 路线 A：先稳后改

1. 先修编码 / 文案乱码
2. 合并依赖声明
3. 把 `/editor` 拆成组件、hooks、API client
4. 再决定是否重做页面结构

适合：你想保留现有后端能力，主要重做前端体验

### 路线 B：前后端一起重构

1. 抽出领域边界：
   `content` / `knowledge` / `workflow` / `runtime`
2. 后端 service 进一步模块化
3. 前端改成真正的多页或模块化工作台
4. 最后再统一运行态和测试入口

适合：你要长期维护这个项目，并继续扩写作工作流

### 路线 C：保留引擎，重写壳层

1. 保留：
   `workflow_service`
   `ai_gateway_service`
   `context_service`
   `knowledge_service`
2. 重写前端
3. 只保留必要 API，对调试接口降级或内聚到 admin/debug 区

适合：你认可后端思路，但不想继续沿用现在这套 UI 结构

## 13. 我对当前项目的判断

这是一个“后端能力已经比前端成熟”的项目：

- 后端已经具备工作流编排器雏形
- 检索、记忆、守门、回滚、分支、运行态观测都已经接上了
- 前端则明显还停在“单页调试台快速堆功能”的阶段

所以如果你要大改，最优先的通常不是“全部推倒重来”，而是：

- 保留核心领域模型和 workflow 引擎
- 重做前端结构
- 顺手把编码、依赖、迁移策略这些基础问题收拾干净

## 14. 改造前建议先确认的 5 件事

1. 你是要保留当前数据库结构，还是愿意做破坏性迁移
2. 你是否还要保留“调试控制台”这一形态
3. 你后续主打的是“小说写作台”还是“AI 工作流平台”
4. 你是否继续保留多 Provider 路由和本地 Ollama fallback
5. 你是否要让知识库 / 世界观 / 角色管理变成一等前端模块

---

如果接下来要继续，我建议下一步直接做一份“重构方案文档”，把：

- 保留模块
- 拆分模块
- 删除模块
- 新目录结构
- 分阶段迁移顺序

也一起定出来。
