## 项目上下文摘要（superpowers-install）

生成时间：2026-04-02 01:12:16

### 1. 相似实现分析

- 本任务不是仓库代码实现，而是外部技能安装流程。
- 现有本机状态：
  - `C:\Users\kanye\.codex\superpowers` 初始不存在。
  - `C:\Users\kanye\.agents\skills` 初始不存在。
  - `C:\Users\kanye\.agents\skills\superpowers` 初始不存在。

### 2. 资料来源

- 远程安装文档：
  - `https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/.codex/INSTALL.md`
- 文档事实：
  - Windows 安装要求将仓库克隆到 `~/.codex/superpowers`。
  - 然后创建 `~/.agents/skills/superpowers` 指向 `~/.codex/superpowers/skills` 的 junction。
  - 完成后需要重启 Codex。

### 3. 本机环境约束

- 操作系统：Windows
- Shell：PowerShell
- `git` 可用：`git version 2.45.2.windows.1`
- 当前工作区外写入需要提权：
  - `C:\Users\kanye\.codex`
  - `C:\Users\kanye\.agents`

### 4. 关键风险点

- `npx.ps1` 受 PowerShell 执行策略限制，说明本机对脚本执行较敏感。
- 安装步骤主要依赖 `git clone` 与 `mklink /J`，需要在用户目录执行。
- 若不重启 Codex，新技能不会被当前会话发现。

### 5. 验证策略

- 检查仓库目录是否存在。
- 检查 `superpowers` junction 是否存在且目标正确。
- 检查 junction 下是否能看到技能目录内容。
