第一版不是“个人专属写作软件完整版”，而是：

## **一个能稳定完成以下闭环的写作工作台**

1. 录入设定
2. 创建章节与场景
3. 基于设定检索上下文
4. 生成场景正文
5. 检查明显设定冲突
6. 保存版本并继续修改

只要这条链路顺，你的软件就已经有用了。

------

# 一、第一版功能边界

先明确什么做，什么不做。

## 1.1 第一版必须做

- 单用户
- 单项目写作
- 章节/场景管理
- 角色库
- 世界观设定库
- 基础时间线事实记录
- RAG 检索注入
- 场景规划
- 场景扩写
- 场景修订
- 一致性检查
- 版本快照
- 基础导出 Markdown

## 1.2 第一版不做

- 多人协作
- 云同步复杂权限
- 自动跑完整本书
- 多供应商智能路由
- 图像生成
- VN 全流程
- 真 Git 分支
- 高级统计面板
- 自动训练私有模型
- 长链自主 Agent 循环

------

# 二、第一版用户主流程

你作为作者，第一版最核心的操作路径应该只有这 7 步：

## Step 1：创建项目

填写：

- 项目名
- 类型（小说 / 剧本 / VN 前置）
- 风格标签
- 简介

## Step 2：录入基础资料

录入：

- 角色
- 地点
- 世界观
- 术语
- 已知剧情事实

## Step 3：创建章节和场景

场景至少填写：

- 标题
- POV
- 地点
- 场景目标
- 必须出现
- 必须避免

## Step 4：系统检索相关设定

自动拉取：

- 当前 POV 角色资料
- 同场角色资料
- 当前地点设定
- 最近剧情事实
- 相关术语

## Step 5：生成场景方案

生成 2 到 3 个方案，不要更多。

## Step 6：生成正文并修订

输出：

- 初稿
- 修订稿
- 风格建议

## Step 7：做一致性检查并保存版本

显示：

- 冲突项
- 风险项
- 建议改写
- 保存快照

这就是第一版闭环。

------

# 三、第一版页面细化

建议只做 5 个页面。

------

## 3.1 项目首页 Dashboard

作用：不是展示炫酷统计，而是让你快速回到创作。

### 页面区块

- 当前项目基本信息
- 最近编辑的章节/场景
- 最近新增角色/设定
- 最近冲突警告
- 快速入口按钮

### 核心按钮

- 新建章节
- 新建角色
- 新建设定
- 继续上次写作

### 第一版可以显示的最小信息

- 项目名
- 章节数
- 场景数
- 角色数
- 设定数
- 最近修改时间

------

## 3.2 写作编辑器页

这是第一版最核心页面。

### 推荐布局：三栏

## 左栏：结构树

显示：

- 书籍
- 章节列表
- 场景列表

支持：

- 新建章节
- 新建场景
- 拖动排序先不做
- 简单上下移动即可

------

## 中栏：主编辑区

分成三个子区域：

### A. 场景元信息

字段：

- 场景标题
- POV
- 地点
- 时间标签
- 场景目标
- 冲突
- 必须出现
- 必须避免

### B. 正文区

字段：

- 草稿文本
- 修订文本可先共用一个编辑器，通过版本切换查看

### C. AI 操作栏

按钮：

- 生成方案
- 扩写正文
- 风格修订
- 一致性检查
- 保存版本

------

## 右栏：上下文面板

分 4 个标签页最合理：

### 标签 1：角色

显示本场景关联角色的关键信息摘要。

### 标签 2：设定

显示本场景命中的 lore 与术语。

### 标签 3：剧情事实

显示最近相关事件。

### 标签 4：警告

显示一致性问题。

右栏一定要是“可引用上下文”，而不是只给一个黑盒 AI 按钮。

------

## 3.3 角色 / 设定库页

第一版这里不要复杂图谱，先做列表 + 详情。

### 左侧

- 搜索框
- 分类筛选
- 条目列表

### 右侧详情

角色字段建议拆成可编辑区块：

#### 角色

- 名称
- 别名
- 外貌
- 性格
- 动机
- 背景
- 说话风格
- 当前状态
- 备注

#### 设定

- 分类
- 标题
- 内容
- 优先级
- 是否 canonical

------

## 3.4 时间线页

第一版不需要炫酷时间轴，做成结构化事件列表就行。

字段：

- 事件标题
- 所属章节
- 所属场景
- 参与者
- 时间标签
- 描述
- 谁知道这件事

这里最有价值的是“谁知道这件事”，后面一致性检查直接用。

------

## 3.5 版本对比页

这是第一版非常值得做的页面。

