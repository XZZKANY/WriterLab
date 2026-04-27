# WritierLab 仓库结构标准化重构设计

生成时间：2026-04-24

## 1. 设计目标

本设计文档用于定义 WritierLab 在本轮“仓库级结构重构”中的目标边界：把当前挂在 `WriterLab-v1/` 下的应用、文档、脚本和验证入口，上提为标准仓库结构，并形成单一主入口。

本轮目标不是重写业务逻辑，而是完成一轮可验证、可回滚、可长期维护的仓库治理收口：

- 把 `WriterLab-v1/fastapi/backend` 与 `WriterLab-v1/Next.js/frontend` 上提为标准应用目录
- 把当前分散的说明文档重组为仓库级 `docs/` 体系
- 把平铺脚本改为按职责归类的 `scripts/` 体系
- 把启动、检查、smoke 与测试说明统一成一套仓库级验证入口
- 删除 `WriterLab-v1/` 这一历史壳层作为长期主入口的角色

本设计已经明确采用“上提为标准仓库结构”的方向，并默认使用**标准应用分层方案**，而不是保留 `WriterLab-v1/` 或进一步扩张为完整 monorepo 工具链改造。

## 2. 范围边界

### 2.1 本轮纳入范围

- 仓库主结构重排：`apps / docs / scripts / .codex / pgvector-src / README.md / AGENTS.md`
- 应用目录迁移：
  - `WriterLab-v1/fastapi/backend` → `apps/backend`
  - `WriterLab-v1/Next.js/frontend` → `apps/frontend`
- 文档体系重组：根 README、运行手册、本地验证说明、测试索引、仓库结构说明
- 脚本体系重组：启动、检查、smoke、数据修复、日志目录
- 路径与命令修复：脚本、文档、测试说明、报告位置、绝对路径示例
- 迁移说明与本地验证留痕

### 2.2 本轮明确不做

- 后端 service、repository、router 的业务语义重写
- 前端状态管理、页面结构或交互逻辑重构
- 新增 `packages/`、workspace manager、统一构建器等重型 monorepo 设施
- 新建 CI 或远程流水线作为主要验证方式
- 在本轮结构迁移中顺手扩展 workflow、timeline、branch、runtime 等业务能力

## 3. 当前基线

### 3.1 当前主入口存在历史壳层

当前仓库根 `README.md` 已承担总入口职责，但真实应用、深度文档、脚本和测试说明都还挂在 `WriterLab-v1/` 下。`WriterLab-v1/` 既不像标准的 `apps/` 容器，也不是单纯的归档目录，而是一个历史版本名驱动的壳层。

这种结构带来两个实际问题：

- 新进入仓库的人必须先理解“为什么主应用还在 `WriterLab-v1/`”
- 文档、脚本和命令都被迫携带这层历史路径，增加路径噪音和迁移成本

### 3.2 文档入口分散且职责交叉

当前至少存在以下入口：

- 根 `README.md`
- `WriterLab-v1/readme.md`
- `WriterLab-v1/docs/local-verification-zh.md`
- `WriterLab-v1/docs/runtime-notes.md`
- `WriterLab-v1/fastapi/backend/tests/README.md`
- `WriterLab-v1/Next.js/frontend/tests/README.md`

这些文档都是真实有效的，但它们之间存在职责交叉：

- 仓库入口、应用入口、运行手册、验证入口没有完全按层分开
- 同一条命令可能在多处出现
- 测试索引承担了部分仓库验证导航职责，却仍留在应用内部目录中

### 3.3 脚本职责已存在，但目录未表达出来

`WriterLab-v1/scripts/` 当前已经自然分出几类脚本：

- 启动/开发：`start-backend.ps1`、`start-frontend.ps1`、`dev-stack.ps1`、`install-backend.ps1`
- 检查：`check-backend.ps1`、`check-frontend.ps1`
- smoke：`backend_full_smoke.py`、`frontend_live_smoke.mjs`
- 数据修复：`fix_demo_garbled_data.py`
- 报告：`logs/`

也就是说，问题不在“缺脚本”，而在“脚本入口仍平铺在历史壳层里”，不利于长期治理。

### 3.4 验证链路已成型，但路径耦合旧结构

当前验证方式并不薄弱：

- 后端有 `pytest` 与 `check-backend.ps1`
- 前端有 `typecheck`、`check-frontend.ps1`、`frontend_live_smoke.mjs`
- 运行手册已定义 smoke matrix 与报告读取方式

真正的问题是：文档、命令和脚本都显式依赖 `WriterLab-v1/` 路径。一旦结构上提，不同步修复就会造成验证入口整体失效。

## 4. 方案选择

### 4.1 方案 A：最小标准化上提

直接把 `WriterLab-v1/` 下的主内容上提到仓库根，保留 `fastapi/`、`Next.js/` 等原始名称。

优点：

