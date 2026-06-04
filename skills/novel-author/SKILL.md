---
name: novel-author
description: Top-level dispatcher for the novel-* skill family — inspects an open-ended novel request (a bare idea / few words / book name / URL / file path / spin-off character / expand·condense·rewrite / 审稿查硬伤 / 评分·能不能火) and routes to the right sub-skill, or resumes an in-progress 写小说/<项目>/ from its _进度.md. Use when the user gives a novel-related task without specifying which tool. Does not write novels itself — only routes; the canonical sub-skill roster is the routing table in the body. Triggers 小说工坊, novel-author, 小说相关任务, 帮我处理小说, 不知道用哪个小说 skill, 小说打分, 小说评分, 能不能火, 值不值得改, 审稿.
---

# novel-author — 小说工坊调度入口

不直接写小说，**读取用户输入 → 路由**到 novel-* 家族最合适的 sub-skill。

和已存在的 `novel2drama` 平行：那条线管漫剧/视频生产、产物落 `制漫剧/`；这条线管纯文本小说生产、**产物统一落 `写小说/<项目>/`**（如 `写小说/仙界闭关小能手-王敦外传/`）。两条线在 novel-fetch（取材）和 novel-spinoff/expand 的输出处自然衔接——`写小说/` 里的成品可交给 `novel2drama` 改编，产物再流向 `制漫剧/`。

**本系列成员**见下方"路由规则"表（家族唯一权威名册；新增/移除子 skill 只改那张表）。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../_偏好约定.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`目标平台`、`权利来源`、`输出格式`、`篇幅档`。

> 作为入口：路由到子 skill 前，若已有项目则读其 `<作品根>/_设置.md`，新项目按全局默认初始化。

## 路由规则

| 用户输入形态 | 路由到 |
|---|---|
| **只有几个字 / 一个想法 / 部分风格 / 零散笔记 / 半成品片段**，没有成型源文 → 要写一本**原创新书** | `novel-create`（访谈→蓝图→设定→章纲→Demo→成书） |
| 给了**书名 / 作者 / URL**，要把书"取回来" | `novel-fetch` |
| 已有原作 + 想**起一个好书名** | `novel-title` |
| 已有原作 + 指定一个**配角名**，要**视角续写**（POV 切换、事件锁定） | `novel-spinoff` |
| 已有原作 + 要**改主线 / 换设定 / 加原创材料**（魔改 / 重构 / 翻拍 / 二创重写） | `novel-rewrite` |
| 已有原作 + 要**接着末章往后写新章节**（时间向前推） | `novel-continue` |
| 已有一段较短的文本，要**扩写章节内细节**（时间不动 / 加厚） | `novel-expand` |
| 已有长篇，要**压缩为短版 / 漫剧脚本量级** | `novel-condense` |
| 自己手写小说时要**工艺指南**（章纲 / 单章 / 扩 / 缩 / 续 的原则） | `novel-craft` |
| 已写好若干章，要**质检 / 审稿 / 查问题**（人设崩 / 视角穿帮 / 设定矛盾 / 锚点漂移 / 节奏 / 原文照搬） | `novel-review` |
| 已写好若干章，要**打分 / 评分 / 市场体检**（题材够不够热、能不能火、值不值得继续写/改、要不要弃稿重立） | `novel-score` |
| 把小说改成**漫剧 / 短剧** | `novel2drama`（另一条管线） |

⚠️ **续 / 扩 / 视角 / 改 四者很容易混**：
- **续写** = 加**新章节**（时间向前推） → novel-continue
- **扩写** = 加**章节内细节**（时间不动 / 既有内容更厚） → novel-expand
- **视角续写** = **换 POV** 写同一段时间、**事件锁定不改** → novel-spinoff
- **改写** = **改主线 / 换设定 / 加原创材料**（事件可改、可新增设定，与视角续写正相反）→ novel-rewrite

⚠️ **审稿(review) vs 评分(score) 别混**：
- **review** = 挑硬伤，判**写得对不对**（人设崩/视角穿帮/设定矛盾/原文照搬）→ novel-review
- **score** = 市场+品质打分，判**值不值得做、能不能火、要不要继续改**（题材热度/爽点/留存/文学性 → 总分+判定+改写ROI）→ novel-score
- 用户问"能不能火/这本行不行/要不要继续写"=score；问"有没有写崩/哪里错了"=review。两者可串用：先 score 定方向，改完再 review 抠细节。

每条路由**简短确认输入后调起对应 skill**，让那个 skill 自走流程。不要在本 skill 里硬写小说。

## 决策树

0. **先看有没有在建项目**：用户指向（或当前正处于）某个 `写小说/<项目>/`，且其下有 `_进度.md` → **先读它**，路由到进度里未完成的那个阶段 skill（与 `novel2drama` 读 `_进度.md` 续跑同理），不要从头追问"你要做什么"。仅当 `_进度.md` 显示已全部完成、或用户明确要开新动作时，才往下走 1-5。
1. 用户给了**书名 / 作者 / URL** 但没给本地文件 → 几乎肯定 `novel-fetch`。
2. 用户给了**本地文件路径** + 明确动作（续写XX视角 / 起书名 / 扩 / 缩 / 漫剧改编）→ 直接按动作路由。
3. 用户给了**本地文件路径** + 没说具体动作 → 问一个澄清问题：要做什么？
4. 用户的输入是**只言片语 / 一个想法 / 一点风格 / 零散碎片**，要写一本**原创新书**（没有成型源文）→ `novel-create`（它会用访谈把碎片补全成蓝图，**别在这里反问"给我个文件"**）。
5. 用户给了**碎片 + 已有半成品/笔记文件**，要继续往成书走 → 也走 `novel-create`，用 `--ingest` 把碎片吃进 `素材/`。

## 何时不路由

- 用户在 `制漫剧/<剧名>/` 目录里有 `_进度.md`（漫剧管线状态）→ 让 `novel2drama` 接手，不要硬塞进 novel-* 家族。
- 用户在写**完全原创**小说（无源文本）→ 路由到 `novel-create`（它有访谈立项 + 蓝图/设定/章纲/Demo/进度跟踪的引导流程）。**只有**用户明确只想"随手聊两句、不要立项不要建项目"时，才不走 skill、直接帮写。

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
