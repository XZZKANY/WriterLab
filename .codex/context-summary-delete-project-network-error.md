## 项目上下文摘要（删除项目网络错误修复）

生成时间：2026-04-02 18:33:26

### 1. 相似实现分析

- **实现1**: `D:/WritierLab/WriterLab-v1/Next.js/frontend/lib/api/client.ts`
  - 模式：统一 API 请求封装，所有页面通过 `apiGet` / `apiPost` / `apiDelete` 进入同一条请求链路。
  - 可复用：`getApiBaseUrl()`、`parseJsonOrThrow()`、`pickErrorMessage()`。
  - 需注意：原实现只处理 HTTP Response，不捕获 `fetch()` 抛出的网络异常，因此会把浏览器原始 `Failed to fetch` 直接泄漏到页面。
- **实现2**: `D:/WritierLab/WriterLab-v1/Next.js/frontend/features/project/project-hub.tsx`
  - 模式：页面层只负责调用 `deleteProject()` 并展示 `Error.message`，不做底层网络错误特判。
  - 可复用：删除入口的状态管理和通知流转无需改动，只要底层错误消息收敛，页面即可直接受益。
  - 需注意：如果在页面层单独修补，会和项目里其他使用同一 API client 的页面形成分叉。
- **实现3**: `D:/WritierLab/WriterLab-v1/Next.js/frontend/tests/features/api-client.test.mjs`
  - 模式：使用 `node:test` + `assert.rejects` 对 API client 做回归测试，直接 mock `globalThis.fetch`。
  - 可复用：现有已覆盖 JSON 错误提取和 204 空响应，这一轮可沿同一模式补网络失败场景。
  - 需注意：测试目标应落在 `client.ts`，而不是项目列表页组件。
- **实现4**: `D:/WritierLab/WriterLab-v1/Next.js/frontend/features/lore/lore-hub.tsx`
  - 模式：其他页面也直接展示 `loadError.message`。
  - 可复用：统一改 `client.ts` 能同时改善 Lore 等页面的网络错误可读性。
  - 需注意：这是跨页面共享模式，说明修复点应该放在 API client，而不是某个单页组件。

### 2. 项目约定

- **命名约定**: 前端使用 camelCase 函数名与状态名，文件名按既有模块命名。
- **文件组织**: 页面组件在 `features/*`，请求封装在 `lib/api/*`，定向回归测试在 `tests/features/*`。
- **导入顺序**: 先第三方库，再项目内模块。
- **代码风格**: TypeScript 严格模式，优先小函数封装，不在页面层重复底层错误处理。

### 3. 可复用组件清单

- `D:/WritierLab/WriterLab-v1/Next.js/frontend/lib/api/client.ts`: API 基址、请求封装、响应解析。
- `D:/WritierLab/WriterLab-v1/Next.js/frontend/lib/api/projects.ts`: 删除项目的业务 API 包装。
- `D:/WritierLab/WriterLab-v1/Next.js/frontend/tests/features/api-client.test.mjs`: API client 定向回归测试入口。

### 4. 测试策略

- **测试框架**: `node:test` + `node:assert/strict`
- **测试模式**: 直接 mock `globalThis.fetch`，覆盖成功、业务失败、网络失败三类分支。
- **参考文件**: `D:/WritierLab/WriterLab-v1/Next.js/frontend/tests/features/api-client.test.mjs`
- **覆盖要求**:
  - JSON 错误响应仍能提取 `detail`
  - 204 空响应仍能返回 `undefined`
  - 网络不可达时返回中文提示，并带上当前 API 基址

### 5. 依赖和集成点

- **外部依赖**: 浏览器/Node 的 `fetch` 与 `Response`
- **内部依赖**:
  - `project-hub.tsx` 依赖 `deleteProject()`
  - `deleteProject()` 依赖 `apiDelete()`
  - `apiDelete()` 依赖 `apiRequest()`
- **集成方式**: 页面统一依赖 `Error.message` 进行错误展示。
- **配置来源**: `NEXT_PUBLIC_API_BASE_URL`，未配置时回退到 `http://127.0.0.1:8000`

### 6. 技术选型理由

- **为什么用统一封装修复**: 现有项目已经把请求入口统一到了 `client.ts`，在这里捕获网络异常能一次性覆盖项目列表、Lore 页面等多个调用方。
- **优势**: 改动面小、回归测试明确、无需改后端和页面层。
- **劣势和风险**: 只能改善提示与可诊断性，无法替代真实的运行环境配置检查。

### 7. 关键风险点

- **边界条件**: 不能破坏现有 204 空响应与 JSON 错误提取逻辑。
- **性能瓶颈**: 新增网络错误格式化只在异常路径执行，影响可忽略。
- **运行风险**: 如果用户实际 API 地址不是 `127.0.0.1:8000` 且未配置环境变量，仍会请求失败，但提示会更明确。
