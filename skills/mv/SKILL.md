---
name: mv
description: 制MV 总调度 — 把歌曲或歌曲企划做成 AI 音乐 MV 视频，开跑先让用户选择【歌曲输入时序】：先传音乐（先有成品歌/用户音频，按真实 beatgrid 卡点）或后配歌曲（先做视觉蓝图 rough，后续由 song 线/用户上传定稿歌，再重跑卡点与正式 timeline）。是与 n2d(制漫剧) 平行的"制MV"生产线，产物落 制MV/曲名/(成片_MV.mp4)。**mv 视觉/剪辑阶段自包含，不复用 n2d-*；后配歌曲只在成品文件层面衔接 song 线或用户上传**。读 _进度.md 路由到 mv-craft(共享契约/AI披露) / mv-script(视觉蓝图) / mv-beat(卡点) / mv-plan(clip/timeline规划) / mv-image(出图) / mv-video(出视频+挑版) / mv-lyric-sync(卡拉OK字幕) / mv-compose(合成)。换脸用本线 mv-video-faceswap。Use when given a finished song/audio, a song concept that needs MV planning before final audio, or an existing 制MV/曲名/ folder, or asked 做MV / 给这首歌做视频 / 先做MV后配歌 / 先传音乐做MV / 卡点 / 卡拉OK / MV出图出视频 / 合成成片. Triggers MV, 音乐视频, 做MV, 给歌做视频, 先传音乐, 后配歌曲, 卡点, 卡拉OK, 歌词字幕, MV出图, MV出视频, MV合成, mv.
---

# mv — 制MV 生产线 · 总调度

把**一首歌或歌曲企划**做成 AI 音乐 MV 视频。**产物 = `制MV/<曲名>/成片_MV.mp4`**。开跑先确认 `歌曲输入时序`：
- **先传音乐**：用户已有成品歌/音频，先入 `歌/song.*`，再用真实 beatgrid 卡点，这是正式 MV 推荐路径。
- **后配歌曲**：用户还没最终音频，先做视觉蓝图 rough；等 song 线产出或用户上传成品歌后，必须再跑 `mv-beat`，用真实节拍重算 `mv-plan`，再出图/视频/合成。

与 `n2d`（小说→漫剧）平行：**写歌 → 制MV**，正如 **写小说 → 制漫剧**。后配歌曲时，写歌仍交给 `song` 线或用户上传；mv 线只做视觉和剪辑。

**完全独立铁律**：mv-* 的视觉、卡点、分镜、出图、出视频、字幕、合成阶段**自包含，不复用 n2d-* / novel-* 或 song-* 的内部实现**。后配歌曲只把“最终歌/歌词产出”路由给 `song` 线或用户上传，并在文件层面接入 `歌/song.*` + `词/lyrics.md`；mv 阶段仍用自己的脚本和契约。换脸调**本线能力 `mv-video-faceswap`**。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/mv-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`MV用途`、`歌曲输入时序`、`MV视觉风格`、`MV规划粒度`、`卡点策略`、`生视频模型`、`生视频渠道`、`生图AI`、`MV一致性增强`、`出视频规格`、`视频分辨率`、`合成画幅`、`AI视觉使用披露`、`发行目标平台`。

> 作为生产线入口：开新曲（`制MV/<曲名>/`）时先问 `歌曲输入时序`（先传音乐 / 后配歌曲）、`生视频模型`（Seedance 2.0、Veo 3.1、Kling 3.0、Hailuo 02/2.3、Runway Gen-4、Luma Ray3.2、Pika 2.5、HunyuanVideo 1.5、Wan 2.2、LTX-2.3、manual）和 `生视频渠道`（即梦/Dreamina、豆包、海螺AI、可灵/Kling、Google Gemini API、Runway API、manual），再初始化 `<作品根>/_设置.md`。若用户已经给音频，可默认建议“先传音乐”；若用户只有歌名/歌词/视觉想法，可建议“后配歌曲”。若 `_设置.md` 已存在或用户本轮已明确模型/渠道，直接沿用/覆盖。旧 `生视频AI` 只作兼容 fallback。

