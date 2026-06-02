---
name: novel-author
description: Top-level dispatcher for the novel-* skill family. Inspects user input (book name / URL / file path / spin-off character / expand or condense request) and routes to the right sub-skill — novel-fetch / novel-title / novel-spinoff / novel-expand / novel-condense / novel-craft. Use when user gives an open-ended novel-related task without specifying which tool to use. Does not write novels itself — only routes. Triggers 小说工坊, novel-author, 小说相关任务, 帮我处理小说, 不知道用哪个小说 skill.
---

# novel-author — 小说工坊调度入口

不直接写小说，**读取用户输入 → 路由**到 novel-* 家族最合适的 sub-skill。

和已存在的 `novel2drama` 平行：那条线管漫剧/视频生产、产物落 `制漫剧/`；这条线管纯文本小说生产、**产物统一落 `写小说/<项目>/`**（如 `写小说/仙界闭关小能手-王敦外传/`）。两条线在 novel-fetch（取材）和 novel-spinoff/expand 的输出处自然衔接——`写小说/` 里的成品可交给 `novel2drama` 改编，产物再流向 `制漫剧/`。

**本系列成员**：`novel-fetch`（取公版）· `novel-title`（起名）· `novel-spinoff`（配角外传·锁事件）· `novel-rewrite`（改写/魔改·改事件加设定）· `novel-continue`（续写）· `novel-expand`/`novel-condense`（扩/缩）· `novel-craft`（写作工艺基元）· `novel-review`（已写章节质检/审稿）。

## 路由规则

| 用户输入形态 | 路由到 |
|---|---|
| 给了**书名 / 作者 / URL**，要把书"取回来" | `novel-fetch` |
| 已有原作 + 想**起一个好书名** | `novel-title` |
| 已有原作 + 指定一个**配角名**，要**视角续写**（POV 切换、事件锁定） | `novel-spinoff` |
| 已有原作 + 要**改主线 / 换设定 / 加原创材料**（魔改 / 重构 / 翻拍 / 二创重写） | `novel-rewrite` |
| 已有原作 + 要**接着末章往后写新章节**（时间向前推） | `novel-continue` |
| 已有一段较短的文本，要**扩写章节内细节**（时间不动 / 加厚） | `novel-expand` |
| 已有长篇，要**压缩为短版 / 漫剧脚本量级** | `novel-condense` |
| 自己手写小说时要**工艺指南**（章纲 / 单章 / 扩 / 缩 / 续 的原则） | `novel-craft` |
| 已写好若干章，要**质检 / 审稿 / 查问题**（人设崩 / 视角穿帮 / 设定矛盾 / 锚点漂移 / 节奏 / 原文照搬） | `novel-review` |
| 把小说改成**漫剧 / 短剧** | `novel2drama`（另一条管线） |

⚠️ **续 / 扩 / 视角 / 改 四者很容易混**：
- **续写** = 加**新章节**（时间向前推） → novel-continue
- **扩写** = 加**章节内细节**（时间不动 / 既有内容更厚） → novel-expand
- **视角续写** = **换 POV** 写同一段时间、**事件锁定不改** → novel-spinoff
- **改写** = **改主线 / 换设定 / 加原创材料**（事件可改、可新增设定，与视角续写正相反）→ novel-rewrite

每条路由**简短确认输入后调起对应 skill**，让那个 skill 自走流程。不要在本 skill 里硬写小说。

## 决策树

1. 用户给了**书名 / 作者 / URL** 但没给本地文件 → 几乎肯定 `novel-fetch`。
2. 用户给了**本地文件路径** + 明确动作（续写XX视角 / 起书名 / 扩 / 缩 / 漫剧改编）→ 直接按动作路由。
3. 用户给了**本地文件路径** + 没说具体动作 → 问一个澄清问题：要做什么？
4. 用户的输入是**只言片语**，没具体材料 → 问要什么材料 / 给什么文件。

## 何时不路由

- 用户在 `制漫剧/<剧名>/` 目录里有 `_进度.md`（漫剧管线状态）→ 让 `novel2drama` 接手，不要硬塞进 novel-* 家族。
- 用户在写**完全原创**小说（无源文本）→ 直接由当前 Claude 协助写，不必走任何 skill。

## 合法性继承（铁律）

novel-* 家族的合法性规则一致：**公版 / 自有 / 用户声明授权（`--i-have-rights`）**。

- 命中付费墙站或当代受版权网文，本 skill **拒绝路由** novel-spinoff / novel-rewrite / novel-expand / novel-condense（这些都会派生作品）。
- 仅当 `novel-fetch` 用来取公版书、或 `novel-title` 用来起原创书名时，才可对原作版权状态宽松。
- 路由前先做一次铁律筛查；命中即拒做并解释为什么。

## 持续改进（meta-capability）

novel-author 同时承担 novel-* 家族的**经验累积**职责。在跑任何 novel-* 流水线的过程中，遇到以下**信号**时及时把发现写进对应文件：

### 触发信号

- **用户明确反馈**："这点不错"/"这样写就对了"/"以后都这样"/"不要那样，要这样"
- **自检反复出现的弱点**：同一类问题在两章 Demo 里都出现 → 升格为 skill 守则
- **用户重复问同一个问题**：可能跨项目都会问 → 升格为 Q&A
- **跨 skill 的判断模式**：例如"用什么标准甄别主角 vs 配角"、"原作太大锚点怎么精筛"

### 写到哪里

| 发现类型 | 写到 |
|---|---|
| 单 skill 的工艺细节 | 该 skill 的 `references/<相关>.md` |
| 单章写作守则 | `novel-craft/references/chapter.md` |
| 章纲编织模式 | `novel-craft/references/outline.md` |
| 扩 / 续 / 缩 的特定工艺 | `novel-craft/references/{expand,continue,condense}.md` |
| 路由判断模式（哪个 skill 适合哪种输入） | `novel-author/SKILL.md` 路由表 |
| 跨 skill 的 Q&A / 判断标准 | `novel-author/Q&A.md` |
| 项目特有的设定 / 角色口吻 | 项目本地的 `设定/角色卡.md`，**不写进 skill** |

### 节奏

- 不要每条都写——**只有清晰、可重用、跨场景适用**的才写。
- 用户明确叫停"别写"时不写。
- 写之前可以确认一次（"我想把这条加进 <文件>，要不要？"）；auto mode 下可以更主动，但优先选 `Q&A.md` 这个低风险落点。

### 反模式

- 把项目特有细节误写进 skill references（如某项目角色卡里的具体设定）。
- 在 SKILL.md 末尾堆 changelog——经验整合到正文，不要 changelog。
- 写进 skill 后不更新该 skill 的"常见错误"表，造成经验孤岛。
- 同一条经验在两个 skill 里写两份——应合并到 `novel-craft/` 后引用。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 拿到模糊请求就硬路由 | 先问澄清问题，2-3 句话搞清楚动作再路由 |
| 把漫剧改编请求路由进 novel-* | 改用 novel2drama 那条线 |
| 跳过合法性筛查 | 路由前必须查；本 skill 的最大职责就是把铁律前置 |
| 在本 skill 里直接开始写 | 不写；路由出去 |
