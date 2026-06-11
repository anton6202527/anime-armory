# mv-* 机器契约

本文件是人读版；机器字段以 `scripts/contract.py` 为准。

## 作品根

```text
制MV/<曲名>/
├── _设置.md
├── _meta.json
├── _进度.md
├── 视觉蓝图.md
├── 歌/song.wav
├── 词/lyrics.md
├── 节拍/beatgrid.json
├── 分镜/
│   ├── clip_plan.json
│   ├── clip_plan.md
│   └── timeline_manifest.json
├── 出图/
├── 出视频/
│   ├── prompt/
│   ├── takes/
│   ├── jobs_manifest.json
│   └── 视频/
├── 字幕/
├── 合规/AI使用说明.md
└── 成片_MV.mp4
```

## 关键选择点

| 选择点 | 用途 |
|---|---|
| `MV用途` | 短视频 Hook / 歌曲 Demo / 正式 MV 草稿 / 投放版 |
| `MV视觉风格` | 控制视觉蓝图、定妆、分镜 prompt |
| `MV规划粒度` | 决定 clip 密度和任务量 |
| `卡点策略` | 副歌碎切、verse 缓切、全程强卡点等 |
| `生图AI` | MV 首帧/定妆图后端（选择点，默认 Codex；阶段1 放行官方多参考后端 Seedream/可灵主体库/Nano Banana/Sora Cameo；不混用、禁即梦逆向出图。见 `scripts/contract.py` `MV_APPROVED_IMAGE_BACKENDS`/`classify_image_backend`）|
| `MV一致性增强` | 组图前提示是否用共享定妆+锚点（默认）、指定参考图、后端主体库或 +LoRA；LoRA 仅接入已有/授权资产 |
| `生视频AI` | 图生视频后端 |
| `出视频规格` | 预算、分辨率、帧率、每 clip 生成版数 |
| `合成画幅` | 输出画幅 |
| `AI视觉使用披露` | 发布/交平台前留痕 |
| `发行目标平台` | 影响画幅、字幕和合规说明 |

## 阶段表

| key | 阶段 | owner | gate |
|---|---|---|---|
| `setup` | 项目骨架 | `mv/scripts/init_project.py` | deterministic |
| `beat` | 节拍/能量 | `mv-beat/scripts/beat_detect.py` | beatgrid |
| `plan` | clip/timeline 规划 | `mv-plan/scripts/plan_clips.py` | clip_plan + timeline_manifest |
| `image` | 定妆/首帧/尾帧 | `mv-image` | visual identity |
| `video_jobs` | 视频生成任务包 | `mv-video/scripts/video_jobs.py` | jobs_manifest |
| `video` | 多版视频登记/挑版 | backend + `video_jobs.py register/select` | selected video per clip |
| `lyric_sync` | 歌词对齐 | `mv-lyric-sync/scripts/align.py` | subtitles |
| `compose` | 时间线合成 | `mv-compose` | timeline + song |
| `review` | 质检 | `mv-review` | machine + human review |
| `handoff` | 发布/交平台 | `mv-craft/scripts/ai_usage.py` | AI usage disclosure |

## clip plan / timeline

`分镜/clip_plan.json` 是 mv-image/mv-video 的上游任务；`分镜/timeline_manifest.json` 是 mv-compose 的剪辑真值源。两者的 clip id 必须一致。

每个 clip 至少包含：
- `clip_id`
- `section`
- `start`
- `end`
- `duration`
- `beat_role`
- `image_prompt_path`
- `video_prompt_path`
- `transition`
- `need_end_frame`
- `continuity`

## video jobs

`出视频/jobs_manifest.json` 记录每个 clip 的生成版数、已登记 take、评分、selected take。`selected_video_path` 不为空时，`出视频/视频/<clip_id>.mp4` 应来自对应 take。
