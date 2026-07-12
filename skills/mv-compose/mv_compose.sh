#!/usr/bin/env bash
# MV 合成：timeline_manifest 选中 clips + 歌/song.*(主音轨) + (可选)字幕/karaoke.ass → 成片_MV.mp4
# 用法: bash mv_compose.sh <MV作品根> [16:9|9:16|1:1] [--allow-fallback]
set -e
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
[ -n "${1:-}" ] || { echo "用法: bash mv_compose.sh <MV作品根> [16:9|9:16|1:1] [--allow-fallback]"; exit 2; }
ROOT="$1"; ASPECT="${2:-16:9}"; ALLOW_FALLBACK="${MV_COMPOSE_ALLOW_FALLBACK:-0}"
[ "${3:-}" = "--allow-fallback" ] && ALLOW_FALLBACK=1
case "$ASPECT" in 16:9) W=1920;H=1080;; 9:16) W=1080;H=1920;; 1:1) W=1080;H=1080;; *) echo "bad aspect"; exit 1;; esac

# clips：兼容 出视频/视频 与 出视频/第1集/视频 两种布局
VID="$ROOT/出视频/视频"; [ -d "$VID" ] || VID="$ROOT/出视频/第1集/视频"
SONG=""
for ext in wav mp3 m4a flac; do
  [ -f "$ROOT/歌/song.$ext" ] && SONG="$ROOT/歌/song.$ext" && break
done
ASS="$ROOT/字幕/karaoke.ass"
BEAT="$ROOT/节拍/beatgrid.json"
TIMELINE="$ROOT/分镜/timeline_manifest.json"
WK="$ROOT/_mvwork"; rm -rf "$WK"; mkdir -p "$WK"
if [ "$ALLOW_FALLBACK" = "1" ]; then
  OUT="$ROOT/预览/fallback_preview.mp4"
  MASTER="$WK/fallback_preview_master.mov"
  mkdir -p "$ROOT/预览"
  echo "    ⚠ fallback 只产预览，不写成片/母版、不推进进度、不生成正式 provenance"
else
  OUT="$ROOT/成片_MV.mp4"
  MASTER="$ROOT/成片_MV_master.mov"
fi

[ -d "$VID" ] || { echo "缺 clips 目录（先 mv-video，作品根=$ROOT）"; exit 1; }
[ -n "$SONG" ] || { echo "缺 $ROOT/歌/song.*（请先补入最终成品歌）"; exit 1; }
[ -f "$TIMELINE" ] || [ "$ALLOW_FALLBACK" = "1" ] || { echo "缺 $TIMELINE（默认不按目录猜顺序；确认要兜底时传 --allow-fallback）"; exit 1; }

CRAFT_DIR="$(cd "$(dirname "$0")/../mv-craft/scripts" && pwd)"
if [ "$ALLOW_FALLBACK" != "1" ]; then
  python3 "$CRAFT_DIR/export_otio.py" "$ROOT"
  python3 "$CRAFT_DIR/gate.py" "$ROOT" compose
fi

SOURCE_LIST="$WK/source_clips.txt"
if [ -f "$TIMELINE" ]; then
  echo "    读取 timeline：分镜/timeline_manifest.json（按已选 clip 顺序合成）"
  python3 - "$ROOT" "$VID" "$TIMELINE" "$SOURCE_LIST" "$ALLOW_FALLBACK" <<'PY'
import glob
import json
import os
import sys

root, vid, timeline_path, out_path, allow_fallback = sys.argv[1:6]
try:
    data = json.load(open(timeline_path, encoding="utf-8"))
except Exception as exc:
    if allow_fallback == "1":
        print(f"    ⚠ timeline_manifest 解析失败，退回目录顺序：{exc}")
        data = {}
    else:
        raise SystemExit(f"timeline_manifest 解析失败：{exc}")

ordered = []
missing = []
for clip in data.get("clips") or []:
    clip_id = clip.get("clip_id")
    candidates = []
    video_path = clip.get("video_path")
    if video_path:
        candidates.append(os.path.join(root, video_path))
    if clip_id:
        candidates.extend(sorted(glob.glob(os.path.join(vid, f"{clip_id}*.mp4"))))
    path = next((p for p in candidates if os.path.exists(p)), None)
    
    dur = clip.get("duration")
    speed_mode = clip.get("speed_mode", "trim")
    
    if path:
        ordered.append((path, dur, speed_mode))
    elif clip_id or video_path:
        missing.append(clip_id or video_path)

