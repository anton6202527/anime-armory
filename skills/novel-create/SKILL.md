---
name: novel-create
description: Cold-start ORIGINAL novel creation from scratch — when the user has only a few words / a vague idea / a partial style / scattered notes / a half-draft (NO finished source novel), guide them step-by-step through an interview → 创作蓝图(premise spec) → 设定圣经/角色卡/世界观 → 书名 → 章纲 → Demo 章 → 逐章写作 + 质检 + 导出. Differs from the rest of the novel-* family, which all REQUIRE an existing source (fetch/spinoff/rewrite/continue/expand/condense/review). Defaults output to 写小说/<项目>/ and tracks state in _进度.md. Use when asked to 写本小说 / 从零写 / 帮我写个原创 / 我有个想法 / 我想写...(只有几个字) / 有点设定想写成书. Triggers 原创小说, 从零写小说, 写本新书, 立项, 创作蓝图, 我有个想法写成小说, 帮我把这个点子写成小说, write original novel from scratch, novel from an idea.
---

# novel-create — 原创从零 · 引导式创作编排

用户**只有几个字 / 一个模糊想法 / 一点风格偏好 / 零散笔记 / 半成品片段**（没有成型源文本），由本 skill **访谈把它补全成蓝图，再一步步带到成书**。这是 novel-* 家族里唯一的「从零原创」编排器——其余 skill（fetch/spinoff/rewrite/continue/expand/condense/review）都需要既有源。

产物统一落 `写小说/<项目>/`，状态进 `_进度.md`（照搬 novel2drama 的分阶段+进度跟踪范式）。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../_偏好约定.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`目标平台`、`权利来源`、`输出格式`、`篇幅档`。

## 核心原则

- **访谈先行，别替用户决定故事**：从"几个字"问出 logline / 主角 / 金手指 / 爽点 / 冲突，**一次问一组、给默认建议让用户确认**，不一次性轰炸。详见 `references/interview.md`。
- **创作蓝图 = 这部书的宪法**：`设定/创作蓝图.md` 写死 logline/题材/平台/主角+金手指/核心爽点/主线冲突/风格卡。后续每章都受它约束。蓝图没敲定不进设定、不进章纲。
- **吃下碎片**：用户给的风格样本 / 零散笔记 / 半成品片段 → `--ingest` 收进 `素材/`，解析成风格卡 + 已知设定，**缺口逐项问**，不丢用户已有的东西。
- **设定圣经做一致性追踪**：原创最大翻车点是设定前后矛盾、金手指无代价。`设定/设定圣经.md` 逐条登记 + 回扫核对。
- **平台决定形态**：题材/爽点/篇幅/开篇钩按目标平台（起点/番茄/晋江/抖音漫剧/红果/历史向）走；起名委托 `novel-title`。
- **Demo gate 最重要**：前 1-3 章定文风/爽点密度/钩子/设定自洽，用户审过才批量写。
- **原创=用户自有，天然合法**：无版权筛查（区别于 spinoff/rewrite/expand/condense 的合法性铁律）。

## 工作流（八步，每步末用户审 gate）

### 0. 立项访谈（核心 · 把"几个字"补全成可写的蓝图）—— 必读 `references/interview.md`
从用户的只言片语 + 碎片，问清这几组（一次一组、带默认建议）：
- **题材类型 + 目标平台**（决定篇幅档/爽点节奏）
- **主角**：是谁 + **金手指/核心能力（必有代价）** + 动机/心结
- **核心爽点**（这本"爽"在哪）+ **主线冲突/反派**
- **规模档**（short/medium/long/微短剧/漫剧 —— 见 `novel-craft/references/split.md` 字数分档）+ **人称视角** + 目标读者
- **风格**：给了样本就吃（→ 风格卡）；没给则记"Demo 后回填"
- **输出**：txt/docx/outline
> 用户给了碎片（风格样本/笔记/半成品）→ 先复述你的理解、确认，再补缺口。**别让用户重答他已经给过的。**

