---
name: mv-video
description: 制MV 出视频 — 把 mv-image 的 PNG 图生视频成 MV clip，clip 时长对齐 mv-plan/beatgrid 卡点（副歌踩鼓点切），用 jobs_manifest 跟踪多版生成、评分和挑版，运镜服务节奏。mv 系列自建，不调 n2d-video；用通用生视频模型/渠道（Seedance/Veo/Kling/即梦/可灵/manual 等）。Use when asked to MV出视频 / 生成MV视频 / MV图生视频 / 卡点剪辑素材 / 登记视频take / 挑版. Triggers MV出视频, MV视频, MV图生视频, MV运镜, 视频take, 挑版, mv-video.
---

# mv-video — 制MV 出视频（mv 系列自建）

把 `出图/` 的 PNG 图生视频成 MV clip，落 `出视频/takes/` 与 `出视频/视频/`。**clip 时长来自 `分镜/clip_plan.json`，而 clip_plan 由 `节拍/beatgrid.json` 卡点驱动**（不等长），运镜服务节奏。**自包含**，不调 n2d-video；用通用生视频 CLI 或人工/网页生成后登记。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/mv-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`生视频模型`、`生视频渠道`、`出视频规格`（三档预算·每次调模型/渠道前告知·见下「出视频规格」节）、`视频分辨率`、`MV规划粒度`、`卡点策略`。旧 `生视频AI` 兼容读取。

## 核心原则
- **卡点驱动 clip 时长**：每个 clip 时长 = 相邻卡点之差（`beatgrid.downbeats`）。**副歌每 1 拍/半小节一切（碎切）、verse 缓（2-4 拍）**。别等长堆叠——这是 MV 的命。
- **图生视频为主**：以 mv-image 的 PNG 为首帧，生视频模型只控运动+运镜，锁画面一致性。纯氛围/转场可文生。
- **运镜服务节奏/情绪**：副歌高能=快推/环绕/轻甩；verse 叙事=缓推/跟；bridge 反转=换机位。爽点对齐 downbeat。
- **动作知识库优先**：先从 `references/action_knowledge.md` 选 `action_family`，再写一个主动作链、动作峰值和转场母题。短 clip 不堆多个动作；复杂接触/多人互动优先拆成手部、道具、剪影、光效切。
- **三件套必写**：人物运动 + 镜头运动 + 动态细节。
- **continuity 必写**：每个 clip 必须有 `continuity.start_state/action/end_state/constraints/negative`，同时读取上一/下一 clip、`beatgrid.json` 起止点、段落张力和歌词画面钩子。`continuity.start_state` 直接抄上一 clip 的 `end_state`（单一真值，别重写）。MV 的连续性不是一镜到底，而是"视觉身份一致 + 动作/视线/道具可切 + 卡点落点准"。
  - **MV 默认卡点硬切**（踩 downbeat 切），接点靠"视觉身份一致 + 卡点准"，**不强求 n2d 那套首尾帧接力**。但**同段落·非卡点切·人物姿态连续**的接缝（如副歌内一段连续动作分两 clip），可选尾帧接力：`clip_plan.json` 标 `need_end_frame=true`，mv-image 出 `出图/段落/图片/Clip_XXX_end.png`=下一 clip 首帧构图，mv-video 首尾双帧引导锁接点。换段/卡点切不需要。
