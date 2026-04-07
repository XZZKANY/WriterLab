## 项目上下文摘要（阶段二 / lore 前端接线）

生成时间：2026-04-07 20:10:05

### 1. 相似实现分析

- **实现 1**: `D:/WritierLab/WriterLab-v1/Next.js/frontend/lib/api/lore.ts`
  - 模式：当前只提供 `fetchCharacters`、`fetchLocations`、`fetchLoreEntries` 三个 list 读取接口。
  - 可复用：统一通过 `@/lib/api/client` 访问 `/api/*`，错误文案在 API 层集中处理。
  - 缺口：缺少 detail / update / delete 等资料域前端合同。

- **实现 2**: `D:/WritierLab/WriterLab-v1/Next.js/frontend/lib/api/projects.ts`
  - 模式：在 API 文件中同时定义类型和请求函数，继续复用 `apiGet / apiPost / apiDelete`。
  - 可复用：项目级资源使用共享 client，不在页面层直接拼接请求。
  - 启发：lore API 也应补齐类型与合同函数，而不是把细节留给页面层。

- **实现 3**: `D:/WritierLab/WriterLab-v1/Next.js/frontend/lib/api/scenes.ts`
  - 模式：对资源明细和更新操作使用 `apiGet / apiPatch / apiPost` 封装。
  - 可复用：`updateScene(sceneId, body)` 这类资源更新函数命名与参数风格。
  - 启发：lore 三域的 update/detail/delete 也应沿用同样写法。

- **实现 4**: `D:/WritierLab/WriterLab-v1/Next.js/frontend/features/lore/lore-library-page.tsx`
  - 模式：客户端组件按 `mode` 切换角色 / 地点 / 词条列表，当前已经通过 `@/lib/api/lore` 取数。
  - 可复用：页面不直接 `fetch('/api/...')`，而是依赖共享 API 客户端。
  - 缺口：组件内部仍内联定义数据类型，未与共享 lore API 类型对齐。

- **实现 5**: `D:/WritierLab/WriterLab-v1/Next.js/frontend/features/lore/lore-hub.tsx`
  - 模式：设定库总览同样通过 `@/lib/api/lore` 和 `@/lib/api/projects` 汇总数据。
  - 可复用：总览页与子页面共享同一 lore API 入口。
  - 缺口：同样存在内联类型，且尚无前端 lore 契约测试锁定这种分层。

### 2. 项目约定

- **前端 API 分层**：`frontend/lib/api/*` 统一承接资源请求；页面组件通过导入函数消费，不直接拼接请求。
- **页面组织**：`app/lore/*/page.tsx` 只负责挂载 `features/lore/lore-library-page.tsx`。
- **测试模式**：`frontend/tests/features/*.mjs` 以 `node:test + readFile` 做结构契约检查。
- **错误处理**：`frontend/lib/api/client.ts` 统一负责 detail/message 提取与网络错误包装。
- **官方依据**：Context7 中 `Next.js /vercel/next.js/v16.0.3` 文档建议在 App Router 中集中数据获取逻辑并避免把请求细节散落在组件里；当前项目已通过共享 API client 落地这一原则。

### 3. 可复用组件清单

- `D:/WritierLab/WriterLab-v1/Next.js/frontend/lib/api/client.ts`
- `D:/WritierLab/WriterLab-v1/Next.js/frontend/lib/api/projects.ts`
- `D:/WritierLab/WriterLab-v1/Next.js/frontend/lib/api/scenes.ts`
- `D:/WritierLab/WriterLab-v1/Next.js/frontend/features/lore/lore-library-page.tsx`
- `D:/WritierLab/WriterLab-v1/Next.js/frontend/features/lore/lore-hub.tsx`
- `D:/WritierLab/WriterLab-v1/Next.js/frontend/tests/features/project-detail-contract.test.mjs`

### 4. 测试策略

- 新建 `frontend/tests/features/lore-domain-contract.test.mjs`。
- 先锁红灯：要求 lore 页面继续通过 `@/lib/api/lore` 取数，且 lore API 暴露最小 detail/update/delete 合同。
- 绿灯后运行：
  - `node D:/WritierLab/WriterLab-v1/Next.js/frontend/tests/features/lore-domain-contract.test.mjs`
  - `npm.cmd run typecheck`

### 5. 依赖和集成点

- **页面消费入口**：`features/lore/lore-library-page.tsx`、`features/lore/lore-hub.tsx`
- **共享 API 入口**：`lib/api/lore.ts`
- **共享底层请求**：`lib/api/client.ts`
- **后端合同来源**：`/api/characters`、`/api/locations`、`/api/lore-entries`

### 6. 风险点

- 若前端继续在组件里复制类型和请求语义，后续 detail/update/delete 很容易与后端合同漂移。
- 当前没有 lore 前端契约测试，分层约束可能被后续改动破坏。
- 当前会话中没有可用的 `github.search_code` 工具，因此无法直接执行仓库外开源代码搜索；本轮已改用项目内模式对照与 Context7 官方文档补足证据。
