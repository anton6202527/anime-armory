---
name: n2d-compose
description: Default final-delivery stage of n2d — maintain an OpenTimelineIO editorial handoff from animatic through accepted clips/rough cut/final master, then assemble a finished episode from video, dialogue/narration, ambience/foley, BGM and subtitles. New projects default to 合成阶段=启用; explicit clip-only projects may skip it. Use for OTIO/剪辑时间线/成片/BGM/subtitles/release packaging/master delivery. Mixes voice with BGM ducking and burns subtitles via Pillow+overlay. Triggers OTIO, OpenTimelineIO, 剪辑时间线, 合成, 成片, 加BGM, 烧字幕, 混音, 导出, compose, 剪映, 母版, 发布.
---

# n2d-compose — 合成成片（剪映那步的脚本化替代）

把一集的 `视频/`(clips) + `配音/voice_*.wav`(可选) + BGM(可选) + 字幕 烧成 `成片_第N集_{mode}.mp4`。

> **默认成片尾段**：新项目默认 `合成阶段=启用`，视频齐片后继续合成、review 与最终签收；只有用户显式写 `合成阶段=跳过` 的 clip-only 项目才停在 `clip_delivery_complete`。`master_delivery_complete` 仍需要后续 release/readiness、production locks、creative governance 和人工验收通过，不能把单个 MP4 存在误当可发布。

> **视频阶段后的真实粗剪代理 + OTIO**：animatic 创建 working `editorial_timeline.otio` 与签收专用 `animatic_timeline.otio` 快照；每个 Clip 验收后只刷新 working 时间线，齐片后 `post_video_proxy.py --render` 生成 `actual_rough_cut.mp4`。只认 manifest `status=accepted`。final voice 未生成时，OTIO 的 A1 用 `MissingReference` 建 planned audio slots，时长和文本来自 `timing_estimate.json`；它们是编辑槽位，不是假音频。final voice 到位后刷新为真实媒体引用。OTIO 同时保留声音 route、casting 状态、V1、旁白/对白、环境/拟音、BGM、字幕 marker、媒体哈希、缺料槽位和 `seam_mode`。

> **持久证据与缓存分离**：working/snapshot OTIO 和锁版 timeline 统一落 `生产数据/timelines/第N集/`，粗剪 HTML 落 `生产数据/views/rough_cut_preview_第N集.html`；`合成/第N集/_work` 与 `_clipcache` 只放可重建缓存。`cache_policy.py refresh|doctor|clean|auto` 维护 `生产数据/cache_manifests/compose_cache_第N集.json`；默认只审计，只有 `_设置.md` 明确 `合成缓存保留=成片后清理|保留7天` 且 doctor 无阻断才自动删缓存，绝不删除正式 Clip、母版、合同或 QC 证据。

**跨集成片一致性登记（2026-06 加固·schema 见 `n2d-review/references/扩展一致性登记表.md`）**：成片阶段维护两张剧级表，让逐集观感不漂——① `设定库/series_grade.json` 剧级**调色锁**（LUT/白平衡/对比/饱和基线），每集套用后写 `合成/<集>/grade_applied.json` 留痕（`tone_light_contract` 只焊片内像素，这层管跨集色温/对比）；② `设定库/ambient_map.json` 每场景**环境声床**（LOC→ambient bed，`reverb_profile` 管混响、这层管底噪连续性）。调色采用层级裁决：`series_grade` 是默认基线，场景光位/剧情天气可局部收紧，情绪/梦境/回忆等有意变调必须在 `grade_applied.json` 写 `grade_override.reason/source_clip`，否则按漂色处理。n2d-review 的 `系列调色(GRD)` / `调色层级(COLORH)` / `环境声(AMB)` 据此对账。

