---
name: n2d-compose
description: Stage 6 of n2d (剪映合成的脚本化替代) — assemble a finished episode 成片 from 视频/ clips + (可选)配音轨 + (可选)BGM(占位/文件/Suno) + 烧录双语字幕. Mixes voice with BGM ducking, burns subtitles via Pillow+overlay (本机 ffmpeg 无 libass). Writes _进度.md 成片 column. Use when asked to 合成, 合成成片, 成片, 加BGM, 加背景音乐, 烧字幕, 混音, 出成片, 导出成片. Triggers 合成, 成片, 加BGM, 背景音乐, 烧字幕, 混音, 导出, compose, 剪映.
---

# n2d-compose — 合成成片（剪映那步的脚本化替代）

把一集的 `视频/`(clips) + `配音/voice_*.wav`(可选) + BGM(可选) + 字幕 烧成 `成片_第N集_{mode}.mp4`。

**跨集成片一致性登记（2026-06 加固·schema 见 `n2d-review/references/扩展一致性登记表.md`）**：成片阶段维护两张剧级表，让逐集观感不漂——① `设定库/series_grade.json` 剧级**调色锁**（LUT/白平衡/对比/饱和基线），每集套用后写 `合成/<集>/grade_applied.json` 留痕（`tone_light_contract` 只焊片内像素，这层管跨集色温/对比）；② `设定库/ambient_map.json` 每场景**环境声床**（LOC→ambient bed，`reverb_profile` 管混响、这层管底噪连续性）。调色采用层级裁决：`series_grade` 是默认基线，场景光位/剧情天气可局部收紧，情绪/梦境/回忆等有意变调必须在 `grade_applied.json` 写 `grade_override.reason/source_clip`，否则按漂色处理。n2d-review 的 `系列调色(GRD)` / `调色层级(COLORH)` / `环境声(AMB)` 据此对账。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/n2d/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill涉及的选择点：`BGM来源`、`画幅`、`制作模式`（决定配音轨是否需先拟合到已成片镜头长·见「先出视频后配音」节）、`视频原生音轨`（丢弃 / 低音量混入环境声 / 保留原片音轨）、`后期拟音策略`（自动 / 强制叠加 / 关闭）、`目标平台`、`发行地区`、`合规用途`。其中 `目标平台/发行地区/合规用途` 只是偏好入口，**实际放行以 `合规/compliance_manifest.json` 为准**，不得只看 `_设置.md`。

> **AI 标识非阻断铁律**：compose `[6/6]` 后可自动跑 `ai_label.py` 做 best-effort 后处理。默认 `AI显式角标=仅元数据`：只写机器可读 AI 元数据，不把「AI生成」角标烤进内部预览画面；正式投放若平台/地区要求显式标识，改为 `AI显式角标=开启` 再叠角标并回写 `合规/compliance_manifest.json` 的 `ai_labeling` 状态。AI 标识/披露/水印不得阻断合成、进度回写、dashboard 记账或后续集推进；失败只形成发布前待办。数字水印、平台侧 AIGC 披露与严格 GB 45438 字节级封装均可在工具外补齐。

