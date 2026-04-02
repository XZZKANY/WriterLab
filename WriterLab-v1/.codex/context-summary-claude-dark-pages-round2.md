## 项目上下文摘要（Claude 暗色业务页继续统一）

生成时间：2026-04-02 01:35:40

### 1. 相似实现分析

- **实现 1**: `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\workspace-shell.tsx`
  - 模式：统一暗色工作区壳层，负责侧边栏、标题区和全局背景
  - 可复用：`eyebrow`、`title`、`description`、`actions` 插槽，以及 `text-zinc-*` / `border-white/6` / `bg-[#171717]` 的整体基调
  - 需注意：所有依赖 `AppShell` 的页面都会继承这套壳层，因此内部控件必须继续沿用相近的暗色层级
- **实现 2**: `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\info-card.tsx`
  - 模式：共享内容卡片，统一圆角、边框、内边距和语义色块
  - 可复用：`rounded-[28px]`、`border-white/8`、`bg-[#212121]` 以及 `amber/sky/emerald` 低透明 tone
  - 需注意：页面内部次级卡片若继续使用浅色 `stone` 系列，会破坏和 `InfoCard` 的层级一致性
- **实现 3**: `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-hub.tsx`
  - 模式：Claude 风格项目页，使用暗色搜索栏、CTA 按钮和项目卡片网格
  - 可复用：输入框 `border-white/8 bg-[#212121]`、主按钮 `bg-zinc-100 text-black`、空态 `border-dashed border-white/10 bg-[#1a1a1a]`
  - 需注意：筛选输入和 CTA 按钮已经形成稳定样式，应直接复用到 `settings` / `lore` / `home-dashboard`
- **实现 4**: `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-detail.tsx`
  - 模式：暗色详情页，使用摘要统计块、书籍卡、章节卡和错误态卡片
  - 可复用：`bg-[#1d1d1d]`、`bg-[#171717]` 的层级搭配，以及 `border-rose-400/20 bg-rose-500/10` 错误样式
  - 需注意：列表卡和 pill 标签应尽量保持与详情页相同的边框和背景节奏
- **实现 5**: `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\runtime\runtime-hub.tsx`
  - 模式：暗色监控页，使用中文标题、就绪度摘要和本地 smoke 信息展示
  - 可复用：语义统计块、状态列表卡、错误块和最近报告列表
  - 需注意：前端 live smoke 依赖该页的页面标记，改文案时必须同步更新脚本

### 2. 项目约定

- **命名约定**: 页面组件使用 PascalCase；数据请求函数继续使用 `fetch*` / `update*`
- **文件组织**: `shared/ui` 放共享壳层与卡片，`features/*` 放业务页内容，`app/*` 只负责路由装配
- **导入顺序**: 先框架和第三方，再 `@/lib/api/*`，再共享 UI
- **代码风格**: React 函数组件 + Tailwind 原子类；不引入额外 CSS 文件；中文文案直接写在组件中

### 3. 可复用组件清单

- `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\workspace-shell.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\app-shell.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\info-card.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-hub.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-detail.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\runtime\runtime-hub.tsx`

### 4. 测试策略

- **测试框架**: 当前以前端 TypeScript 检查、Next.js 生产构建检查和 Live UI Smoke 为主
- **参考脚本**: `D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1`
- **冒烟规则**: `D:\WritierLab\WriterLab-v1\scripts\frontend_live_smoke.mjs`
- **覆盖要求**: 至少执行 `npm.cmd run typecheck`、`check-frontend.ps1`，涉及页面文案标记时补跑 `check-frontend.ps1 -LiveUiSmoke`

### 5. 依赖和集成点

- **外部依赖**: `next@16.2.1`、`react@19.2.4`、`tailwindcss@^4`、`lucide-react@^1.7.0`
- **内部依赖**:
  - `settings-hub.tsx` 依赖 `fetchProviderSettings` 与 `updateProviderSettings`
  - `lore-hub.tsx` / `lore-library-page.tsx` 依赖 `fetchProjects`、`fetchCharacters`、`fetchLocations`、`fetchLoreEntries`
  - `home-dashboard.tsx` / `runtime-hub.tsx` 依赖 `fetchHealth`
- **集成方式**: 页面组件内部 `useEffect` 拉取数据，交由 `AppShell` 与 `InfoCard` 承载展示
- **配置来源**: `package.json` 的 `typecheck`、`build:node`，以及 `scripts/check-frontend.ps1`

### 6. 技术选型理由

- **为什么用这个方案**: 已有暗色工作区模式已经稳定存在，直接复用能最快实现全站视觉一致，不引入第二套设计系统
- **优势**: 改动只落在表现层；不动 API、hooks 和路由；验证链现成
- **劣势和风险**: 前端 smoke 依赖页面文案标记，改中文或标题时要同步维护脚本；终端直接查看 UTF-8 中文仍可能显示乱码

### 7. 关键风险点

- **并发问题**: 并发执行两个 `next build` 会触发 “Another next build process is already running”，验证需要串行执行
- **边界条件**: 无项目、无 Provider、无设定数据时要保留空态，不可只做纯样式替换
- **性能瓶颈**: 本轮仅替换类名和文案，不新增请求与状态，性能风险很低
- **工具限制**: 当前会话没有 `github.search_code`；因此本轮以本地现有实现分析为主，并在日志中记录这一点