显示三类版本：

- 原始草稿
- AI 生成稿
- 你手工修改稿

支持：

- 查看 diff
- 一键恢复旧版本
- 将当前版本标记为“满意样本”

“满意样本”后续可以进入 style_sample 向量库。

------

# 四、第一版数据字段进一步细化

下面我把最关键的几个对象细化到“开发时不会含糊”的程度。

------

## 4.1 Scene 对象

第一版场景对象建议这样定：

```
{
  "id": "uuid",
  "chapter_id": "uuid",
  "scene_no": 1,
  "title": "车站重逢",
  "pov_character_id": "uuid",
  "location_id": "uuid",
  "time_label": "夜晚，主线第3天",
  "goal": "让主角确认对方没有死",
  "conflict": "主角想靠近，对方保持冷淡",
  "outcome": "关系没有修复，但留下怀疑线索",
  "must_include": [
    "雨夜",
    "对方手上的旧伤",
    "一句带试探意味的对白"
  ],
  "must_avoid": [
    "直接揭露身份",
    "解释性旁白过多"
  ],
  "status": "draft",
  "draft_text": "",
  "revised_text": ""
}
```

### 为什么这样设计

因为 AI 写作不是围绕“章节”发起，而是围绕“场景”发起。
 Scene 必须足够结构化，才能稳定编排。

------

## 4.2 Character 对象

```
{
  "id": "uuid",
  "name": "林岚",
  "aliases": ["阿岚"],
  "appearance": "黑发，眼尾锋利，左手腕有旧伤",
  "personality": "克制、冷淡、观察欲强",
  "background": "曾在北站事故中失踪",
  "motivation": "查清事故真相，避免主角卷入",
  "speaking_style": "短句，少解释，带刺",
  "status": "存活，隐藏身份中",
  "secrets": "真实身份未公开",
  "canonical_facts": [
    "不主动解释自己",
    "对主角仍有保护欲"
  ]
}
```

### 第一版重点

别追求字段特别全，先保证这些字段可直接用于 prompt。

------

## 4.3 Lore 对象

```
{
  "id": "uuid",
  "category": "组织设定",
  "title": "北站调查局",
  "content": "负责处理事故相关封锁与信息回收……",
  "priority": 80,
  "canonical": true,
  "version": 1
}
```

### priority 用处

第一版检索后做排序时可直接加权。

------

## 4.4 Timeline Event 对象

```
{
  "id": "uuid",
  "title": "北站事故发生",
  "chapter_id": "uuid",
  "scene_id": null,
  "event_type": "incident",
  "description": "北站爆炸后官方封锁现场，林岚失踪。",
  "participants": ["林岚", "主角", "调查局"],
  "event_time_label": "主线第0天",
  "knowledge_scope": {
    "public": ["北站爆炸"],
    "restricted": {
      "林岚存活": ["林岚"],
      "事故并非意外": ["林岚", "某调查员"]
    }
  }
}
```

### 第一版为什么一定要做 knowledge_scope

因为“谁知道什么”是长篇逻辑错误最高发的来源。

------

# 五、第一版 AI 链路细化

第一版只做 4 个 AI 动作。

------

## 5.1 动作一：生成场景方案

### 输入

- scene 元信息
- 当前章节摘要
- 命中的上下文包

### 输出

- 2 到 3 个场景方案
- 每个方案含：
  - 核心推进
  - 情绪走向
  - 风险点

### 前端交互

显示成卡片供选择，不要直接覆盖正文。

### 生成按钮文案

“生成推进方案”

------

## 5.2 动作二：生成正文

### 输入

- 选中的方案
- scene 约束
- 上下文包
- 目标长度

### 输出

- draft_text

### 生成模式建议

第一版先做 3 档长度：

- 短
- 中
- 长

不要让用户自由输入 token 目标。

------

## 5.3 动作三：风格修订

### 输入

- 当前正文
- style rules
- terminology
- 用户选择的修订模式

### 修订模式建议只保留 3 个

- 精简
- 文学化
- 统一风格

不要一开始做十几个按钮。

------

## 5.4 动作四：一致性检查

### 输入

- 当前正文
- scene 上下文
- timeline facts
- character facts
- lore constraints

### 输出分两类

#### 硬冲突

必须提示，比如：

- 角色已死却出场
- 知情范围错误
- 术语错误
- 设定规则冲突

#### 软风险

建议提示，比如：

- 说话风格偏差
- 情绪推进太快
- 场景目标不够明显

第一版只要把这两层分清楚，就已经很实用。

------

# 六、第一版 Context Compiler 细化

