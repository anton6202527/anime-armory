# mv-* 机器契约

本文件是人读版；机器字段以 `scripts/contract.py` 为准。

## 作品根

```text
创作区/制MV/<曲名>/
├── _设置.md
├── _meta.json
├── _进度.md
├── 视觉蓝图.md
├── 歌/song.*            # song.wav / song.mp3 / song.m4a / song.flac
├── 词/lyrics.md
├── 节拍/beatgrid.json
├── 分镜/
│   ├── clip_plan.json
│   ├── clip_plan.md
│   ├── timeline_manifest.json
│   ├── timeline.otio
│   └── animatic.mp4
├── 出图/
├── 出视频/
│   ├── prompt/
│   ├── takes/
│   ├── jobs_manifest.json
│   └── 视频/
├── 字幕/
├── 制片/picture_lock.json
├── 生产数据/otio/otio_receipt.json
├── 合规/AI使用说明.md
└── 成片_MV_master.mov + 成片_MV.mp4
```

## 关键选择点

| 选择点 | 用途 |
|---|---|
| `MV用途` | 短视频 Hook / 歌曲 Demo / 正式 MV 草稿 / 投放版 |
| `歌曲输入时序` | `先传音乐`=先有成品歌再按真实 beatgrid 做 MV；`后配歌曲`=先做 rough 视觉蓝图，成品歌补入后再卡点 |
| `MV视觉风格` | 控制视觉蓝图、定妆、分镜 prompt |
| `MV规划粒度` | 决定 clip 密度和任务量 |
| `卡点策略` | 副歌碎切、verse 缓切、全程强卡点等 |
| `生图模型` | 具体图像模型；当前候选由官方来源刷新，默认 GPT Image 2 |
| `生图渠道` | Codex / 官方 API / manual 等真实访问入口；与模型分轴记录，旧 `生图AI` 只兼容 |
| `MV一致性增强` | 组图前提示是否用共享定妆+锚点（默认）、指定参考图、后端主体库或 +LoRA；LoRA 仅接入已有/授权资产 |
| `生视频模型` | 图生视频模型 |
| `生视频渠道` | 实际调用产品/API/CLI |
| `出视频规格` | 预算、分辨率、帧率、每 clip 生成版数 |
| `演唱口型` | 关闭 / 仅正面演唱镜 / 全演唱镜 / 后期修复 |
| `字幕语言` | 中文 / 中英双语 / 英文 / 无字幕；决定正式 compose 是否要求对齐产物 |
| `合成画幅` | 输出画幅 |
| `AI视觉使用披露` | 发布/交平台前留痕 |
| `发行目标平台` | 影响画幅、字幕和合规说明 |

## 阶段表

> 行序＝机器 `MV_STAGE_TABLE`（contract.py）的默认（`先传音乐`）顺序，仅作 owner/gate 速查。
> **实际跑序随 `歌曲输入时序` 变**（`后配歌曲` 把 `script(rough)` 提到 `beat` 之前）——见下方「歌曲输入时序分支」，勿据本表推断默认流。

| key | 阶段 | owner | gate |
|---|---|---|---|
| `setup` | 项目骨架 | `mv/scripts/init_project.py` | deterministic |
| `song_ingest` | 歌曲入库/定稿 | 用户文件入库 | `歌/song.*`；需要字幕/唱演口型时另需 `词/lyrics.md` |
| `beat` | 节拍/能量 | `mv-beat/scripts/beat_detect.py` | beatgrid |
| `lyric_sync` | 歌词时间轴 | `mv-lyric-sync/scripts/align.py` | 当前歌曲/歌词 hash-bound alignment |
| `script` | 视觉蓝图/设定 | `mv-script` | visual blueprint |
| `script_review` | 视觉蓝图复核 | `mv-script` | beatgrid-reviewed blueprint |
| `plan` | clip/timeline 规划 | `mv-plan/scripts/plan_clips.py` | clip_plan + timeline_manifest |
| `pacing_check` | 节奏预检 | `mv-score/scripts/score_pacing.py` | fresh deterministic receipt |
| `image` | 定妆/首帧/尾帧 | `mv-image` | visual identity |
| `picture_lock` | Animatic/Picture Lock | `mv-craft` | OTIO V1+A1 + named hash-bound signoff |
| `video_jobs` | 视频生成任务包 | `mv-video/scripts/video_jobs.py` | jobs_manifest |
| `video` | 多版视频登记/挑版 | backend + `video_jobs.py register/select` | selected video per clip |
| `compose` | 时间线合成 | `mv-compose` | timeline + song |
| `review` | 质检 | `mv-review` | machine + human review |
| `handoff` | 发布/交平台 | `mv-craft/scripts/ai_usage.py` | AI usage disclosure |

## 闸门与进度回写

