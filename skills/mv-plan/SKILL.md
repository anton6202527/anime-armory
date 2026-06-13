---
name: mv-plan
description: 制MV clip/timeline 规划 — 从 视觉蓝图 + lyrics + beatgrid 生成 分镜/clip_plan.json、clip_plan.md、timeline_manifest.json，并为 mv-image/mv-video 生成逐 clip prompt 包。Use when asked to MV分镜规划 / 自动拆clip / timeline_manifest / clip_plan / 按beatgrid规划MV. Triggers MV分镜规划, 自动拆clip, clip_plan, timeline_manifest, MV时间线, mv-plan.
---

# mv-plan — clip/timeline 规划

把 `制MV/<曲名>/` 里的 `节拍/beatgrid.json`、`词/lyrics.md`、`视觉蓝图.md` 和 `_设置.md` 变成机器可读的 MV 时间线。若项目选择 `歌曲输入时序=后配歌曲`，必须等最终 `歌/song.*` 入库并跑完真实 beatgrid 后再执行本阶段。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/mv-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`MV规划粒度`、`卡点策略`、`MV视觉风格`。

## 产物

- `分镜/clip_plan.json`：给 `mv-image` / `mv-video` 的逐 clip 任务。
- `分镜/clip_plan.md`：人读版分镜。
- `分镜/timeline_manifest.json`：给 `mv-compose` 的剪辑真值源。
- `出图/段落/prompt/Clip_XXX.md`：首帧/尾帧需求。
- `出视频/prompt/Clip_XXX.md`：视频 motion prompt 任务。
- `分镜/semantic_prompts.json`：语义分镜引擎补写后的结构化留痕。

`clip_plan.json` 除时间线外还要沉淀 MV 的动作与一致性字段：`action_family`、`action_peak`、`visual_motif`、`transition_motif`。这些字段由本阶段初填，语义分镜引擎可精修，后续 `mv-image` / `mv-video` / `mv-score` / `mv-review` 直接消费，不再临场猜“炫酷动作”。

## 用法

```bash
python3 skills/mv-plan/scripts/plan_clips.py "<制MV作品根>"
python3 skills/mv-plan/scripts/plan_clips.py "<制MV作品根>" --granularity 精细 --strategy 全程强卡点
```

## 工作流

1. 先跑 `mv-beat` 得到 `节拍/beatgrid.json`。没有最终歌/beatgrid 时不得用 rough 蓝图硬拆正式 timeline。
2. 跑本脚本 `plan_clips.py`。脚本入口会先过 `mv-craft/scripts/gate.py plan`：缺 `歌/song.*`、`词/lyrics.md`、`beatgrid.json`、`视觉蓝图.md` 或后配歌曲仍是 rough 蓝图时直接阻断；成功后生成 clip/timeline 框架并回写 `_进度.md` 的 `plan` 行。
3. **【AI 代理交互节点】**：跑完 `plan_clips.py` 后，AI 代理**必须**主动向用户提问（使用 `ask_user` 或直接对话）：“是否需要开启「语义分镜引擎」为你自动规划每个镜头的具体画面和动作？”
   - 如果用户同意，AI 代理负责执行 `python3 skills/mv-plan/scripts/compose_prompts.py <作品根>`，读取输出的 prompt 并利用自身的 LLM 能力生成包含画面语义的 JSON，然后通过 `--mock-assessment` 注写入项目。
   - 语义补全时读取 `mv-video/references/action_knowledge.md`（动作家族/动作峰值/转场母题）和 `mv-image/references/visual_consistency.md`（身份锚点/主色/母题），优先补 `action_family/action_peak/visual_motif/transition_motif`，再补 continuity；写回时同步落 `分镜/semantic_prompts.json`，便于复查和重跑。
4. `mv-image` 按 `clip_plan.json` 出首帧和需要的尾帧。
5. `mv-video/scripts/video_jobs.py` 按 `clip_plan.json` 生成视频任务包。
6. `mv-compose` 按 `timeline_manifest.json` 合成。

## 原则

- 没有 sections 时按 `_meta.structure` 等分歌曲，先给可跑计划；后续可人工改 sections 重跑。
- 副歌/高潮按 downbeat 密切，verse 按多小节缓切。
- `timeline_manifest.json` 是合成真值源；不要让 `mv-compose` 再凭文件名猜顺序。
- MV 不做跨集强一致，但同一首歌内必须继承视觉一致性包；动作知识库只提供可选动作家族，不覆盖歌曲情绪。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 没有生成 `beatgrid.json` 就尝试切分镜头 | 必须先由 `mv-beat` 确定歌曲真实的重拍 (downbeat) 阵列后，才能进行有效卡点切分 |
| 后配歌曲路线未补最终歌就跑 mv-plan | 先让 song 线产歌或用户上传成品歌，再跑 mv-beat；然后重跑/复核 mv-script |
| 让 compose 自己猜播放顺序 | compose 只能严格服从 `timeline_manifest.json`，如果该清单为空或内容未更新，合成将会混乱 |
| 生成后完全不让用户确认直接发往下游 | 本阶段结束后**必须**询问用户是否要人工调整或启动「语义分镜引擎」，否则画面将会高度重复或平淡 |
| 语义分镜只靠聊天记录 | 语义补全必须写回 `clip_plan.json`，并落 `semantic_prompts.json` 作为可追踪产物 |
