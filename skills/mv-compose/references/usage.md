# mv-compose 调用规范（mv 系列自包含）

## 基本
```bash
bash <skill>/mv_compose.sh <制MV作品根> [16:9|9:16|1:1]
# 例：横屏 MV
bash <skill>/mv_compose.sh "制MV/我的歌" 16:9
# 抖音竖屏
bash <skill>/mv_compose.sh "制MV/我的歌" 9:16
```

## 输入约定（作品根 = `制MV/<曲名>/`）
- timeline：`<根>/分镜/timeline_manifest.json`（推荐；mv-plan 产、mv-video 挑版后更新）
- clips：`<根>/出视频/视频/*.mp4`（mv-video 产；无 timeline 或 timeline 无可用视频时兜底）
- 歌轨：`<根>/歌/song.wav`（mv-song 产，**必需**，整首歌作主音轨）
- beatgrid：`<根>/节拍/beatgrid.json`（mv-beat 产，可选；存在则提示卡点已在上游对齐）
- 字幕：`<根>/字幕/karaoke.ass` 或 `lyrics.lrc`（mv-lyric-sync 产，可选）

## Clip 顺序
1. 优先读取 `分镜/timeline_manifest.json` 的 `clips[].video_path`，按 manifest 顺序拼接。
2. timeline 中某个 `video_path` 缺失时会提示缺料；若 timeline 没有任何可用视频，退回 `出视频/视频/*.mp4` 文件名顺序。
3. 外部/网页生成的视频先用 `mv-video/scripts/video_jobs.py --register` 登记，再用 `--select` 挑版；`--select` 会复制到 `出视频/视频/Clip_XXX.mp4` 并同步 timeline。

## 字幕降级链（全在本 skill 内，不借外部 skill）
1. `karaoke.ass` + ffmpeg 带 **libass** → `subtitles=` 逐字高亮烧录（最佳）。
2. 无 libass，但有 `.ass`/`.lrc` → 本 skill `render_lyrics.py`（Pillow 渲染逐行 PNG → ffmpeg overlay，按 enable=between 计时）。
3. 无任何字幕文件 → 纯歌 + 画面。

> 查 libass：`ffmpeg -hide_banner -filters | grep ' subtitles '`。本机 Homebrew ffmpeg 常无。

## 时长校验
脚本会比对 `画面总时长` vs `歌时长`：相差 >1s 告警。**正解是上游对齐**——mv-plan/mv-video 出 clip 时按 `beatgrid.json` 的段落/鼓点定 clip 时长，而不是在 compose 里硬 trim。

## 依赖（仅通用工具）
- ffmpeg（必需）。卡拉OK逐字烧录需 libass 编译版。
- Pillow（无 libass 时 `render_lyrics.py` 用）。

## 进度回写
完成后回写 `_进度.md`「合成成片」行（`成片_MV.mp4`）。
