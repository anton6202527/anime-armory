---
name: novel-create
description: Cold-start ORIGINAL novel creation from scratch — when the user has only a few words / a vague idea / a partial style / scattered notes / a half-draft (NO finished source novel), guide them step-by-step through an interview → 创作蓝图(premise spec) → 设定圣经/角色卡/世界观 → 书名 → 章纲 → Demo 章 → 逐章写作 + 质检 + 导出. Differs from the rest of the novel-* family, which all REQUIRE an existing source (fetch/spinoff/rewrite/continue/expand/condense/review). Defaults output to 创作区/写小说/<项目>/ and tracks state in _进度.md. Use when asked to 写本小说 / 从零写 / 帮我写个原创 / 我有个想法 / 我想写...(只有几个字) / 有点设定想写成书. Triggers 原创小说, 从零写小说, 写本新书, 立项, 创作蓝图, 我有个想法写成小说, 帮我把这个点子写成小说, write original novel from scratch, novel from an idea.
---

# novel-create — 原创从零 · 引导式创作编排

用户**只有几个字 / 一个模糊想法 / 一点风格偏好 / 零散笔记 / 半成品片段**（没有成型源文本），由本 skill **访谈把它补全成蓝图，再一步步带到成书**。这是 novel-* 家族里唯一的「从零原创」编排器——其余 skill（fetch/spinoff/rewrite/continue/expand/condense/review）都需要既有源。

产物统一落 `创作区/写小说/<项目>/`，状态进 `_进度.md`。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**，按 `../skills/novel-craft/references/选择点与偏好.md`（家族统一的偏好读写机制 + 全部选择点目录与缺省）解析：`<作品根>/_设置.md` → 全局默认 `创作偏好-默认.md` 预填并告知一句 → 缺则**首次问一次**→写回 `_设置.md`→**沉默沿用**（合规/不可逆/花钱点每次仍确认）。

本 skill 涉及的选择点：`小说用途`、`目标平台`、`权利来源`、`输出格式`、`篇幅档`、`小说生成模式`、`小说生成工作流`、`小批回扫间隔`、`章节生成粒度`、`文本主创模式`、`AI使用披露`。

## 核心原则

