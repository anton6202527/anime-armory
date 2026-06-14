---
name: n2d-compose
description: Stage 6 of n2d (剪映合成的脚本化替代) — assemble a finished episode 成片 from 视频/ clips + (可选)配音轨 + (可选)BGM(占位/文件/Suno) + 烧录双语字幕. Mixes voice with BGM ducking, burns subtitles via Pillow+overlay (本机 ffmpeg 无 libass). Writes _进度.md 成片 column. Use when asked to 合成, 合成成片, 成片, 加BGM, 加背景音乐, 烧字幕, 混音, 出成片, 导出成片. Triggers 合成, 成片, 加BGM, 背景音乐, 烧字幕, 混音, 导出, compose, 剪映.
---

# n2d-compose — 合成成片（剪映那步的脚本化替代）

把一集的 `视频/`(clips) + `配音/voice_*.wav`(可选) + BGM(可选) + 字幕 烧成 `成片_第N集_{mode}.mp4`。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/n2d/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill涉及的选择点：`BGM来源`、`画幅`、`制作模式`（决定配音轨是否需先拟合到已成片镜头长·见「先出视频后配音」节）、`视频原生音轨`（丢弃 / 低音量混入环境声 / 保留原片音轨）、`目标平台`、`发行地区`、`合规用途`。其中 `目标平台/发行地区/合规用途` 只是偏好入口，**实际放行以 `合规/compliance_manifest.json` 为准**，不得只看 `_设置.md`。

> **AI 标识/水印不再由本流水线处理**：compose 不再生成可见 AI 标识/水印、不再调用任何 watermark skill。AI 标识/AI 披露/水印等合规义务移到工具之外，由使用方按各平台/各地区法规自行处理。

## 核心原则
- **剪辑节奏 = 不许等长化**（`n2d/references/导演节奏.md §四/§五`）：clip 的时长曲线就是剪辑节奏，由上游（配音时长 + 故事板节奏注记）设计好——铺垫长镜、爽点碎切、爽点后留白。本 skill **按原时长拼接（concat -c copy），绝不把 clip 拉成等长**，否则节奏塌成 PPT。
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
- **张力感知 BGM 增益（爽点抬/细节压·替代一刀切）**：`DUCK_RATIO` 是整集统一档；要让爽点/爆发镜 BGM 顶上去、悬念/细节镜压更狠，先跑 `python3 skills/n2d-compose/tension_mix.py <作品根> 第N集 --expr` 读 `storyboard.json` 每 Clip `rhythm` 映射成随时间变化的 BGM 基准音量包络，再喂给 compose：`BGM_GAIN_EXPR="$(python3 skills/n2d-compose/tension_mix.py <作品根> 第N集 --expr)" bash compose.sh ...`。这条增益作用在 voice 侧链 ducking **之前**的 BGM 基准上，与既有 `DUCK_RATIO` 侧链叠加。**不传 `BGM_GAIN_EXPR` 时保持原固定 `0.9/0.85` 行为**（向后兼容）；缺 storyboard 时给提示不臆造。`tension_mix.py`（无 `--expr`）打人读包络图 + 建议叠音效的爽点镜清单。
- **clip 原生音频处理（P1 原生音画 opt-in）**：Veo / Seedance / Kling 出的 clip 可能**自带原生音轨**（环境音甚至台词）。n2d-video 阶段保留平台原片，不提前去音轨；本 skill 是唯一处理原生音轨的地方。默认仍是配音先行，不让原生台词接管角色声音。选择点 `视频原生音轨`：
  - `丢弃`（默认）：只在 compose 工作缓存/最终合成链路里剥掉 clip 原生音轨，**不改写 `出视频/第N集/视频/` 的 AI 原片**；音频全部由 配音+BGM+SFX 这条受控链路提供，避免双人声。
  - `低音量混入环境声`：仅当 n2d-video 的「原生音画 opt-in 清单」确认该 Clip 低风险、无口型、无原生人声时，将 clip 原生音轨按 `CLIP_AUDIO_GAIN`（默认 0.35）压低混入作环境底。
  - `保留原片音轨`：仅用于无配音/测试预览/明确要原片声时；有 n2d-voice 配音轨时必须先提醒双人声风险，compose gate 会把“保留原片音轨 + 存在配音轨 + clip 有音频流”视为阻断。
  - 命令覆盖：`VIDEO_NATIVE_AUDIO_POLICY=丢弃|低音量混入环境声|保留原片音轨`；旧 `KEEP_CLIP_AUDIO=1` 兼容为 `低音量混入环境声`。
  - **原生音画模式例外（自动覆盖）**：`制作模式=原生音画` 时台词在 clip 自带音轨里，丢弃会丢台词——compose 自动把策略转为 `保留原片音轨`（`compose.sh` 实现）。要强制别的策略须显式设 `VIDEO_NATIVE_AUDIO_POLICY_EXPLICIT=1` 一并指定 `VIDEO_NATIVE_AUDIO_POLICY`。
