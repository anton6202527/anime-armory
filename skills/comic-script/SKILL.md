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
- `脚本/第N话/分话大纲.md`：本话目标、冲突、转折、结尾钩子、预计格数。
- `脚本/第N话/panel_script.json`：逐格脚本，schema 见 `references/panel_script_schema.md`。
- `_进度.md`：本话 `漫画脚本` 列完成后回写为 `✅`。

## 工作流

1. 先读作品根 `_进度.md` 和 `_设置.md`，确认当前话、输入模式、漫画形态。
2. 读 `story_bible.md`；缺角色、场景、视觉规则时先补草案并标 `待确认`。
3. 选择分话目标：本话必须有开场吸引、冲突推进、转折或爽点、结尾钩子。
4. 写 `分话大纲.md`，避免只按字数切段；边界服从戏剧闭环。
5. 写 `panel_script.json`。每格至少有 `panel_id`、`story_function`、`description`、`characters`、`dialogue`、`narration`、`sfx`、`art_notes`。
6. 台词写入结构字段，不要求图像模型直接生成文字。
7. 自检通过后回写 `_进度.md` 的 `漫画脚本` 列。

## 分格规则

- 每格只承担一个主要阅读动作：揭示、反应、动作、转折、信息或留白。
- 大格用于情绪峰值、奇观、转折或页末钩子，不用于普通交代。
- 台词要短；一个气泡尽量不超过两行，长说明拆成旁白或多格。
- 角色首次出场格要给足识别信息：脸、发型、服装、标志物或动作习惯。
- 复杂动作拆成“准备 → 接触/爆发 → 后果”，不要塞进一格。
- 出图难点只影响实现路径，不删掉必要剧情；必要时在 `art_notes` 标明分层、反打或合成建议。

## 回写进度

完成本话脚本后，把 `_进度.md` 对应行的 `漫画脚本` 标成 `✅`。若只是草稿，写 `⏳draft`，不要伪装完成。

## 不做什么

- 不做页面坐标和气泡精排；那是 `comic-layout`。
- 不写逐格出图 prompt；那是 `comic-image`。
- 不把长篇源本当唯一入口。