- **访谈先行，别替用户决定故事**：从"几个字"问出 logline / 主角 / 金手指 / 爽点 / 冲突，**一次问一组、给默认建议让用户确认**，不一次性轰炸。详见 `references/interview.md`。
- **创作蓝图 = 这部书的宪法**：`设定/创作蓝图.md` 写死 logline/题材/平台/主角+金手指/核心爽点/主线冲突/风格卡。后续每章都受它约束。蓝图没敲定不进设定、不进章纲。
- **读者契约 = 不偏题 + 好看 + 文学性的执行锚**：蓝图通过后补 `设定/读者契约.md`（模板见 `novel-craft/references/reader-contract.md`），锁定核心题旨、读者承诺、好看机制、文学质感和禁偏清单；Demo 通过后同步到 `审稿/demo_gate.json.reader_contract`，后续每章任务包都必须携带。
- **市场基准先于商业蓝图**：`商业连载` / `漫剧源书` / 红果/抖音/番茄等平台项目，在填蓝图前先跑 `novel-score/scripts/collect_market_baseline.py` 或补结构化且未过期的人工证据；没有日期和来源的“热门套路”只能记为假设，不能当蓝图依据。
- **专业资料包先于行业场景**：医疗/法律/刑侦/金融/军事/历史/宗教/海外/科技/职业文，或用户要求“专业、真实、行业感、别外行”时，先用 `novel-research` 建 `资料/专业资料包_<主题>.md` + `资料/research_sources.json`；没有 ready 资料包的事实不能写成确定事实。
- **生活观察先于生活感**：用户要求烟火气、现实质感、人物像活人、职业/地域/日常细节时，先用 `novel-observe` 建 `素材/观察札记.jsonl`；写章时只转化行为、五感和戏剧用途，不照搬真实隐私。
- **审美样本先于精品化**：品质向、文学向、历史、悬疑、Demo 精修或投稿级项目，Demo 过审后用 `novel-aesthetic` 登记项目高光和授权/公版正向样本，后续 line edit 按“为什么有效”的规则改，而不是只按扣分表修。
- **吃下碎片**：用户给的风格样本 / 零散笔记 / 半成品片段 → `--ingest` 收进 `素材/`，解析成风格卡 + 已知设定，**缺口逐项问**，不丢用户已有的东西。
- **设定圣经做一致性追踪**：原创最大翻车点是设定前后矛盾、金手指无代价。`设定/设定圣经.md` 逐条登记 + 回扫核对。
- **用途先于平台**：先确认小说最终用途（传统小说 / 漫剧源书 / 微短剧源书 / **短故事·超短篇** / 短篇试写等），再按目标平台（起点/番茄/七猫/晋江/抖音漫剧/红果/历史向）调读者口味、爽点节奏和开篇钩；起名委托 `novel-title`。**保持当前默认**：用途无默认，`写小说` 不自动等于 `漫剧源书`；用户没选漫剧/微短剧时，按普通小说/网文立项继续。
- **短故事是一等创作目标**：用户要写「短故事 / 超短篇 / 番茄短故事 / 短剧选品池底稿」时，选 `--scale microstory`（别名 `短故事`/`超短篇`），**走单篇闭环结构而非连载章纲**：100 字内抛冲突+金手指 → 一次升级 → 强反转 + 一句话简介，工艺见 `novel-craft/references/short-story.md`。短故事/短中篇是否是当前最快验证形态，必须以 `novel-score` 的 market baseline 或 `novel-research` 平台资料包为准。
- **Demo gate 最重要**：前 1-3 章定文风/爽点密度/钩子/设定自洽，用户审过才批量写。
- **文本主创模式先定**：投稿/出版目标，尤其晋江/起点/番茄/红果等中文网文平台，默认推荐 `人类主创` 或 `AI辅助`；`AI生成` 正文会在 QA gate 被标为高风险并阻断投稿导出，除非用户提供平台接受 AI 正文的当日证据，并写入作用域匹配的 `ai_generated_text_platform_exception` 豁免。
- **批量写章先出任务包**：Demo 过审后先跑 `novel-craft/scripts/draft_packets.py`，每章带蓝图/设定/章纲/Demo 风格锚点/状态账本，再写正文。`商业连载` / `漫剧源书` 默认自动走 Architect → Ghostwriter → Senior Editor 三段式任务包；写完填 `审稿/state_delta_第NN章.json`，避免长篇越写越漂。
- **原创=用户自有，天然合法**：无版权筛查（区别于 spinoff/rewrite/expand/condense 的合法性铁律）。

## 工作流（八步，每步末用户审 gate）

### 0. 立项访谈（核心 · 把"几个字"补全成可写的蓝图）—— 必读 `references/interview.md`
> **先看自有差异化候选（选题闭环读端）**：若 `<repo>/生产战绩/差异化候选.json` 存在（由外部投放侧从战绩反推回灌），立项时**先读它**，把高分「题材×开场×结尾」白空间组合作为推荐方向之一报给用户（"我们做过的里这类还没做烂，且复用了已验证有效的节奏轴"）。这是 选题→生产→投放→**反哺选题** 闭环的上游落地；没有该文件就正常按用户想法走。
> **商业/平台项目先落市场基准**：若用户选择 `商业连载` / `漫剧源书` / `微短剧源书`，或目标平台含红果/抖音/番茄/晋江/起点，本轮先确定要采集的平台；第 1 步建出作品根后立即采集或补人工证据，再填蓝图：
```bash
python3 skills/novel-score/scripts/collect_market_baseline.py "<作品根>/评分" \
  --target-platform "<目标平台>" \
  --allow-fetch-errors
```
红果/抖音榜单无公开网页时，用 `--manual-evidence "红果短剧|YYYY-MM-DD|第三方榜单|结论|URL"` 补证据。把基准结论写入 `设定/创作蓝图.md` 的“市场假设/差异化”小节；采集失败则明确标“未核验”，不要凭旧印象决定题材。
> **专业场景资料包**：若访谈/素材/章纲已命中医疗、法律、刑侦、金融、军事、历史、宗教、海外、科技、职业行业细节，同步建 `novel-research` 资料包；写蓝图时只把已核验事实写成“可用事实”，把未证实内容放进“不确定项/禁用项”。
> **生活观察素材库**：若题材依赖现实质感（县城、医院、学校、打工、家庭、职场、行业日常等），同步跑 `novel-observe` 初始化素材库；没有现成观察时先列“需观察/需采访”任务，不用空泛形容词硬写真实感。

