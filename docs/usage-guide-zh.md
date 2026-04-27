# WriterLab 使用指南

> 本文面向实际使用 WriterLab 进行小说创作的用户。系统定位是"场景级 AI 写作工作台"，而不是通用写作 App——它的核心是把 AI 能力有组织地嵌入到你的创作流程里。

---

## 目录

1. [基本概念](#1-基本概念)
2. [启动系统](#2-启动系统)
3. [第一次使用：创建项目结构](#3-第一次使用创建项目结构)
4. [编辑器主界面](#4-编辑器主界面)
5. [AI 写作功能](#5-ai-写作功能)
6. [完整工作流（推荐路径）](#6-完整工作流推荐路径)
7. [版本管理与分支](#7-版本管理与分支)
8. [上下文与知识库](#8-上下文与知识库)
9. [Provider 设置](#9-provider-设置)
10. [运行时健康检查](#10-运行时健康检查)
11. [常见问题](#11-常见问题)

---

## 1. 基本概念

WriterLab 用层级结构组织你的创作内容：

```
项目 (Project)
└─ 书 (Book)
   └─ 章节 (Chapter)
      └─ 场景 (Scene)  ← 最小工作单元
```

**场景**是所有 AI 能力的入口。每个场景有：

- `draft_text`：当前正文草稿
- `must_include`：必须出现的元素（角色行为、关键台词等）
- `must_avoid`：必须回避的内容
- `guidance`：对 AI 的额外写作指引

---

## 2. 启动系统

### 日常启动（两个终端）

**终端 1 — 后端：**
```powershell
powershell -ExecutionPolicy Bypass -File D:\WritierLab\scripts\dev\start-backend.ps1
```
看到 `Uvicorn running on http://127.0.0.1:8000` 表示启动成功。

**终端 2 — 前端：**
```powershell
powershell -ExecutionPolicy Bypass -File D:\WritierLab\scripts\dev\start-frontend.ps1
```
看到 `Ready in ...ms` 后打开浏览器访问 <http://127.0.0.1:3000/editor>。

### 启动顺序说明

后端启动时会自动完成三件事：
1. 校验 Alembic 迁移状态（数据库结构是否最新）
2. 恢复上次意外中断的工作流（重新排队）
3. 启动后台 workflow runner（负责异步处理 AI 任务）

如果后端日志出现 `WARNING schema not ready` 或 `alembic` 相关错误，先手动跑一次迁移：
```powershell
cd D:\WritierLab\apps\backend
.\.venv\Scripts\python.exe -m alembic upgrade head
```

---

## 3. 第一次使用：创建项目结构

目前项目/书/章节/场景的创建入口在 `/project` 与编辑器的侧边面板。推荐按以下顺序操作：

1. 访问 <http://127.0.0.1:3000/project>，新建一个**项目**（填项目名称即可）
2. 在项目内新建一本**书**
3. 在书内新建一个**章节**
4. 在章节内新建一个**场景**，场景是你后续写作的基础单元

场景创建后，在编辑器里选中它，就可以开始使用 AI 功能。

---

## 4. 编辑器主界面

访问 <http://127.0.0.1:3000/editor>，页面布局如下：

```
┌────────────────────────────────────────┐
│  顶部：场景选择器 + 状态 + 操作按钮     │
├──────────────────────┬─────────────────┤
│                      │                 │
│  左侧：正文编辑区     │ 右侧：上下文侧边栏│
│  （写作/版本 两个Tab）│ （分析/规划/记忆）│
│                      │                 │
└──────────────────────┴─────────────────┘
```

### 顶部操作栏

- **场景选择器**：切换当前编辑的场景（跨项目/书/章节）
- **状态标签**：显示场景当前状态（`draft` / `analyzed` / `complete` 等）
- **分析 / 写作 / 润色 / 工作流** 等按钮：触发不同 AI 功能

### 左侧写作区

- **Writing tab**：直接编辑 `draft_text`，修改会即时保存到后端
- **Versions tab**：查看历史版本快照，可以一键恢复到任意历史版本

### 右侧上下文侧边栏

显示当前场景编译出的上下文，包括：
- POV 角色信息
- 地点设定
- 最近场景概要
- 时间线命中
- 知识库检索结果
- 已选分析建议
- 工作流调试信息

---

## 5. AI 写作功能

### 5.1 场景分析（Analyze）

**作用**：让 AI 阅读当前草稿，识别潜在问题和改进建议。

**触发方式**：编辑器顶部点击「分析」按钮，或通过工作流步骤自动触发。

**结果**：返回若干条分析项，每条包含：
- 问题类型（一致性 / 风格 / 叙事逻辑等）
- 问题位置（文本片段）
- 改进建议

分析完成后，你可以在右侧侧边栏选择哪些分析建议纳入下一步的写作上下文。

---

### 5.2 AI 写作（Write）

**作用**：基于当前场景上下文（角色、地点、记忆、分析建议）生成初稿。

**触发方式**：编辑器顶部点击「写作」按钮。

**参数说明**：

| 参数 | 说明 |
|------|------|
| `guidance` | 对本次写作的额外指引，例如"重点描写心理活动"、"保持悬疑感" |
| `length_mode` | 输出长度：`short`（500字）/ `medium`（1000字）/ `long`（2000字） |
| `provider_mode` | `auto`（线上模型）/ `local`（本地 Ollama）/ `smoke_fixture`（调试用）|

写作完成后结果自动填入 `draft_text`。

---

### 5.3 AI 润色（Revise）

**作用**：在已有草稿基础上进行局部修改，而不是整体重写。

**触发方式**：编辑器顶部点击「润色」按钮。

**模式说明**：

| `revise_mode` | 作用 |
|---------------|------|
| `trim` | 删减冗余，精简表达 |
| `literary` | 提升文学性，改善措辞 |
| `unify` | 统一语气和风格，消除前后不一致 |

---

### 5.4 一致性扫描（Consistency Scan）

**作用**：检查场景文本是否违反已定义的角色/地点/时间线约束。

**触发方式**：编辑器顶部点击「一致性」按钮。

**检测类型**：
- `must_include` 缺失（场景里要求出现的元素没有出现）
- `must_avoid` 命中（场景里出现了要回避的内容）
- 地点锚点不一致
- 时间标签冲突
- 角色外貌前后矛盾

---

## 6. 完整工作流（推荐路径）

工作流是把**分析 → 规划 → 写作 → 风格润色 → 一致性检查 → 守门**串成一个自动化链路的功能。推荐在正式写作时使用，而不是单独调用每个步骤。

### 6.1 启动工作流

编辑器顶部点击「工作流」按钮，选择运行模式：

- **队列模式（异步）**：任务进入后台队列，可以继续操作界面
- **同步模式**：阻塞等待完成（调试时用）

### 6.2 工作流步骤

工作流按顺序执行 7 个步骤：

| 步骤 | 名称 | 说明 |
|------|------|------|
| `analyze` | 场景分析 | 分析草稿质量与问题 |
| `plan` | 规划 | AI 生成写作计划（目标、约束、提示） |
| `write` | 写作 | 按规划生成正文 |
| `style` | 风格润色 | 应用风格记忆，统一语气 |
| `check` | 一致性检查 | 验证输出是否满足约束 |
| `guard` | 守门 | 拦截说明腔/分析腔/语言漂移等 AI 输出问题 |
| `store` | 保存 | 写回草稿、生成风格记忆候选、保存版本 |

### 6.3 工作流状态说明

| 状态 | 含义 |
|------|------|
| `queued` | 等待 runner 处理 |
| `running` | 正在执行某一步 |
| `waiting_user_review` | `plan` 步骤完成，等你审阅规划后决定是否继续 |
| `partial_success` | 部分步骤完成，遇到软性错误 |
| `completed` | 全部步骤完成 |
| `failed` | 某步骤失败，见错误信息 |

### 6.4 规划审阅（waiting_user_review）

当工作流到达 `waiting_user_review` 状态时，AI 已经生成了写作规划（`plan` 步骤输出），你需要：

1. 在编辑器「工作流调试」面板查看 `plan` 步骤的输出内容
2. 确认规划符合你的意图，点击「恢复」继续执行后续步骤
3. 如果规划不合适，可以在「覆盖规划」面板输入修改后的规划再继续

### 6.5 恢复（Resume）与覆盖（Override）

**恢复**：工作流意外中断（网络断开、服务重启等）后，系统会自动在启动时将其重新排队。你也可以手动从上次完成的检查点继续。

**覆盖规划**（`override`）：只对 `plan` 步骤有效。允许你替换 AI 生成的规划内容，然后从 `write` 步骤重新开始执行。

---

## 7. 版本管理与分支

### 7.1 版本快照

每次 AI 写作或润色完成后，系统会自动保存一份版本快照（`SceneVersion`）。你也可以手动在 Versions Tab 浏览历史，点击「恢复」将任意历史版本还原为当前草稿。

### 7.2 剧情分支（Branch）

**作用**：从某个版本快照创建一个平行剧情方向，不影响主线。

**用法**：
1. 在 Versions Tab 选择某个历史版本
2. 点击「创建分支」，填写分支说明
3. 在分支上继续写作
4. 完成后可以「查看差异」，或「采纳」将分支文本合并回主线

分支适合用于：
- 同一场景的多种走向对比
- 在不确定时保留两条线并排推进
- 探索性写作后只取其中一种结果

---

## 8. 上下文与知识库

### 8.1 上下文编译

AI 在写作时会自动编译当前场景的上下文，包括：

- **POV 角色**：主视角角色的外貌、性格、背景
- **地点**：场景所在地点的描述与细节
- **时间线**：当前时间节点相关的事件
- **最近场景**：当前场景前后的场景概要（保持连贯性）
- **知识文档命中**：从知识库检索到的相关片段
- **风格记忆**：已确认的写作风格规律

右侧侧边栏的「上下文」面板可以实时查看这次编译的结果和各来源的相关度得分。

### 8.2 Lore（世界观设定）

通过 `/lore` 页面管理你的世界观内容：

- **角色（Characters）**：姓名、外貌、性格、背景
- **地点（Locations）**：名称、描述、细节
- **世界观条目（Lore Entries）**：自由格式的设定条目（势力、历史事件、规则等）

这些内容会在上下文编译时自动被引用，不需要手动粘贴到每个场景。

### 8.3 知识文档

通过 `/api/knowledge` 接口（或后续前端入口）录入长篇设定文档。系统会自动切块 + 向量检索，在写作时把相关片段注入上下文。

适合用于：
- 大纲文档
- 长背景故事
- 人物关系图谱（文字描述版）

### 8.4 风格记忆

工作流完成后会生成**风格记忆候选**。你可以在「知识」面板里浏览这些候选，确认有价值的条目（点击「确认」）。

被确认的风格记忆会在后续工作流的 `style` 步骤中作为规范引用，让 AI 的输出风格逐渐向你的偏好收敛。

---

## 9. Provider 设置

访问 <http://127.0.0.1:3000/settings>，或通过编辑器顶部「设置」入口。

### 9.1 支持的 Provider

| Provider | 说明 |
|----------|------|
| `openai` | OpenAI API（GPT 系列） |
| `anthropic` | Anthropic API（Claude 系列） |
| `deepseek` | DeepSeek API |
| `ollama` | 本地 Ollama，无需 API Key |

### 9.2 配置 API Key

1. 在设置页填入对应 Provider 的 API Key
2. 点击「保存」
3. API Key 只存在后端本地文件，不上传到任何服务

### 9.3 本地 Ollama 使用

Ollama 不需要 API Key，只需要：
1. 在本机安装并启动 Ollama（<https://ollama.ai>）
2. 拉取所需模型：`ollama pull <model-name>`
3. 在工作流请求中设置 `provider_mode: "local"`

系统会自动检测 Ollama 是否可用，并在 Provider 状态面板显示。

### 9.4 Provider 矩阵与回退

每个工作流步骤（analyze / plan / write / style / check）都有独立的 Provider 优先级配置。当首选 Provider 不可用（超时/限流/熔断）时，系统会自动回退到备选 Provider，整个过程对你透明。

可以通过 <http://127.0.0.1:8000/api/ai/provider-matrix> 查看当前矩阵配置。

---

## 10. 运行时健康检查

### 10.1 快速检查

```powershell
powershell -ExecutionPolicy Bypass -File D:\WritierLab\scripts\check\check-backend.ps1
```

正常输出示例：
```
[1/4] Backend import check... backend imports ok
[2/4] Database connection check... database ok
[3/4] Alembic state check... (current head)
[4/4] Runtime API smoke check...
Health status: ok | schema_ready=True | runner_started=True | pgvector_ready=True
```

### 10.2 健康检查端点

| 端点 | 用途 |
|------|------|
| `GET /api/health` | 系统整体就绪状态 |
| `GET /api/runtime/self-check` | 详细自检报告（Provider / 工作流 / pgvector） |
| `GET /api/runtime/provider-state` | 各 Provider 的实时状态（熔断 / 限流 / 可用性） |
| `GET /api/ai/provider-matrix` | 工作流步骤与 Provider 的对应规则 |

### 10.3 完整 Smoke 测试（可选）

需要后端正在运行时执行：

```powershell
# 确定性 fixture 测试（不消耗真实 API 配额）
powershell -ExecutionPolicy Bypass -File D:\WritierLab\scripts\check\check-backend.ps1 -FullSmoke

# 指定单个场景
powershell -ExecutionPolicy Bypass -File D:\WritierLab\scripts\check\check-backend.ps1 -FullSmoke -Scenario guard_block

# 使用真实 Provider（消耗 API 配额）
powershell -ExecutionPolicy Bypass -File D:\WritierLab\scripts\check\check-backend.ps1 -FullSmoke -LiveProviders
```

Smoke 报告保存在 `scripts/logs/backend-full-smoke-<时间戳>.json`。

---

## 11. 常见问题

**Q：工作流卡在 `running` 很久不动？**

后端可能崩溃或网络中断导致租约过期。重启后端，系统会在启动时自动恢复过期的工作流，重新排队继续。

---

**Q：工作流显示 `failed`，错误信息是 `lease_expired`？**

这是正常的 crash recovery 机制——工作流在 runner 处理时 runner 意外退出，下次启动自动重试。如果反复失败，检查 `/api/health` 确认 `workflow_runner_started=True`。

---

**Q：AI 输出被 guard 拦截，提示"输出风格不符"？**

`guard` 步骤拦截了常见的 AI 输出问题（说明腔 / 分析腔 / 语言漂移）。这通常意味着当前 Provider 模型在给定上下文下输出了非叙事格式的内容。可以：
- 调整 `guidance`，明确要求"用叙事正文写，不要分析和解释"
- 切换到其他 Provider 或模型

---

**Q：`pgvector_ready=False`，知识库检索失败？**

pgvector 扩展未在 PostgreSQL 中启用。系统会自动回退到本地向量相似度检索，功能不受影响，只是检索质量略有差异。

---

**Q：前端页面报 `Failed to fetch` 或请求全部失败？**

确认后端已启动并监听 `http://127.0.0.1:8000`。检查方法：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health"
```

---

**Q：`npm run build:node` 报 `spawn EPERM`？**

这是 Windows 受限 Shell 环境的已知限制，不是代码回归。如果 `tsc --noEmit` 和 `npm run lint` 都通过，可以忽略这个错误。

---

## 快速参考

| 我想做的事 | 入口 |
|-----------|------|
| 启动后端 | `scripts\dev\start-backend.ps1` |
| 启动前端 | `scripts\dev\start-frontend.ps1` |
| 写作编辑器 | <http://127.0.0.1:3000/editor> |
| 管理世界观 | <http://127.0.0.1:3000/lore> |
| 管理项目结构 | <http://127.0.0.1:3000/project> |
| 配置 Provider | <http://127.0.0.1:3000/settings> |
| 查看运行时状态 | <http://127.0.0.1:3000/runtime> |
| 后端健康检查 | `GET /api/health` |
| 后端自检报告 | `GET /api/runtime/self-check` |
| 验证脚本（后端）| `scripts\check\check-backend.ps1` |
| 验证脚本（前端）| `scripts\check\check-frontend.ps1` |
