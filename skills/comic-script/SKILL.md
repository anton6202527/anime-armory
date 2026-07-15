---
name: comic-script
description: 画漫画脚本阶段。Use when converting a story source, idea, outline, or existing script into comic story bible updates, chapter outlines, panel scripts, dialogue, narration, SFX, per-panel dramatic functions, visual contracts, layout weights, and optional ink/tone/effects hints. Produces 设定库/story_bible.md, 脚本/第N话/分话大纲.md, and panel_script.json for projects under 创作区/画漫画. Triggers 漫画脚本, 分格脚本, 分话大纲, panel_script, 分格, 漫画改编, 写漫画故事板, comic-script.
---

# comic-script — 漫画脚本与分格

把源本、点子或已有脚本改成漫画可执行的分话大纲和逐格脚本。目标不是写散文正文，而是给排版、出图、嵌字和审查提供结构化真值。

输入可来自 `源本/`、用户口述、已有大纲或已有对白脚本。完整小说不是硬前置；原创漫画可以从故事蓝图直接开始。`source_semantics_gate.py` 可直接读取 TXT / Markdown / JSON / DOCX 主文档正文；不再要求用户先把 Word 另存为 TXT。

## 输入

- `_设置.md`：输入模式、漫画形态、阅读方向、视觉风格。
- `设定库/story_bible.md`：角色、世界观、视觉规则；缺失时先补草案。
- `源本/`：可选源本、梗概或脚本。
- 已有 `脚本/第N话/分话大纲.md` / `panel_script.json`：续写或修订时读取。

## 输出

- `设定库/story_bible.md`：补齐角色、场景、道具、视觉禁漂移项。
- `脚本/第N话/source_semantics.json/md`：当源本是外语、文言/古汉语、混合语言或用户要求强制归一化时，先记录源语言、目标嵌字语言、专名表、逐段白话/译文、歧义点和改编取舍账。
- `脚本/第N话/分话大纲.md`：本话目标、冲突、转折/兑现、结尾模式和软容量意图。
- `脚本/第N话/panel_script.json`：逐格脚本，schema 见 `references/panel_script_schema.md`。
- `_进度.md`：本话 `漫画脚本` 列完成后回写为 `✅`。

## 工作流

1. 先读作品根 `_进度.md` 和 `_设置.md`，确认当前话、输入模式、漫画形态。
2. 读 `story_bible.md`；缺角色、场景、视觉规则时先补草案并标 `待确认`。
3. 源本是外语、文言/古汉语、混合语言，或用户要求跨语种/古文改编时，先跑源语义归一化 gate；未通过前不要写最终 `panel_script.json`。
4. 先填 `脚本/split_blueprint.json` v2 的本话 chapter contract：`source_spans / reader_promise / core_conflict / turning_point / payoff / ending_mode / budget / entry_state / continuity_delta / exit_state`，schema 见 `references/chapter_contract_schema.md`。连载话边界服从戏剧闭环；四格、完结短篇和情绪落点不强制 cliffhanger。
5. 写 `分话大纲.md`，避免按字数、固定格数或源回目硬切；容量只写 `budget.soft_range`，不得设置硬上下限。
6. 写 `panel_script.json`。顶层必须有 `visual_contract`，把本话风格基线、场景锚、光位/冷暖、轴线视线、角色状态演进和人物完整性口径写成可审字段。每格至少有 `panel_id`、`story_function`、`description`、`characters`、`dialogue`、`narration`、`sfx`、`art_notes`；含角色格还必须有 `character_bindings[]`（`character_id/form_id/outfit_id/expression_id/state_id`）、`gaze_target`、`eyeline_direction`、`character_integrity`，含场景格还必须有 `scene_anchor_id`、`spatial_layout`、`lighting_anchor`、`axis_eyeline`（可从 `visual_contract.scene_anchors` 继承）。`scene_anchor_id` 必须登记成 `LOC_` 场景锚；眼神目标不能只写情绪词、远方或看镜头；多人同格必须写 `spatial_relationships/blocking/staging`。需要镜头感时，参考 `skills/comic/references/运镜/manifest.json`，把视频运镜转译为静态机位/景别/前景遮挡/速度线/格子轻重（如推镜头=近景聚焦，拉镜头=扩大环境，甩镜=斜切格+速度线，焦点转移=前后景虚实）。源本改编时每格还要写 `source_segment_refs`；跨语种/古文归一化继续保留 `source_excerpt`、`meaning_zh`、`text_target`、`adaptation_note`。需要传统漫画审美时，可预填 `layout_weight`、`panel_shape`、`gutter_intent`、`ink_plan`、`black_fill_plan`、`tone_plan`、`value_plan`、`effects_plan`，供 `comic-name` 和 `comic-finishing` 继承。
7. 台词写入结构字段，不要求图像模型直接生成文字；跨语种/古文改编时，最终嵌字文本写 `dialogue[].text_target`、`narration_target` 或对应目标字段，原文不要覆盖掉。
8. 自检通过后回写 `_进度.md` 的 `漫画脚本` 列。