从用户的只言片语 + 碎片，问清这几组（一次一组、带默认建议）：
- **题材类型 + 小说用途 + 目标平台**（决定交付形态/篇幅档/爽点节奏）
- **主角**：是谁 + **金手指/核心能力（必有代价）** + 动机/心结
- **核心爽点**（这本"爽"在哪）+ **主线冲突/反派**
- **规模档**（microstory(短故事)/short/medium/long/微短剧/漫剧 —— 见 `novel-craft/references/split.md` 字数分档）+ **人称视角** + 目标读者
- **风格**：给了样本就吃（→ 风格卡）；没给则记"Demo 后回填"
- **输出**：txt/docx/outline。
> 用户给了碎片（风格样本/笔记/半成品）→ 先复述你的理解、确认，再补缺口。**别让用户重答他已经给过的。**

### 1. 建骨架
```bash
python3 <skill>/scripts/init_project.py \
    --title "<书名或'待定'>" --genre "<题材类型>" \
    --premise "<一句话故事>" --scale short|medium|long|微短剧|漫剧 \
    [--purpose 漫剧源书] [--platform 红果] [--person third-limited] [--target-chapters N] \
    [--ingest <碎片路径>]...
```
→ `创作区/写小说/<项目>/`（设定/{创作蓝图,设定圣经,角色卡,世界观,章纲} + 素材/(碎片) + 章节/ + 审稿/ + 导出/ + _meta + _进度）。

### 2. 填创作蓝图.md + 读者契约.md（最重要 · 这部的宪法）
**先发散再收敛（创意闸 · 蓝图三方案）**：锁定蓝图前必须先给出 **3 个差异化方向**（不是同一方案的三种措辞），每个方向从不同切口发散——如题材/类型混搭、非常规主角视角、结构性玩法（时间线/叙事框架）、金手指的反向设计（代价先行/限制即爽点）。**发散不靠灵感碰运气**：`novel-craft/references/premise-divergence.md` 给了六个撬棍（金手指反向/视角错位/类型杂交/场域平移/前提取反/约束逼创意）+「生成≥5→三项打分→挑或杂交」的可操作步骤；命中高频套路时，`novel-review/scripts/trope_cliche.py` 会在开写前提示，按 premise-divergence 的"命中之后怎么真差异化"处理。每个方向写三行：① 一句话 logline；② **差异化记忆点**（读者能一句话转述传播的"别人没有的东西"）；③ 最像的既有爆款 + 与它的关键差异。然后做**套路自查**：老读者能否从 logline 直接预测前 10 章走向和结局？能 → 该方向回炉或杂交。把选定方向（或杂交结果）与被否方向的一句话理由一起写进蓝图的「差异化决策」小节——留下否稿理由，score 的 novelty 维度与后续 spinoff 选题都会回读。→ **用户选一或杂交**。
把访谈结论写实写细：logline / 主角+金手指 / 核心爽点 / 主线冲突 / 基调 / 风格卡（若有样本）。商业/平台项目把 `评分/market_baseline_<日期>.json` 或人工证据的“热度、拥挤度、差异化缺口”写进“市场假设/差异化”小节，并标明采集日期；没证据的判断只写“待验证假设”。→ **用户审**。
用户审过后，按 `novel-craft/references/reader-contract.md` 补 `设定/读者契约.md`：一句话题旨、核心戏剧问题、开篇/中段/终局读者承诺、好看机制、文学质感、禁偏清单。这个文件后续被 `draft_packets.py` 每章读取，防止成稿偏题、只刷事件或文笔变薄。