### 1. 建骨架
```bash
python3 <skill>/scripts/init_project.py \
    --title "<书名或'待定'>" --genre "<题材类型>" \
    --premise "<一句话故事>" --scale short|medium|long|微短剧|漫剧 \
    [--platform 抖音漫剧] [--person third-limited] [--target-chapters N] \
    [--ingest <碎片路径>]...
```
→ `写小说/<项目>/`（设定/{创作蓝图,设定圣经,角色卡,世界观,章纲} + 素材/(碎片) + 章节/ + 审稿/ + 导出/ + _meta + _进度）。

### 2. 填创作蓝图.md（最重要 · 这部的宪法）
把访谈结论写实写细：logline / 主角+金手指 / 核心爽点 / 主线冲突 / 基调 / 风格卡（若有样本）。→ **用户审**。

### 3. 建设定圣经 + 角色卡 + 世界观
把蓝图展开成可一致性追踪的设定：金手指的**代价/边界**、势力、关键人物、地理、术语 + 一致性约束清单。→ **用户审**。

### 4. 书名
委托 `novel-title`（原创类型，按目标平台 5 维打分）。蓝图/设定齐了再起，名字才贴。→ **用户审**，选定写回 `_meta.title` + 各文件标题。

### 5. 章纲
三幕 + 反转 + 钩子；**节拍优先字数兜底**，按平台档定章数/字数 —— 用 `novel-craft/references/{outline,split}.md`。开篇黄金前 3 章立爽点/悬念。→ **用户审**（章纲未敲定不进 Demo）。

### 6. Demo（前 1-3 章）+ 用户审【最重要 gate】
逐章写（每章一个戏剧节拍 + ≥1 钩子，用 `novel-craft/references/chapter.md` 的单章守则 + 子代理 prompt 模板）。验：文风对不对 / 爽点够不够 / 钩子留没留 / 设定自洽。**每章独立审**。文风定了回填 `创作蓝图.md` 风格卡。

### 7. 续写余下 + 回扫 + 导出
- **逐章写**：subagent 逐章，喂【创作蓝图 + 设定圣经 + Demo 文风样本 + 章纲本章条目 + 风格卡】；写完更新 `_进度.md` 写作表。
- **回扫**：用 `novel-review` 分批扫——重点**设定圣经一致性**（金手指代价没破、设定没前后矛盾）、人设不崩、钩子回收、文风不漂。
- **导出**：txt / docx / outline → `导出/`。成稿可交 `novel2drama` 改编漫剧。

## 与家族其它 skill 的边界（防误路由）

| 你手上有的 | 用 |
|---|---|
| **只有几个字 / 想法 / 风格 / 碎片，没成型源文** | **novel-create（本 skill）** |
| 一本写好的书，要起名 | `novel-title` |
| 源书 + 配角名，换视角写（事件锁定） | `novel-spinoff` |
| 源书，要改主线/换设定/魔改 | `novel-rewrite` |
| 源书末章后接着写新章节 | `novel-continue` |
| 短文加细节 / 长文压缩 | `novel-expand` / `novel-condense` |
| 已写章节查质量 | `novel-review` |

> 关键区分：**novel-create 从零生成事件骨架**；rewrite/continue/spinoff 都站在一本**已有的书**上改。手里没有"那本书"就是 novel-create。

## 详细参考
- **立项访谈引导（几个字→蓝图 / 吃碎片 / 不轰炸用户）**：`references/interview.md`
- **章纲 / 单章 / 拆分工艺**：`novel-craft/references/{outline,chapter,split}.md`
- **起名**：`novel-title`　**质检**：`novel-review`　**跨家族经验沉淀 + 路由**：`novel-author`

## 常见错误

| 错误 | 纠正 |
|---|---|
| 上来就替用户编故事 | 先访谈问清 logline/主角/金手指/爽点/冲突，给默认让用户确认 |
| 让用户重答已给过的碎片 | 先复述理解 + 吃 `素材/`，只补缺口 |
| 蓝图没敲定就建设定/章纲 | 蓝图是宪法，未审不下推 |
| 金手指无代价 / 设定前后矛盾 | 设定圣经登记代价边界 + 回扫逐条核 |
| 跳过 Demo gate 直接批量写 | 文风/爽点/设定自洽 1-3 章就能看出 |
| 一次性把 8 步全抛给用户 | 一步一 gate，逐步推进（这是引导式的灵魂） |
| 误把"已有源书"的活塞进来 | 有源书 → spinoff/rewrite/continue/expand，别用 novel-create |