## 核心原则
- **剪辑节奏 = 不许等长化**（`n2d/references/导演节奏.md §四/§五`）：clip 的时长曲线就是剪辑节奏，由上游（配音时长 + 故事板节奏注记）设计好——铺垫长镜、爽点碎切、爽点后留白。本 skill **按原时长拼接（concat -c copy），绝不把 clip 拉成等长**，否则节奏塌成 PPT。
- **三轨后期执行铁律（旁白/字幕/花字都归 compose）**：`n2d-script` 产出的 `dialogue / narration / screen_text` 三轨在本阶段合流。角色对白若已由原生音画 clip 生成，则本阶段只保留/混音并做字幕对齐；旁白一律在 compose 阶段用 TTS/配音轨生成并混入，不让视频模型直接生成旁白音频；`screen_text_lines[]`、标题卡、花字、系统面板数值和普通字幕一律由 compose 用 Pillow/overlay 叠加，不让视频模型烤字。`dialogue_fact_contract_第N集.json` 是三轨事实账本：旁白和屏幕文案必须按合同取词，年龄、身高、灵根、趟数等数字不得在后期脚本里临场改写。字幕也是 compose 阶段统一产物：原生音画可先出无字幕 draft，但 review/发布前必须从原生音轨或三轨合同生成/对齐 `字幕_中文.srt` 并过 `native_av_subtitle_alignment`。
- **卡点**：爽点的冲击 = 画面 + 声音同一帧砸下。用 `BGM_OFFSET` 平移 BGM，让 drop/炸点落在 `故事板.md` 标的爽点时间戳（如 `💥爽点 @ 0:48`）那一帧；反转/觉醒处铺 bgm.txt 标的"重音"音效。
- **留白呼吸**：爆发后那个 `留白·定格` clip 不要被音效填满——让它喘一口（必要时 BGM 瞬时拉低再起）。
- **声音连续 / J-cut / 空镜缓冲**：合成默认尊重 `故事板.md` 的衔接设计：BGM 全程连续铺底，不按 clip 断；空镜缓冲 clip 原样保留呼吸；默认 `J_CUT_SEC=0.25`，脚本基于 `line_*.wav + 时长清单.json` 重建轻量提前入声的配音轨，让下一句更早粘住画面切换。正面口型特写多的集可设 `J_CUT_SEC=0` 关闭。
- **按转场类型接 clip，别盲拼**（接力链末端兜底）：读 `故事板.md`/`storyboard.json` 每个接缝的 `转场类型` 决定接法，而不是一律裸切——
  - `match_cut / 动作切 / 有尾帧接力的硬切`：直接硬切（上游已用首尾双帧焊好接点，这里无缝最稳）。
  - `空镜缓冲`：契约要求缓冲但 `视频/` 里没有对应空镜 clip → **停下报警**（缺料），不要默默硬切糊过去；有就原样保留其呼吸。
  - `转场未定 / 上下 clip 视觉跳变明显`（接点没焊住又非有意硬切）：可加 **0.1–0.3s 微交叉溶解**兜底跳切——ffmpeg `xfade` 滤镜即可（不依赖 libass），仅在该接缝局部重编码、其余仍 `concat -c copy`。爽点/反转的有意硬切**不要**加溶解（会泄掉冲击）。
  - 默认策略走 `创作偏好-默认.md`，可在 `_设置.md` 记 `接缝兜底=硬切|微溶解|报警`；接法属可控点，拿不准时按"有意硬切硬切、跳变溶解、缺空镜报警"。
  - **实现现状（已落地·不再是 TODO）**：`compose.sh` 拼接步已改调 `seam_concat.py`——自动读 `storyboard.json` 每接缝 `continuity.transition` 分类：**硬切→裸拼、微溶解→局部 `xfade`、缺空镜→报警**（写 `合成/<ep>/_work/接缝报告.md` + stderr）。**支持 Split Relay (拆段接力)**：同一逻辑镜的子段（`_partN`）强制硬切以保证无缝，仅跨逻辑镜接缝才应用 storyboard 转场。实现策略：硬切/报警/Split子段相连的 clip 归为一个 run 先 `concat -c copy`（零重编码），只在**溶解接缝**间做 xfade，把重编码压到最小。**无溶解接缝时等价今天的 `concat -c copy`**；clip 数与 storyboard 对不上、或 ffmpeg 失败 → 自动回退裸拼，绝不中断合成。兜底/溶解秒可用环境变量 `SEAM_FALLBACK`（默认硬切）/`SEAM_DISSOLVE_SEC`（默认 0.25）覆盖。缺空镜仍只报警**不自造素材**——要消除生硬跳切需人工补一个空镜 clip 再合成。`seam_concat.py --plan-only` 可干跑看接法计划。
