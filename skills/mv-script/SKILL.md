---
name: mv-script
description: 制MV 剧本创作 — 听歌识影。从 歌词 + 节拍分析(beatgrid) 创作 MV 的【视觉蓝图】（叙事结构、视觉隐喻、角色张力）与角色/场景设定；也支持 `歌曲输入时序=后配歌曲` 时先根据歌名/歌词草稿/视觉想法做 rough 蓝图，待成品歌入库后再按真实 beatgrid 复核。Use when asked to 为MV写脚本 / 创作视觉蓝图 / 设计MV情节 / 听歌识影 / MV编剧 / 后配歌曲先做视觉 / mv-script.
---

# mv-script — MV 剧本创作（导演/编剧）

你是 **AI MV 导演/编剧**。你的任务是为一首歌设计**视觉灵魂**。若 `歌曲输入时序=先传音乐`，以成品歌 + beatgrid 为准；若 `歌曲输入时序=后配歌曲` 且还没有最终音频，只能先做 rough 视觉蓝图，不能锁正式 clip 时长。

## 核心任务

1.  **听歌识影**：分析歌词的主题、情绪和叙事弧光。
2.  **创作视觉蓝图**：将宏观的段落（Verse/Chorus）映射到具体的画面意图、主色调和转场风格。
3.  **定死视觉契约**：在出图前定好主角形象（身份锚点）和全局画风（Global Style），确保全片视觉一致，而不是让生图 AI 随缘发挥。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/mv-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md`；再缺则**首次问一次**。

涉及的选择点：`歌曲输入时序`、`MV视觉风格`、`MV叙事模式`（写实叙事/意识流隐喻/纯舞台/混剪）、`MV一致性增强`。

## 工作流

1.  **先判定歌曲输入时序**：读 `<作品根>/_设置.md` 的 `歌曲输入时序`。
    *   `先传音乐`：确保 `歌/`、`词/` 已入库，且已运行 `mv-beat` 产出 `节拍/beatgrid.json`。
    *   `后配歌曲`：若没有 `歌/song.*`，可先读取歌名、歌词草稿、主题/风格需求做 rough 蓝图；在 `视觉蓝图.md` 顶部标 `状态：rough（待成品歌/beatgrid 复核）`。
2.  **概念提案**：
    *   读取 `lyrics.md` 和 `beatgrid.json`。
    *   有 beatgrid 时分析歌曲能量起伏（Energy Profile）；后配且无音频时只做段落/情绪假设，不写死秒点。
    *   向用户提供 2-3 个不同方向的视觉概念（Concept Sketches）。
3.  **蓝图落地**：
    *   先用 `write_script.py --save` 保存本次创作 prompt 到 `设定/mv_script_prompt.md`。
    *   AI 生成蓝图 Markdown 后，用 `write_script.py --content-file <生成稿.md>` 写回 `视觉蓝图.md`；脚本会落 `设定/mv_script_state.json` 并按当前状态回写 `_进度.md` 的 `script` 或 `script_review` 行。
    *   在 `设定/characters/` 和 `设定/locations/` 下生成最初的角色卡和场景卡文本（含定妆词）。
4.  **更新进度**：由 `--content-file` 写回时自动处理。后配歌曲 rough 蓝图完成后，下一步是 `歌曲入库/定稿`，不是 `mv-plan`；最终歌和 beatgrid 入库后再次复核，完成后标 `script_review`。

## 产物

- `视觉蓝图.md`：深度导演脚本，包含段落↔画面映射。
- `设定/mv_script_prompt.md`：本次蓝图创作 prompt（`--save` 时）。
- `设定/mv_script_state.json`：蓝图来源、歌曲时序、是否已有歌和 beatgrid 的状态留痕。
- `设定/characters/*.md`：主角形象定稿。
- `设定/locations/*.md`：主场景定稿。

## 用法

```bash
python3 skills/mv-script/scripts/write_script.py "<制MV作品根>"
python3 skills/mv-script/scripts/write_script.py "<制MV作品根>" --save
python3 skills/mv-script/scripts/write_script.py "<制MV作品根>" --content-file /path/to/generated_blueprint.md
```

## 原则

- **画面服务音乐**：副歌（Chorus）必须有高能量画面或核心视觉冲突；间奏（Bridge）通常伴随视觉反转或色彩偏移。
- **一致性是底线**：MV 的主角必须有清晰的身份锚点（Identity Anchor），禁止跨镜头的严重漂移。
- **避免平铺直叙**：不要只是简单地用画面复述歌词，要寻找歌词背后的隐喻或平行时空的叙事。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 视觉蓝图为空或太简略 | 必须明确每个段落的画面意图，不能只写"画面：跳舞" |
| 角色设定没有定妆词 | 角色卡必须包含具体的妆造、发型、服装描述，供下游出图使用 |
| 后配歌曲 rough 蓝图写死每个 clip 秒点 | 未有最终歌前只能写段落/情绪，不锁正式时间线 |
| 先传音乐路线忽略节奏数据 | 必须参考 `beatgrid.json` 中的能量分布来安排画面的复杂度 |
| 蓝图只留在聊天里 | 用 `--content-file` 写回 `视觉蓝图.md`，同时生成 `mv_script_state.json` 和进度回写 |