## 作品根约定
```
制MV/<曲名>/
├── _进度.md / _meta.json / _设置.md
├── 视觉蓝图.md          MV 视觉概念：主角/场景/画风 + 段落↔画面映射 + 卡点策略
├── 歌/song.wav          输入成品歌（先传音乐时开局就有；后配歌曲时后续补入）
├── 词/lyrics.md         歌词（从 写歌/ 拷入，或用户给）—— 卡拉OK对齐用
├── 节拍/beatgrid.json   BPM + beat/downbeat + 段落图（mv-beat 产）
├── 分镜/                clip_plan.json + timeline_manifest.json（mv-plan 产）
├── 字幕/                karaoke.ass / lyrics.lrc（mv-lyric-sync 产）
├── 设定/                角色卡/场景卡/global_style（mv 自管，锁视觉一致性）
├── 出图/                mv-image：共享定妆 + 分段分镜 PNG
├── 出视频/              jobs_manifest.json + takes/ + 视频/（mv-video 产）
├── 合规/                AI视觉使用披露（mv-craft 产）
└── 成片_MV.mp4
```

## 阶段 + 路由

| 阶段 | skill | 产物 | 状态 |
|---|---|---|---|
| 共享契约/立项 | 本调度 + **`mv-craft`** | `_设置.md` + `_meta.json` + `_进度.md` + AI披露脚本 | ✅ 已建 |
| 歌曲入库/定稿 | **`song` 或用户上传** | `歌/song.*` + `词/lyrics.md` | ✅ 已建（阶段顺序随 `歌曲输入时序` 变化） |
| 剧本创作 | **`mv-script`** | `视觉蓝图.md` + 角色/场景设定 | ✅ 已建 |
| 卡点 | **`mv-beat`** | `节拍/beatgrid.json`（BPM+beat+downbeat+能量+段落） | ✅ 已建（librosa） |
| clip/timeline 规划 | **`mv-plan`** | `分镜/clip_plan.json` + `timeline_manifest.json` + prompt 包 | ✅ 已建 |
| 分镜体检(可选) | **`mv-score`** | 视觉概念与卡点节奏分析报告 | ✅ 已建（出图出视频前拦截平庸分镜） |
| 出图 | **`mv-image`** | `出图/`（共享定妆 + 分段分镜 PNG） | ✅ 已建（生图 CLI） |
| 出视频 | **`mv-video`** | `出视频/jobs_manifest.json` + `takes/` + `视频/`（按段落+卡点挑版） | ✅ 已建（生视频 CLI/登记脚本） |
| 卡拉OK字幕 | **`mv-lyric-sync`** | `字幕/karaoke.ass` + `lyrics.lrc` + `alignment_report.json` | ✅ 已建（whisperx） |
| 合成 | **`mv-compose`** | `成片_MV.mp4`（读 timeline 顺序 + 歌轨 + 精准裁切 + 卡拉OK烧录） | ✅ 已建（自包含 ffmpeg） |
| 质检/自审(横切) | **`mv-review`** | 双模 QA：作品质检（视觉一致性/卡点/字幕/音画合成/合规）+ 流程自审 | ✅ 已建（机检+人判，不生产只审） |

| 用户输入 | 路由到 |
|---|---|
| 有成品歌/用户音频，要立项做 MV | 本调度选择 `歌曲输入时序=先传音乐`，建 `制MV/<曲名>/`（拷入歌+词）→ `mv-beat` |
| 还没有歌，但想先定 MV 视觉 | 本调度选择 `歌曲输入时序=后配歌曲`，先 `mv-script` 做 rough 视觉蓝图；随后去 `song` 或等用户上传成品歌，再回 `mv-beat` |
| 还没有歌，只想先写歌 | 去 `song`（写歌线），出歌后再回 mv 选择“先传音乐” |
| 要分析卡点 | `mv-beat` |
| 要按歌自动拆 clip / 生成时间线 | `mv-plan` |
| 已有分镜，要评估视觉概念与节奏 | `mv-score`（生成前打分） |
| 要给 MV 出画 | `mv-image`（出图）→ `mv-video`（出视频）；整首当一个"作品"，段落≈分镜组 |
| 要卡拉OK字幕 | `mv-lyric-sync` |
| 素材齐了要合成成片 | `mv-compose` |
| 要给某段视频换脸 | 本线 `mv-video-faceswap`（先过其合规闸门） |
| 审 MV / 卡点对账 / 字幕检查 / 成片体检 / 流程自审 | `mv-review`（成品后审，出定位报告） |
| 给了 `制MV/<曲名>/` 没说动作 | 读 `_进度.md` 报进度 + 建议下一步 |