- **配音先行**：BGM 垫在配音下面并被配音 ducking（先有配音再压 BGM）。配音轨由 n2d-voice 在前置阶段产出，本 skill **只消费不生成**。
- **默认后期配音线（2026-07 起）**：长期量产默认 `制作模式=配音先行`，不是原生音画。视频层只生产无声 Image2Video；对白层由 CosyVoice / Fish Speech / MiniMax Speech / 其它 TTS 独立生成并按角色固定音色；音效层单独规划脚步、开门、风雨、爆炸、打斗、环境声；音乐层按剧情段落铺温馨/战斗/悲伤等情绪，不按镜头碎切；最后由 FFmpeg 统一混音、ducking、烧字幕并输出 MP4。`原生音画` 仅作为快速预览或特殊后端选项。
- **张力感知 BGM 增益（爽点抬/细节压·替代一刀切）**：`DUCK_RATIO` 是整集统一档；要让爽点/爆发镜 BGM 顶上去、悬念/细节镜压更狠，先跑 `python3 skills/n2d-compose/tension_mix.py <作品根> 第N集 --expr` 读 `storyboard.json` 每 Clip `rhythm` 映射成随时间变化的 BGM 基准音量包络，再喂给 compose：`BGM_GAIN_EXPR="$(python3 skills/n2d-compose/tension_mix.py <作品根> 第N集 --expr)" bash compose.sh ...`。这条增益作用在 voice 侧链 ducking **之前**的 BGM 基准上，与既有 `DUCK_RATIO` 侧链叠加。**不传 `BGM_GAIN_EXPR` 时保持原固定 `0.9/0.85` 行为**（向后兼容）；缺 storyboard 时给提示不臆造。`tension_mix.py`（无 `--expr`）打人读包络图 + 建议叠音效的爽点镜清单。
- **🎼 角色/势力主题动机（leitmotif·确定性复用）**：BGM 此前只到「逐集情绪 + 张力 ducking」，没有跨集「听见就知道是他」的复现旋律。生成式音乐跨集维持同一动机极不稳，故用**确定性复用**：可选 `<作品根>/设定库/motif.json`（`{"沈念":{"file":"素材/motif/shen.wav","cue":"focus","gain":0.5}}`）一次性登记角色/势力的一段动机 clip。compose `[6/6]` 后自动跑 `motif_registry.py --mix`：读 `时长清单.json` 在角色焦点 span 开头铺**同一段 clip**（`min_gap` 去重防刷屏），视频流直 copy 只改音轨。缺 motif.json=空规划 no-op，成片一字不动。巡检：`python3 motif_registry.py <作品根> 第N集`。
- **📊 集成响度（LUFS）达标巡检**：compose `[6/6]` 后自动跑 `loudness_conform.py`，量成片**集成响度/真峰** vs 平台目标（youtube/bilibili/tiktok≈-14、broadcast -23、默认 -16 LUFS·候选快照），advisory 不阻断——超标给整改提示（既有逐句 loudnorm + dynaudnorm/alimiter 之外的最终符合性对账）。`--platform` 可指定目标。
- **交付包装证据包（review warn 回灌）**：成片通过不只看 MP4 存在。每次正式合成后要补齐或刷新 `final_timeline_probe_第N集.json`、`合成/<集>/grade_applied.json`、混合视频后端时的 color match/grade report、`tension_mix`/BGM gain 证据、room tone/foley/ambient bed 证据、`loudness_conform` 报告和 `series_packaging`/release manifest。缺这些证据时，review/score 的 `delivery_packaging_consistency` 只能给 warn/缺数据；production/release profile 下先回 compose 补证据，不把内部预览误当可投放母带。
- **clip 原生音频处理（P1 原生音画 / 配音先行分流）**：Veo / Seedance / Kling 出的 clip 可能**自带原生音轨**（环境音甚至台词）。n2d-video 阶段保留平台原片，不提前去音轨；本 skill 是唯一处理原生音轨的地方。默认 `配音先行` 会丢弃 clip 原生音轨，不让原生台词接管角色声音；只有显式 `原生音画` 时才保留原片音轨承接台词。选择点 `视频原生音轨`：
  - `丢弃`（默认）：只在 compose 工作缓存/最终合成链路里剥掉 clip 原生音轨，**不改写 `出视频/第N集/视频/` 的 AI 原片**；音频全部由 配音+BGM+SFX 这条受控链路提供，避免双人声。
  - `低音量混入环境声`：仅当 n2d-video 的「原生音画 opt-in 清单」确认该 Clip 低风险、无口型、无原生人声时，将 clip 原生音轨按 `CLIP_AUDIO_GAIN`（默认 0.35）压低混入作环境底。
  - `保留原片音轨`：仅用于无配音/测试预览/明确要原片声时；有 n2d-voice 配音轨时 `compose.sh` 会直接阻断，compose gate 也会把“保留原片音轨 + 存在配音轨 + clip 有音频流”视为阻断。原生音画项目若配音轨确认为旁白/系统层，先过 gate/sidecar，再显式 `ALLOW_NATIVE_AV_VOICEOVER=1`；仅内部预览才可 `ALLOW_DOUBLE_VOICE=1` 自担风险。
  - **release gate**：只要策略不是 `丢弃`，就必须存在 `生产数据/native_av_physics_第N集.json`，逐 Clip 说明声源、可见动作证据、空间混响、后期处理策略；低风险 ambience/native_sfx 也不例外。缺 sidecar 时先回 `n2d-video` 补「原生音画物理一致性契约」，不要在 compose 阶段凭听感放行。
  - 命令覆盖：`VIDEO_NATIVE_AUDIO_POLICY=丢弃|低音量混入环境声|保留原片音轨`；旧 `KEEP_CLIP_AUDIO=1` 兼容为 `低音量混入环境声`。
  - **原生音画模式例外（自动覆盖）**：`制作模式=原生音画` 时台词在 clip 自带音轨里，丢弃会丢台词——compose 自动把策略转为 `保留原片音轨`（`compose.sh` 实现）。要强制别的策略须显式设 `VIDEO_NATIVE_AUDIO_POLICY_EXPLICIT=1` 一并指定 `VIDEO_NATIVE_AUDIO_POLICY`。
