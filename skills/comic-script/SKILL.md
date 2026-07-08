---
name: comic-script
description: 画漫画脚本阶段。Use when converting a story source, idea, outline, or existing script into comic story bible updates, chapter outlines, panel scripts, dialogue, narration, SFX, and per-panel dramatic functions. Produces 设定库/story_bible.md, 脚本/第N话/分话大纲.md, and panel_script.json for projects under 创作区/画漫画. Triggers 漫画脚本, 分格脚本, 分话大纲, panel_script, 分格, 漫画改编, 写漫画故事板, comic-script.
---

# comic-script — 漫画脚本与分格

把源本、点子或已有脚本改成漫画可执行的分话大纲和逐格脚本。目标不是写散文正文，而是给排版、出图、嵌字和审查提供结构化真值。

输入可来自 `源本/`、用户口述、已有大纲或已有对白脚本。完整小说不是硬前置；原创漫画可以从故事蓝图直接开始。

## 输入

- `_设置.md`：输入模式、漫画形态、阅读方向、视觉风格。
- `设定库/story_bible.md`：角色、世界观、视觉规则；缺失时先补草案。
- `源本/`：可选源本、梗概或脚本。
- 已有 `脚本/第N话/分话大纲.md` / `panel_script.json`：续写或修订时读取。

## 输出

- `设定库/story_bible.md`：补齐角色、场景、道具、视觉禁漂移项。
- `脚本/第N话/source_semantics.json/md`：当源本是外语、文言/古汉语、混合语言或用户要求强制归一化时，先记录源语言、目标嵌字语言、专名表、逐段白话/译文、歧义点和改编取舍账。
- `脚本/第N话/分话大纲.md`：本话目标、冲突、转折、结尾钩子、预计格数。
- `脚本/第N话/panel_script.json`：逐格脚本，schema 见 `references/panel_script_schema.md`。
- `_进度.md`：本话 `漫画脚本` 列完成后回写为 `✅`。

## 工作流

1. 先读作品根 `_进度.md` 和 `_设置.md`，确认当前话、输入模式、漫画形态。
2. 读 `story_bible.md`；缺角色、场景、视觉规则时先补草案并标 `待确认`。
3. 源本是外语、文言/古汉语、混合语言，或用户要求跨语种/古文改编时，先跑源语义归一化 gate；未通过前不要写最终 `panel_script.json`。
4. 选择分话目标：本话必须有开场吸引、冲突推进、转折或爽点、结尾钩子。
5. 写 `分话大纲.md`，避免只按字数切段；边界服从戏剧闭环。
6. 写 `panel_script.json`。顶层必须有 `visual_contract`，把本话风格基线、场景锚、光位/冷暖、轴线视线、角色状态演进和人物完整性口径写成可审字段。每格至少有 `panel_id`、`story_function`、`description`、`characters`、`dialogue`、`narration`、`sfx`、`art_notes`；含角色格还必须有 `gaze_target`、`eyeline_direction`、`character_integrity`，含场景格还必须有 `scene_anchor_id`、`spatial_layout`、`lighting_anchor`、`axis_eyeline`（可从 `visual_contract.scene_anchors` 继承）。`scene_anchor_id` 必须登记成 `LOC_` 场景锚；眼神目标不能只写情绪词、远方或看镜头；多人同格必须写 `spatial_relationships/blocking/staging`。若本话经过源语义归一化，每格还要保留 `source_excerpt`、`meaning_zh`、`text_target`、`adaptation_note`。
7. 台词写入结构字段，不要求图像模型直接生成文字；跨语种/古文改编时，最终嵌字文本写 `dialogue[].text_target`、`narration_target` 或对应目标字段，原文不要覆盖掉。
8. 自检通过后回写 `_进度.md` 的 `漫画脚本` 列。

## 源语义归一化 gate

默认扫描作品根 `源本/`，自动判断源语言；若检测到外语、文言/古汉语或混合语言，会生成待填写账本并以非零状态退出。填完专名、释义、目标嵌字、歧义和改编取舍后再次运行，同一文件通过才继续分格。

```bash
python3 skills/comic-script/scripts/source_semantics_gate.py "创作区/画漫画/作品名" --chapter 第1话
```

常用覆盖：

```bash
python3 skills/comic-script/scripts/source_semantics_gate.py "创作区/画漫画/作品名" --chapter 第1话 --source-language 文言 --target-text-language 中文 --force-normalization
```

通过标准：

- `source_language`、`target_text_language` 已记录。
- `proper_noun_glossary` 已处理，`glossary_reviewed=true`。
- 每段有 `source_excerpt`、`meaning_zh`、`text_target`、`adaptation_decision`、`adaptation_note`。
- 歧义点已处理，`ambiguity_reviewed=true`。
- `panel_script.json` 中的每格能追溯到源摘录、中文释义、目标嵌字文本和改编取舍说明。

## 分格规则

- 每格只承担一个主要阅读动作：揭示、反应、动作、转折、信息或留白。
- 大格用于情绪峰值、奇观、转折或页末钩子，不用于普通交代。
- 台词要短；一个气泡尽量不超过两行，长说明拆成旁白或多格。
- 外语、文言/古汉语、专名密集文本的衡量以“语义动作”和“可嵌字目标文本”为准，不用源文长度直接决定格数。
- 角色首次出场格要给足识别信息：脸、发型、服装、标志物或动作习惯。
- 含角色格必须写眼神目标和视线方向：看对话对象、对手、道具、命中点、画外声源或下一动作目标；除明确 POV/破第四墙外，不要默认看读者镜头，也不要写“坚定眼神/看前方/远方”这种不可执行目标。
- 含场景格必须继承同一 `LOC_` 场景锚：空间布局、常驻物件、主光方向/冷暖和人物左右轴线不能跨格随机漂移。
- 人物完整性要逐格写清：脸型、眼型/眼距、发际线、发型轮廓、服装主色、标志物、手脚和关键道具是否完整可读；动作格写清接触点和不可裁掉的部位。
- 复杂动作拆成“准备 → 接触/爆发 → 后果”，不要塞进一格。
- 出图难点只影响实现路径，不删掉必要剧情；必要时在 `art_notes` 标明分层、反打或合成建议。

## 回写进度

完成本话脚本后，把 `_进度.md` 对应行的 `漫画脚本` 标成 `✅`。若只是草稿，写 `⏳draft`，不要伪装完成。

## 不做什么

- 不做页面坐标和气泡精排；那是 `comic-layout`。
- 不写逐格出图 prompt；那是 `comic-image`。
- 不把长篇源本当唯一入口。