### 3. 建设定圣经 + 角色卡 + 世界观
把蓝图展开成可一致性追踪的设定：金手指的**代价/边界**、势力、关键人物、地理、术语 + 一致性约束清单。**严格按家族统一 schema `novel-craft/references/setting-bible.md`**（设定圣经字段 + 角色卡字段 + 首现章/复用范围/代价三列），这样 spinoff/rewrite/review 读的是同一套字段、不漂。长篇/商业项目同步建 `设定/character_guardrails.json`：把主要角色的 `hard_limits` / `forbidden_actions` / `allow_if_context` 结构化，供 `logic_sentry.py` 机检底线违背。→ **用户审**。

长篇/商业连载/系统流/修仙/群像/复杂世界观项目，设定完成后、章纲批量展开前先跑 storyworld 写前压力测试：

```bash
python3 skills/novel-wiki/scripts/storyworld_pressure_test.py "<作品根>"
```

若 `verdict=block_pre_draft`，先补角色目标、世界规则、地理势力、时间线、章纲压力或读者契约，不进入 Demo/批量写章。

### 4. 书名
委托 `novel-title`（原创类型，按目标平台 5 维打分）。蓝图/设定齐了再起，名字才贴。→ **用户审**，选定写回 `_meta.title` + 各文件标题。

### 5. 章纲
三幕 + 反转 + 钩子；**节拍优先字数兜底**，按平台档定章数/字数 —— 用 `novel-craft/references/{outline,split}.md`。开篇黄金前 3 章立爽点/悬念。每个弧段（3-5 章）按 outline.md「意外性设计位」登记至少一处预期违背：先写读者此刻的预期线，再写违背方式与回看合理性的伏笔位；twist 型伏笔同步进 `设定/foreshadowing_ledger.json`（`payoff_is_twist=true`），让 wiki 台账能对账"惊喜是否兑现"。→ **用户审**（章纲未敲定不进 Demo）。

### 6. Demo（前 1-3 章）+ 用户审【最重要 gate】
逐章写（每章一个戏剧节拍 + ≥1 钩子，用 `novel-craft/references/chapter.md` 的单章守则 + 子代理 prompt 模板）。验：文风对不对 / 爽点够不够 / 钩子留没留 / 设定自洽。**每章独立审**。文风定了回填 `创作蓝图.md` 风格卡。
Demo 里真正有效的高光（开篇动作、对白潜台词、场景质感、人物选择、句式节奏）要登记进 `novel-aesthetic`，作为后续全书的正向审美标尺；不是为了仿写原句，而是让后续章节知道“这本书好看的机制是什么”。
> **市场体检（批量前最便宜的 go/no-go）**：Demo 过审后，对 `商业连载` 必跑一次 `novel-score`（题材够不够热、黄金三章钩子、能不能火）。`score_report.json.production_decision` 只允许三类：`go` / `revise` / `kill`；`revise` 先回蓝图/章纲/开篇修，`kill` 停止批量写。普通稳妥初稿可由用户选择是否评分。
> **机器留痕（必做）**：Demo 审完必须写 `审稿/demo_gate.json`（schema 见 `novel-craft/references/demo-gate.md`）。`status != passed` 不批量写；`style_anchor`、`reader_promises`、`setting_constraints`、`reader_contract` 必须喂给后续逐章子任务和 `novel-review`。

> **微短剧/漫剧源书合规预检**：小说用途为 `微短剧源书` / `漫剧源书`，或目标平台含红果/抖音时，Demo 过审后、批量写章前跑：
```bash
python3 skills/novel-review/scripts/platform_compliance.py "<作品根>"
```
`block` 风险先回蓝图/章纲/正文修；`review` 风险作为发布前待办记录。