- 迁移路径最短
- 现有代码目录名改动较少

缺点：

- 目录名仍然过于技术实现导向
- 后续如果继续扩应用或增加辅助节点，结构会再次失衡

### 4.2 方案 B：标准应用分层上提（推荐）

把当前应用、文档、脚本上提为仓库标准分层：

- `apps/`
- `docs/`
- `scripts/`

并在其内部进一步按职责稳定命名。

优点：

- 结构语义清晰，长期维护成本最低
- 文档、脚本、验证入口都能自然收口
- 既标准化，又不过度工程化

缺点：

- 路径变更最多
- 需要系统更新现有文档与脚本路径

### 4.3 方案 C：彻底 monorepo 化

在方案 B 的基础上进一步引入 `packages/`、共享工具层与更完整的 workspace 设施。

优点：

- 可扩展性最强

缺点：

- 明显超出本轮任务边界
- 会把“仓库结构重构”扩大为“工程系统重构”

### 4.4 方案结论

本轮明确采用**方案 B：标准应用分层上提**。

理由：

- 它能直接回应“目录、文档、脚本、验证流程统一”这一目标
- 它比方案 A 更能解决长期治理问题
- 它又比方案 C 更克制，不会把任务扩大成工具链革命

## 5. 目标拓扑设计

本轮重构完成后的目标拓扑如下：

```text
WritierLab/
├─ apps/
│  ├─ backend/
│  └─ frontend/
├─ docs/
│  ├─ architecture/
│  ├─ project/
│  ├─ runbooks/
│  └─ verification/
├─ scripts/
│  ├─ check/
│  ├─ data/
│  ├─ dev/
│  ├─ logs/
│  └─ smoke/
├─ .codex/
├─ pgvector-src/
├─ README.md
└─ AGENTS.md
```

该拓扑遵循四条原则：

1. **应用归应用**：主业务代码统一收进 `apps/backend` 与 `apps/frontend`
2. **文档按用途分层**：结构说明、项目概览、运行手册、验证说明分开承载
3. **脚本按职责归类**：开发、检查、smoke、数据修复、日志目录一眼可见
4. **根入口只保留总导航**：根 `README.md` 不再与子级文档争夺职责

## 6. 迁移设计

### 6.1 应用目录迁移

本轮采用一次性上提，而不是保留长期双结构：

- `WriterLab-v1/fastapi/backend` → `apps/backend`
- `WriterLab-v1/Next.js/frontend` → `apps/frontend`

这里不重写业务代码，只修复因目录移动导致的路径、说明和脚本引用。

### 6.2 文档重组映射

文档重组后的建议映射如下：

- 根 `README.md`
  - 仓库总入口、目录导航、快速启动与验证跳转
- `docs/architecture/repository-layout.md`
  - 新仓库结构说明、目录职责、旧路径到新路径映射
- `docs/project/overview.md`
  - 项目定位、能力概览、应用模块说明
- `docs/runbooks/runtime-runbook.md`
  - 启动顺序、运行时说明、self-check、smoke matrix、故障解释
- `docs/verification/local-verification.md`
  - 本地检查顺序、关键命令、smoke 报告位置
- `docs/verification/backend-tests-index.md`
  - 后端测试索引与薄入口说明
- `docs/verification/frontend-tests-index.md`
  - 前端测试索引与 smoke 入口说明

### 6.3 脚本重组映射

脚本重组后的建议映射如下：

- `scripts/dev/`
  - `start-backend.ps1`
  - `start-frontend.ps1`
  - `dev-stack.ps1`
  - `install-backend.ps1`
- `scripts/check/`
  - `check-backend.ps1`
  - `check-frontend.ps1`
- `scripts/smoke/`
  - `backend_full_smoke.py`
  - `frontend_live_smoke.mjs`
- `scripts/data/`
  - `fix_demo_garbled_data.py`
- `scripts/logs/`
  - 保留 smoke 报告与检查报告输出目录职责

### 6.4 路径策略

本轮迁移完成后，应统一遵循以下路径策略：

- 所有新文档只使用新路径表达主入口
- 旧 `WriterLab-v1/` 只允许出现在迁移说明或历史上下文中
- 能通过脚本位置推导仓库根的脚本，应优先改为基于脚本位置推导，而不是继续硬编码 `D:/WritierLab/WriterLab-v1/...`
- 示例命令可继续使用 PowerShell 与 Windows 绝对路径，但必须对齐新结构

## 7. 兼容与收口策略

### 7.1 采用破坏式收口，不保留长期双入口

本轮不建议保留长期兼容层，不保留“旧路径镜像文档”“双份脚本”“双份应用入口”。

原因很明确：

- 仓库级重构最怕双结构并存
- 只要旧入口还能继续用，后续文档与脚本就会重新分叉
- 这次任务目标是统一，而不是温和共存

### 7.2 保留的唯一历史承接物

