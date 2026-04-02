## 项目上下文摘要（统一暗色项目工作区壳层）

生成时间：2026-04-02 01:14:20

### 1. 相似实现分析

- **实现1**: `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\app-shell.tsx`
  - 模式：当前所有业务页共用的页面壳层
  - 可复用：标题、描述、actions、children 这些标准槽位
  - 关键约束：只要修改这里，`project-detail`、`lore`、`runtime`、`settings`、首页都会一起变化
- **实现2**: `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\info-card.tsx`
  - 模式：业务页的基础卡片容器
  - 可复用：卡片标题与说明结构
  - 关键约束：暗色工作区改造必须同步改卡片，不然页面层级会割裂
- **实现3**: `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-hub.tsx`
  - 模式：`/project` 已有一版 Claude 风格项目页，但侧边栏语义仍偏聊天/通用工作区
  - 可复用：搜索栏、卡片网格、Lucide 图标、项目数据加载逻辑
  - 关键约束：需要把它并回共享壳层，避免单页维护两套侧边栏

### 2. 依赖与边界

- `lucide-react` 已安装，可安全用于共享壳层和项目页图标
- `fetchProjects` 继续作为项目列表数据来源
- `LiveUiSmoke` 要求页面保留 `WriterLab` 标记和 `/project`、`/editor`、`/lore`、`/runtime`、`/settings` 这些导航链接

### 3. 设计决策

- 新增 `shared/ui/workspace-shell.tsx` 作为统一暗色工作区壳层
- `AppShell` 退化成对 `WorkspaceShell` 的轻包装，保留原有 props 接口
- 侧边栏改成项目语义：
  - 新建项目
  - 搜索项目
  - 项目总览
  - 项目列表
  - 写作编辑
  - 设定资料
  - 运行诊断
  - 偏好设置
- `InfoCard` 统一切到深色卡片与低对比边框
- `ProjectHub` 回收进共享壳层，保留搜索、项目卡片与详情跳转

### 4. 风险点

- 如果共享壳层漏掉现有导航链接，前端 smoke 会失败
- 如果 `ProjectHub` 继续保留单独侧边栏，会导致“所有界面往同一风格改”落不实
- 暗色壳层改造会同时影响首页和业务页，因此必须通过完整前端检查确认没有构建回归