> **先传音乐推荐顺序**：成品歌/歌词入库 → mv-craft 立项/选择 → mv-beat 卡点 → mv-script 剧本创作 → mv-plan 时间线 → 分镜体检(mv-score) → 出图 → 视频任务/挑版 → 卡拉OK字幕 → 合成 → AI使用披露/质检。

> **后配歌曲推荐顺序**：mv-craft 立项/选择 → mv-script rough 视觉蓝图/设定 → song 线产歌或用户上传成品歌+歌词 → mv-beat 卡点 → mv-script 按真实 beatgrid 复核蓝图 → mv-plan 时间线 → 分镜体检(mv-score) → 出图 → 视频任务/挑版 → 卡拉OK字幕 → 合成 → AI使用披露/质检。**未补最终音频前不得跑 mv-plan / mv-image / mv-video / mv-compose 的正式产物**。

> **mv-image/mv-video 是 mv 自己的视觉 skill**（不调 n2d-image/n2d-video）。可借鉴两层定妆、尾帧接力、出图前一致性包和视频动作模板化思路，但代码与文档各写各的。

> **MV 版一致性边界**：MV 通常是一支歌/一集长视频，不需要 n2d 那种跨集状态账本；但仍要锁“同一首歌内部”的主角身份、主色、画风、反复视觉母题和段落光色。使用 `mv-image/references/visual_consistency.md`：主角/主唱最严，段落场景中等，特效转场最宽松。
> **MV 出图一致性增强**：组图前 `mv-image` 必须提示 `MV一致性增强` 四档：共享定妆+锚点（默认）、指定参考图、后端主体库、+LoRA。MV 不默认训练 LoRA；只有用户已有或明确授权的 LoRA 资产才接入。

> **MV 动作知识库**：炫酷动作优先从 `mv-video/references/action_knowledge.md` 选动作家族，再写进 `clip_plan.json` 的 `action_family/action_peak/visual_motif/transition_motif`。原则是“一 clip 一个主动作，动作峰值踩 beat/downbeat”，避免空泛写“炫酷运镜”。

## 合法性
- 输入歌的版权随歌而定（自有/授权/原创）；本线只做视觉，不改词曲版权属性。
- 用 `mv-video-faceswap` 换脸时，遵守它的合规闸门（仅本人/授权/合成脸 + 强制 AI 标识）。

## 与别的线
- **创作线**：`novel`(写小说) / `song`(写歌)。**生产线**：`n2d`(制漫剧) / **`mv`(制MV)**。写小说→制漫剧、**写歌→制MV**。
- 各线**互不依赖**（自包含）；换脸是**本线** `mv-video-faceswap`。

## 持续改进
工艺/翻车 → 写进对应 mv-* skill 的 `references/`。**新增/改 mv-* skill 后同步更新 `skills/README.md`。**

## 常见错误

| 错误 | 纠正 |
|---|---|
| 后配歌曲路线在未定稿音频前就正式拆 timeline/出视频 | 只能先做 rough 视觉蓝图；最终歌入库后必须跑 `mv-beat` + `mv-plan` |
| 将半成品或尚未完成创作的音频当成先传音乐路线送入制MV管线 | 先传音乐路线要求音频是最终成品；若还会改歌，请选后配歌曲 |
| 跳过视觉蓝图直接批量生成片段 | 分镜与生成必须要有总体视觉规划和卡点策略引导，不要无脑调用 `mv-video` |
| 不打合规/AI披露标签直接发布 | 无论是音频、视频还是换脸生成，在交付最终 MP4 之前必须通过 `mv-craft` 完成 AI 使用说明和披露登记 |
