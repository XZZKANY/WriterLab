## 项目上下文摘要（阶段二 / lore 更多字段交互）

生成时间：2026-04-07 21:38:02

### 1. 相似实现分析

- **实现 1**: `D:/WritierLab/WriterLab-v1/Next.js/frontend/features/lore/lore-library-page.tsx`
  - 当前已具备 lore 子页最小 create / detail / edit / delete 闭环。
  - 可复用：`selectedItemId / isEditing / isCreating / draft / saving / deleting / detailError / message` 这一套状态模型。
  - 缺口：角色更多字段与词条 priority 还未暴露到 UI。

- **实现 2**: `D:/WritierLab/WriterLab-v1/Next.js/frontend/lib/api/lore.ts`
  - 已暴露角色 `appearance / background / motivation / speaking_style / secrets` 和词条 `priority` 的类型与 create/update 客户端。
  - 说明本轮不需要新增 API 层，只需要前端页面接线。

- **实现 3**: `D:/WritierLab/WriterLab-v1/fastapi/backend/app/schemas/character.py`
  - 后端合同已支持角色扩展字段。
  - 说明前端扩字段不会越界到后端新增需求。

- **实现 4**: `D:/WritierLab/WriterLab-v1/fastapi/backend/app/schemas/lore_entry.py`
  - 后端合同已支持 `priority` 的 create/update。
  - 说明词条优先级可以直接接到现有共享 API。

- **实现 5**: `D:/WritierLab/WriterLab-v1/Next.js/frontend/features/settings/settings-hub.tsx` 与 `features/project/project-create-page.tsx`
  - 可复用更多 `input / textarea` 的暗色表单样式和错误提示写法。

### 2. 项目约定

- 继续只改 `features/lore/lore-library-page.tsx` 和 `tests/features/lore-domain-contract.test.mjs`。
- 不新增页面、不改 `lore-hub.tsx`、不改共享 API 分层。
- 扩展字段优先选择后端已存在且前端尚未暴露的字段。

### 3. 本轮目标

- 角色：补 `appearance / background / motivation / speaking_style / secrets` 的查看与编辑。
- 词条：补 `priority` 的查看与编辑，并在创建时可设置。
- 保持最小交互闭环不变。

### 4. 风险点

- `lore-library-page.tsx` 已较长，本轮必须控制在“字段接线”而不是再拆新组件。
- 字段扩展后仍需保持 create / edit 表单与详情显示语义一致。