- **导演视角八维（视频版）**：①镜头/③人物/⑤场景/⑥光影/⑧画风**已由首帧 PNG 锁死**（出图阶段做完），视频阶段**只升级 ④动作→人物运动+表情(踩段落)、②机位→运镜(对齐 downbeat)、⑦张力**，其余严禁重定（改了=与首帧打架=闪烁）。详见 `mv/references/导演视角prompt.md §四`。
- **MV 单曲一致性继承**：`mv-image` 已锁主角身份、主色、母题和段落 look；视频 prompt 只让它动起来，不改脸、不换衣型、不换场景风格。副歌可以让光效和相机更猛，但不能换成另一套视觉语言。
- **生视频贵**：先在图阶段锁死视觉，视频只调动作/运镜；每 clip 跑几版挑稳由 `出视频规格` 档统一决定（见下节）。
- **视频任务 manifest**：先用 `scripts/video_jobs.py` 从 `分镜/clip_plan.json` 生成 `出视频/jobs_manifest.json` 和逐 take prompt；AI/网页/人工生成的视频先登记到 `takes/`，评分后挑版复制到 `出视频/视频/Clip_XXX.mp4` 并同步 `分镜/timeline_manifest.json`。不要只把 mp4 扔进目录让下游猜来源。
- **生视频 CLI**：本机官方 CLI（dreamina/kling/veo/seedance）直调；没有则生成 job 包并指导 web/manual 登记。**不装第三方逆向 CLI**。
- **出视频规格按三档预算 + 每次调模型/渠道前告知**：调即梦或任何生视频模型/渠道出 MV clip 前，**像出图预算提示一样先把本次生成规格告知用户**——规格打包成 `出视频规格` 三档预算（**预算充足 / 预算一般（默认）/ 预算不够**），每档预设*分辨率·帧率·每clip跑几版挑稳·平台质量档*。**首次问一次**→记入 `_设置.md`→之后**沉默沿用但每次开跑前一行告知当前档**（随时可改）。与 n2d-video 同义同源。三档表 + 告知话术见下「出视频规格」节。

## 出视频规格（选择点 `出视频规格` · 三档预算 · 每次调模型/渠道前告知）

和出图阶段的预算提示同一套思路、与 n2d-video 同义同源：**真正调生视频模型/渠道前，把本次的生成规格告知用户**，别默默用了贵档或抠档。规格打包成三档预算，每档预设四件事——**分辨率 · 帧率 · 每个 clip 跑几版挑稳 · 平台质量/模型档**：

| 规格档 | 分辨率 | 帧率 | 每 clip 跑几版挑稳 | 平台质量/模型档 |
|---|---|---|---|---|
| **预算充足** | 1080p | 30fps | 关键镜 2-3 版挑最稳 · 普通镜 2 版 | 平台高质量档（即梦 Pro / 可灵 Master / Veo 高保真 / Seedance Pro） |
| **预算一般**（默认） | 720p | 24-30fps | 关键镜 2 版挑稳 · 普通镜 1 版 | 平台标准档 |
| **预算不够** | 720p | 24fps | 全部 1 版 | 平台快速/省积分档（即梦 Lite 等） |

- **解析顺序**（按 `../skills/mv-craft/references/选择点与偏好.md`）：读 `<作品根>/_设置.md` 的 `出视频规格` → 缺则全局默认（`预算一般`）预填并告知一句 → 再缺则**首次问一次**→写回 `_设置.md`。**默认 `预算一般`**（对齐既有 720p 默认 + 视频贵的克制）。
- **每次开跑前必告知当前档**（沉默沿用 ≠ 闷头跑）：进真正调 AI 那一步，先念一行——
  > 「即将出 MV 视频，当前规格档 = **预算一般**（720p · 24-30fps · 关键镜跑 2 版挑稳 / 普通镜 1 版 · 标准档）。可改 **预算充足**（1080p·30fps·多跑挑稳·高质量档，更清晰更贵）或 **预算不够**（720p·24fps·全 1 版·省积分档，最省）。要改说一声，否则按此档跑。」
- **MV 的「关键镜」= 副歌高光/爽点 clip · 人脸特写 · 对齐 downbeat 的卡点镜**；verse 叙事镜/纯空镜/转场为普通镜。「跑几版挑稳」就是「每 clip 跑 2 版挑脸/运动稳」的预算开关——本档统一决定，不再每 clip 临时拍脑袋。
- **单项可覆盖**：规格档只设默认，`视频分辨率` 等单项仍可在 `_设置.md` 单独覆盖。单 clip **时长不在本档内**——由 `beatgrid.json` 卡点驱动（见核心原则）；合成画幅另见 `合成画幅` 选择点（MV 默认 16:9 横屏）。
- **落实到调用**：选定档后，把该档的分辨率/帧率喂给 CLI 的 `--resolution`/`--fps`（或平台对应 flag），并按「跑几版」决定每 clip抽几版挑稳。

