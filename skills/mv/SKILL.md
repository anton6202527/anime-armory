---
name: mv
description: 制MV 总调度 — 把一首【已做好的歌】（来自 写歌/song 线，或用户给的音频）做成 AI 音乐 MV 视频。是与 novel2drama(制漫剧) 平行的"制MV"生产线，输入=成品歌，产物落 制MV/<曲名>/(成片_MV.mp4)。**自包含，不复用 n2d-* 或任何家族 skill**。读 _进度.md 路由到 mv-beat(卡点) / mv-image(出图) / mv-video(出视频) / mv-lyric-sync(卡拉OK字幕) / mv-compose(合成)。换脸用公共 video-faceswap。Use when given a finished song/audio or an existing 制MV/<曲名>/ folder, or asked 做MV / 给这首歌做视频 / 卡点 / 卡拉OK / MV出图出视频 / 合成成片. Triggers MV, 音乐视频, 做MV, 给歌做视频, 卡点, 卡拉OK, 歌词字幕, MV出图, MV出视频, MV合成, mv.
---

# mv — 制MV 生产线 · 总调度

把**一首已经做好的歌**做成 AI 音乐 MV 视频。**输入 = 成品歌**（来自 `写歌/<曲名>/`（song 线产）或用户直接给的音频 + 词）；**产物 = `制MV/<曲名>/成片_MV.mp4`**。

与 `novel2drama`（小说→漫剧）平行：**写歌 → 制MV**，正如 **写小说 → 制漫剧**。歌怎么来不归本线管（那是 `song` 写歌线）。

**完全独立铁律**：mv-* **自包含，不复用 n2d-*/novel-*/song-* 任何家族 skill**。视觉/合成/字幕全在 mv-* 内自实现；只用通用外部工具（ffmpeg / librosa / whisperx / 生图生视频 CLI）。换脸调**公共能力 `video-faceswap`**（它不属于任何家族）。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../_偏好约定.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`生视频AI`、`生图AI`、`视频分辨率`、`合成画幅`。

> 作为生产线入口：开新曲（`制MV/<曲名>/`）时按全局默认初始化 `<作品根>/_设置.md`。

## 作品根约定
```
制MV/<曲名>/
├── _进度.md / _meta.json
├── 视觉蓝图.md          MV 视觉概念：主角/场景/画风 + 段落↔画面映射 + 卡点策略
├── 歌/song.wav          输入成品歌（从 写歌/<曲名>/歌/ 拷入，或用户给）
├── 词/lyrics.md         歌词（从 写歌/ 拷入，或用户给）—— 卡拉OK对齐用
├── 节拍/beatgrid.json   BPM + beat/downbeat + 段落图（mv-beat 产）
├── 字幕/                karaoke.ass / lyrics.lrc（mv-lyric-sync 产）
├── 设定/                角色卡/场景卡/global_style（mv 自管，锁视觉一致性）
├── 出图/                mv-image：共享定妆 + 分段分镜 PNG
├── 出视频/视频/         mv-video：图生视频（按段落+卡点）
└── 成片_MV.mp4
```

## 阶段 + 路由

| 阶段 | skill | 产物 | 状态 |
|---|---|---|---|
| 立项(视觉蓝图) | 本调度 + `mv-image` 起手 | `视觉蓝图.md` + 设定 | — |
| 卡点 | **`mv-beat`** | `节拍/beatgrid.json`（BPM+beat+段落） | ✅ 已建（librosa） |
| 出图 | **`mv-image`** | `出图/`（共享定妆 + 分段分镜 PNG） | ✅ 已建（生图 CLI） |
| 出视频 | **`mv-video`** | `出视频/视频/`（图生视频，按段落+卡点） | ✅ 已建（生视频 CLI） |
| 卡拉OK字幕 | **`mv-lyric-sync`** | `字幕/karaoke.ass`（词级高亮） | ✅ 已建（whisperx） |
| 合成 | **`mv-compose`** | `成片_MV.mp4`（歌轨+卡点剪辑+卡拉OK烧录） | ✅ 已建（自包含 ffmpeg） |
| 质检/自审(横切) | **`mv-review`** | 双模 QA：作品质检（视觉一致性/卡点/字幕/音画合成/合规）+ 流程自审 | ✅ 已建（机检+人判，不生产只审） |

| 用户输入 | 路由到 |
|---|---|
| 还没有歌，要先写歌 | 去 `song`（写歌线），出歌后再回 mv |
| 有成品歌，要立项做 MV | 本调度建 `制MV/<曲名>/`（拷入歌+词）→ 定视觉蓝图 |
| 要分析卡点 | `mv-beat` |
| 要给 MV 出画 | `mv-image`（出图）→ `mv-video`（出视频）；整首当一个"作品"，段落≈分镜组 |
| 要卡拉OK字幕 | `mv-lyric-sync` |
| 素材齐了要合成成片 | `mv-compose` |
| 要给某段视频换脸 | 公共 `video-faceswap`（先过其合规闸门） |
| 审 MV / 卡点对账 / 字幕检查 / 成片体检 / 流程自审 | `mv-review`（不生产只审，出定位报告） |
| 给了 `制MV/<曲名>/` 没说动作 | 读 `_进度.md` 报进度 + 建议下一步 |

> 推荐顺序：**(成品歌) → 卡点 → 出图 → 出视频 → 卡拉OK字幕 → 合成**。

> **mv-image/mv-video 是 mv 自己的视觉 skill**（不调 n2d-image/n2d-video）。可借鉴两层定妆/卡点思路，但代码与文档各写各的。

## 合法性
- 输入歌的版权随歌而定（自有/授权/原创）；本线只做视觉，不改词曲版权属性。
- 用 `video-faceswap` 换脸时，遵守它的合规闸门（仅本人/授权/合成脸 + 强制 AI 标识）。

## 与别的线
- **创作线**：`novel-author`(写小说) / `song`(写歌)。**生产线**：`novel2drama`(制漫剧) / **`mv`(制MV)**。写小说→制漫剧、**写歌→制MV**。
- 各线**互不依赖**（自包含）；换脸是**公共** `video-faceswap`。

## 持续改进
工艺/翻车 → 写进对应 mv-* skill 的 `references/`。**新增/改 mv-* skill 后同步更新 `skills/README.md`。**
