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
├── 生产数据/image_acceptance/image_acceptance.json
├── 生产数据/color/color_input_manifest.json
├── 生产数据/review/review_receipt.json
├── 合规/AI使用说明.md
├── 合规/ai_usage.json
├── 合规/provenance.json
├── 合规/release_decision.json
├── 合规/<平台上传回执>.json + 原始 API JSON 或 UI 导出
├── 合规/handoff_receipt.json
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
| `semantic_plan` | 语义分镜注入 | `mv-plan/scripts/compose_prompts.py` | 当前输入 hash 绑定且逐 clip 完整的语义 prompt 收据 |
| `pacing_check` | 节奏预检 | `mv-score/scripts/score_pacing.py` | fresh deterministic receipt |
| `image` | 定妆/首帧/尾帧 | `mv-image` | visual identity |
| `picture_lock` | Animatic/Picture Lock | `mv-craft` | OTIO V1+A1 + named hash-bound signoff |
| `video_jobs` | 视频生成任务包 | `mv-video/scripts/video_jobs.py` | jobs_manifest |
| `video` | 多版视频登记/挑版 | backend + `video_jobs.py register/select` | selected video per clip |
| `compose` | 时间线合成 | `mv-compose` | timeline + song |
| `disclosure` | AI 使用披露 | `mv-craft/scripts/ai_usage.py` | 当前设置/模型/渠道/平台/法域绑定的具名披露 |
| `provenance` | 来源链锁定 | `mv-craft/scripts/provenance.py` | 成片稳定后的完整来源链；请求 C2PA 时分层核验 |
| `review` | 质检 | `mv-review/scripts/mv_check.py --write-receipt` | 0 hard block + 具名 hash-bound review receipt |
| `handoff` | 发布/交平台 | `mv-craft/scripts/release_decision.py` + `completion.py` | review health 通过后重算平台/法域规则；schema v3 绑定实际上传资产、API/UI 原始证据、真实作品 URL 与具名 handoff receipt |

### 发布证据

`compose → disclosure → provenance → review → release decision → handoff` 是正式顺序。上传回执 v3 必须以项目内相对 `path+sha256` 绑定实际上传资产：`machine_label_method=c2pa` 时精确对账当前 `provenance.c2pa.output+output_sha256`，其他方法绑定当前 `成片_MV.mp4`。平台 API 原始 JSON 仍须按 JSON Pointer 复提取 remote ID/时间/URL；UI 导出只是具名人证，C2PA 不证明 claim 事实本身为真。完整字段与 API/UI JSON 示例见 [`release-evidence-schema.md`](release-evidence-schema.md)。

## 闸门与进度回写

- **编排入口**：已初始化项目用 `python3 skills/mv/run.py next <作品根> [--json]` 从 `_设置.md` 派生流程，再审计 `_meta.json` / `_进度.md`；不一致时返回 `state_inconsistent` 和显式 sync 命令，不猜哪份旧状态是真的。它对已完成阶段逐项跑 output-health，缺失/过期收据返回 `stale_receipts`。缺 `_进度.md` 时当前 setup card 是不可执行 legacy 占位，必须先用 `init_project.py --title ... --out ... --song-timing ...` 初始化。`run.py impact --clip Clip_00N --change image|prompt|edit` 输出 clip 级返工级联清单。
- 统一歌轨探测走 `scripts/mv_utils.py find_song()`：支持 `歌/song.wav`、`song.mp3`、`song.m4a`、`song.flac`；下游不得只写死 `song.wav`。
- 正式阶段入口用 `scripts/gate.py <作品根> <stage>` 做确定性前置检查。除文件存在外还校验完整 SHA-256 输入收据、beat 段落签收、plan/timeline/OTIO 编辑合同、语义 prompt、节奏报告、出图生成收据、picture lock、视频签收与字幕对齐新鲜度。
- 产物阶段写出核心文件后统一调用 `completion.mark_stage_complete()` 或 `progress_set.py`；控制器先复算 health，成功后才回写 `_进度.md`。仅不产收据的早期文本/分析阶段可由本阶段 owner 直接更新进度。
- `ai_usage.py` / `provenance.py` 默认在写证据后尝试完成当前阶段；health 不成立时命令必须返回非 0，不能吞掉错误。显式 `--no-progress` 只表示“仅写证据”，不产生完成态。
- 不能靠手工把 `_进度.md` 改成 done 冒充完成。`[x]`、`✅`、`1/1` 都走同一语义；`scripts/completion.py health` 复核 semantic/image/video_jobs/video/compose/disclosure/provenance/review/handoff。设置迁移用 `state_contract.py audit|sync`，sync 会把已失效的完成态降回待办。
- `mv-compose` 默认严格服从 `timeline_manifest.json` 和已选 `video_path`。显式 `--allow-fallback` 只能写 `预览/fallback_preview.mp4`，不会产生正式母版、进度、delivery QC 或 provenance。

