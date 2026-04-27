## 项目上下文摘要（repository-restructure）

生成时间：2026-04-24 00:00:00

### 1. 相似实现分析

- **实现1**: `D:/WritierLab/README.md`
  - 模式：仓库根入口文档
  - 可复用：总览、仓库结构、启动与验证导航
  - 需注意：当前仍把主应用描述为 `WriterLab-v1/` 子工作区，适合作为旧结构基线，不适合作为目标结构

- **实现2**: `D:/WritierLab/WriterLab-v1/readme.md`
  - 模式：应用工作区入口文档
  - 可复用：模块清单、运行命令、核心能力列表
  - 需注意：它把 `fastapi/backend`、`Next.js/frontend`、`docs`、`scripts` 都挂在 `WriterLab-v1/` 下，是本轮要被上提和拆分的主要来源

- **实现3**: `D:/WritierLab/WriterLab-v1/docs/local-verification-zh.md`
  - 模式：本地验证总入口
  - 可复用：前端/后端检查顺序、smoke 命令、脚本说明、报告位置
  - 需注意：路径与脚本命令大量硬编码 `WriterLab-v1/`，迁移时必须系统修复

- **实现4**: `D:/WritierLab/WriterLab-v1/docs/runtime-notes.md`
  - 模式：运行手册与 smoke runbook
  - 可复用：启动顺序、运行时自检、failure interpretation、smoke matrix
  - 需注意：当前与本地验证说明、根 README 存在内容交叉，需要在新文档体系中按职责拆分

- **实现5**: `D:/WritierLab/WriterLab-v1/fastapi/backend/tests/README.md`
  - 模式：后端测试索引
  - 可复用：测试入口、分类说明、薄入口策略
  - 需注意：迁移后应转换为仓库级 `docs/verification/backend-tests-index.md`，而不是继续埋在应用子目录里承担导航职责

- **实现6**: `D:/WritierLab/WriterLab-v1/Next.js/frontend/tests/README.md`
  - 模式：前端测试索引
  - 可复用：前端验证现状、smoke 覆盖、测试入口
  - 需注意：应与后端测试索引一起并入统一验证文档层，而不是继续作为分散入口

- **实现7**: `D:/WritierLab/WriterLab-v1/scripts/*`
  - 模式：脚本平铺目录
  - 可复用：`start-*`、`check-*`、`*_smoke`、`fix_demo_*` 等职责明确的脚本文件
  - 需注意：脚本本身已按用途形成自然分层，但目录尚未按职责归类，迁移后应改为 `dev / check / smoke / data / logs`

### 2. 项目约定

- **命名约定**:
  - 仓库说明文档使用中文标题与分章节结构
  - 脚本文件延续现有英文命名，如 `check-backend.ps1`、`frontend_live_smoke.mjs`
  - 目录名应优先表达稳定语义，而不是实现细节或历史版本号

- **文件组织**:
  - 当前结构以 `WriterLab-v1/` 作为应用壳层
  - 根目录负责总 README、AGENTS、`.codex/` 和外围资源
  - 文档、脚本、测试说明实际已经具备仓库级职责，但仍被挂在旧壳层内部

- **代码与文档风格**:
  - 文档使用“概览 → 边界 → 结构 → 命令/验证 → 风险/说明”的写法
  - 命令示例以 PowerShell 与 Windows 绝对路径为主
  - 现有 spec 文档采用“设计目标、范围边界、当前基线、方案选择、验证、风险、结论”的结构

### 3. 可复用组件清单

- `D:/WritierLab/README.md`
- `D:/WritierLab/WriterLab-v1/readme.md`
- `D:/WritierLab/WriterLab-v1/docs/local-verification-zh.md`
- `D:/WritierLab/WriterLab-v1/docs/runtime-notes.md`
- `D:/WritierLab/WriterLab-v1/fastapi/backend/tests/README.md`
- `D:/WritierLab/WriterLab-v1/Next.js/frontend/tests/README.md`
- `D:/WritierLab/WriterLab-v1/scripts/check-backend.ps1`
- `D:/WritierLab/WriterLab-v1/scripts/check-frontend.ps1`
- `D:/WritierLab/WriterLab-v1/scripts/backend_full_smoke.py`
- `D:/WritierLab/WriterLab-v1/scripts/frontend_live_smoke.mjs`

### 4. 测试策略

- **当前测试框架**:
  - 后端：`pytest`
  - 前端：`npm.cmd run typecheck`、`check-frontend.ps1`、`frontend_live_smoke.mjs`
  - 仓库级验证核心仍然是脚本入口和文档命令一致性

- **迁移后需要保持的验证面**:
  - 后端检查入口仍可通过新脚本路径运行
  - 前端检查入口仍可通过新脚本路径运行
  - backend/full smoke 与 frontend/live smoke 报告输出仍稳定落到 `scripts/logs/`
  - 文档命令、脚本内部路径和实际目录结构一致

### 5. 依赖和集成点

- **应用目录集成**:
  - `WriterLab-v1/fastapi/backend` 与 `WriterLab-v1/Next.js/frontend` 是本轮上提的核心目标
- **文档集成**:
  - 根 `README.md`、`WriterLab-v1/readme.md`、`WriterLab-v1/docs/*.md`、测试 README 之间存在多点导航关系
- **脚本集成**:
  - `check-*`、`start-*`、`*_smoke` 之间形成启动与验证闭环
  - 报告输出依赖 `scripts/logs/`
- **路径风险**:
  - 多份文档与脚本命令显式引用 `D:/WritierLab/WriterLab-v1/...`
  - 若目录上提后不统一修复，会直接造成运行与验证说明失效

### 6. 技术选型理由

- **为什么不继续保留 `WriterLab-v1/`**:
  - 该目录名携带历史版本语义，不适合作为长期仓库主入口
  - 它让文档、脚本和验证入口额外挂了一层无业务意义的壳

- **为什么采用 `apps / docs / scripts` 的标准分层**:
  - 可以稳定表达“应用、文档、脚本”三种长期职责
  - 能自然收口仓库入口、运行手册和验证体系
  - 为后续继续扩展工作节点保留空间，但不提前引入过重的 monorepo 设施

- **为什么不走彻底 monorepo 化**:
  - 当前仓库还没有明显的 `packages/`、共享 SDK 或多应用并行需求
  - 本轮目标是结构标准化，而不是工具链重构

### 7. 关键风险点

- **路径漂移风险**: 文档与脚本中旧路径很多，必须成体系地修，不适合零散手改
- **双入口并存风险**: 若保留 `WriterLab-v1/` 作为半兼容层，后续文档和命令会再次分叉
- **脚本硬编码风险**: 现有 PowerShell 命令多用绝对路径，迁移后需要统一改为新路径，最好进一步改成基于脚本位置推导仓库根
- **验证错位风险**: 如果先搬目录不先修说明和脚本，很容易造成“代码没坏但入口全失效”的假回归
- **工具可用性限制**: 当前会话未提供 `desktop-commander`、`context7`、`github.search_code`、`sequential-thinking`、`shrimp-task-manager` 等专用工具，因此本轮上下文收集改用仓库内现有文档、脚本、Git 历史与结构化人工分析，并在 `operations-log.md` 中留痕
