## 项目上下文摘要（阶段二 / lore 子页 create-delete）

生成时间：2026-04-07

### 1. 相似实现分析

- **实现 1**: `D:/WritierLab/WriterLab-v1/Next.js/frontend/features/lore/lore-library-page.tsx`
  - 当前已具备 `selectedItemId / isEditing / draft / saving / detailError / message`。
  - 最小增量可继续收敛在同一文件，不需要改 `app/lore/*` 或 `lore-hub.tsx`。

- **实现 2**: `D:/WritierLab/WriterLab-v1/Next.js/frontend/features/settings/settings-hub.tsx`
  - 可复用 `busy / message / error`、按钮禁用和成功/失败提示条模式。

- **实现 3**: `D:/WritierLab/WriterLab-v1/Next.js/frontend/features/project/project-detail.tsx`
  - 可复用 `AppShell.actions` 区域放轻量动作按钮的布局思路。

- **实现 4**: `D:/WritierLab/WriterLab-v1/Next.js/frontend/shared/ui/info-card.tsx`
  - 详情、创建表单和删除提示都应继续放在 `InfoCard` 容器中。

- **实现 5**: `D:/WritierLab/WriterLab-v1/Next.js/frontend/lib/api/lore.ts`
  - 已具备三域 `create* / delete*` 共享客户端，是本轮直接复用的 API 边界。

### 2. 项目约定

- lore 页面请求继续集中在 `lib/api/lore.ts`，页面层不直接 `fetch('/api/...')`。
- 最小 UI 交互继续使用暗色按钮、`InfoCard`、成功/失败消息条。
- 不新增 modal、独立创建页、service 层或全局 store。

### 3. 当前缺口

- `lore-library-page.tsx` 目前只有 detail/edit，没有 create/delete 交互。
- `lore-domain-contract.test.mjs` 目前也只锁定了 detail/edit。

### 4. 推荐最小方案

- 在 `lore-library-page.tsx` 里新增“新建资料”入口，切到创建草稿模式。
- 在已选中项详情区新增“删除当前”按钮，走轻量确认。
- 保存创建后把新条目插入当前列表并切为选中项；删除后从列表移除并自动切到相邻项。