- **合规与版权前置（P0）**：compose 不是“先出片再补救”的地方。正式合成前必须存在 `合规/compliance_manifest.json`，并已通过 `n2d-compliance` 填好：版权/改编权、角色授权、声音克隆授权、目标平台审核、出海本地化。`gate.py --stage compose` 会在合成前阻断：缺合规包、投放平台未定、海外投放未声明字幕/本地化。（AI 标识/AI 披露/水印不再由本流水线强制，移到工具之外处理。）
- **生产数据记账铁律（P0）**：合成完成或失败后必须调用 `n2d-dashboard` 记录 `stage=compose` 事件，至少包含输出文件、耗时、原生音轨策略；若 gate 阻断或合成失败，用 QA/manual 事件记录原因。否则无法统计每集成片耗时、音轨策略风险和最终通过率。
- **字幕烧录**：本机 Homebrew ffmpeg **无 libass**（无 subtitles/drawtext 滤镜）→ 用 Pillow 把 SRT 渲染成透明 PNG 再 overlay 烧录（render_subs.py）。
- **占位 BGM 为主**：默认程序化占位；可选真实文件覆盖。
- **占位配音不许成片**：`compose.sh` 进门先查 `配音/时长清单.json`——若仍含占位句且未用 `VOICEFILE` 指定别的轨，**拒绝合成**（占位时长≠真实时长，烧进成片必音画错位）。仅 rough preview 可 `ALLOW_PLACEHOLDER_COMPOSE=1` 放行。

## 先出视频后配音（`制作模式` 选择点 · 真音拟合到已成片镜头长）

仅当 `制作模式=先出视频后配音`（快速 demo·不推荐，见 `n2d` SKILL「制作模式」节）。默认 `配音先行` **不走本节**——那条线配音先行、镜头时长本就由真音驱动，`voice_<lang>.wav` 与 clip 天然对齐，直接合成即可。

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

## 输入前置
- `出视频/第N集/视频/` 有 clip MP4（n2d-video 产物，必须是 AI 平台原片，不应出现 `.noaudio.mp4`、`*_noaudio.mp4` 或 `_raw_with_audio/` 这类提前剥音轨中间件）。否则报错建议先 n2d-video。
- `合成/第N集/配音/voice_{zh,en}.wav`（n2d-voice 产物，可选；无则纯 BGM+字幕）。
- `脚本/第N集/字幕_{中文,英文}.srt`。
- 正式合成前必须先跑确定性 gate 并入账：`python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage compose`（内部调用 `n2d-review/scripts/gate.py --json`；检查视频列、`storyboard.json`、clip 音轨/时长、原生音画 opt-in 清单、占位配音、字幕、`合规/compliance_manifest.json` 的平台/本地化计划）。缺合规包时先跑 `python3 skills/n2d-compliance/scripts/compliance.py <作品根> 第N集 --init`，人工补齐后再 `--check`。

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

> **AI 标识/水印不在本阶段处理**：compose 出成片即收尾，不再生成可见 AI 标识/水印、不再调用任何 watermark skill。若投放地区/平台需要 AI 标识或披露，由使用方在工具之外按当地法规自行处理。

## 调用
见 references/usage.md。
