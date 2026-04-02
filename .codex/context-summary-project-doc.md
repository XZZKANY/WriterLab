## 项目上下文摘要（project-doc）

生成时间：2026-04-02 16:05:00

### 1. 相似实现分析

- **实现1**: `D:/WritierLab/README.md`
  - 模式：仓库根入口文档
  - 可复用：项目一句话描述、仓库结构、快速启动入口
  - 需注意：当前内容为英文且信息较薄，只适合做入口，不足以承担完整中文项目文档
- **实现2**: `D:/WritierLab/WriterLab-v1/readme.md`
  - 模式：子工作区说明文档
  - 可复用：模块清单、核心能力列表、运行命令写法
  - 需注意：职责边界在 `WriterLab-v1/`，不应直接替代仓库级 README
- **实现3**: `D:/WritierLab/WriterLab-v1/docs/project-overview-zh.md`
  - 模式：中文项目盘点文档
  - 可复用：中文章节组织方式、模块拆解、能力说明粒度
  - 需注意：该文档适合深度盘点，不适合把所有细节原样复制到根 README
- **实现4**: `D:/WritierLab/WriterLab-v1/docs/local-verification-zh.md`
  - 模式：验证说明文档
  - 可复用：前后端验证顺序、脚本入口、环境限制写法
  - 需注意：根 README 只应摘要验证路径，并链接到该文档
- **实现5**: `D:/WritierLab/WriterLab-v1/docs/runtime-notes.md`
  - 模式：运行手册
  - 可复用：启动顺序、smoke 命令、已知环境 caveat
  - 需注意：文档当前为英文，根 README 引用时应提炼出中文总览

### 2. 项目约定

- **命名约定**: 前端使用 `camelCase` 和 `PascalCase`；后端函数与文件以 `snake_case` 为主；文档文件名混合使用 `README.md` 与 `*-zh.md`
- **文件组织**:
  - 仓库根目录负责总入口和外层资源
  - `WriterLab-v1/` 是主应用工作区
  - 深度说明集中在 `WriterLab-v1/docs/`
- **导入/组织风格**: 文档普遍采用“概览 -> 模块 -> 运行/验证 -> 附加说明”的章节顺序
- **代码/文档风格**: 命令示例以 PowerShell 为主，路径常使用绝对 Windows 路径

### 3. 可复用组件清单

- `D:/WritierLab/WriterLab-v1/readme.md`: 子工作区说明模板
- `D:/WritierLab/WriterLab-v1/docs/project-overview-zh.md`: 深度盘点内容来源
- `D:/WritierLab/WriterLab-v1/docs/local-verification-zh.md`: 本地验证入口来源
- `D:/WritierLab/WriterLab-v1/docs/runtime-notes.md`: 运行与 smoke 说明来源
- `D:/WritierLab/WriterLab-v1/scripts/check-backend.ps1`: 后端验证脚本入口
- `D:/WritierLab/WriterLab-v1/scripts/check-frontend.ps1`: 前端验证脚本入口

### 4. 测试策略

- **测试框架/方式**:
  - 后端：`pytest`
  - 前端：`typecheck + build + live smoke`
- **参考文件**:
  - `D:/WritierLab/WriterLab-v1/fastapi/backend/tests/README.md`
  - `D:/WritierLab/WriterLab-v1/Next.js/frontend/tests/README.md`
  - `D:/WritierLab/WriterLab-v1/docs/local-verification-zh.md`
- **本轮验证重点**:
  - README 内容与现有结构一致
  - 命令、目录和文档路径准确可读
  - `.codex` 留痕文件补齐

### 5. 依赖和集成点

- **前端依赖**: Next.js 16、React 19、TypeScript、Tailwind 4、`lucide-react`
- **后端依赖**: FastAPI、Uvicorn、Pydantic、Starlette
- **运行入口**:
  - 后端启动：`WriterLab-v1/scripts/start-backend.ps1` 或 `uvicorn`
  - 前端启动：`WriterLab-v1/scripts/start-frontend.ps1` 或 `npm.cmd run dev`
- **验证入口**:
  - `WriterLab-v1/scripts/check-backend.ps1`
  - `WriterLab-v1/scripts/check-frontend.ps1`

### 6. 技术选型理由

- **为什么更新根 README**: 根 README 已经承担仓库入口职责，升级它比新增平行文档更符合现有结构
- **为什么采用“总览 + 跳转索引”**: `WriterLab-v1/docs/` 已存在更细的盘点、验证和运行文档，根 README 适合作为导航页
- **为什么保持 PowerShell 命令**: 现有脚本和文档均围绕 Windows/PowerShell 组织，继续沿用能减少认知切换

### 7. 关键风险点

- **工作区较脏**: 当前仓库存在大量未提交改动，本轮只能安全修改根 README 和 `.codex` 留痕文件
- **根 README 与子文档职责易混淆**: 如果复制过多实现细节，会与 `WriterLab-v1/docs/project-overview-zh.md` 重复
- **文档与实际代码可能继续变化**: 由于仓库仍在活跃开发，根 README 需要更多强调“当前状态”而非永久承诺
- **GitHub 开源示例检索不可用**: 本会话未暴露 GitHub 代码搜索工具，因此本轮仅基于仓库内现有文档模式整理
