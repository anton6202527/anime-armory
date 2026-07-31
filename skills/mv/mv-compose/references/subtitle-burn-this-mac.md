# 本机字幕烧录实况 — ffmpeg 精简版 + mv_compose 的 Pillow 断点

> 2026-06 实测，烧《仗剑下山》歌词时踩到。给 mv-compose 烧字幕用。

## 本机 ffmpeg 能力（homebrew 精简版）
- **无 libass**：`ffmpeg -filters | grep ' subtitles '` 为空 → `.ass`/`.srt` **烧不了**（subtitles 滤镜不存在）。
- **也无 drawtext**：未编 libfreetype → `drawtext` 滤镜 `No such filter`。文字滤镜全废。
- ✅ 有 `overlay`（核心滤镜）→ 唯一可行路 = 把字幕渲成**透明 PNG** 再 overlay。

## mv_compose.sh 的降级在本机会断
- 脚本第 2 步无 libass 时调 `python3 render_lyrics.py`（Pillow 渲 PNG）。
- **但脚本顶部 `export PATH="/opt/homebrew/bin:..."` 把 homebrew python3(3.14) 排到最前，而它没 Pillow（PEP668 装不上）→ render_lyrics 失败 → 出无字幕版**。
- 修法：用带 Pillow 的 conda env 渲 PNG（如 `conda run -n cosyvoice python ...`），别靠系统 python3。

## 本次可行流程（绕开 mv_compose 的字幕段，直接烧到成片）
1. 词级时间：whisperx 未装时，用 `conda run -n cosyvoice python` 的 **openai-whisper 转写**成品歌（`word_timestamps=True`）拿实唱词+时间；唱腔有错别字 → 按已知 `词/lyrics.md` **校正文字、沿用时间**。
2. Pillow（conda env）渲每行透明 PNG（中文字体用 `/System/Library/Fonts/Supplemental/Songti.ttc` 古风；PingFang.ttc 本机不存在）。
3. overlay 时间窗烧到**已有歌轨的成片**上，音轨直接 `-c:a copy`：
   ```bash
   IN=(); for i in 0..N; do IN+=(-i l$i.png); done   # zsh 数组！不可用裸 $IN(zsh 不词分割)
   ffmpeg -i 成片.mp4 "${IN[@]}" -filter_complex \
     "[0:v][1:v]overlay=0:0:enable='between(t,s0,e0)'[s0];[s0][2:v]overlay=...[v]" \
     -map "[v]" -map 0:a -c:a copy -c:v libx264 -crf 19 -movflags +faststart 出.mp4
   ```
- 脚本化样例见某作品的 `字幕/_build_subs.py`（渲 PNG + 出 `_overlay.filter`）。
- 长久解：`brew install ffmpeg`（完整版带 libass）后可直接 `subtitles=karaoke.ass` 烧逐字卡拉OK。
