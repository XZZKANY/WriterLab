## 项目上下文摘要（按建议文档调整项目工作区）

生成时间：2026-04-02 02:17:10

### 1. 外部建议来源

- **来源文件**: [建议.md](D:/记事本/建议.md)
- **关键要求**:
  - “项目设定资料应该放在项目中”
  - “写作编辑也应该在项目中”
  - “点进具体项目应该是像这样，左边是写作台功能”
  - “偏好设置名字改为模型设置”
  - “新建项目应该和 project 一列，排序方式放在右边”
  - “三点应该有展开，并且 hover 时才显示”
  - “搜索项目后面的界面好像没做，新建项目这一项可以移开”

### 2. 相似实现分析

- **实现 1**: `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\workspace-shell.tsx`
  - 模式：统一暗色全局工作区壳层
  - 可复用：一级导航、标题区与暗色布局基调
  - 需注意：如果要把写作编辑和设定资料收回项目内，必须先从这里调整导航语义
- **实现 2**: `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-hub.tsx`
  - 模式：项目列表页，已具备搜索、排序和卡片列表
  - 可复用：搜索栏、排序块、暗色卡片样式
  - 需注意：当前三点按钮常显且没有展开菜单，不符合建议图示
- **实现 3**: `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-detail.tsx`
  - 模式：项目详情页，已有书籍/章节/场景数据加载
  - 可复用：结构摘要、书籍与章节浏览能力
  - 需注意：当前没有“左边是写作台功能”的项目内入口区
- **实现 4**: `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\lore\lore-hub.tsx`
  - 模式：设定资料页，已有项目选择器和三类设定摘要
  - 可复用：项目上下文选择和设定摘要
  - 需注意：目前没有从项目详情透传上下文
- **实现 5**: `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\editor\editor-workspace.tsx`
  - 模式：编辑器工作台，已通过查询参数读取 `scene_id`
  - 可复用：说明编辑器具备接收 URL 上下文的扩展能力
  - 需注意：当前并未直接消费 `projectId`，因此本轮更适合先做入口整合，而不是改写整套编辑器

### 3. 项目约定

- **命名约定**: 页面组件保持 PascalCase；数据请求仍用 `fetch*` / `update*`
- **文件组织**: `shared/ui` 管全局壳层；`features/project`、`features/lore`、`features/settings` 承载业务页
- **风格约定**: 暗色界面统一使用 `#171717` / `#212121`、`border-white/8`、`text-zinc-*`
- **交互约定**: 项目列表和详情都优先使用现有路由，不引入新后端接口

### 4. 可复用组件清单

- `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\workspace-shell.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\app-shell.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\info-card.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-hub.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-detail.tsx`
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\lore\lore-hub.tsx`

### 5. 测试策略

- **验证命令**:
  - `npm.cmd run typecheck`
  - `powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1`
  - `powershell -ExecutionPolicy Bypass -File D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1 -LiveUiSmoke`
- **验证重点**:
  - 导航语义调整后关键路由仍可访问
  - 项目列表页 hover 三点菜单不影响渲染和交互
  - lore 页通过查询参数预选项目后，Next.js 构建仍通过

### 6. 依赖与集成点

- `project-detail.tsx` 继续依赖 `fetchProjects`、`fetchBooksByProject`、`fetchChaptersByBook`、`fetchScenesByChapter`
- `lore-hub.tsx` 与 `lore-library-page.tsx` 继续依赖 `fetchProjects`、`fetchCharacters`、`fetchLocations`、`fetchLoreEntries`
- `editor-workspace.tsx` 已证实使用查询参数读取上下文，因此项目详情页可以安全追加 `projectId` 或 `scene_id`
- `scripts/frontend_live_smoke.mjs` 与全局导航存在联动，导航语义调整后要同步更新脚本

### 7. 风险点

- **构建风险**: `useSearchParams()` 在静态页面中会触发 Next 16 的 suspense 约束，因此查询参数预选应改为浏览器端读取
- **验证风险**: Windows 下并发 `next build` 会报 “Another next build process is already running”，验证需串行执行
- **范围风险**: 建议文档提到“编辑器界面还是原来的界面”，但本轮优先完成入口整合；若要继续满足这一点，需要单独重构 `editor-workspace.tsx`
