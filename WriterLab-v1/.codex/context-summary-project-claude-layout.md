## 项目上下文摘要（Claude 风格项目管理页）

生成时间：2026-04-02 00:54:47

### 1. 相似实现分析

- **实现1**: `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-hub.tsx`
  - 模式：`/project` 入口页，负责拉取项目列表并渲染卡片
  - 可复用：`fetchProjects` 数据加载、项目卡片与详情页跳转关系
  - 约束：仍需保持 `/project/${project.id}` 详情入口不变
- **实现2**: `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\app-shell.tsx`
  - 模式：现有应用壳层统一维护一级导航
  - 可复用：导航信息架构与顶层页面入口约定
  - 约束：新的 Claude 风格页虽然不直接复用 `AppShell`，但仍要保留 `/project`、`/editor`、`/lore`、`/runtime`、`/settings` 这些导航链接，避免 smoke 断裂
- **实现3**: `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\home-dashboard.tsx`
  - 模式：首页通过大标题、操作按钮和信息卡组织页面节奏
  - 可复用：标题区、CTA 按钮、模块分区的布局惯例
  - 约束：本轮可替换视觉语言，但要维持 React + Tailwind 的实现方式

### 2. 项目约定

- **目录结构**：`app/*` 装配路由，`features/*` 承担页面能力，`shared/*` 提供复用 UI
- **字体策略**：`app/layout.tsx` 已注入 Geist / Geist Mono；`globals.css` 里 `font-sans` 已指向 Geist Sans
- **样式方式**：Tailwind CSS 4 原子类，没有额外 CSS Modules
- **验证方式**：前端统一走 `npm.cmd run typecheck`、`scripts/check-frontend.ps1` 和 `-LiveUiSmoke`

### 3. 依赖与集成点

- `D:\WritierLab\WriterLab-v1\Next.js\frontend\package.json`
  - 事实：原先没有声明 `lucide-react`
  - 处理：本轮已安装 `lucide-react`，用于侧边栏、搜索栏和卡片操作图标
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\lib\api\projects.ts`
  - 事实：项目页继续通过 `fetchProjects` 读取真实项目数据
- `D:\WritierLab\WriterLab-v1\scripts\frontend_live_smoke.mjs`
  - 事实：`/project` 页面必须保留通用导航链接和 `WriterLab` 关键标记

### 4. 设计决策

- 不复用现有浅色 `AppShell`，因为用户明确要求 Claude Web UI / Shadcn 暗色风格
- 继续保留真实项目数据、搜索过滤和详情跳转，不做纯静态示意页
- 侧边栏使用 Lucide 细线图标，主区使用深色卡片、圆角按钮、极简搜索框
- 卡片文案保留两行描述、左下角更新时间、右上角更多操作图标

### 5. 风险点

- 新视觉页若缺少现有全局导航链接，会导致 `LiveUiSmoke` 失败
- `lucide-react` 未安装前直接引入会导致构建失败
- 卡片或导航若改成纯装饰结构，容易丢失真实项目页可用性