这是最容易被忽视、但最关键的模块之一。

AI 不能直接吃检索结果原文，必须有一个上下文编译器。

------

## 6.1 输入源

- 当前 scene
- POV 角色
- 在场角色
- 地点
- 近期 timeline event
- lore 检索结果
- terminology 命中结果
- style rules

------

## 6.2 编译后输出格式

建议固定成：

```
{
  "scene_summary": {
    "goal": "",
    "conflict": "",
    "outcome_target": ""
  },
  "characters": [
    {
      "name": "",
      "appearance": "",
      "personality": "",
      "speaking_style": "",
      "known_constraints": []
    }
  ],
  "location": {
    "name": "",
    "description": "",
    "rules": []
  },
  "plot_facts": [],
  "lore_constraints": [],
  "terminology_rules": [],
  "style_rules": []
}
```

------

## 6.3 第一版的上下文长度控制

要限制，不然 prompt 会失控。

建议：

- 角色：最多 3 人
- 地点：1 条
- plot facts：最多 8 条
- lore constraints：最多 8 条
- style rules：最多 10 条
- terminology：最多 20 条短规则

不是越多越好，越多越容易把模型淹死。

------

# 七、第一版一致性引擎进一步细化

第一版不追求“像编辑一样懂文学”，只追求**能抓住高价值错误**。

------

## 7.1 规则层检查

这层不用大模型，也应该先做。

### 可以规则化的内容

- 术语是否用了 forbidden variant
- 角色名字是否写错
- 地名是否写错
- 已禁用设定是否出现
- 场景 must_avoid 是否被触发

### 输出格式

```
[
  {
    "type": "term_violation",
    "severity": "medium",
    "message": "术语“调查总署”应统一为“北站调查局”"
  }
]
```

------

## 7.2 LLM 检查层

专门查这些：

- 角色认知越界
- 情节推进跳跃
- 台词不符合角色口吻
- 情感变化缺乏铺垫
- 叙述与设定冲突

------

## 7.3 第一版评分逻辑

第一版直接给一个简单分数：

- 90 到 100：基本安全
- 75 到 89：存在可修风险
- 0 到 74：存在明显冲突

不要一开始搞复杂加权面板。

------

# 八、第一版后端接口细化

我把第一版压缩成最核心的一组。

------

## 8.1 项目接口

### POST /api/projects

创建项目

### GET /api/projects/:id

获取项目详情

### GET /api/projects/:id/dashboard

获取首页信息

------

## 8.2 角色与设定接口

### POST /api/characters

### PATCH /api/characters/:id

### GET /api/characters/:id

### GET /api/characters?project_id=xxx

### POST /api/lore

### PATCH /api/lore/:id

### GET /api/lore?project_id=xxx

### POST /api/timeline-events

### GET /api/timeline-events?project_id=xxx

------

## 8.3 章节场景接口

### POST /api/chapters

### GET /api/chapters?book_id=xxx

### POST /api/scenes

### GET /api/scenes/:id

### PATCH /api/scenes/:id

### PATCH /api/scenes/:id/text

------

## 8.4 AI 接口

### POST /api/ai/plan-scene

### POST /api/ai/write-scene

### POST /api/ai/revise-scene

### POST /api/ai/check-scene

------

## 8.5 版本接口

### POST /api/versions/snapshot

### GET /api/versions?entity_type=scene&entity_id=xxx

### GET /api/versions/:id/diff/:other_id

------

# 九、第一版后台任务细化

至少做 4 个异步任务。

------

## 9.1 embedding_build_task

触发时机：

- 角色更新
- lore 更新
- timeline event 更新
- 标记满意文本样本

作用：

- 重建向量数据

------

## 9.2 consistency_scan_task

触发时机：

- 场景生成后
- 用户点击检查时
- 大幅修改后

作用：

- 跑规则检查 + LLM 检查

------

## 9.3 style_extract_task

触发时机：

- 用户将版本标记为“满意样本”
- 收集到足够 diff 时

作用：

- 提炼 style rule 候选

------

## 9.4 export_markdown_task

触发时机：

- 导出整章 / 整书时

作用：

- 合并文本
- 清洗标记
- 输出 md 文件

------

# 十、第一版前端组件拆分建议

为了避免页面越写越乱，组件要尽早拆。

------

## 编辑器页组件

- `ChapterTree`
- `SceneMetaForm`
- `SceneEditor`
- `AiActionPanel`
- `ContextTabs`
- `ConsistencyIssueList`
- `VersionToolbar`

------

## 角色设定页组件

- `CharacterList`
- `CharacterDetailForm`
- `LoreList`
- `LoreDetailForm`
- `TimelineList`

