#!/usr/bin/env bash
# 拍广告 剪辑包装：拼 clips + 混 VO/音乐床 + 字幕 + 片尾包装 → 成片_主片.mp4
# 自包含（本机 ffmpeg 无 libass，字幕走 render_subs.py 的 PNG overlay）。
# 用法：bash compose.sh <作品根> [输出比例 16:9]
set -euo pipefail

ROOT="${1:?用法: compose.sh <作品根> [比例]}"
ASPECT="${2:-16:9}"
WORK="$ROOT/合成/_work"
OUT="$ROOT/合成/成片_主片.mp4"
CLIP_DIR="$ROOT/出视频/分镜/视频"
VO="$ROOT/配音/vo.wav"
mkdir -p "$WORK" "$ROOT/合成"

command -v ffmpeg >/dev/null || { echo "[err] 需要 ffmpeg"; exit 2; }

# 1) 拼接 clips（按文件名排序；接缝处理见 references/usage.md，默认硬切裸拼）
LIST="$WORK/_concat.txt"; : > "$LIST"
shopt -s nullglob
clips=( "$CLIP_DIR"/*.mp4 )
[ ${#clips[@]} -gt 0 ] || { echo "[err] $CLIP_DIR 没有 clip"; exit 2; }
for c in "${clips[@]}"; do echo "file '$c'" >> "$LIST"; done
VIDEO="$WORK/_video.mp4"
ffmpeg -y -f concat -safe 0 -i "$LIST" -c copy "$VIDEO" 2>/dev/null \
  || ffmpeg -y -f concat -safe 0 -i "$LIST" -c:v libx264 -pix_fmt yuv420p "$VIDEO"

# 2) 片尾 end card（若已生成 endcard.png，追加 2.5s）
ENDCARD="$WORK/endcard.png"
if [ -f "$ENDCARD" ]; then
  ffmpeg -y -loop 1 -t 2.5 -i "$ENDCARD" -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" \
    -c:v libx264 -pix_fmt yuv420p "$WORK/_endcard.mp4"
  echo "file '$VIDEO'" > "$WORK/_full.txt"
  echo "file '$WORK/_endcard.mp4'" >> "$WORK/_full.txt"
  ffmpeg -y -f concat -safe 0 -i "$WORK/_full.txt" -c:v libx264 -pix_fmt yuv420p "$WORK/_video_full.mp4"
  VIDEO="$WORK/_video_full.mp4"
fi

# 3) 混音：VO（主）+ 音乐床（duck）。音乐床可选：$ROOT/配音/music.wav
AUDIO_ARGS=(); FILTER=""
if [ -f "$VO" ]; then AUDIO_ARGS+=( -i "$VO" ); fi
MUSIC="$ROOT/配音/music.wav"
if [ -f "$VO" ] && [ -f "$MUSIC" ]; then
  ffmpeg -y -i "$VIDEO" -i "$VO" -i "$MUSIC" \
    -filter_complex "[2:a]volume=0.25[m];[1:a][m]amix=inputs=2:duration=first:dropout_transition=2[a]" \
    -map 0:v -map "[a]" -c:v copy -c:a aac -shortest "$OUT"
elif [ -f "$VO" ]; then
  ffmpeg -y -i "$VIDEO" -i "$VO" -map 0:v -map 1:a -c:v copy -c:a aac -shortest "$OUT"
else
  cp "$VIDEO" "$OUT"
fi

echo "[ok] 成片：$OUT"
echo "下一步：字幕 overlay（render_subs.py）→ 多比例 reframe.py → cutdown.py → 交付规格响度归一"