## 源语义归一化 gate

v2 改编合同优先消费 `split_blueprint.source_spans`，不再默认把第 N 话等同源本第 N 章；没有 v2 合同时才兼容扫描作品根 `源本/`。报告绑定本话合同 SHA 和源文件 SHA，源变化会 stale。所有源段完整建账，`--max-segments` 仅保留兼容参数、不再截断第 12 段之后的内容。外语、文言/古汉语或混合语言还须填专名、释义、目标嵌字与歧义；panel_script 存在后会确定性验证 `source_segment_refs` 和改编决策 coverage。

```bash
python3 skills/comic-script/scripts/source_semantics_gate.py "创作区/画漫画/作品名" --chapter 第1话
```

DOCX 会用标准库直接读取 `word/document.xml` 的正文段落；页眉、批注和修订说明不会混入改编源文本。DOCX/TXT 的统一清洗只删除已登记、完整且独立成段的抓取包装签名（例如 Wikisource 导出残留 `Public domainPublic domainfalsefalse`，也兼容其拆成相邻文本行的形态）；包含额外正文或标点的 `public domain` 叙述一律保留，避免用关键词误删原文。无法解析的 DOCX 会显式记为 `invalid` 并阻断，不会静默当作无源本。

常用覆盖：

```bash
python3 skills/comic-script/scripts/source_semantics_gate.py "创作区/画漫画/作品名" --chapter 第1话 --source-language 文言 --target-text-language 中文 --force-normalization
```

通过标准：

- `source_language`、`target_text_language` 已记录。
- `proper_noun_glossary` 已处理，`glossary_reviewed=true`。
- 每段都有 `source_excerpt`、已定稿的 `adaptation_decision` 和 `adaptation_note`；需语言归一化时另有 `meaning_zh`、`text_target`。
- 歧义点已处理，`ambiguity_reviewed=true`。
- `panel_script.json` 中每格用 `source_segment_refs` 追溯源段；新增衔接格须显式写 `adaptation_origin=original_bridge` 和改编说明。

## 系列级开发与机检（2026-07 落地·参照同仓成熟生产线已验证模式的漫画重实现）