------

## 版本页组件

- `VersionList`
- `DiffViewer`
- `VersionPreview`

------

# 十一、第一版数据库最小集合

如果你现在就开工，第一版真正最小必需表，我建议定成这 10 张：

- projects
- books
- chapters
- scenes
- characters
- lore_entries
- timeline_events
- terminology
- document_versions
- ai_runs

`style_rules` 可以有，但甚至能放到第二小阶段。
 因为最开始你还没有足够反馈数据。

------

# 十二、第一版 Prompt 模板细化

第一版至少需要 4 套 prompt 模板。

------

## 12.1 planner prompt

职责：

- 基于 scene brief 和记忆包输出 2 到 3 个推进方案

重点要求：

- 不可违反 must_avoid
- 不可越界使用未公开信息
- 优先保留人物既有口吻

------

## 12.2 writer prompt

职责：

- 生成场景正文

重点要求：

- 明确 POV
- 严格遵守 lore/plot facts
- 输出自然正文，不要解释过程

------

## 12.3 reviser prompt

职责：

- 修订已有文本

重点要求：

- 不改变事实
- 不新增设定
- 仅优化表达、节奏、风格统一

------

## 12.4 consistency prompt

职责：

- 做审校式检查

重点要求：

- 标出冲突位置
- 引用依据
- 不直接重写全文
- 只给问题与建议

------

# 十三、第一版模型策略

第一版不要做复杂模型矩阵。

建议固定成：

## 本地模型

负责：

- embedding
- 术语提取
- 轻量检查
- 文本结构化
- 摘要

## 云端主模型

负责：

- plan
- write
- revise
- high-level consistency review

第一版最好只有一个主云模型入口，最多再加一个备用，不要在 UI 暴露“选模型”。

------

# 十四、第一版状态机

为了避免场景状态混乱，建议 Scene 有明确状态。

```
idea -> planned -> drafted -> revised -> checked -> locked
```

## 各状态含义

- `idea`：只有场景目标
- `planned`：已经有剧情方案
- `drafted`：已有 AI 或人工初稿
- `revised`：经过修订
- `checked`：完成一致性检查
- `locked`：作者确认冻结

这样后面你做时间线和导出也更稳。

------

# 十五、第一版验收标准

第一版不要凭感觉验收，要有明确标准。

------

## 功能验收

- 能创建一个项目
- 能录入至少 10 个角色和 20 条设定
- 能创建章节和场景
- 能基于场景生成 2 到 3 个方案
- 能生成一段正文
- 能做至少一次风格修订
- 能检测至少 3 类明显冲突
- 能保存并回看版本

------

## 质量验收

- 单次生成平均响应时间可接受
- 检索上下文不会明显错乱
- 同一角色口吻不会严重漂移
- 一致性检查能抓到“知情越界”和“术语错误”
- 失败时有可见错误提示，不会静默失败

------

# 十六、第一版开发顺序

我建议这样拆迭代，而不是一起上。

------

## Phase 1：静态骨架

做：

- 项目
- 章节
- 场景
- 角色
- lore
- 基础编辑器

目标：

- 先把写作容器搭起来

------

## Phase 2：检索记忆

做：

- pgvector
- embedding
- context compiler
- 右栏上下文展示

目标：

- AI 写作前能拿到正确上下文

------

## Phase 3：AI 核心链路

做：

- plan-scene
- write-scene
- revise-scene

目标：

- 从 brief 到正文跑通

------

## Phase 4：一致性检查

做：

- 术语规则检查
- must_avoid 检查
- LLM 审核

目标：

- 把“吃设定”问题压下来

------

## Phase 5：版本与反馈

做：

- snapshot
- diff
- 满意样本标记

目标：

- 为下一版风格学习打基础

------

# 十七、第一版最值得你优先投入的三个难点

如果你资源有限，最该花时间打磨的是这三个地方：

## 1. Scene 结构化输入

scene brief 结构越清晰，后续所有生成越稳。

## 2. Context Compiler

检索结果怎么整理成模型真正能用的上下文，这是核心壁垒之一。

## 3. Consistency Engine

哪怕第一版只做 60 分的一致性检查，也会比多接一个模型更值钱。

------

# 十八、我建议你把第一版定义成这个名字

## **WriterLab v1：结构化写作与设定一致性版本**

它的主卖点不要写“AI 自动写小说”，而应该是：

- 按场景组织创作
- 自动挂载角色/设定记忆
- 生成前可规划
- 生成后可审校
- 帮你守住设定

这会让第一版目标非常清晰。SS