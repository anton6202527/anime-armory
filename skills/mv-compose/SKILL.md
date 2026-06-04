---
name: mv-compose
description: MV 合成成片（mv 系列自包含，不依赖 n2d-compose）— 把 制MV/<曲名>/ 的 出视频/视频/ clips + 歌/song.wav(整首歌作主音轨) + (可选)字幕/karaoke.ass 卡拉OK字幕 烧成 成片_MV.mp4。剪辑点对齐 节拍/beatgrid.json，beatgrid/字幕缺失时优雅降级；无 libass 时用 mv 自带 render_lyrics.py。Use when asked to 合成MV / 出MV成片 / 歌轨合成 / 烧卡拉OK字幕 / MV导出. Triggers 合成MV, MV成片, 出MV, 卡拉OK烧录, 歌轨合成, mv-compose.
---

# mv-compose — MV 合成成片（mv 系列·自包含）

把一支 MV 的 `出视频/视频/`(clips) + `歌/song.wav`(整首歌=主音轨) + (可选)`字幕/karaoke.ass`(卡拉OK逐字字幕) 烧成 `成片_MV.mp4`。

> **完全独立**：本 skill 不依赖 n2d-compose 或任何其他 skill；只用通用工具 ffmpeg + 自带 `render_lyrics.py`。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../_偏好约定.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`合成画幅`。

## 核心原则
- **歌是主音轴**：MV 用整首 `歌/song.wav` 作主音轨，clip 自带音效一律静音/极低。不做配音 ducking。
- **卡点驱动剪辑**：剪辑点对齐 `节拍/beatgrid.json`（副歌踩鼓点切、verse 缓）。**clip 时长由 beatgrid 在 mv-video 上游就对齐**（出 clip 时按段落/鼓点定时长）；compose 保留不等长化，并校验总时长≈歌长。
- **卡拉OK字幕**：优先 `.ass` 逐字高亮（需 ffmpeg 带 **libass**）；无 libass → 用 **mv 自带 `render_lyrics.py`**（Pillow 渲染逐行 PNG → overlay），从 `.lrc`/`.ass` 取行级时间。
- **优雅降级**：无 beatgrid → 按 clip 原时长顺接；无字幕 → 纯歌+画面。

## 输入前置（作品根=`制MV/<曲名>/`）
- `出视频/视频/*.mp4`（mv-video 产）
- `歌/song.wav`（mv-song 产；必需）
- `节拍/beatgrid.json`（mv-beat 产；可选，缺则不卡点）
- `字幕/karaoke.ass` 或 `字幕/lyrics.lrc`（mv-lyric-sync 产；可选）

## 工作流
```bash
bash <skill>/mv_compose.sh <制MV作品根> [aspect=16:9|9:16]
# 真歌轨：歌/song.wav 已在；字幕自动探测 .ass→.lrc→无
```
1. 归集 `出视频/视频/` clips → 统一画幅(默认 16:9 1920x1080，竖屏传 9:16)/30fps → 拼接。
2. 校验拼接总时长 vs `歌/song.wav` 时长：差值大则告警（提示回 mv-video 按 beatgrid 调 clip 或补空镜）。
3. 铺 `歌/song.wav` 为唯一主音轨（clip 原声静音）。
4. 字幕：`.ass`(有 libass)烧录 / 无 libass → 调本 skill `render_lyrics.py`(Pillow 逐行 PNG overlay) / 无字幕则跳过。
5. 输出 `成片_MV.mp4`；回写 `_进度.md` 成片行。

## 依赖（仅通用工具，无 skill 依赖）
- **ffmpeg**（必需）。`.ass` 卡拉OK逐字需 libass 编译版（`ffmpeg -filters | grep subtitles`）。
- **Pillow**（无 libass 时的字幕降级，`render_lyrics.py` 用）。

## 详细参考
- 调用 / 画幅 / 字幕降级：`references/usage.md`
- 上游（mv 自家）：`mv-song`(歌) · `mv-beat`(beatgrid) · `mv-lyric-sync`(卡拉OK) · `mv-video`(clips)

## 常见错误
| 错误 | 纠正 |
|---|---|
| 把 clip 拉成等长 | beatgrid 卡点曲线就是 MV 节奏，保留不等长 |
| clip 总时长和歌对不上 | 上游 mv-video 按 beatgrid 调 clip 时长；compose 只校验告警 |
| 拿 .ass 在无 libass 的 ffmpeg 上烧 | 自动降级本 skill `render_lyrics.py`（Pillow overlay） |
| 用配音 ducking 逻辑做 MV | MV 主音轴是整首歌，不 ducking |
| 想复用 n2d-compose 的脚本 | 本系列完全独立，用自带 mv_compose.sh + render_lyrics.py |