if missing:
    msg = f"timeline 有 {len(missing)} 个 clip 尚无可用视频：{', '.join(missing[:8])}"
    if allow_fallback == "1":
        print(f"    ⚠ {msg}")
    else:
        raise SystemExit(msg)

with open(out_path, "w", encoding="utf-8") as f:
    for path, dur, speed_mode in ordered:
        dur_str = str(dur) if dur is not None else ""
        f.write(f"{path}|{dur_str}|{speed_mode}\n")
PY
fi

if [ ! -s "$SOURCE_LIST" ]; then
  [ "$ALLOW_FALLBACK" = "1" ] || { echo "timeline 没有可用视频，拒绝按目录顺序猜；确认要兜底时传 --allow-fallback"; exit 1; }
  [ -f "$TIMELINE" ] && echo "    timeline 未提供可用视频，退回 $VID 文件名顺序"
  : > "$SOURCE_LIST"
  for c in "$VID"/*.mp4; do
    [ -e "$c" ] && printf '%s||trim\n' "$c" >> "$SOURCE_LIST"
  done
fi
[ -s "$SOURCE_LIST" ] || { echo "$VID 无 clip"; exit 1; }
FPS="${MV_OUTPUT_FPS:-}"
if [ -z "$FPS" ]; then
  FIRST_CLIP=$(awk -F '|' 'NR==1 {print $1}' "$SOURCE_LIST")
  RATE=$(ffprobe -v error -select_streams v:0 -show_entries stream=avg_frame_rate -of csv=p=0 "$FIRST_CLIP" 2>/dev/null || true)
  FPS=$(python3 - "$RATE" <<'PY'
import sys
try:
    a, b = sys.argv[1].split('/')
    value = float(a) / float(b)
    print(round(value, 3) if value > 0 else 24)
except Exception:
    print(24)
PY
)
fi

echo "=== [1/6] 时长裁切/尾帧补齐 + ProRes 422 HQ 统一画幅 ${W}x${H}/${FPS}fps + 拼接 ==="
: > "$WK/list.txt"; i=0
while IFS='|' read -r c dur speed_mode; do
  [ -f "$c" ] || continue
  TRIM_OPT=""
  TIMING_FILTER=""
  
  if [ -n "$dur" ] && [ "$dur" != "None" ]; then
    SRC_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$c" || echo "")
    if [ "$speed_mode" = "warp" ] || [ "$speed_mode" = "retime" ]; then
      if [ -n "$SRC_DUR" ]; then
        FACTOR=$(python3 -c "print(round($dur / $SRC_DUR, 4))" 2>/dev/null || echo "")
        if [ -n "$FACTOR" ]; then
          TIMING_FILTER="setpts=${FACTOR}*PTS,trim=duration=${dur},setpts=PTS-STARTPTS,"
          echo "    显式重定时: $(basename "$c") ($SRC_DUR s -> ${dur}s, ${FACTOR}x)"
        else
          TRIM_OPT="-t $dur"
          echo "    精确裁切: $(basename "$c") -> ${dur}s (重定时计算失败)"
        fi
      else
        TRIM_OPT="-t $dur"
        echo "    精确裁切: $(basename "$c") -> ${dur}s (ffprobe失败)"
      fi
    else
      if [ -n "$SRC_DUR" ]; then
        PAD_DUR=$(python3 -c "print(max(0, round($dur - $SRC_DUR, 4)))" 2>/dev/null || echo "0")
        TIMING_FILTER="tpad=stop_mode=clone:stop_duration=${PAD_DUR},trim=duration=${dur},setpts=PTS-STARTPTS,"
        echo "    保持动作速度，精确裁切/尾帧停稳: $(basename "$c") ($SRC_DUR s -> ${dur}s)"
      else
        TRIM_OPT="-t $dur"
        echo "    精确裁切: $(basename "$c") -> ${dur}s (ffprobe失败)"
      fi
    fi
  fi
  
  ffmpeg -y -loglevel error -i "$c" \
    -vf "${TIMING_FILTER}scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:black,fps=${FPS},format=yuv422p10le" \
    -an $TRIM_OPT -c:v prores_ks -profile:v 3 -pix_fmt yuv422p10le \
    -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv "$WK/n$i.mov"
  echo "file 'n$i.mov'" >> "$WK/list.txt"; i=$((i+1))
done < "$SOURCE_LIST"
[ "$i" -gt 0 ] || { echo "没有可合成的 clip"; exit 1; }
ffmpeg -y -loglevel error -f concat -safe 0 -i "$WK/list.txt" -c copy "$WK/silent.mov"

VDUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$WK/silent.mov")
SDUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SONG")
echo "    画面总时长=${VDUR}s  歌时长=${SDUR}s"
if ! python3 - "$VDUR" "$SDUR" "$FPS" <<'PY'
import sys
v,s,fps=float(sys.argv[1]),float(sys.argv[2]),float(sys.argv[3])
tolerance=max(0.10, 2.0/max(fps, 1.0))
diff=abs(v-s)
if diff>tolerance:
    print(f"    ❌ 画面与歌相差 {diff:.3f}s（容差 {tolerance:.3f}s / 2 frames）")
    raise SystemExit(1)
PY
then
  if [ "$ALLOW_FALLBACK" != "1" ]; then
    echo "正式合成拒绝截短歌曲或用大段空镜掩盖时长错误；回 mv-video/剪辑时间线修正"
    exit 1
  fi
  echo "    ⚠ fallback 预览继续，但不得当正式成片"
fi
[ -f "$BEAT" ] && echo "    （beatgrid 存在：剪辑点应已在 mv-video 上游对齐鼓点）" || echo "    （无 beatgrid：按 clip 原时长顺接，未卡点）"

# Quantisation at clip/frame boundaries may leave a sub-frame tail even after
# the edit contract passes.  Normalise picture to the exact song duration by
# holding the final frame; never let a shortest-stream mux rule cut the music master.
ffmpeg -y -loglevel error -i "$WK/silent.mov" \
  -vf "tpad=stop_mode=clone:stop_duration=${SDUR},trim=duration=${SDUR},setpts=PTS-STARTPTS" \
  -an -c:v prores_ks -profile:v 3 -pix_fmt yuv422p10le \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv "$WK/silent_exact.mov"
mv "$WK/silent_exact.mov" "$WK/silent.mov"

echo "=== [2/6] 字幕探测（mv 自包含：libass 优先 → 自带 render_lyrics.py 降级）==="
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

echo "=== [3/6] 生成 10-bit ProRes 422 HQ / 48kHz PCM 母版 ==="
MASTER_COM=(-c:v prores_ks -profile:v 3 -pix_fmt yuv422p10le -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv -c:a pcm_s24le -ar 48000)
if [ -n "$SUB_VF" ]; then                       # libass 逐字
  ffmpeg -y -loglevel error -i "$WK/silent.mov" -i "$SONG" $SUB_VF \
    -map 0:v -map 1:a -t "$SDUR" "${MASTER_COM[@]}" "$MASTER"
elif [ -f "$WK/sub_filter.txt" ]; then          # 自带 render_lyrics PNG overlay
  PNGS=(); while IFS= read -r p; do [ -n "$p" ] && PNGS+=(-i "$p"); done < "$WK/sub_inputs.txt"
  ffmpeg -y -loglevel error -i "$WK/silent.mov" -i "$SONG" "${PNGS[@]}" \
    -filter_complex "$(cat "$WK/sub_filter.txt")" -map "[v]" -map 1:a -t "$SDUR" "${MASTER_COM[@]}" "$MASTER"
else                                            # 无字幕
  ffmpeg -y -loglevel error -i "$WK/silent.mov" -i "$SONG" \
    -map 0:v -map 1:a -t "$SDUR" "${MASTER_COM[@]}" "$MASTER"
fi

echo "=== [4/6] 从母版派生 YouTube/通用 SDR MP4 ==="
GOP=$(python3 - "$FPS" <<'PY'
import sys
print(max(1, int(round(float(sys.argv[1]) / 2.0))))
PY
)
ffmpeg -y -loglevel error -i "$MASTER" \
  -vf "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv" \
  -c:v libx264 -profile:v high -level:v 4.2 -preset slow -crf 18 -pix_fmt yuv420p \
  -g "$GOP" -keyint_min "$GOP" -sc_threshold 0 -bf 2 -flags +cgop \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
  -c:a aac -ar 48000 -b:a 320k -movflags +faststart "$OUT"

echo "=== [5/6] 交付 QC + provenance ==="
if [ "$ALLOW_FALLBACK" = "1" ]; then
  echo "=== [6/6] fallback 预览完成: $OUT ==="
  ls -la "$OUT"
  exit 0
fi
python3 "$(dirname "$0")/delivery_qc.py" "$ROOT" "$OUT" --master "$MASTER"
python3 "$CRAFT_DIR/provenance.py" "$ROOT" --final "$OUT" --master "$MASTER"

echo "=== [6/6] 完成: $OUT (master: $MASTER) ==="
python3 "$CRAFT_DIR/progress_set.py" "$ROOT" compose || echo "⚠ _进度.md 回写失败"
ls -la "$MASTER" "$OUT"
