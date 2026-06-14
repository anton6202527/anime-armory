---
name: novel-create
description: Cold-start ORIGINAL novel creation from scratch — when the user has only a few words / a vague idea / a partial style / scattered notes / a half-draft (NO finished source novel), guide them step-by-step through an interview → 创作蓝图(premise spec) → 设定圣经/角色卡/世界观 → 书名 → 章纲 → Demo 章 → 逐章写作 + 质检 + 导出. Differs from the rest of the novel-* family, which all REQUIRE an existing source (fetch/spinoff/rewrite/continue/expand/condense/review). Defaults output to 写小说/<项目>/ and tracks state in _进度.md. Use when asked to 写本小说 / 从零写 / 帮我写个原创 / 我有个想法 / 我想写...(只有几个字) / 有点设定想写成书. Triggers 原创小说, 从零写小说, 写本新书, 立项, 创作蓝图, 我有个想法写成小说, 帮我把这个点子写成小说, write original novel from scratch, novel from an idea.
---

# novel-create — 原创从零 · 引导式创作编排

用户**只有几个字 / 一个模糊想法 / 一点风格偏好 / 零散笔记 / 半成品片段**（没有成型源文本），由本 skill **访谈把它补全成蓝图，再一步步带到成书**。这是 novel-* 家族里唯一的「从零原创」编排器——其余 skill（fetch/spinoff/rewrite/continue/expand/condense/review）都需要既有源。

产物统一落 `写小说/<项目>/`，状态进 `_进度.md`（照搬 n2d 的分阶段+进度跟踪范式）。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**，按 `../skills/novel-craft/references/选择点与偏好.md`（家族统一的偏好读写机制 + 全部选择点目录与缺省）解析：`<作品根>/_设置.md` → 全局默认 `创作偏好-默认.md` 预填并告知一句 → 缺则**首次问一次**→写回 `_设置.md`→**沉默沿用**（合规/不可逆/花钱点每次仍确认）。

本 skill 涉及的选择点：`目标平台`、`权利来源`、`输出格式`、`篇幅档`、`小说生成模式`、`章节生成粒度`、`AI使用披露`。

## 核心原则

- **访谈先行，别替用户决定故事**：从"几个字"问出 logline / 主角 / 金手指 / 爽点 / 冲突，**一次问一组、给默认建议让用户确认**，不一次性轰炸。详见 `references/interview.md`。
- **创作蓝图 = 这部书的宪法**：`设定/创作蓝图.md` 写死 logline/题材/平台/主角+金手指/核心爽点/主线冲突/风格卡。后续每章都受它约束。蓝图没敲定不进设定、不进章纲。
- **读者契约 = 不偏题 + 好看 + 文学性的执行锚**：蓝图通过后补 `设定/读者契约.md`（模板见 `novel-craft/references/reader-contract.md`），锁定核心题旨、读者承诺、好看机制、文学质感和禁偏清单；Demo 通过后同步到 `审稿/demo_gate.json.reader_contract`，后续每章任务包都必须携带。
- **吃下碎片**：用户给的风格样本 / 零散笔记 / 半成品片段 → `--ingest` 收进 `素材/`，解析成风格卡 + 已知设定，**缺口逐项问**，不丢用户已有的东西。
- **设定圣经做一致性追踪**：原创最大翻车点是设定前后矛盾、金手指无代价。`设定/设定圣经.md` 逐条登记 + 回扫核对。
- **平台决定形态**：题材/爽点/篇幅/开篇钩按目标平台（起点/番茄/晋江/抖音漫剧/红果/历史向）走；起名委托 `novel-title`。
- **Demo gate 最重要**：前 1-3 章定文风/爽点密度/钩子/设定自洽，用户审过才批量写。
- **批量写章先出任务包**：Demo 过审后先跑 `novel-craft/scripts/draft_packets.py`，每章带蓝图/设定/章纲/Demo 风格锚点/状态账本，再写正文。`商业连载` / `漫剧源书` 默认自动走 Architect → Ghostwriter → Senior Editor 三段式任务包；写完填 `审稿/state_delta_第NN章.json`，避免长篇越写越漂。
- **原创=用户自有，天然合法**：无版权筛查（区别于 spinoff/rewrite/expand/condense 的合法性铁律）。

## 工作流（八步，每步末用户审 gate）

