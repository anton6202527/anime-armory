#!/usr/bin/env bash
# MV 合成：出视频/视频 clips + 歌/song.wav(主音轨) + (可选)字幕/karaoke.ass → 成片_MV.mp4
# 用法: bash mv_compose.sh <MV作品根> [16:9|9:16|1:1]
set -e
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
ROOT="$1"; ASPECT="${2:-16:9}"
case "$ASPECT" in 16:9) W=1920;H=1080;; 9:16) W=1080;H=1920;; 1:1) W=1080;H=1080;; *) echo "bad aspect"; exit 1;; esac

# clips：兼容 出视频/视频 与 出视频/第1集/视频 两种布局
VID="$ROOT/出视频/视频"; [ -d "$VID" ] || VID="$ROOT/出视频/第1集/视频"
SONG="$ROOT/歌/song.wav"
ASS="$ROOT/字幕/karaoke.ass"
BEAT="$ROOT/节拍/beatgrid.json"
OUT="$ROOT/成片_MV.mp4"
WK="$ROOT/_mvwork"; rm -rf "$WK"; mkdir -p "$WK"

[ -d "$VID" ] || { echo "缺 clips 目录（先 /mv-video，作品根=$ROOT）"; exit 1; }
CLIPS=("$VID"/*.mp4); [ -e "${CLIPS[0]}" ] || { echo "$VID 无 clip"; exit 1; }
[ -f "$SONG" ] || { echo "缺 $SONG（先 /mv-song 出歌）"; exit 1; }

echo "=== [1/4] 统一画幅 ${W}x${H}/30fps + 拼接 ==="
: > "$WK/list.txt"; i=0
for c in "${CLIPS[@]}"; do
  ffmpeg -y -loglevel error -i "$c" \
    -vf "scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:black,fps=30,format=yuv420p" \
    -an -c:v libx264 -preset medium -crf 18 "$WK/n$i.mp4"
  echo "file 'n$i.mp4'" >> "$WK/list.txt"; i=$((i+1))
done
ffmpeg -y -loglevel error -f concat -safe 0 -i "$WK/list.txt" -c copy "$WK/silent.mp4"

VDUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$WK/silent.mp4")
SDUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SONG")
echo "    画面总时长=${VDUR}s  歌时长=${SDUR}s"
python3 - "$VDUR" "$SDUR" <<'PY'
import sys
v,s=float(sys.argv[1]),float(sys.argv[2])
if abs(v-s)>1.0:
    print(f"    ⚠ 画面与歌相差 {abs(v-s):.1f}s —— 回 mv-video 按 beatgrid 调 clip 时长，或在剪辑里 trim/补空镜")
PY
[ -f "$BEAT" ] && echo "    （beatgrid 存在：剪辑点应已在 mv-video 上游对齐鼓点）" || echo "    （无 beatgrid：按 clip 原时长顺接，未卡点）"

echo "=== [2/4] 字幕探测（mv 自包含：libass 优先 → 自带 render_lyrics.py 降级）==="
SUB_VF=""; LRC="$ROOT/字幕/lyrics.lrc"
if [ -f "$ASS" ] && ffmpeg -hide_banner -filters 2>/dev/null | grep -q ' subtitles '; then
  cp "$ASS" "$WK/k.ass"; SUB_VF="-vf subtitles=$WK/k.ass"
  echo "    用 .ass 卡拉OK逐字烧录（libass 可用）"
elif [ -f "$ASS" ] || [ -f "$LRC" ]; then
  SRC="$ASS"; [ -f "$SRC" ] || SRC="$LRC"
  if python3 "$(dirname "$0")/render_lyrics.py" "$SRC" "$WK" "$W" "$H" 2>"$WK/sub.err"; then
    echo "    无 libass → 自带 render_lyrics.py 逐行 PNG overlay（见 $WK/sub_filter.txt）"
    # render_lyrics.py 输出 sub_inputs.txt(每行一个 PNG) + sub_filter.txt(overlay 链)
  else
    echo "    ⚠ render_lyrics.py 失败（缺 Pillow？见 $WK/sub.err），出无字幕版"
  fi
else
  echo "    无 字幕/karaoke.ass|lyrics.lrc，出无字幕版（mv-lyric-sync 生成后重跑可加字幕）"
fi

echo "=== [3/4] 铺歌轨（整首歌=主音轨，画面静音）+ 烧字幕 ==="
COM=(-c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 256k -movflags +faststart)
if [ -n "$SUB_VF" ]; then                       # libass 逐字
  ffmpeg -y -loglevel error -i "$WK/silent.mp4" -i "$SONG" $SUB_VF \
    -map 0:v -map 1:a -shortest "${COM[@]}" "$OUT"
elif [ -f "$WK/sub_filter.txt" ]; then          # 自带 render_lyrics PNG overlay
  PNGS=(); while IFS= read -r p; do [ -n "$p" ] && PNGS+=(-i "$p"); done < "$WK/sub_inputs.txt"
  ffmpeg -y -loglevel error -i "$WK/silent.mp4" -i "$SONG" "${PNGS[@]}" \
    -filter_complex "$(cat "$WK/sub_filter.txt")" -map "[v]" -map 1:a -shortest "${COM[@]}" "$OUT"
else                                            # 无字幕
  ffmpeg -y -loglevel error -i "$WK/silent.mp4" -i "$SONG" \
    -map 0:v -map 1:a -shortest "${COM[@]}" "$OUT"
fi

echo "=== [4/4] 完成: $OUT ==="
ls -la "$OUT"