- **编排入口**：`python3 skills/mv/run.py next <作品根> [--json]` 是「读进度 → 跑 gate → 定下一步」的单一机器入口（只读）：算前沿、对前沿阶段跑 gate、对已 done 的 image/video_jobs/compose 做收据健康度巡检，输出登记制 `stop_reason`（missing_progress / all_stages_done / stale_receipts / blocked_by_gate / needs_user_files / needs_agent_generation / needs_human_signoff / ready_to_run）。`run.py impact --clip Clip_00N --change image|prompt|edit` 输出 clip 级返工级联清单。
- 统一歌轨探测走 `scripts/mv_utils.py find_song()`：支持 `歌/song.wav`、`song.mp3`、`song.m4a`、`song.flac`；下游不得只写死 `song.wav`。
- 正式阶段入口用 `scripts/gate.py <作品根> <stage>` 做确定性前置检查。除文件存在外还校验完整 SHA-256 输入收据、beat 段落签收、plan/timeline/OTIO 编辑合同、语义 prompt、节奏报告、出图生成收据、picture lock、视频签收与字幕对齐新鲜度。
- 阶段脚本成功写出核心产物后调用 `scripts/progress_set.py <作品根> <stage_key>` 或 `mv_utils.update_progress_stage()` 回写 `_进度.md`；同时刷新 `_meta.has_song/has_lyrics`。
- `mv-compose` 默认严格服从 `timeline_manifest.json` 和已选 `video_path`。显式 `--allow-fallback` 只能写 `预览/fallback_preview.mp4`，不会产生正式母版、进度、delivery QC 或 provenance。

## 歌曲输入时序分支

- `先传音乐`：`setup → song_ingest → beat → [lyric_sync] → script → plan → pacing_check → image → picture_lock → video_jobs → video → compose → review → handoff`。`lyric_sync` 仅在字幕不为“无字幕”或演唱口型不为“关闭”时出现；纯器乐视觉 MV 合法跳过歌词。
- `后配歌曲`：`setup → script(rough) → song_ingest → beat → [lyric_sync] → script_review → plan → pacing_check → image → picture_lock → video_jobs → video → compose → review → handoff`。未补最终音频前不得跑正式 `mv-plan`、出图、出视频或合成。

## clip plan / timeline

`分镜/clip_plan.json` 是 mv-image/mv-video 的上游任务；`分镜/timeline_manifest.json` 是 mv-compose 的剪辑真值源；`timeline.otio` 是交给 NLE 的 V1 画面 + A1 正式歌曲交换件。三者通过 source plan hash、规范化 edit hash 和 OTIO receipt 对账。

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
- `seam_contract`（`beat_cut` / `section_break` / `match_action` / `terminal`）
- `need_end_frame`
- `continuity`

计划顶层必须有当前 song / beatgrid / lyrics / blueprint / settings 的 `inputs_sha256`。正式项目不能用固定间隔或歌词字数估算伪造段落；`max_clips` 只是成本目标，不能跨段落吞并。

## video jobs

`出视频/jobs_manifest.json` 记录每个 clip 的生成版数、已登记 take、具名评分、selected take，以及后端支持时的 `sequence_units`。连续镜/唱演镜分别增加 seam/lip-sync 维度；多镜头一次生成仍须按锁定切点拆回逐 clip 登记与签收。`selected_video_path` 不为空时，`出视频/视频/<clip_id>.mp4` 应来自对应 take。

`--register` 登记时每 take 落三类绑定/留痕：
- `first_frame_sha256` / `end_frame_sha256`：登记时首/尾帧 PNG 的内容 SHA（出图→出视频像素级绑定）。inherit_contract 核对当前 PNG 与登记值，不一致＝图在出视频后被替换 → block（`frame_changed_after_registration`）。
- `generation.seed` / `generation.params` / `generation.provider_job_id`（`--seed` / `--generation-param K=V` / `--provider-job-id`）：可复现性留痕，登记时已知则必记，网页入口拿不到时可缺省（不阻断）。
- `video_sha256`：登记文件内容 hash（既有约定）。

## 一致性收据与例外账本

- `生产数据/image_qc/image_qc.json` 携带 `assets_sha256`（被检图片内容收据）；gate 用它做 hash 级新鲜度核对，取代 mtime。正式项目 prompt 缺『身份锚点/禁止漂移』块（或 prompt 文件不存在）＝身份合同未被下游消费 → image_qc hard（B12 合同消费闸）。
- 视频帧脸 embedding 跌破重度带（自标定阈值−0.15，下限 0.20）→ `video_face_identity_drift_severe` block；唯一出口是 `video_qc.py --accept-face-drift <Clip_ID> --reviewer <name> --notes <理由>` 写入 `制片/face_drift_waivers.json`（绑定当时 selected 视频 sha，换版即失效）。轻/中度漂移仍是 warn+人审。
- `制片/intentional_discontinuity.json`：有意不连续接缝例外账本（既有约定，具名+理由才生效）。

每阶段机器证据、人工签收和失败回流的完整矩阵见 `production-standards.md`。