### 0. 立项访谈（核心 · 把"几个字"补全成可写的蓝图）—— 必读 `references/interview.md`
> **先看自有差异化候选（选题闭环读端）**：若 `<repo>/生产战绩/差异化候选.json` 存在（由 `n2d-feedback/differentiate.py` 从投放战绩反推），立项时**先读它**，把高分「题材×开场×结尾」白空间组合作为推荐方向之一报给用户（"我们做过的里这类还没做烂，且复用了已验证有效的节奏轴"）。这是 选题→生产→投放→**反哺选题** 闭环的上游落地；没有该文件就正常按用户想法走。

从用户的只言片语 + 碎片，问清这几组（一次一组、带默认建议）：
- **题材类型 + 目标平台**（决定篇幅档/爽点节奏）
- **主角**：是谁 + **金手指/核心能力（必有代价）** + 动机/心结
- **核心爽点**（这本"爽"在哪）+ **主线冲突/反派**
- **规模档**（short/medium/long/微短剧/漫剧 —— 见 `novel-craft/references/split.md` 字数分档）+ **人称视角** + 目标读者
- **风格**：给了样本就吃（→ 风格卡）；没给则记"Demo 后回填"
- **输出**：txt/docx/outline；规模或平台为微短剧/漫剧/红果/抖音漫剧时默认包含 n2d。
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

### 2. 填创作蓝图.md + 读者契约.md（最重要 · 这部的宪法）
把访谈结论写实写细：logline / 主角+金手指 / 核心爽点 / 主线冲突 / 基调 / 风格卡（若有样本）。→ **用户审**。
用户审过后，按 `novel-craft/references/reader-contract.md` 补 `设定/读者契约.md`：一句话题旨、核心戏剧问题、开篇/中段/终局读者承诺、好看机制、文学质感、禁偏清单。这个文件后续被 `draft_packets.py` 每章读取，防止成稿偏题、只刷事件或文笔变薄。

### 3. 建设定圣经 + 角色卡 + 世界观
把蓝图展开成可一致性追踪的设定：金手指的**代价/边界**、势力、关键人物、地理、术语 + 一致性约束清单。**严格按家族统一 schema `novel-craft/references/setting-bible.md`**（设定圣经字段 + 角色卡字段 + 首现章/复用范围/代价三列），这样 spinoff/rewrite/review 读的是同一套字段、不漂。→ **用户审**。

### 4. 书名
委托 `novel-title`（原创类型，按目标平台 5 维打分）。蓝图/设定齐了再起，名字才贴。→ **用户审**，选定写回 `_meta.title` + 各文件标题。

### 5. 章纲
三幕 + 反转 + 钩子；**节拍优先字数兜底**，按平台档定章数/字数 —— 用 `novel-craft/references/{outline,split}.md`。开篇黄金前 3 章立爽点/悬念。→ **用户审**（章纲未敲定不进 Demo）。

### 6. Demo（前 1-3 章）+ 用户审【最重要 gate】
逐章写（每章一个戏剧节拍 + ≥1 钩子，用 `novel-craft/references/chapter.md` 的单章守则 + 子代理 prompt 模板）。验：文风对不对 / 爽点够不够 / 钩子留没留 / 设定自洽。**每章独立审**。文风定了回填 `创作蓝图.md` 风格卡。
> **市场体检（批量前最便宜的 go/no-go）**：Demo 过审后，对 `商业连载` / `漫剧源书` 必跑一次 `novel-score`（题材够不够热、黄金三章钩子、能不能火）。`score_report.json.production_decision` 只允许四类：`go` / `revise` / `kill` / `n2d-adapt`；`n2d-adapt` 才进入 n2d handoff，`revise` 先回蓝图/章纲/开篇修，`kill` 停止批量写。普通稳妥初稿可由用户选择是否评分。
> **机器留痕（必做）**：Demo 审完必须写 `审稿/demo_gate.json`（schema 见 `novel-craft/references/demo-gate.md`）。`status != passed` 不批量写；`style_anchor`、`reader_promises`、`setting_constraints`、`reader_contract` 必须喂给后续逐章子任务和 `novel-review`。