- **合规与版权前置（P0）**：compose 不是“先出片再补救”的地方。正式合成前必须存在 `合规/compliance_manifest.json`，并已通过 `n2d-compliance` 填好：版权/改编权、角色授权、声音克隆授权、目标平台审核、出海本地化。`gate.py --stage compose` 会在合成前阻断缺合规包、投放平台未定、海外投放未声明字幕/本地化等硬项。**AI 生成合成内容标识（`ai_labeling`）只做 INFO 待办**；compose `[6/6]` 后 `ai_label.py` 可 best-effort 落显式角标 + 元数据并回写 manifest，失败不阻断主流程。
- **生产数据记账铁律（P0）**：合成完成或失败后必须调用 `n2d-dashboard` 记录 `stage=compose` 事件，至少包含输出文件、耗时、原生音轨策略；若 gate 阻断或合成失败，用 QA/manual 事件记录原因。否则无法统计每集成片耗时、音轨策略风险和最终通过率。
- **付费/续看闭环字段**：成片进入投放、解锁或追更平台时，发布侧的 `platform_metrics.*` 不只写留存和收入；必须带 `paywall_position_sec`、`paywall_after_promise_id`、`unlock_friction`、`continue_path`。这些字段由 `n2d-feedback` 分析“卡点是否落在已打开承诺之后、哪条续看路径追更最高”，下一批再回灌到分镜和交付策略；compose 不直接改平台数据，但交付说明必须提醒运营/发布工序落这些列。
- **字幕烧录**：本机 Homebrew ffmpeg **无 libass**（无 subtitles/drawtext 滤镜）→ 用 Pillow 把 SRT 渲染成透明 PNG 再 overlay 烧录（render_subs.py）。
- **原生音画字幕闭环**：`制作模式=原生音画` 时，compose 可在缺 `字幕_中文.srt` 的情况下先出 draft（脚本会跳过字幕并给 warning），但这不是可交付成片。成片后必须用 whisperx 或等效词级对齐从原生音轨生成中文字幕，落 `脚本/第N集/字幕_中文.srt`，并写 `生产数据/native_av_subtitle_alignment_第N集.json`（`kind=n2d_native_av_subtitle_alignment`、`status=pass|aligned`、`alignment_tool/source`、`word_level=true`、`subtitle_path`、可选逐 Clip 状态）。`n2d-review` 的 review gate 与 `paid_distribution` compose gate 会 BLOCK 缺 sidecar 或 sidecar 不完整。
- **占位 BGM 为主**：默认程序化占位；可选真实文件覆盖。
- **占位配音不许成片**：`compose.sh` 进门先查 `配音/时长清单.json`——若仍含占位句且未用 `VOICEFILE` 指定别的轨，**拒绝合成**（占位时长≠真实时长，烧进成片必音画错位）。仅 rough preview 可 `ALLOW_PLACEHOLDER_COMPOSE=1` 放行。