为了降低迁移成本，可以保留且只保留以下两类承接物：

- `docs/architecture/repository-layout.md` 中的旧 → 新路径映射
- `.codex/` 与现有历史 spec 中对 `WriterLab-v1/` 的背景记录

除此之外，不新增长期兼容壳层。

## 8. 文档治理设计

### 8.1 根 README 的单一职责

根 `README.md` 只承担以下职责：

- 项目一句话定位
- 仓库主结构说明
- 快速启动入口
- 本地验证入口
- 关键文档导航

它不再重复承载深度 runbook、测试索引或模块级细节。

### 8.2 二级文档职责拆分

- `docs/architecture/`：结构与映射
- `docs/project/`：项目与模块概览
- `docs/runbooks/`：运行与排障
- `docs/verification/`：测试与验证命令

这样可以避免“同一条命令在三份文档里维护”的情况。

## 9. 验证设计

### 9.1 验证目标

本轮结构重构的验证重点不是业务逻辑新功能，而是四件事：

1. **结构正确**：目标目录真实存在，旧壳层不再作为主入口
2. **引用正确**：文档、脚本、测试说明中的路径与实际结构一致
3. **入口正确**：启动、检查、smoke 命令都指向新路径
4. **留痕完整**：迁移说明、上下文摘要、操作记录、验证报告齐全

### 9.2 推荐验证面

至少需要验证以下入口在新结构下仍有一致表达：

- 后端开发启动入口
- 前端开发启动入口
- 后端检查入口
- 前端检查入口
- backend full smoke 入口
- frontend live smoke 入口

### 9.3 推荐命令表达（目标态）

```powershell
powershell -ExecutionPolicy Bypass -File D:\WritierLab\scripts\dev\start-backend.ps1
powershell -ExecutionPolicy Bypass -File D:\WritierLab\scripts\dev\start-frontend.ps1
powershell -ExecutionPolicy Bypass -File D:\WritierLab\scripts\check\check-backend.ps1
powershell -ExecutionPolicy Bypass -File D:\WritierLab\scripts\check\check-frontend.ps1
powershell -ExecutionPolicy Bypass -File D:\WritierLab\scripts\check\check-backend.ps1 -FullSmoke
powershell -ExecutionPolicy Bypass -File D:\WritierLab\scripts\check\check-frontend.ps1 -LiveUiSmoke
```

如果环境限制导致完整命令无法在受限 shell 下跑通，至少也必须证明：

- 命令所指向的新文件存在
- 脚本内部引用与新路径一致
- 文档中对应入口与脚本位置一致

## 10. 实施顺序设计

本轮实施建议分为六个阶段：

1. **建立新拓扑骨架**
   - 先创建 `apps/`、`docs/`、`scripts/` 及其子目录
2. **迁移应用目录**
   - 上提 `backend` 与 `frontend`
3. **迁移与重组脚本**
   - 将脚本归类到 `dev / check / smoke / data / logs`
4. **重写并统一文档**
   - 写新根 README 与新的仓库级二级文档
5. **全量修复路径引用**
   - 修文档、脚本、报告路径与测试说明
6. **删除旧壳并完成验证**
   - 清理 `WriterLab-v1/` 主入口角色，输出迁移说明与验证报告

这一顺序的原则是：

> 先建新结构，再迁内容；先修引用，再删旧壳。

## 11. 风险与约束

- **脚本硬编码失效风险**：这是本轮最大真实风险，必须系统搜索并集中修复
- **文档再次分叉风险**：如果只搬文件不重写职责，很快又会回到多入口混乱状态
- **验证命令过时风险**：结构改完后，文档命令和脚本命令必须同步更新
- **双入口并存风险**：如果保留旧 `WriterLab-v1/` 兼容层，后续治理会再次失败
- **范围膨胀风险**：本轮必须克制在“仓库治理层”，不扩散到业务逻辑重写

## 12. 验收标准

本轮结构重构完成后，应满足以下标准：

1. 仓库主结构以 `apps / docs / scripts` 为唯一主入口
2. 根 `README.md` 可以单点导航到应用、文档、运行与验证入口
3. `scripts/` 目录按职责清晰分层
4. 仓库中不再把 `WriterLab-v1/` 当作主运行路径引用
5. 启动、检查、smoke 入口在新结构下具有一致路径表达
6. `.codex`、迁移说明与验证报告留痕齐全

## 13. 交付结论

本设计已经明确以下决策：

- 采用“标准应用分层上提”方案
- 目标拓扑为 `apps / docs / scripts` 主导的仓库结构
- 采用破坏式收口，不保留长期双入口
- 本轮只做结构、文档、脚本和验证流程统一，不改业务逻辑语义

该设计文档确认后，下一步才进入 implementation plan。implementation plan 必须继承本文件的边界：以仓库治理层改造为主，不允许重新扩张为业务架构重写或完整 monorepo 改造。