### 7. 续写余下 + 状态增量 + 回扫 + 导出
- **定模式**：按 `skills/novel-craft/references/选择点与偏好.md` 读/问 `小说生成模式`（极速初稿/稳妥初稿/商业连载/漫剧源书）和 `章节生成粒度`（逐章/小批/全书草稿）。缺省推荐 `稳妥初稿 + 逐章`；用户明确要快时用 `极速初稿 + 小批`；要喂漫剧线时用 `漫剧源书`，并把 `输出格式` 设为包含 `n2d`。
- **出任务包**：先读 `novel-craft/references/draft-pipeline.md`；进入小批/全书草稿时先建队列并认领章节，避免多代理重复写：
```bash
python3 skills/novel-craft/scripts/draft_queue.py "<作品根>" init
python3 skills/novel-craft/scripts/draft_queue.py "<作品根>" claim --agent "<名字>"
```
再按认领章号出任务包：
```bash
python3 skills/novel-craft/scripts/draft_packets.py "<作品根>" --next
python3 skills/novel-craft/scripts/draft_packets.py "<作品根>" --range 4-8
```
- `商业连载` / `漫剧源书` 或 `_设置.md` 写 `小说生成工作流：三步迭代` 时，`draft_packets.py` 的 `auto` 默认会一次生成 `第NN章_architect.md`、`第NN章_ghostwriter.md`、`第NN章_editor.md`。只想强制单包时显式传 `--step full`；只想补三段包时传 `--step trio`。
- **逐章写**：按 `写作任务/第NN章.md` 写到 `章节/第NN章.md`。不要跳过任务包直接凭记忆写长篇。
- **状态增量**：每章写完填 `审稿/state_delta_第NN章.json`；涉及人物/能力/伏笔/关系变化时合并回 `审稿/state_ledger.json`，必要时同步 `设定/设定圣经.md` / `设定/角色卡.md`。
- **队列回写**：该章 review/对账通过后跑 `python3 skills/novel-craft/scripts/draft_queue.py "<作品根>" done NN --agent "<名字>"`；返工则 `fail NN --reason "<原因>"` 或 `todo NN`。
- **回扫**：用 `novel-review` 分批扫——重点**设定圣经一致性**（金手指代价没破、设定没前后矛盾）、人设不崩、钩子回收、文风不漂。至少跑一次机检：
```bash
python3 skills/novel-review/scripts/mechanical_check.py "<作品根>" --json-out "<作品根>/审稿/mechanical_findings.json"
```
- **AI 使用披露**：发布/交平台前按 `_设置.md` 的 `AI使用披露` 跑：
```bash
python3 skills/novel-craft/scripts/ai_usage.py "<作品根>" --text-mode AI-generated --publish-target "<平台>"
```
- **导出**：`python3 skills/novel-craft/scripts/export.py "<作品根>" --formats txt,docx,outline[,n2d]`（家族通用导出器）→ `导出/`。`小说生成模式=漫剧源书`、目标平台含抖音漫剧/红果/微短剧/漫剧、或 `score_report.json.production_decision=n2d-adapt` 时，`n2d` 是默认必带格式：导出器会铺 `制漫剧/<书名>/小说/<书名>.docx`、`_n2d_handoff.json`、`asset_registry_preflight.json`，成稿即可交 `n2d` 改编漫剧。

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
- **起名**：`novel-title`　**质检**：`novel-review`　**跨家族经验沉淀 + 路由**：`novel`

## 常见错误

| 错误 | 纠正 |
|---|---|
| 上来就替用户编故事 | 先访谈问清 logline/主角/金手指/爽点/冲突，给默认让用户确认 |
| 让用户重答已给过的碎片 | 先复述理解 + 吃 `素材/`，只补缺口 |
| 蓝图没敲定就建设定/章纲 | 蓝图是宪法，未审不下推 |
| 金手指无代价 / 设定前后矛盾 | 设定圣经登记代价边界 + 回扫逐条核 |
| 跳过 Demo gate 直接批量写 | 文风/爽点/设定自洽 1-3 章就能看出 |
| Demo 过审后不出任务包，直接靠主对话记忆写长篇 | 先跑 `draft_packets.py`，每章用任务包 + 状态账本 |
| 写完章节不填状态增量 | 填 `state_delta_第NN章.json`，合并进 `state_ledger.json` |
| 要发布却没留 AI 使用披露 | 跑 `ai_usage.py`，产出 `合规/AI使用说明.md` |
| 一次性把 8 步全抛给用户 | 一步一 gate，逐步推进（这是引导式的灵魂） |
| 误把"已有源书"的活塞进来 | 有源书 → spinoff/rewrite/continue/expand，别用 novel-create |