## 歌曲输入时序分支

- `先传音乐`：`setup → song_ingest → beat → [lyric_sync] → script → plan → semantic_plan → pacing_check → image → picture_lock → video_jobs → video → compose → disclosure → provenance → review → handoff`。`lyric_sync` 仅在字幕不为“无字幕”或演唱口型不为“关闭”时出现；纯器乐视觉 MV 合法跳过歌词。
- `后配歌曲`：`setup → script(rough) → song_ingest → beat → [lyric_sync] → script_review → plan → semantic_plan → pacing_check → image → picture_lock → video_jobs → video → compose → disclosure → provenance → review → handoff`。未补最终音频前不得跑正式 `mv-plan`、出图、出视频或合成。

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

`出视频/jobs_manifest.json` schema v4 记录 model×channel 能力解析、每个 clip 的实际提交控制、take、具名评分、selected take，以及后端支持时的 `sequence_units`。无法解析的模型/渠道或 `manual/custom` 缺显式 adapter 时 fail-closed，不静默换路。连续镜/唱演镜分别增加 seam/lip-sync 维度；多镜头母片仍须按当前真实媒体切点生成具名 `cut_map`，再拆回逐 clip 登记与签收，不能按计划时长盲切。

每次生成/登记必须留下真实提交证据，而不仅是计划：
- `submitted_refs` 逐项记录供应商实际收到的参考角色、路径和 SHA-256；与计划的 reference roles、数量、组合不一致时阻断。
- `controls` 与提交收据分别绑定 prompt/首尾帧/参考、模型、渠道、参数和能力 profile hash；计划或控制变化后旧收据立即失效。
- 严格渠道必须写 provider job/request receipt；manual/custom 则写具名 adapter 和人工提交证据。所选视频、take、继承/QC 报告与 cut map 都绑定当前 SHA-256。
- 能力快照带版本与采集日期，明确输入角色/数量/组合、时长、分辨率、声轨与渠道约束；过期或版本混用时重新核验，不能把粗布尔当供应商真能力。

## 一致性收据与例外账本

- `生产数据/image_acceptance/image_acceptance.json` 是出图权威 ledger：逐资产同时绑定 generation receipt、当前文件 SHA、完整机器 QC 与具名视觉签收，且 B14 pre/post gate 均通过才允许进入 video_jobs。旧 `--accept-degraded` 只保留兼容记录，不能替代机器 QC 或令 block 变 pass。正式项目 prompt 缺身份锚点/禁止漂移块（或 prompt 文件不存在）仍为 hard。
- 视频帧脸 embedding 跌破重度带（自标定阈值−0.15，下限 0.20）→ `video_face_identity_drift_severe` block；唯一出口是 `video_qc.py --accept-face-drift <Clip_ID> --reviewer <name> --notes <理由>` 写入 `制片/face_drift_waivers.json`（绑定当时 selected 视频 sha，换版即失效）。轻/中度漂移仍是 warn+人审。
- `制片/intentional_discontinuity.json`：有意不连续接缝例外账本（既有约定，具名+理由才生效）。
- `字幕/alignment_report.json` 必须把文字覆盖率与声学证据分开；WhisperX 原始分数不能包装成歌声专用置信度。正式接受要么提供经声明校准且适用于歌声的逐字/逐音素证据，要么提供具名逐行听审，并核对 vocal stem 到 master 的 offset/drift。
- `生产数据/color/color_input_manifest.json` schema v2 精确同序覆盖 timeline 选中视频；每项绑定当前 hash、输入色彩分类和实际 ffmpeg 变换。BT.709 full 只在显式 full→limited 时通过；无标签只认具名且 hash-bound 的解释。
- `生产数据/review/review_receipt.json` 绑定 final/master/delivery QC/provenance/disclosure 五个当前 SHA；`合规/handoff_receipt.json` 再绑定 review、release decision 与当前交付资产。任一上游变化都会令完成态陈旧。

每阶段机器证据、人工签收和失败回流的完整矩阵见 `production-standards.md`。