## 工作流
1. 先跑 `mv-plan`，确认 `分镜/clip_plan.json` 与 `timeline_manifest.json` 已存在；若 `歌曲输入时序=后配歌曲`，必须已经补入最终 `歌/song.*` 并跑完真实 `节拍/beatgrid.json`。
2. 生成视频任务包：
   ```bash
   python3 skills/mv-video/scripts/video_jobs.py "<制MV作品根>"
   ```
   脚本入口会先过 `mv-craft/scripts/gate.py video_jobs`：缺最终 `歌/song.*`、歌词、beatgrid、正式视觉蓝图、clip_plan 或首帧 PNG 时直接阻断。通过后产 `出视频/jobs_manifest.json` + `出视频/prompt/Clip_XXX_take_YY.md`，并回写 `_进度.md` 的 `video_jobs` 行。每个 job 带首帧、时长、转场、continuity、跑几版、关键镜标记。
3. 调 AI 前**先念「出视频规格」告知话术**（当前规格档 + 三档可改，见上节）→ 按 job prompt 逐 take 图生视频。外部生成后登记：
   ```bash
   python3 skills/mv-video/scripts/video_jobs.py "<制MV作品根>" --register /path/to/take.mp4 --clip Clip_001 --take 1
   ```
4. 对 take 评分/挑版：
   ```bash
   python3 skills/mv-video/scripts/video_jobs.py "<制MV作品根>" --score Clip_001 --take 1 --motion-score 90 --identity-score 88 --beat-score 92 --clarity-score 86
   python3 skills/mv-video/scripts/video_jobs.py "<制MV作品根>" --select Clip_001 --take 1
   ```
   `--select` 会复制到 `出视频/视频/Clip_001.mp4`，并同步 `分镜/timeline_manifest.json`；全部 clip 都选中后脚本自动回写 `_进度.md` 的 `video` 行。
5. 校验：clip 总时长 ≈ 歌长（差太多回头调 clip/补空镜）。
6. 下一步 mv-lyric-sync（字幕）/ mv-compose（合成，按 timeline 拼）。

## 详细参考
- 导演视角八维（视频版·只调动作/运镜/张力，其余继承首帧）：`mv/references/导演视角prompt.md §四`
- jobs manifest 格式 + 卡点定时长 + 运镜映射：`references/prompt_format.md`
- MV 动作知识库（动作家族/动作峰值/炫酷转场母题）：`references/action_knowledge.md`

## 常见错误
| 错误 | 纠正 |
|---|---|
| clip 等长不卡点 | 先跑 mv-plan，时长按 beatgrid 相邻卡点定，副歌碎切 |
| 后配歌曲未补最终歌就出视频 | 先补成品歌、跑 mv-beat 和正式 mv-plan；rough 蓝图不生成正式视频 |
| 不告知规格就闷头调 AI 出视频 | 违反 `出视频规格` 选择点——调 AI 前先念三档话术告知当前规格档（分辨率/帧率/跑几版/质量档），用户可改 |
| 外部生成后只丢 mp4 | 用 `video_jobs.py --register/--score/--select` 登记 take、挑版并同步 timeline |
| 首帧还没出就生成视频任务 | `video_jobs.py` 会 gate 阻断；先跑 mv-image 产出 `clip.image_path` 指向的 PNG |
| 只写画面不写运动 | 人物运动+镜头运动+动态细节三件套 |
| 每条都写“炫酷动作/酷炫运镜” | 从动作知识库选 `action_family`，写一个主动作链和动作峰值 |
| 一个短 clip 塞太多动作 | 一 clip 一个主动作；副歌短 clip 尤其要克制 |
| clip 单条好看但剪起来跳 | 每条补 `continuity` 五字段：承接上一条、给下一条留落点、锁服装发型/场景/轴线/道具，负面禁止换脸换衣新增人物 |
| 运镜乱炫 | 服务节奏：副歌快/verse 缓/爽点对 downbeat |
| 有角色用文生视频 | 用图生视频，首帧=mv-image PNG |
| 想复用 n2d-video | mv 自建，各写各的 |