### 7. 续写余下 + 状态增量 + 回扫 + 导出
- **定模式**：按 `skills/novel-craft/references/选择点与偏好.md` 读/问 `小说生成模式`（极速初稿/稳妥初稿/商业连载）、`小说生成工作流`（默认单步/三步迭代/边写边自检）、`小批回扫间隔`（3章/5章/关闭）和 `章节生成粒度`（逐章/小批/全书草稿）。缺省推荐 `稳妥初稿 + 5章回扫 + 逐章`；长篇/商业连载/漫剧源书在 `draft_packets.py --step auto` 下自动升三步迭代，用户明确写 `默认单步` 才降回单包。用户明确要写完每章立刻自动自检时选 `边写边自检`，用户明确要快时用 `极速初稿 + 小批`。
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
- `篇幅档=long` / `target_chapters>=30` / `商业连载` / `漫剧源书` 或 `_设置.md` 写 `小说生成工作流：三步迭代` 时，`draft_packets.py` 的 `auto` 默认会一次生成 `第NN章_architect.md`、`第NN章_ghostwriter.md`、`第NN章_editor.md`。只想强制单包时显式传 `--step full` 或把项目工作流写成 `默认单步`；只想补三段包时传 `--step trio`。`_设置.md` 写 `小说生成工作流：边写边自检` 时，任务包会自动写入每章的 `post_write.py` 写后自检闭环，并按 `小批回扫间隔` 提示每 3-5 章跑 novel-review 集中修正。
- **长篇弧段包**：每 3-5 章或一个自然 arc 前先跑：
```bash
python3 skills/novel-craft/scripts/arc_packets.py "<作品根>" --arc 4-8
```
该窗口写完后跑：
```bash
python3 skills/novel-review/scripts/arc_gate.py "<作品根>" --arc 4-8
```
连续 3 章不推进读者契约、整段没有题旨对齐、长窗口只种不收会被拦下或提示回修。
- **逐章写**：按 `写作任务/第NN章.md` 写到 `章节/第NN章.md`。不要跳过任务包直接凭记忆写长篇。
- **素材与审美注入**：生活感薄的章节先从 `novel-observe` 选 3-5 条观察素材；投稿级/品质向章节先从 `novel-aesthetic` 选 1-3 条正向样本规则。素材服务场景，样本服务判断，不照搬原句。
- **状态增量**：每章写完填 `审稿/state_delta_第NN章.json`；涉及人物/能力/伏笔/关系变化时合并回 `审稿/state_ledger.json`，必要时同步 `设定/设定圣经.md` / `设定/角色卡.md`。
- **队列回写**：该章 review/对账通过后跑 `python3 skills/novel-craft/scripts/draft_queue.py "<作品根>" done NN --agent "<名字>"`；返工则 `fail NN --reason "<原因>"` 或 `todo NN`。
- **回扫**：用 `novel-review` 分批扫——重点**设定圣经一致性**（金手指代价没破、设定没前后矛盾）、人设不崩、钩子回收、文风不漂。至少跑一次机检：
```bash
python3 skills/novel-review/scripts/mechanical_check.py "<作品根>" --json-out "<作品根>/审稿/mechanical_findings.json"
```
- **AI 使用披露**：发布/交平台前按 `_设置.md` 的 `AI使用披露` 跑：
```bash
python3 skills/novel-craft/scripts/ai_usage.py "<作品根>" \
  --text-mode AI-generated \
  --text-authorship-mode AI生成 \
  --publish-target "<平台>" \
  --human-contribution "<人工蓝图/设定/审稿贡献>" \
  --text-directness outline_to_draft \
  --human-steering "<人工如何控制目标、取舍和终稿>" \
  --review-step 人工通读
```
- **导出**：`python3 skills/novel-craft/scripts/export.py "<作品根>" --formats txt,docx,outline`（家族通用导出器）→ `导出/`。

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
