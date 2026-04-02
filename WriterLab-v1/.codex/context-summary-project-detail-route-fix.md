## 项目上下文摘要（项目详情页动态路由参数修复）

生成时间：2026-04-02 00:28:03

### 1. 相似实现分析

- **实现1**: `D:\WritierLab\WriterLab-v1\Next.js\frontend\app\project\[projectId]\page.tsx`
  - 模式：App Router 动态路由页只负责读取 `params` 并装配 `ProjectDetail`
  - 可复用：`ProjectDetail` 作为统一详情入口
  - 需注意：Next.js 16 下 `params` 必须按 Promise 处理并 `await`
- **实现2**: `D:\WritierLab\WriterLab-v1\Next.js\frontend\app\project\[projectId]\books\page.tsx`
  - 模式：子路由继续复用统一详情组件，而不是重复创建独立页面状态
  - 可复用：与主详情页完全一致的异步 `params` 读取方式
  - 需注意：books/chapters/scenes 三个子路由都要一起修，不然问题会残留
- **实现3**: `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-hub.tsx`
  - 模式：列表页通过 `Link href={\`/project/${project.id}\`}` 跳转详情页
  - 可复用：现有项目入口和导航关系，无需新增跳转层
  - 需注意：详情页参数修复后要保证与列表页生成的 UUID 路径保持一致
- **实现4**: `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-detail.tsx`
  - 模式：客户端组件统一聚合 `fetchProjects`、`fetchBooksByProject`、`fetchChaptersByBook`、`fetchScenesByChapter`
  - 可复用：详情页聚合加载逻辑与现有信息卡布局
  - 需注意：若 `projectId` 为空，需要先短路，避免继续请求 `/api/books?project_id=undefined`

### 2. 项目约定

- **命名约定**：路由页使用 `ProjectDetailPage`、`ProjectBooksPage` 这类 PascalCase 导出函数；前端 API 使用 `fetch*` 命名
- **文件组织**：`app/*` 负责路由装配，`features/*` 承担页面能力，`lib/api/*` 承担请求入口
- **导入顺序**：先导入 features/lib/shared，再定义类型和组件
- **代码风格**：TypeScript + React，字符串和尾随逗号风格与现有文件一致

### 3. 可复用组件清单

- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-detail.tsx`：项目详情聚合视图
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\features\project\project-hub.tsx`：项目列表入口和详情跳转模式
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\lib\api\projects.ts`：项目、书籍、章节请求
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\lib\api\scenes.ts`：场景请求
- `D:\WritierLab\WriterLab-v1\Next.js\frontend\shared\ui\app-shell.tsx`：统一页面壳层

### 4. 测试策略

- **测试框架**：前端以 `npm.cmd run typecheck`、`next build` 和 `scripts/check-frontend.ps1` 为主
- **测试模式**：类型检查 + 生产构建 + 本地 live smoke + 定向 HTTP 验证
- **参考文件**：`D:\WritierLab\WriterLab-v1\scripts\check-frontend.ps1`、`D:\WritierLab\WriterLab-v1\scripts\frontend_live_smoke.mjs`
- **覆盖要求**：至少覆盖 `/project` 体系的动态详情页、子路由和导航入口

### 5. 依赖和集成点

- **外部依赖**：Next.js `16.2.1`、React `19.2.4`
- **内部依赖**：`ProjectHub -> /project/[projectId] -> ProjectDetail -> lib/api/projects|scenes`
- **集成方式**：Server Component 路由页把 `projectId` 传给 Client Component，Client Component 再请求后端 API
- **配置来源**：`lib/api/client.ts` 默认请求 `http://127.0.0.1:8000`

### 6. 技术选型理由

- **为什么用这个方案**：问题根因就在 App Router 动态路由参数读取方式，按 Next.js 16 官方模式修复成本最低、影响最小
- **优势**：不改 API、不改页面结构，只修复路由边界和空值保护即可消除 `undefined` 透传
- **劣势和风险**：当前定向验证主要基于前端服务端输出和路由响应，未包含浏览器交互级断言

### 7. 关键风险点

- **并发问题**：`ProjectDetail` 内部有并发加载书籍/章节/场景，请求前必须保证 `projectId` 已就绪
- **边界条件**：空 `projectId`、无项目数据、后端 8000 未启动时都应有可控表现
- **性能瓶颈**：详情页会级联请求多个资源，但本轮未改变该策略
- **验证局限**：本地 live smoke 只覆盖静态路由矩阵，动态详情页额外通过真实 UUID 路径 HTTP 检查补足

### 8. 外部资料

- **Context7 /vercel/next.js/v16.0.3**：动态路由 `page.tsx` 需按 `params: Promise<{ slug: string }>` 编写并 `await params`