## 先出视频后配音（`制作模式` 选择点 · 真音拟合到已成片镜头长）

仅当 `制作模式=先出视频后配音`（快速 demo·不推荐，见 `n2d` SKILL「制作模式」节）。`原生音画` 默认不走本节；`配音先行` 也不走本节——那条线镜头时长本就由真音驱动，`voice_<lang>.wav` 与 clip 天然对齐，直接合成即可。

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

`fit_voice_to_clips.py` 按 `脚本/第N集/镜头时长.json`（锁定槽位）逐镜头核对真音（实测 `line_*.wav`），三档处理，**拟合轨总长精确 = 锁定槽位总长 = 视频总长**：

| 情况 | 动作 | 代价 |
|---|---|---|
| 真音 ≤ 镜头槽位 | `pad`：放槽位起点 + 尾部补静音 | 无损 |
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
python3 skills/n2d-compose/deliver.py <作品根> 第N集
bash    skills/n2d-compose/compose.sh deliver <作品根> 第N集      # 等价子命令
# 实际派生（需 ffmpeg）：
python3 skills/n2d-compose/deliver.py <作品根> 第N集 --run
# 显式覆盖规格（首个比例=母带原生·不重出）：
python3 skills/n2d-compose/deliver.py <作品根> 第N集 --run --aspects 9:16,16:9,1:1 --durations 30s,15s
```

- **规格由选择点决定，不写死单一平台**：`deliver.py` 读 `_设置.md` 的 `目标平台`（→ 推荐画幅 + 响度目标）、`画幅`（母带原生比例；`多比例` 时派生全比例）、`交付时长`（cutdown 时长集，默认 30s/15s 引流版）。无成片母带 → **优雅报错**（提示先合成本集），不臆造。
- **多时长 cutdown（`cutdown.py`）= 漫剧语境的重剪，不是机械截断**：按 storyboard 每 Clip 的 `rhythm`（张力词：钩子/爽点/反转/高潮/**集尾 cliffhanger**…，与 `tension_mix.py` 同源词表）+ `钩子` 字段（hook/climax/end）选镜，**必保钩子/爽点/反转/集尾断点骨架**（引流版要留住人 + 留断点逼追更），砍铺垫/留白/细节。镜头时长读权威 `脚本/第N集/镜头时长.json`（finalize 定稿产物，n2d 里是 `{镜头键: 秒}` **字典**）；必保镜时长缺/为 0 → **block 拒绝出计划**（防 0s 假通过），先回 n2d-script `finalize_storyboard.py` 出定稿时长。保序输出保叙事连贯。
- **多比例 reframe（`reframe.py`）**：母带原生比例（默认竖屏 9:16）不重出；横屏/方版用 ffmpeg crop/pad 派生。**竖→横/方默认 `pad` 加边保全画**（避免裁掉竖屏母带上下信息）；主体偏置时可 `--crop-x/--crop-y` 焦点裁切。
- **响度复用既有 `loudness_conform.py`**（不重造）：交付矩阵按目标平台取响度目标（抖音/快手/TikTok≈-14、B站/YouTube -14、广电 -23、其余 -16 LUFS·候选快照）写进 `delivery_matrix.json`；逐件响度归一仍走 compose 末段 `loudness_conform` 巡检。
- **独立性**：`cutdown.py`/`reframe.py`/`deliver.py` 是参照同仓另一条创作线成熟交付实现的 **vendored fork**（复制+改写进本目录，词表/路径/schema 全改适配 n2d 漫剧），**不跨线 import 任何模块**，也不依赖 `n2d/_lib` 共享常量（`deliver.py` 用最小本地 `_设置.md` 解析）。纯逻辑（选镜优先级/时长裁剪计划、reframe 几何、规格派生矩阵）有 `test_delivery_matrix.py` 覆盖。

## 发布 Manifest（可发布边界 · `release_manifest.py`）

合成结束不等于可发布。正式交给投放/运营前，必须把母带、合规包、review gate、机器分、人审签收、AI 标识待办和事件账本审计汇总成发布 manifest：

```bash
python3 skills/n2d-compose/release_manifest.py build <作品根> 第N集 --stage review --write
python3 skills/n2d-compose/release_manifest.py check <作品根> 第N集
```

输出：

```text
合规/release_manifest_第N集.json
合规/release_manifest_第N集.md
```

`readiness.status=ready` 的最小条件：母带存在且 SHA256 可验、`compliance.py --check` 无 BLOCK、gate findings 无 block、存在人审签收。AI 标识/水印/C2PA 仍按本线铁律只进发布待办，不阻断 compose；但 release manifest 会把这些待办集中列出来，避免“主流程已合成”被误当成“可以投放”。

## 输入前置
- `出视频/第N集/视频/` 有 clip MP4（n2d-video 产物，必须是 AI 平台原片，不应出现 `.noaudio.mp4`、`*_noaudio.mp4` 或 `_raw_with_audio/` 这类提前剥音轨中间件）。否则报错建议先 n2d-video。
- `合成/第N集/配音/voice_{zh,en}.wav`（n2d-voice 产物，可选；无则纯 BGM+字幕）。
- `脚本/第N集/字幕_{中文,英文}.srt`。`原生音画` draft 可临时缺中文字幕，但 review/付费投放前必须补 whisperx/词级对齐字幕和 `native_av_subtitle_alignment` sidecar。
- 正式合成前必须先跑确定性 gate 并入账：`python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage compose`（内部调用 `n2d-review/scripts/gate.py --json`；检查视频列、`storyboard.json`、clip 音轨/时长、原生音画 opt-in 清单、占位配音、字幕、`合规/compliance_manifest.json` 的平台/本地化计划）。缺合规包时先跑 `python3 skills/n2d-compliance/scripts/compliance.py <作品根> 第N集 --init`，人工补齐后再 `--check`。
- 发布前建议先跑 `python3 skills/n2d-dashboard/scripts/event_ledger.py doctor <作品根>`，再跑 `release_manifest.py build --write`；manifest 只汇总证据，不替代人审签收。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 强行把 clip 拉成等长，破坏剪辑节奏 | 严禁等长化。必须按原时长拼接，保留上游设计的节奏曲线 |
| 爽点/反转处画面与声音不同步 | 必须用 `BGM_OFFSET` 卡点，确保 drop/炸点与爽点时间戳同一帧砸下 |
| 在原生音画模式下仍然丢弃 clip 原生音频 | 错误。原生音画模式下台词在 clip 里，必须 `保留原片音轨` |
| 合成前未检查 `合规/compliance_manifest.json` | 版权/角色授权/声音克隆/平台审核是合规闸门，必须先在合规包声明策略 |
| 将占位配音烧进正式成片 | 严禁。占位时长不准，会导致音画错位。成片前必须换真音色拟合或配音先行 |
| 在 `先出视频后配音` 模式下直接合成 | 必须先跑 `fit_voice_to_clips.py` 拟合真音到锁定槽位，产生拟合轨后再合成 |
| 忽略 `J-cut` 设计，导致对话感生硬 | 默认开启 `J_CUT_SEC=0.25`，让声音轻微提前入场，增强连贯性 |
| 字幕遮挡关键画面或风格不符 | 字幕渲染应按 `render_subs.py` 约束，确需调整则修改渲染策略 |
| 合成后未回写 `合规/compliance_manifest.json` 的最终资产路径 | 导致 `review` gate 阻断，无法进行质检 |

## 加 BGM —— 给用户更丰富选项 + 接受自定义
到 BGM 环节，提示用户：
> 「BGM 怎么来？ⓐ 你用 Suno 生成一条给我文件 ⓑ 素材库选 ⓒ 指定本地文件 ⓓ 占位合成。也可以直接说你的想法（循环某首/某风格/某时长），我**鉴定合理可行**(文件存在/格式/时长够循环/版权)后按你的来；不可行说明原因给替代。」
用户给文件 → `BGMFILE=<路径>`；否则占位。

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
2. BGM：`BGMFILE` 文件(loop/trim+fade) 或 程序化占位。
3. 混音：配音(若有) + ducking BGM + clip 自带音效底。若显式 `J_CUT_SEC>0` 且存在 `line_*.wav`，先重建一条 `voice_jcut.wav` 参与混音。
4. 烧字幕（render_subs.py，模式 zh/en/bilingual）。
5. 输出 `合成/第N集/成片_第N集_{mode}.mp4`；回写 `_进度.md` 成片列。
6. 记录生产数据：
   ```bash
   python3 skills/n2d-dashboard/scripts/dashboard.py record <作品根> \
     --episode 第N集 --stage compose --event generation \
     --asset <成片MP4路径> --status pass \
     --duration-sec <合成耗时秒> --provider local-ffmpeg \
     --meta native_audio_policy=<丢弃|低音量混入环境声|保留原片音轨>
   ```
   若本集用于海外投放或产出英文/双语字幕，compose/review gate 会要求 `设定库/translation_glossary.json` 覆盖人名、称谓、境界、招式、口头禅、系统提示语，并与字幕/OCR 检查一起过 gate。

> **AI 标识/水印不阻断本阶段**：compose 出成片即主流程收尾；`ai_label.py` 只是 best-effort 发布待办辅助。若投放地区/平台需要 AI 标识、披露或数字水印，由使用方在发布工序或工具之外按当地法规自行处理。

## 完成后 · 详列下一步（收尾必做 · 本集成片后还要验收）

回写「成片」列后，**跑 `python3 skills/n2d/progress.py <作品根>` 看整部前沿**，并把下一步念给用户——本集只是出片完成，主流程下一步是「验收」。验收通过并人工签收后，才回写 `_进度.md`「验收」列：

```
第K集 成片完成：合成/第K集/成片_第K集_{mode}.mp4
- _进度.md「成片」列已勾 ✅
下一步建议：
- 质检验收（必做）：
    python3 skills/n2d/run.py next <作品根> 第K集
    # 自动刷新 review gate、progress DAG、P-3 check、score、consistency_ledger、review-ui、
    # failure_taxonomy、release_verdict；通过后停在 needs_acceptance_signoff，再显式回写「验收」列 ✅
- 上线后投放回灌：n2d-feedback <作品根> --metrics <平台指标.csv>   留存/追更/跳出反哺导演节奏；
    # 付费/追更平台的 platform_metrics 需带 paywall_position_sec / paywall_after_promise_id / unlock_friction / continue_path
    再 n2d-dashboard build <作品根> --markdown 看成本/ROI/通过率
- 推进下一集：n2d <作品根>（调度器按前沿路由）或直接 n2d-script <作品根> 第K+1集
- 整部进度总览 + 下一步：n2d-progress <作品根>
- 发布前归档：
    python3 skills/n2d-dashboard/scripts/event_ledger.py doctor <作品根>
    python3 skills/n2d-compose/release_manifest.py build <作品根> 第K集 --stage review --write
```

> 量产时优先 `n2d-batch` 排队推进多集，`n2d-dashboard` 盯成本/通过率/重抽率，红灯先回产线修。

## 调用
见 references/usage.md。
