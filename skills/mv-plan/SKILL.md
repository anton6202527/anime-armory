---
name: mv-plan
description: 制MV clip/timeline 规划 — 从 视觉蓝图 + lyrics + beatgrid 生成 分镜/clip_plan.json、clip_plan.md、timeline_manifest.json，并为 mv-image/mv-video 生成逐 clip prompt 包。Use when asked to MV分镜规划 / 自动拆clip / timeline_manifest / clip_plan / 按beatgrid规划MV. Triggers MV分镜规划, 自动拆clip, clip_plan, timeline_manifest, MV时间线, mv-plan.
---

# mv-plan — clip/timeline 规划

把 `制MV/<曲名>/` 里的 `节拍/beatgrid.json`、`词/lyrics.md`、`视觉蓝图.md` 和 `_设置.md` 变成机器可读的 MV 时间线。

## 产物

- `分镜/clip_plan.json`：给 `mv-image` / `mv-video` 的逐 clip 任务。
- `分镜/clip_plan.md`：人读版分镜。
- `分镜/timeline_manifest.json`：给 `mv-compose` 的剪辑真值源。
- `出图/段落/prompt/Clip_XXX.md`：首帧/尾帧需求。
- `出视频/prompt/Clip_XXX.md`：视频 motion prompt 任务。

## 用法

```bash
python3 skills/mv-plan/scripts/plan_clips.py "<制MV作品根>"
python3 skills/mv-plan/scripts/plan_clips.py "<制MV作品根>" --granularity 精细 --strategy 全程强卡点
```

## 工作流

1. 先跑 `mv-beat` 得到 `节拍/beatgrid.json`。
2. 跑本脚本 `plan_clips.py` 生成 clip/timeline 框架。
3. **【AI 代理交互节点】**：跑完 `plan_clips.py` 后，AI 代理**必须**主动向用户提问（使用 `ask_user` 或直接对话）：“是否需要开启「语义分镜引擎」为你自动规划每个镜头的具体画面和动作？”
   - 如果用户同意，AI 代理负责执行 `python3 skills/mv-plan/scripts/compose_prompts.py <作品根>`，读取输出的 prompt 并利用自身的 LLM 能力生成包含画面语义的 JSON，然后通过 `--mock-assessment` 注写入项目。
4. `mv-image` 按 `clip_plan.json` 出首帧和需要的尾帧。
5. `mv-video/scripts/video_jobs.py` 按 `clip_plan.json` 生成视频任务包。
6. `mv-compose` 按 `timeline_manifest.json` 合成。

## 原则

- 没有 sections 时按 `_meta.structure` 等分歌曲，先给可跑计划；后续可人工改 sections 重跑。
- 副歌/高潮按 downbeat 密切，verse 按多小节缓切。
- `timeline_manifest.json` 是合成真值源；不要让 `mv-compose` 再凭文件名猜顺序。