- **开发包（长篇源本改编建议先跑）**：`python3 skills/comic-script/scripts/development_pack.py <作品根> scaffold --write` 生成开发三件套和 v2 `split_blueprint`。每话以真实 `source_spans`、读者承诺、冲突/转折/兑现、精确 `ending_mode`、软 `budget` 和长线状态三段式形成可签收合同。内容填完置 `confirmed` 后，由 reviewer 在 `开发包/signoff.json` 对三件套 SHA 签收；`check --strict` 对缺件、v1 未迁移、缺源、合同字段/话次/coverage 缺口、占位与签收 stale 非零退出。
- **分话节拍机检**：`chapter_beat_audit.py <作品根> 第N话 --write`。合同/文件缺失是确定性 must；首屏、末格功能、高潮格序、软容量和平台投稿快照都是 `heuristic/platform WARN`。四格不套 20 格与 cliffhanger，`20` 只在目标平台明确为快看时提示，不能作为通用切话标准。
- **伏笔种下→兑现跨话账本（SP1·report-only 起步·gate image_preflight 自动跑）**：`development_pack.foreshadowing_ledger` 是立项期一次性静态清单，逐话写完分格后无人回头核对「这坑第几话兑现、有没有忘、兑现有没有早于种下」。条漫是长线连载，实证空档正是「后续话次断供」（伏笔埋了不收=追更动力流失）。`setup_payoff_ledger.py <作品根> 第N话 --write` 从故事面文本（台词/旁白/音效·不扫 art_notes craft 术语）按**显式悬念标记**捞 `open` 坑（进 gate）、按**挖坑句式**捞 `candidate` 弱信号（只提示），并把 development_pack 手填坑作**种子**合入 `设定库/setup_payoff_ledger.json`（不覆盖已填 payoff_chapter）。逐话审 `setup_unlogged/payoff_unfilled/payoff_overdue/payoff_before_setup`。`--all` 刷全书账本；`--strict` 本话 must 级 exit 1（想开硬闸时用）。SP1 与 `source_semantics`（语言归一）、`visual_contract`（视觉状态跨格）、`chapter_beat_audit`（单话节拍）正交——它管**叙事坑跨话**。
- **分话量化原则**：没有跨格式通用格数。快看投稿不少于 20 格仅属于目标平台快照；页漫、条漫、四格、短篇分别用自己的 `format_profile`，周更产能只进 `budget.soft_range`。高潮格序同样只是粗筛，正式节奏在缩略分镜/name board、页面或滚动几何中复核。

## 分格规则

- 每格只承担一个主要阅读动作：揭示、反应、动作、转折、信息或留白。
- 大格用于情绪峰值、奇观、转折或页末钩子，不用于普通交代。
- 重要格写 `layout_weight=heavy`，过渡/反应格写 `compact` 或 `medium`；这会影响 `comic-name` 的缩略分镜/name board 和 `comic-layout` 的格子比例。
- 台词要短；一个气泡尽量不超过两行，长说明拆成旁白或多格。
- 外语、文言/古汉语、专名密集文本的衡量以“语义动作”和“可嵌字目标文本”为准，不用源文长度直接决定格数。
- 角色首次出场格要给足识别信息：脸、发型、服装、标志物或动作习惯。
- 含角色格必须写眼神目标和视线方向：看对话对象、对手、道具、命中点、画外声源或下一动作目标；除明确 POV/破第四墙外，不要默认看读者镜头，也不要写“坚定眼神/看前方/远方”这种不可执行目标。
- 含场景格必须继承同一 `LOC_` 场景锚：空间布局、常驻物件、主光方向/冷暖和人物左右轴线不能跨格随机漂移。
- 人物完整性要逐格写清：脸型、眼型/眼距、发际线、发型轮廓、服装主色、标志物、手脚和关键道具是否完整可读；动作格写清接触点和不可裁掉的部位。
- 复杂动作拆成“准备 → 接触/爆发 → 后果”，不要塞进一格。
- 动作、冲击、揭示、恐惧、速度感强的格子可写 `effects_plan`；黑白页漫和日漫网点风格建议写 `tone_plan` 或让 `comic-finishing` 生成显式计划。
- 运镜库只作为漫画镜头语言参考，不要求单格表达完整运动。优先把 `skills/comic/references/运镜/manifest.json` 的条目转译成静态构图、速度线、集中线、格子尺寸和阅读顺序。
- 出图难点只影响实现路径，不删掉必要剧情；必要时在 `art_notes` 标明分层、反打或合成建议。

## 回写进度

完成本话脚本后，把 `_进度.md` 对应行的 `漫画脚本` 标成 `✅`。若只是草稿，写 `⏳draft`，不要伪装完成。

## 不做什么

- 不做页面坐标和气泡精排；那是 `comic-layout`。
- 不写逐格出图 prompt；那是 `comic-image`。
- 不把长篇源本当唯一入口。