> **一个母版色彩合同**：首次 compose 自动写安全默认 `设定库/color_pipeline.json`（SDR Rec.709、BT.709 primaries/transfer/matrix、limited range、`yuv420p`），`compose.sh` 和 `deliver.py` 派生链显式写这些 ffmpeg 标签，不再依赖播放器猜测。`color_pipeline.py <作品根> 第N集 --write-missing --json` 在 compose 阶段允许“母版尚未生成”返回 pending；进入 review 后会 ffprobe 当前 canonical master，标签缺失或与合同不符即 BLOCK。HDR/ACES/自定义 OCIO 不是偷偷自动转换：先显式修改同一合同与实际变换链，再重新输出母版；`series_grade` 管创作调色，`color_pipeline` 管可交付编码色彩语义，两者不能互相冒充。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在执行脚本里**。按 `../skills/n2d/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则由 producer-owned 推荐器选一个安全默认并以 `source=auto_recommended` 写回，同项目之后沉默沿用；仅 `普通选择策略=逐项询问` 时才展示菜单。阶段预算包创建/扩大/失效、合规、不可逆覆盖与最终验收仍显式确认。

**首次安全本地合成自动继续**：`BGM来源=无`、compose gate 已过且 canonical master 尚不存在时，本地 ffmpeg 合成不产生 provider 花费，也不消费 spend envelope，`run.py` 可直接返回 `needs_stage_execution`。这不是覆盖授权：只要 working/未验收/已验收 canonical master 已存在、acceptance receipt 损坏，或 canonical resolver 无法证明目标，均 fail-closed 停在人审；不能仅因“尚未最终验收”就覆盖已有母版。新母版产出后仍必须走 compose/review gate、canonical release verdict 与最终具名签收。

> **RenderTransaction + current MediaArtifactReceipt**：正式母版先渲染到每次唯一的 staging 路径，再在 canonical-scoped 锁内按“预期旧 SHA”做 compare-and-swap；候选必须通过完整 EOF 解码、H.264/AAC、yuv420p、Rec.709 limited、48 kHz stereo、faststart、响度与锁版时长校验，才可原子晋级。晋级同时写一份绑定当前母版 SHA/大小、规格 SHA、render recipe 文件与内容 SHA、picture-lock 时长和验证器版本的收据；失败恢复旧母版，旧版本归档到 `_versions/`。`_进度.md` 只能在母版与收据都 durable 后推进；review/release 每次都重新验证当前字节，不能信任手改的 `status=pass`。

本 skill涉及的选择点：`合成阶段`、`合成缓存保留`、`BGM来源`、`画幅`、`制作模式`、`视频原生音轨`、`后期拟音策略`、`目标平台`、`发行地区`、`合规用途`。混合模式还必须消费逐镜 `audio_strategy/final_voice_stage/post_lipsync_required`，不能只凭项目级模式决定音轨。平台与合规仍以 `合规/compliance_manifest.json` 为准。

> **AI 标识非阻断铁律**：compose `[6/6]` 后可自动跑 `ai_label.py` 做 best-effort 后处理。默认 `AI显式角标=仅元数据`：只写机器可读 AI 元数据，不把「AI生成」角标烤进内部预览画面；正式投放若平台/地区要求显式标识，改为 `AI显式角标=开启` 再叠角标并回写 `合规/compliance_manifest.json` 的 `ai_labeling` 状态。AI 标识/披露/水印不得阻断合成、进度回写、dashboard 记账或后续集推进；失败只形成发布前待办。数字水印、平台侧 AIGC 披露与严格 GB 45438 字节级封装均可在工具外补齐。

## 核心原则
- **剪辑节奏 = `edit_target_sec`，不是后端原片长度**（`n2d/references/导演节奏.md §四/§五`）：铺垫长镜、爽点碎切、爽点后留白由上游设计。compose 优先读 `video_batch_*.json` 的 `edit_target_duration/duration_plan.edit_target_sec`，后端因离散档位多生成的尾端默认 `trim`；绝不把所有 clip 拉成等长，也不默认用 `setpts` 整段变速。`speed_mode=warp` 仅供导演显式慢动作/加速。
- **三轨后期执行铁律（旁白/字幕/花字都归 compose）**：`n2d-script` 产出的 `dialogue / narration / screen_text` 三轨在本阶段合流。角色对白若已由原生音画 clip 生成，则本阶段只保留/混音并做字幕对齐；旁白一律在 compose 阶段用 TTS/配音轨生成并混入，不让视频模型直接生成旁白音频；`screen_text_lines[]`、标题卡、花字、系统面板数值和普通字幕一律由 compose 用 Pillow/overlay 叠加，不让视频模型烤字。`dialogue_fact_contract_第N集.json` 是三轨事实账本：旁白和屏幕文案必须按合同取词，年龄、身高、灵根、趟数等数字不得在后期脚本里临场改写。字幕也是 compose 阶段统一产物：原生音画可先出无字幕 draft，但 review/发布前必须从原生音轨或三轨合同生成/对齐 `字幕_中文.srt` 并过 `native_av_subtitle_alignment`。
- **卡点**：爽点的冲击 = 画面 + 声音同一帧砸下。用 `BGM_OFFSET` 平移 BGM，让 drop/炸点落在 `故事板.md` 标的爽点时间戳（如 `💥爽点 @ 0:48`）那一帧；反转/觉醒处铺 bgm.txt 标的"重音"音效。
- **留白呼吸**：爆发后那个 `留白·定格` clip 不要被音效填满——让它喘一口（必要时 BGM 瞬时拉低再起）。
- **声音连续 / J-cut / 空镜缓冲**：合成默认尊重 `故事板.md` 的衔接设计：BGM 全程连续铺底，不按 clip 断；空镜缓冲 clip 原样保留呼吸；默认 `J_CUT_SEC=0.25`，脚本基于 `line_*.wav + 时长清单.json` 重建轻量提前入声的配音轨，让下一句更早粘住画面切换。正面口型特写多的集可设 `J_CUT_SEC=0` 关闭。
- **按 `seam_mode` 接 clip**：优先读 P-3 chain。只有 relay 要相同边界帧；match-on-action、graphic match、eyeline、reaction、insert、J/L、hard cut 与 intentional discontinuity 保留各自证据并切接；dissolve 按每缝 `seam_evidence.duration_sec` 写 OTIO Transition/xfade。显式 dissolve 渲染失败直接阻断，不静默降成硬切；缺显式模式先回 P-2/P-3。
- **声音选角先行、最终配音后置**：机器默认是 `混合自动路由`。本 skill 不生成角色 final voice；它只消费已签收声音、逐镜原生音轨和 planned audio slots。需要外部声音的 route 在 final voice 未齐时阻断正式合成。
- **后期口型是独立交付通道**：`base_video_then_post_lipsync` 镜头不能直接把 base plate 当最终 clip。compose/review gate 要求 `出视频/第N集/视频_lipsync/Clip_XX_lipsync.mp4` 存在并通过 QC；OTIO V1 应引用该版本。
- **张力感知 BGM 增益（爽点抬/细节压·替代一刀切）**：`DUCK_RATIO` 是整集统一档；要让爽点/爆发镜 BGM 顶上去、悬念/细节镜压更狠，先跑 `python3 skills/n2d/n2d-compose/tension_mix.py <作品根> 第N集 --expr` 读 `storyboard.json` 每 Clip `rhythm` 映射成随时间变化的 BGM 基准音量包络，再喂给 compose：`BGM_GAIN_EXPR="$(python3 skills/n2d/n2d-compose/tension_mix.py <作品根> 第N集 --expr)" bash compose.sh ...`。这条增益作用在 voice 侧链 ducking **之前**的 BGM 基准上，与既有 `DUCK_RATIO` 侧链叠加。**不传 `BGM_GAIN_EXPR` 时保持原固定 `0.9/0.85` 行为**（向后兼容）；缺 storyboard 时给提示不臆造。`tension_mix.py`（无 `--expr`）打人读包络图 + 建议叠音效的爽点镜清单。
- **🎼 角色/势力主题动机（leitmotif·确定性复用）**：BGM 此前只到「逐集情绪 + 张力 ducking」，没有跨集「听见就知道是他」的复现旋律。生成式音乐跨集维持同一动机极不稳，故用**确定性复用**：可选 `<作品根>/设定库/motif.json`（`{"沈念":{"file":"素材/motif/shen.wav","cue":"focus","gain":0.5}}`）一次性登记角色/势力的一段动机 clip。compose `[6/6]` 后自动跑 `motif_registry.py --mix`：读 `时长清单.json` 在角色焦点 span 开头铺**同一段 clip**（`min_gap` 去重防刷屏），视频流直 copy 只改音轨。缺 motif.json=空规划 no-op，成片一字不动。巡检：`python3 motif_registry.py <作品根> 第N集`。
- **📊 集成响度（LUFS）达标巡检**：compose `[6/6]` 后自动跑 `loudness_conform.py`；多集/发布项目优先消费已签收 `设定库/series_consistency.json.audio_baseline`，把全剧目标响度、容差与真峰锁成同一基线。平台候选只在未启用剧级合同的单集内部粗剪中兜底。
- **粗剪锁版 + 交付包装证据包**：`final_timeline_probe.py --write` 同时刷新 `生产数据/timelines/第N集/timeline.json`、`生产数据/views/rough_cut_preview_第N集.html` 与同集 `editorial_timeline.otio`，并把阶段推进到 rough_cut/final_master；OTIO sidecar 记录每个媒体 SHA、缺料槽位、轨道和接缝证据。review 前还要补 `script_supervisor_log`、调色、声音、响度、series packaging/release manifest；单个 MP4 存在不能代替这些锁版证据。
- **audio_timing_gate 前置**：正式合成前除 `preventive_contracts.json.audio_timing` 外，还要检查 `production_mode_route_第N集.json`、`voice_casting.json`、final voice manifest 与 lipsync 产物。对白近景、后配音、原生音画必须写清 timing basis、表演轨、字幕、声纹/音色、时长拟合和 overflow 策略。
- **clip 原生音频处理（按逐镜 route 分流）**：Veo / Seedance / Kling 出的 clip 可能自带环境音甚至台词。本 skill 是统一处理点：普通/base plate/表演条件镜丢弃模型音轨，低风险环境声镜可压低混入，`native_av` 镜保留原片声。不要用一个项目级开关覆盖所有 Clip。选择点 `视频原生音轨`：
  - `丢弃`（默认）：只在 compose 工作缓存/最终合成链路里剥掉 clip 原生音轨，**不改写 `出视频/第N集/视频/` 的 AI 原片**；音频全部由 配音+BGM+SFX 这条受控链路提供，避免双人声。
  - `低音量混入环境声`：仅当 n2d-video 的「原生音画 opt-in 清单」确认该 Clip 低风险、无口型、无原生人声时，将 clip 原生音轨按 `CLIP_AUDIO_GAIN`（默认 0.35）压低混入作环境底。
  - `保留原片音轨`：仅用于无配音/测试预览/明确要原片声时；有 n2d-voice 配音轨时 `compose.sh` 会直接阻断，compose gate 也会把“保留原片音轨 + 存在配音轨 + clip 有音频流”视为阻断。原生音画项目若配音轨确认为旁白/系统层，先过 gate/sidecar，再显式 `ALLOW_NATIVE_AV_VOICEOVER=1`；仅内部预览才可 `ALLOW_DOUBLE_VOICE=1` 自担风险。
  - **release gate**：只要策略不是 `丢弃`，就必须存在 `生产数据/native_av_physics_第N集.json`，逐 Clip 说明声源、可见动作证据、空间混响、后期处理策略；低风险 ambience/native_sfx 也不例外。缺 sidecar 时先回 `n2d-video` 补「原生音画物理一致性契约」，不要在 compose 阶段凭听感放行。
  - 命令覆盖：`VIDEO_NATIVE_AUDIO_POLICY=丢弃|低音量混入环境声|保留原片音轨`；旧 `KEEP_CLIP_AUDIO=1` 兼容为 `低音量混入环境声`。
  - **原生音画模式例外（自动覆盖）**：`制作模式=原生音画` 时台词在 clip 自带音轨里，丢弃会丢台词——compose 自动把策略转为 `保留原片音轨`（`compose.sh` 实现）。要强制别的策略须显式设 `VIDEO_NATIVE_AUDIO_POLICY_EXPLICIT=1` 一并指定 `VIDEO_NATIVE_AUDIO_POLICY`。
- **合规与版权前置（P0）**：compose 不是“先出片再补救”的地方。正式合成前必须存在 `合规/compliance_manifest.json`，并已通过 `n2d-compliance` 填好：版权/改编权、角色授权、声音克隆授权、目标平台审核、出海本地化。`gate.py --stage compose` 会在合成前阻断缺合规包、投放平台未定、海外投放未声明字幕/本地化等硬项。**AI 生成合成内容标识（`ai_labeling`）只做 INFO 待办**；compose `[6/6]` 后 `ai_label.py` 可 best-effort 落显式角标 + 元数据并回写 manifest，失败不阻断合成进度回写。
- **生产数据记账铁律（P0）**：合成完成或失败后必须调用 `n2d-dashboard` 记录 `stage=compose` 事件，至少包含输出文件、耗时、原生音轨策略；若 gate 阻断或合成失败，用 QA/manual 事件记录原因。否则无法统计每集成片耗时、音轨策略风险和最终通过率。
- **付费/续看闭环字段**：成片进入投放、解锁或追更平台时，发布侧的 `platform_metrics.*` 不只写留存和收入；必须带 `paywall_position_sec`、`paywall_after_promise_id`、`unlock_friction`、`continue_path`。这些字段由 `n2d-feedback` 分析“卡点是否落在已打开承诺之后、哪条续看路径追更最高”，下一批再回灌到分镜和交付策略；compose 不直接改平台数据，但交付说明必须提醒运营/发布工序落这些列。
- **字幕烧录**：本机 Homebrew ffmpeg **无 libass**（无 subtitles/drawtext 滤镜）→ 用 Pillow 把 SRT 渲染成透明 PNG 再 overlay 烧录（render_subs.py）。
- **字幕母版与平台适配分层**：项目内 SRT 继续作为轻量创作/剪辑事实源；需要专业交换或无障碍交付时，可额外导出并校验 W3C IMSC Text Profile 1.3（2026-05 Recommendation）母版，再由平台 adapter 映射到该平台接受的 SRT/WebVTT/TTML。三者不是互相替代的“完成状态”，每个派生字幕必须绑定同一 cue 时间轴、语言、源文本 SHA 与目标视频 SHA。
- **原生音画字幕闭环**：`制作模式=原生音画` 时，compose 可在缺 `字幕_中文.srt` 的情况下先出 draft（脚本会跳过字幕并给 warning），但这不是可交付成片。进入 review/付费投放前必须用 whisperx 或等效词级对齐从原生音轨生成中文字幕，落 `脚本/第N集/字幕_中文.srt`，并写 `生产数据/native_av_subtitle_alignment_第N集.json`（`kind=n2d_native_av_subtitle_alignment`、`status=pass|aligned`、`alignment_tool/source`、`word_level=true`、`subtitle_path`、可选逐 Clip 状态）。`n2d-review` 的 review gate 与 `paid_distribution` compose gate 会 BLOCK 缺 sidecar 或 sidecar 不完整。
- **BGM 是机器合同，不是隐式占位**：正式/直调 compose 都先校验 `合成/第N集/bgm_contract.json`。`licensed_file/generated` 必须有真实文件和版权/模型+渠道来源；`none` 产生静音底；程序化 `placeholder` 只有明确 `approved_by` 且 `scope=internal_rough_only` 才可生成，并在 review/发布边界硬阻断。`BGMFILE` 不得与合同 source.file 静默换轨。
- **生成式 BGM 有统一适配入口**：`gen_bgm.py` 不写死厂商，读取合同生成 `bgm_generation_job.json`；配置 `N2D_BGM_CMD` 后用 `--run` 执行，已有 Suno/ACE-Step/其它合成音乐文件可用 `--register-existing` 登记。两条路径都写带合同 SHA 与音频 SHA 的 `bgm_generation_receipt.json`；文件或合同变化后 gate 判过期。
- **占位配音不许成片**：`compose.sh` 进门先查 `配音/时长清单.json`——若仍含占位句且未用 `VOICEFILE` 指定别的轨，**拒绝合成**（占位时长≠真实时长，烧进成片必音画错位）。仅 rough preview 可 `ALLOW_PLACEHOLDER_COMPOSE=1` 放行。

## 混合/画面先行镜头的最终配音拟合（真音拟合到已锁定视频镜头长）

适用于默认混合模式中 `rough_timing_final_dub_later`、`post_dub`、`base_video_then_post_lipsync`，也兼容整项目 `先出视频后配音`。`performance_audio_first` 与纯 `native_av` 不走本节。报告绑定镜头时长、最终配音清单、逐镜 route 和输出拟合轨 SHA；任一输入或拟合轨变化都会被 compose/review gate 判过期。

这条线的视频是按**估算时长**锁死出的，真实配音补在最后，每句长短与锁定镜头不一致；若把真音整轨直接 amix 到拼好的 clip 上会**渐进失步**。所以合成前**必须先拟合**：

```bash
# ① 确认真音已补（n2d-voice 用 CosyVoice/克隆/MiniMax 重跑，时长清单 占位=false）
# ② 拟合对账（dry-run，先看有没有 overflow）
python3 <skill>/fit_voice_to_clips.py <作品根> 第N集 zh
# ③ 生成拟合轨
python3 <skill>/fit_voice_to_clips.py <作品根> 第N集 zh --apply
# ④ 用拟合轨合成
VOICEFILE=<作品根>/合成/第N集/配音/voice_zh_fitted.wav bash <skill>/compose.sh <作品根> 第N集 zh
```

`fit_voice_to_clips.py` 按 `脚本/第N集/镜头时长.json`（锁定槽位）逐镜核对真音（实测 `line_*.wav`），四档处理，**拟合轨总长精确 = 锁定槽位总长 = 视频总长**：

| 情况 | 动作 | 代价 |
|---|---|---|
| 真音 ≤ 镜头槽位 | `pad`：放槽位起点 + 尾部补静音 | 无损 |
| 真音只超槽位且仍在 `FIT_TOLERANCE` 内 | `trim`：裁掉容差内尾差 | 避免为 0.01s 误差无谓变速 |
| 槽位 < 真音 ≤ 槽位×`FIT_MAX_STRETCH`(默认1.25) | `stretch`：atempo 轻微提速塞入 | 语速略快（已告警） |
| 真音 > 槽位×1.25 | `overflow`：**不静默处理**，列出镜头、退出码 2 | 须回 `n2d-video` 重出/重切加长，或显式调高阈值 |

> 有 overflow 时脚本拒绝产轨——这正是「先出视频后配音」最贵的返工点暴露处：要么回去重出那几个镜头加长，要么用户明知地接受重度变速。**别为了出片把它压过去。**

## 文件夹分工（2026 调整）
- **`出视频/第N集/视频/`** = 出视频阶段的**唯一**产物：各镜头 clip MP4。`出视频/` 不再放配音/成片。
- **`合成/第N集/`** = 本阶段的工作区：`配音/`（n2d-voice 产物，前置阶段已落这里）、`_voicecache/`、中间件 `_work/`、成片 `成片_第N集_{mode}.mp4`。
- compose 跨文件夹消费：clips 读 `出视频/`，配音读 `合成/`，成片写 `合成/`。

## 交付矩阵（G10 · 一母带 → 全平台 · `deliver.py`）

本集成片**母带**（`合成/第N集/成片_第N集_{mode}.mp4`）产出后，可一次从它派生 **多比例 × 多时长 cutdown × 平台规格**，落 `合成/交付/第N集/`，省去逐次手跑单一画幅/单时长。入口：

```bash
# 计划（只看将派生什么，不渲染）：读 _设置.md 的 目标平台/画幅/交付时长 决定规格
python3 skills/n2d/n2d-compose/deliver.py <作品根> 第N集
bash    skills/n2d/n2d-compose/compose.sh deliver <作品根> 第N集      # 等价子命令
# 实际派生（需 ffmpeg）：
python3 skills/n2d/n2d-compose/deliver.py <作品根> 第N集 --run
# 显式覆盖规格（首个比例=母带原生·不重出）：
python3 skills/n2d/n2d-compose/deliver.py <作品根> 第N集 --run --aspects 9:16,16:9,1:1 --durations 30s,15s
```

- **规格由选择点决定，不写死单一平台**：`deliver.py` 读 `_设置.md` 的 `目标平台`（→ 推荐画幅 + 响度目标）、`画幅`（母带原生比例；`多比例` 时派生全比例）、`交付时长`（cutdown 时长集，默认 30s/15s 引流版）。无成片母带 → **优雅报错**（提示先合成本集），不臆造。
- **多时长 cutdown（`cutdown.py`）= 漫剧语境的重剪，不是机械截断**：按 storyboard 每 Clip 的 `rhythm`（张力词：钩子/爽点/反转/高潮/**集尾 cliffhanger**…，与 `tension_mix.py` 同源词表）+ `钩子` 字段（hook/climax/end）选镜，**必保钩子/爽点/反转/集尾断点骨架**（引流版要留住人 + 留断点逼追更），砍铺垫/留白/细节。镜头时长读权威 `脚本/第N集/镜头时长.json`（finalize 定稿产物，n2d 里是 `{镜头键: 秒}` **字典**）；必保镜时长缺/为 0 → **block 拒绝出计划**（防 0s 假通过），先回 n2d-script `finalize_storyboard.py` 出定稿时长。保序输出保叙事连贯。
- **多比例 reframe（`reframe.py`）**：母带原生比例（默认竖屏 9:16）不重出；横屏/方版用 ffmpeg crop/pad 派生。**竖→横/方默认 `pad` 加边保全画**（避免裁掉竖屏母带上下信息）；主体偏置时可 `--crop-x/--crop-y` 焦点裁切。
- **响度复用既有 `loudness_conform.py`**（不重造）：交付矩阵按目标平台取响度目标（抖音/快手/TikTok≈-14、B站/YouTube -14、广电 -23、其余 -16 LUFS·候选快照）写进 `delivery_matrix.json`；逐件响度归一仍走 compose 末段 `loudness_conform` 巡检。
- **独立性**：`cutdown.py`/`reframe.py`/`deliver.py` 是参照同仓另一条创作线成熟交付实现的 **vendored fork**（复制+改写进本目录，词表/路径/schema 全改适配 n2d 漫剧），**不跨线 import 任何模块**，也不依赖 `n2d/_lib` 共享常量（`deliver.py` 用最小本地 `_设置.md` 解析）。纯逻辑（选镜优先级/时长裁剪计划、reframe 几何、规格派生矩阵）有 `test_delivery_matrix.py` 覆盖。

## 发布 Manifest（可发布边界 · `release_manifest.py`）

合成结束不等于可发布。正式交给投放/运营前，必须把母带、合规包、review gate、机器分、人审签收、AI 标识待办和事件账本审计汇总成发布 manifest：

```bash
python3 skills/n2d/n2d-compose/release_manifest.py build <作品根> 第N集 --stage review --write
python3 skills/n2d/n2d-compose/release_manifest.py check <作品根> 第N集
```

输出：

```text
合规/release_manifest_第N集.json
合规/release_manifest_第N集.md
```

`readiness.status=ready` 的最小条件：母带存在且 SHA256 可验、`compliance.py --check` 无 BLOCK、gate findings 无 block、production locks 未漂移、crew RACI 可追责、存在人审签收。AI 标识/水印/C2PA 仍按本线铁律只进发布待办，不阻断 compose；但 release manifest 会把这些待办集中列出来，避免“主流程已合成”被误当成“可以投放”。

**C2PA 2.4 证据边界**：`release_manifest.py` 不再因目录里“有一个 `.c2pa` / `.json` 文件”就宣称 provenance 已验证。只有 `c2pa_validation.json`（或兼容 receipt）明确 `well_formed=true`、`valid=true`，并绑定当前母版 `asset_sha256`，才计 `valid_trusted` 或 `valid_untrusted`；只有 Content Credentials/crJSON 的派生视图、缺源 manifest、哈希不一致或解析失败均记 `derived_view_unverified/invalid`。签名链可信度与内容是否 AI 生成是不同命题；机器可读 AI 标识也可由显式元数据/平台水印证明，不能拿未验证 C2PA 占位文件代替。

## 输入前置
- `出视频/第N集/视频/` 有 clip MP4（n2d-video 产物，必须是 AI 平台原片，不应出现 `.noaudio.mp4`、`*_noaudio.mp4` 或 `_raw_with_audio/` 这类提前剥音轨中间件）。否则报错建议先 n2d-video。
- `合成/第N集/配音/voice_{zh,en}.wav`（n2d-voice 产物，可选；无则纯 BGM+字幕）。
- 混合模式先读 `生产数据/production_mode_route_第N集.json`：若任一 route `final_voice_required=true`，上述 final voice 不再可选；若任一 route `post_lipsync_required=true`，必须先有相应 `视频_lipsync/Clip_XX_lipsync.mp4`。`timing_estimate.json` 只能填 OTIO planned slots，不能作为正式混音输入。
- `脚本/第N集/字幕_{中文,英文}.srt`。`原生音画` draft 可临时缺中文字幕，但 review/付费投放前必须补 whisperx/词级对齐字幕和 `native_av_subtitle_alignment` sidecar。
- 正式合成前必须先跑确定性 gate 并入账：`python3 skills/n2d/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage compose`（内部调用 `n2d-review/scripts/gate.py --json`；检查视频列、`storyboard.json`、clip 音轨/时长、原生音画 opt-in 清单、占位配音、字幕、`合规/compliance_manifest.json` 的平台/本地化计划）。缺合规包时先跑 `python3 skills/n2d/n2d-compliance/scripts/compliance.py <作品根> 第N集 --init`，人工补齐后再 `--check`。
- 发布前建议先跑 `python3 skills/n2d/n2d-dashboard/scripts/event_ledger.py doctor <作品根>`，再跑 `release_manifest.py build --write`；manifest 只汇总证据，不替代人审签收。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 强行把 clip 拉成等长，破坏剪辑节奏 | 严禁等长化。必须按原时长拼接，保留上游设计的节奏曲线 |
| 爽点/反转处画面与声音不同步 | 必须用 `BGM_OFFSET` 卡点，确保 drop/炸点与爽点时间戳同一帧砸下 |
| 在原生音画模式下仍然丢弃 clip 原生音频 | 错误。原生音画模式下台词在 clip 里，必须 `保留原片音轨` |
| 合成前未检查 `合规/compliance_manifest.json` | 版权/角色授权/声音克隆/平台审核是合规闸门，必须先在合规包声明策略 |
| 把 `timing_estimate.json` 或占位配音当正式声音 | 严禁。前者没有音频，后者没有签收；先完成声音定妆与 final voice，再刷新 OTIO/拟合 |
| 直接用 neutral-mouth base plate 合成正面对白 | 先完成 route 要求的独立 lipsync pass，并让 OTIO V1 指向 `视频_lipsync` 版本 |
| 在 `先出视频后配音` 模式下直接合成 | 必须先跑 `fit_voice_to_clips.py` 拟合真音到锁定槽位，产生拟合轨后再合成 |
| 忽略 `J-cut` 设计，导致对话感生硬 | 默认开启 `J_CUT_SEC=0.25`，让声音轻微提前入场，增强连贯性 |
| 字幕遮挡关键画面或风格不符 | 字幕渲染应按 `render_subs.py` 约束，确需调整则修改渲染策略 |
| 合成后未回写 `合规/compliance_manifest.json` 的最终资产路径 | 导致 `review` gate 阻断，无法进行质检 |

## 加 BGM —— 默认安全继续，用户可覆盖

缺少项目值、已授权文件或已配置生成后端时，推荐器自动落 `BGM来源=无`，`bgm_contract.py --write-missing` 生成可交付的 `strategy=none/status=confirmed` 合同，流水线继续产出无 BGM 母版。若用户已选本地授权文件、生成模型/渠道或内部粗剪占位，则严格按该选择校验文件、时长、版权和来源；生成付费与权利缺口仍停审。不能只靠临时 `BGMFILE`，也不能把未签收占位带进 review。

## 转场音效（可选层）
clip 已带即梦原生音效。额外「2~5 个转场音效」做成可选：用户给 SFX 文件就在 clip 边界铺，不给跳过。

## 视觉拟音 SFX（V2A·可插拔后端·`scripts/foley_agent.py`）
compose 混音前自动跑 `foley_agent.py`：分析 `storyboard.json` 识别视觉动因（拔剑/脚步/雨/门/爆炸…）→ 产**带绝对时间戳的拟音计划**（`_work/foley_plan.json`：环境/天气类铺满整 clip·冲击/动作类落 clip 内动作时刻），再交拟音后端合成 SFX 轨（`_work/foley_mix.wav`，作 compose ducking 混音的 `[foley]` 输入）。**拟音后端是选择点**：默认产**静音占位轨**（诚实·不假装真音效，向后兼容）；接真 V2A 后端设环境变量 `N2D_FOLEY_CMD` 命令模板（与 `N2D_VLM_CMD` 同套路·厂商无关·`{plan}{out}{duration}` 占位，可包装 Sony Woosh 本地/Mirelo·WaveSpeed 云）。`后期拟音策略=自动` 时，若本集路由为原生音画/原生音频后端且 compose 保留 clip 原生音轨，`foley_agent` 会只留 `foley_plan.json` 和静音 `foley_mix.wav`，让模型原生 foley/SFX 站台，避免双层打击声；需要补拟音时写 `后期拟音策略=强制叠加` 或临时设 `FORCE_COMPOSE_FOLEY=1`。**对齐粒度（2026-06-29 修真·治"打斗 SFX 对不上画面命中"）**：冲击类踩拍优先级 = **storyboard 命中/撞点秒（`impact_seconds_from_clip` 读 impact_frame/collision_or_apex_frame/post_cue_points/anchors keyframe·与 `anchor_planner.apex_anchor_seconds` 同源·多回合命中各一击·标 `aligned=apex`）** > 显式 `动作时刻/sfx_at`（`explicit`）> clip 中点估计（`estimated` 兜底）。即上游 apex-aware 算好的命中帧现在真的交给 foley 踩点，而非落镜头中间。打斗/动作题材爽感吃重时配真后端最值。详见 `n2d/references/模型矩阵.md` 横切 § 「SFX 拟音 V2A」。

## 打斗命中帧微震屏（P2·`scripts/combat_punch.py`·让规划好的撞点有物理冲击）
`[1/6]` 逐 clip 规格化重编码时，对 `fight_exchange/magic_burst` 且有命中秒的镜，把一段**保时长**的 ffmpeg `-vf` 微震屏拼进既有 `-vf` 链尾（**零额外重编码**）：命中秒 ±0.09s 窗口内做低幅 crop 抖动（screen-shake）再 scale 回 `PXWxPXH`，让命中帧有冲击力。**保时长是硬约束**——hit-stop（冻帧）会改时长、和配音对轨错位，故**刻意只做抖动不做冻帧**（白闪因本机 ffmpeg 的 eq 表达式解析器不稳也暂不做）。抖幅按可用 headroom 自适应（恒 ≤ headroom·永不越界）；命中秒来自 `foley_agent.impact_seconds_from_clip`（与拟音同源）。拆段子文件保守跳过。`combat_punch.py <root> <ep> <PXW> <PXH> --json` 可看每个打斗镜的命中秒+震屏片段。

## 行业参考（决定音频时展示给用户）
> 对于 90 秒左右的一集漫剧，很多工作室会准备：
> - 1 条背景音乐（全程循环）
> - 2~5 个转场音效
> - AI 角色配音

## 工作流
1. 归集 `视频/` clips → 统一 1080x1920/30fps → 拼接。
2. BGM：按 `bgm_contract.json` 执行真实文件、明确无 BGM 或已签收的 internal rough 占位；无合同直接拒绝。
3. 混音：配音(若有) + ducking BGM + clip 自带音效底。若显式 `J_CUT_SEC>0` 且存在 `line_*.wav`，先重建一条 `voice_jcut.wav` 参与混音。
4. 烧字幕（render_subs.py，模式 zh/en/bilingual）。
5. 输出 `合成/第N集/成片_第N集_{mode}.mp4`；回写 `_进度.md` 成片列。
6. 记录生产数据：
   ```bash
   python3 skills/n2d/n2d-dashboard/scripts/dashboard.py record <作品根> \
     --episode 第N集 --stage compose --event generation \
     --asset <成片MP4路径> --status pass \
     --duration-sec <合成耗时秒> --provider local-ffmpeg \
     --meta native_audio_policy=<丢弃|低音量混入环境声|保留原片音轨>
   ```
   若本集用于海外投放或产出英文/双语字幕，compose/review gate 会要求 `设定库/translation_glossary.json` 覆盖人名、称谓、境界、招式、口头禅、系统提示语，并与字幕/OCR 检查一起过 gate。

> **AI 标识/水印不阻断本阶段**：compose 出成片即完成可选合成尾段；`ai_label.py` 只是 best-effort 发布待办辅助。若投放地区/平台需要 AI 标识、披露或数字水印，由使用方在发布工序或工具之外按当地法规自行处理。

## 完成后 · 可选后续

回写「成片」列后，**跑 `python3 skills/n2d/progress.py <作品根>` 看整部前沿**，并把下一步念给用户。默认镜头交付早已在 `视频` 完成时收为 `clip_delivery_complete`；若本次启用合成尾段是为了发布包或交付母带，继续跑 review/release/readiness 证据包、production locks 和人工签收「验收」列：

```
第K集 成片完成：合成/第K集/成片_第K集_{mode}.mp4
- _进度.md「成片」列已勾 ✅
下一步建议：
- 质检验收（发布包/交付母带建议）：
    python3 skills/n2d/run.py next <作品根> 第K集
    # 自动刷新 review gate、progress DAG、P-3 check、score、consistency_ledger、review-ui、
    # failure_taxonomy、release_verdict、production_locks、creative_governance；
    # 通过后停在 needs_acceptance_signoff，再显式回写「验收」列 ✅
- 上线后投放回灌：n2d-feedback <作品根> --metrics <平台指标.csv>   留存/追更/跳出反哺导演节奏；
    # 付费/追更平台的 platform_metrics 需带 paywall_position_sec / paywall_after_promise_id / unlock_friction / continue_path
    再 n2d-dashboard build <作品根> --markdown 看成本/ROI/通过率
- 推进下一集：n2d <作品根>（调度器按前沿路由）或直接 n2d-script <作品根> 第K+1集
- 整部进度总览 + 下一步：n2d-progress <作品根>
- 发布前归档：
    python3 skills/n2d/n2d-dashboard/scripts/event_ledger.py doctor <作品根>
    python3 skills/n2d/n2d-compose/release_manifest.py build <作品根> 第K集 --stage review --write
    python3 skills/n2d/scripts/production_locks.py <作品根> 第K集 check --json
    python3 skills/n2d/scripts/creative_governance.py <作品根> check --json
```

> 量产时优先 `n2d-batch` 排队推进多集，`n2d-dashboard` 盯成本/通过率/重抽率，红灯先回产线修。

## 调用
见 references/usage.md。
