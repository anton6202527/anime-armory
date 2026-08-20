# mv-compose 调用规范（mv 系列自包含）

## 基本
```bash
bash <skill>/mv_compose.sh <制MV作品根> [16:9|9:16|1:1]
# 例：横屏 MV
bash <skill>/mv_compose.sh "创作区/制MV/我的歌" 16:9
# 抖音竖屏
bash <skill>/mv_compose.sh "创作区/制MV/我的歌" 9:16
# 临时救场：只写 预览/fallback_preview.mp4，不构成正式交付
bash <skill>/mv_compose.sh "创作区/制MV/我的歌" 16:9 --allow-fallback
```

## 输入约定（作品根 = `创作区/制MV/<曲名>/`）
- timeline：`<根>/分镜/timeline_manifest.json`（必需；mv-plan 产、mv-video 挑版后更新；显式 `--allow-fallback` 除外）
- clips：`<根>/出视频/视频/*.mp4`（mv-video 产；显式 `--allow-fallback` 时才按目录顺序兜底）
- 歌轨：`<根>/歌/song.*`（最终成品歌，**必需**，支持 wav/mp3/m4a/flac，整首歌作主音轨）
- beatgrid：`<根>/节拍/beatgrid.json`（mv-beat 产，默认必需；显式 fallback 时仅提示缺失）
- 字幕：`<根>/字幕/karaoke.ass` 或 `lyrics.lrc`（mv-lyric-sync 产，可选）

## Clip 顺序
1. 优先读取 `分镜/timeline_manifest.json` 的 `clips[].video_path`，按 manifest 顺序拼接。
2. timeline 中某个 `video_path` 缺失时会提示缺料并阻断；显式 `--allow-fallback` 才退回文件名顺序，且只写预览，不写正式母版/成片、进度、QC 或 provenance。
3. 外部/网页生成的视频先用 `mv-video/scripts/video_jobs.py --register` 登记，再用 `--select` 挑版；`--select` 会复制到 `出视频/视频/Clip_XXX.mp4` 并同步 timeline。

## 字幕降级链（全在本 skill 内，不借外部 skill）
1. `karaoke.ass` + ffmpeg 带 **libass** → `subtitles=` 逐字高亮烧录（最佳）。
2. 无 libass，但有 `.ass`/`.lrc` → 本 skill `render_lyrics.py`（Pillow 渲染逐行 PNG → ffmpeg overlay，按 enable=between 计时）。
3. 无任何字幕文件 → 纯歌 + 画面。

> 查 libass：`ffmpeg -hide_banner -filters | grep ' subtitles '`。本机 Homebrew ffmpeg 常无。

## 时长与重定时

- 正式模式比对 `画面总时长` vs `歌时长`：差值大于 `max(100ms, 2帧)` 直接拒产。
- 默认逐镜 `trim_hold`：长素材裁切、短素材尾帧停稳；只在 timeline 逐镜显式 `retime` 时变速。
- 通过合同后把最终画面精确 hold 到歌曲尾；不使用 `-shortest` 截掉母带尾音。
- 正解仍是上游对齐：mv-plan/mv-video 按已签收 beatgrid 和 picture lock 生成/挑选镜头，compose 不替剪辑师重新发明节奏。

内部画幅统一、裁切/尾帧 hold 和拼接使用 ProRes 422 HQ/10-bit 临时中间件，避免在母版前先压一代 H.264；每次运行用 `mktemp` 在作品根建立唯一 `.mvwork.*` 临时目录，并由退出 trap 精确清理，避免覆盖并发任务或递归误删固定目录。

`歌曲输入时序=后配歌曲` 时，compose 只接受最终成品歌后的正式 timeline；rough 视觉蓝图阶段不合成。

## 依赖（仅通用工具）
- ffmpeg（必需）。卡拉OK逐字烧录需 libass 编译版。
- Pillow（无 libass 时 `render_lyrics.py` 用）。

## 进度回写
正式母版、交付 MP4、逐输入色彩清单与 delivery QC 全部通过后，`completion.py` 才回写 `_进度.md` 的「合成成片」行。之后按独立阶段依次生成 AI 使用披露与 provenance；它们各有自己的完成收据，不能反向冒充 compose 证据。fallback 预览永不推进任何正式阶段。
