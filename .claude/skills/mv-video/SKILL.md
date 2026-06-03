---
name: mv-video
description: 制MV 出视频 — 把 mv-image 的 PNG 图生视频成 MV clip，clip 时长对齐 beatgrid 卡点（副歌踩鼓点切），运镜服务节奏。mv 系列自建，不调 n2d-video；用通用生视频 CLI（即梦/可灵/Veo/Seedance）。Use when asked to MV出视频 / 生成MV视频 / MV图生视频 / 卡点剪辑素材. Triggers MV出视频, MV视频, MV图生视频, MV运镜, mv-video.
---

# mv-video — 制MV 出视频（mv 系列自建）

把 `出图/` 的 PNG 图生视频成 MV clip，落 `出视频/视频/`。**clip 时长对齐 `节拍/beatgrid.json` 卡点**（不等长），运镜服务节奏。**自包含**，不调 n2d-video；用通用生视频 CLI。

## 核心原则
- **卡点驱动 clip 时长**：每个 clip 时长 = 相邻卡点之差（`beatgrid.downbeats`）。**副歌每 1 拍/半小节一切（碎切）、verse 缓（2-4 拍）**。别等长堆叠——这是 MV 的命。
- **图生视频为主**：以 mv-image 的 PNG 为首帧，视频 AI 只控运动+运镜，锁画面一致性。纯氛围/转场可文生。
- **运镜服务节奏/情绪**：副歌高能=快推/环绕/轻甩；verse 叙事=缓推/跟；bridge 反转=换机位。爽点对齐 downbeat。
- **三件套必写**：人物运动 + 镜头运动 + 动态细节。
- **生视频贵**：先在图阶段锁死视觉，视频只调动作/运镜；每 clip 可跑 2 版挑稳。
- **生视频 CLI**：本机官方 CLI（dreamina/kling/veo/seedance）直调；没有则一步步指导 web。**不装第三方逆向 CLI**。

## 工作流
1. 读 `beatgrid.json`（downbeats/段落）+ `出图/` PNG + `视觉蓝图` 段落映射。
2. 规划 clip：按段落 + 卡点定**每 clip 时长**（副歌密、verse 疏），列 clip 表（首帧 PNG / 时长 / 运镜 / 段落）。
3. 逐 clip 图生视频 → `出视频/视频/Clip<NN>_<描述>.mp4`；废片归 `common/废料/`。
4. 校验：clip 总时长 ≈ 歌长（差太多回头调 clip/补空镜）。
5. 回写 `_进度.md` 视频行。下一步 mv-lyric-sync（字幕）/ mv-compose（合成，按 beatgrid 卡点拼）。

## 详细参考
- clip 表格式 + 卡点定时长 + 运镜映射：`references/prompt_format.md`

## 常见错误
| 错误 | 纠正 |
|---|---|
| clip 等长不卡点 | 时长按 beatgrid 相邻卡点定，副歌碎切 |
| 只写画面不写运动 | 人物运动+镜头运动+动态细节三件套 |
| 运镜乱炫 | 服务节奏：副歌快/verse 缓/爽点对 downbeat |
| 有角色用文生视频 | 用图生视频，首帧=mv-image PNG |
| 想复用 n2d-video | mv 自建，各写各的 |
